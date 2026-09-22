"""High level driver for the dongle."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Final

from . import protocol
from .discovery import find_ports
from .exceptions import (
    CommandRejectedError,
    DongleNotFoundError,
    NotADongleError,
    ProtocolError,
    ResponseTimeoutError,
    UnknownChannelError,
    UnknownCommandError,
)
from .models import Action, Channel, DongleInfo
from .transport import SerialTransport, Transport

#: Logs go to the host's handlers, never to ours: an integration such as Home Assistant
#: owns the logging configuration and filters on this very name (``pyneosol.dongle``).
_LOGGER = logging.getLogger(__name__)

#: Enough for a single-line answer.
DEFAULT_TIMEOUT: Final = 3.0

#: ``AT$C?`` returns fifty channels and takes noticeably longer.
TABLE_TIMEOUT: Final = 6.0

#: The device needs a moment after the port opens before it answers.
STARTUP_DELAY: Final = 0.4


class Dongle:
    """Asyncio driver.

    The AT dialogue is strictly sequential — one command in flight at a time — so every
    exchange is serialised by a lock. The class holds no state about the shutters: the device
    cannot report any (it only transmits), so anything resembling a position belongs to a
    higher layer.

    Every method that talks to the device is a coroutine and never blocks the event loop: the
    reply is awaited as its lines arrive, not polled.
    """

    def __init__(self, transport: Transport) -> None:
        """Wrap an already opened ``transport``."""
        self._transport = transport
        # Built outside any loop on purpose: an asyncio.Lock binds to the running loop on
        # first use, not on creation, so a Dongle can be constructed before the loop starts.
        self._lock = asyncio.Lock()

    @classmethod
    async def open(
        cls,
        port: str | None = None,
        *,
        verify: bool = True,
        startup_delay: float = STARTUP_DELAY,
    ) -> Dongle:
        """Open a dongle, discovering the port when none is given.

        The caller owns the returned dongle and must :meth:`close` it; :meth:`connect` does
        that on its own.

        Args:
            port: serial port to use. When omitted, the first port whose USB identifiers
                match is picked.
            verify: check the identification marker before returning. Leave it on unless you
                know what is plugged in: the USB vendor id alone proves nothing.
            startup_delay: pause after opening, before the first command.

        Raises:
            DongleNotFoundError: no matching port, or the port cannot be opened.
            NotADongleError: the device did not identify itself as compatible.

        """
        if port is None:
            ports = await find_ports()
            if not ports:
                raise DongleNotFoundError("no serial port matching the dongle USB identifiers")
            port = ports[0].device

        _LOGGER.debug("opening %s", protocol.redact_port(port))
        dongle = cls(await SerialTransport.open(port))
        if startup_delay > 0:
            await asyncio.sleep(startup_delay)
        if verify:
            try:
                await dongle.info()
            except Exception:
                await dongle.close()
                raise
        return dongle

    @classmethod
    @asynccontextmanager
    async def connect(
        cls,
        port: str | None = None,
        *,
        verify: bool = True,
        startup_delay: float = STARTUP_DELAY,
    ) -> AsyncIterator[Dongle]:
        """Open a dongle for the duration of an ``async with`` block, and close it after.

        Same arguments as :meth:`open`. This exists so that the ergonomic form stays
        ``async with Dongle.connect() as dongle:`` rather than the ``async with await
        Dongle.open()`` that an awaitable context manager would impose.
        """
        dongle = await cls.open(port, verify=verify, startup_delay=startup_delay)
        try:
            yield dongle
        finally:
            await dongle.close()

    # ------------------------------------------------------------------ dialogue

    async def execute(self, command: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
        """Send a raw AT command and return its response lines, terminator excluded.

        Raises:
            UnknownCommandError: the firmware does not know this command (bare ``KO``).
            CommandRejectedError: the firmware knows it but refused it (``<COMMAND>:KO``).
            ResponseTimeoutError: no terminator arrived in time.

        """
        # Masked once, then used everywhere the command is exposed: the trace and the three
        # errors below. The exceptions therefore carry the redacted form in their .command,
        # which still identifies the command without carrying its secret.
        redacted = protocol.redact_command(command)
        async with self._lock:
            _LOGGER.debug("> %s", redacted)
            self._transport.reset_input()
            await self._transport.write(protocol.encode(command))

            started = time.monotonic()
            lines: list[str] = []
            try:
                async with asyncio.timeout(timeout):
                    # Line by line, since every line the device sends ends with CRLF — the
                    # terminator included. Nothing is polled: the loop hands us each line as
                    # it lands, and the deadline covers the whole response, however many
                    # lines it takes.
                    while (terminator := protocol.find_terminator(lines)) is None:
                        raw = await self._transport.readline()
                        lines += protocol.split_lines(raw.decode("utf-8", "replace"))
            except TimeoutError as error:
                raise ResponseTimeoutError(
                    f"no response to {redacted!r} within {timeout}s"
                ) from error

            # Every response the driver receives funnels through here, so masking at this
            # single point is what keeps keys and serial numbers out of the logs for good.
            # The guard skips that pass — fifty lines for AT$C? — when debug logging is off.
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("< %s (%.3fs)", protocol.redact(lines), time.monotonic() - started)
            _, status = terminator
            if status == "KO":
                # A bare KO means the verb itself is unknown, a prefixed one that the command
                # exists but this form or these parameters do not.
                raise (
                    UnknownCommandError(redacted)
                    if terminator[0] is None
                    else CommandRejectedError(redacted)
                )
            return protocol.payload(lines)

    async def ping(self) -> bool:
        """Return whether the device answers ``AT``."""
        try:
            await self.execute("AT", timeout=1.0)
        except (ResponseTimeoutError, CommandRejectedError, UnknownCommandError):
            return False
        return True

    # ------------------------------------------------------------------ reading

    async def info(self) -> DongleInfo:
        """Read identification and active configuration (``AT&V``).

        Raises:
            NotADongleError: the identification marker is missing.

        """
        lines = await self.execute("AT&V")
        if protocol.IDENTIFICATION_MARKER not in lines:
            raise NotADongleError(
                f"device did not report {protocol.IDENTIFICATION_MARKER!r}; "
                "it is probably not a compatible dongle"
            )
        return protocol.parse_info(lines)

    async def channels(self) -> list[Channel]:
        """Read the whole channel table (``AT$C?``)."""
        return protocol.parse_channel_table(await self.execute("AT$C?", timeout=TABLE_TIMEOUT))

    async def channel(self, index: int) -> Channel:
        """Read a single channel.

        Raises:
            UnknownChannelError: no such channel on this device.

        """
        for channel in await self.channels():
            if channel.index == index:
                return channel
        raise UnknownChannelError(f"channel {index} is not exposed by this dongle")

    async def used_channels(self) -> list[Channel]:
        """Return the channels that have already transmitted, i.e. the paired ones."""
        return [channel for channel in await self.channels() if channel.is_used]

    async def transmit_power(self) -> int:
        """Read the transmit power (``AT$CP?``).

        Raises:
            ProtocolError: the response carried no value, or one that is not a number.

        """
        lines = await self.execute("AT$CP?")
        if not lines:
            # Not a timeout: execute() returned, so the terminator did arrive and only the
            # value is missing.
            raise ProtocolError("no value in the response to AT$CP?")
        try:
            return int(lines[0])
        except ValueError as error:
            # Everything this library raises must stay under NeosolError: a caller guarding
            # with `except NeosolError` would never catch a bare ValueError. The offending
            # line goes through redact() first — an exception message is quoted in bug
            # reports just like a log line, and whatever desynchronised the dialogue enough
            # to land here could just as well have put a channel table row in its place.
            raise ProtocolError(
                f"unexpected transmit power {protocol.redact([lines[0]])[0]!r}"
            ) from error

    # ------------------------------------------------------------------ transmitting

    async def send(self, channel: int, action: Action) -> None:
        """Transmit ``action`` on ``channel`` (``AT$SF``).

        Success only means the dongle accepted and transmitted the frame. The device cannot
        tell whether a motor acted on it: the link is one-way.
        """
        await self.execute(f"AT$SF={channel},{int(action)}")

    async def open_shutter(self, channel: int) -> None:
        """Start opening. The motor runs until its end stop, or until :meth:`stop`."""
        await self.send(channel, Action.OPEN)

    async def close_shutter(self, channel: int) -> None:
        """Start closing. The motor runs until its end stop, or until :meth:`stop`."""
        await self.send(channel, Action.CLOSE)

    async def stop(self, channel: int) -> None:
        """Stop the motor where it is."""
        await self.send(channel, Action.STOP)

    async def favourite(self, channel: int) -> None:
        """Send the shutter to its favourite position.

        The position is stored in the motor, and is recorded from the original remote, not
        through the dongle. Calling this on a motor with no favourite set does nothing.
        """
        await self.send(channel, Action.FAVOURITE)

    async def register(self, channel: int) -> None:
        """Start pairing ``channel`` with a motor.

        This opens a window of roughly sixty seconds. Pairing only completes if, during that
        window, the motor is driven through its learning sequence **from its own remote** —
        which is also what selects the shutter, leaving the others untouched. See
        ``docs/SPEC-PROTOCOLE-AT.md`` for the sequence.
        """
        await self.send(channel, Action.REGISTER)

    # ------------------------------------------------------------------ lifecycle

    async def close(self) -> None:
        """Release the serial port."""
        await self._transport.close()

    async def __aenter__(self) -> Dongle:
        """Return self, for use as an async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the port on exit."""
        await self.close()
