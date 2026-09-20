"""High level driver for the dongle."""

from __future__ import annotations

import threading
import time
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

#: Enough for a single-line answer.
DEFAULT_TIMEOUT: Final = 3.0

#: ``AT$C?`` returns fifty channels and takes noticeably longer.
TABLE_TIMEOUT: Final = 6.0

#: The device needs a moment after the port opens before it answers.
STARTUP_DELAY: Final = 0.4

_POLL_INTERVAL: Final = 0.01


class Dongle:
    """Synchronous driver.

    The AT dialogue is strictly sequential — one command in flight at a time — so every
    exchange is serialised by a lock. The class holds no state about the shutters: the device
    cannot report any (it only transmits), so anything resembling a position belongs to a
    higher layer.
    """

    def __init__(self, transport: Transport) -> None:
        """Wrap an already opened ``transport``."""
        self._transport = transport
        self._lock = threading.Lock()

    @classmethod
    def open(
        cls,
        port: str | None = None,
        *,
        verify: bool = True,
        startup_delay: float = STARTUP_DELAY,
    ) -> Dongle:
        """Open a dongle, discovering the port when none is given.

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
            ports = find_ports()
            if not ports:
                raise DongleNotFoundError("no serial port matching the dongle USB identifiers")
            port = ports[0].device

        dongle = cls(SerialTransport(port))
        if startup_delay > 0:
            time.sleep(startup_delay)
        if verify:
            try:
                dongle.info()
            except Exception:
                dongle.close()
                raise
        return dongle

    # ------------------------------------------------------------------ dialogue

    def execute(self, command: str, *, timeout: float = DEFAULT_TIMEOUT) -> list[str]:
        """Send a raw AT command and return its response lines, terminator excluded.

        Raises:
            UnknownCommandError: the firmware does not know this command (bare ``KO``).
            CommandRejectedError: the firmware knows it but refused it (``<COMMAND>:KO``).
            ResponseTimeoutError: no terminator arrived in time.

        """
        with self._lock:
            self._transport.reset_input()
            self._transport.write(protocol.encode(command))

            deadline = time.monotonic() + timeout
            raw = ""
            while True:
                if chunk := self._transport.read_available():
                    raw += chunk.decode("utf-8", "replace")
                    lines = protocol.split_lines(raw)
                    if (terminator := protocol.find_terminator(lines)) is not None:
                        _, status = terminator
                        if status == "KO":
                            # A bare KO means the verb itself is unknown, a prefixed one that
                            # the command exists but this form or these parameters do not.
                            raise (
                                UnknownCommandError(command)
                                if terminator[0] is None
                                else CommandRejectedError(command)
                            )
                        return protocol.payload(lines)
                if time.monotonic() >= deadline:
                    raise ResponseTimeoutError(f"no response to {command!r} within {timeout}s")
                time.sleep(_POLL_INTERVAL)

    def ping(self) -> bool:
        """Return whether the device answers ``AT``."""
        try:
            self.execute("AT", timeout=1.0)
        except (ResponseTimeoutError, CommandRejectedError, UnknownCommandError):
            return False
        return True

    # ------------------------------------------------------------------ reading

    def info(self) -> DongleInfo:
        """Read identification and active configuration (``AT&V``).

        Raises:
            NotADongleError: the identification marker is missing.

        """
        lines = self.execute("AT&V")
        if protocol.IDENTIFICATION_MARKER not in lines:
            raise NotADongleError(
                f"device did not report {protocol.IDENTIFICATION_MARKER!r}; "
                "it is probably not a compatible dongle"
            )
        return protocol.parse_info(lines)

    def channels(self) -> list[Channel]:
        """Read the whole channel table (``AT$C?``)."""
        return protocol.parse_channel_table(self.execute("AT$C?", timeout=TABLE_TIMEOUT))

    def channel(self, index: int) -> Channel:
        """Read a single channel.

        Raises:
            UnknownChannelError: no such channel on this device.

        """
        for channel in self.channels():
            if channel.index == index:
                return channel
        raise UnknownChannelError(f"channel {index} is not exposed by this dongle")

    def used_channels(self) -> list[Channel]:
        """Return the channels that have already transmitted, i.e. the paired ones."""
        return [channel for channel in self.channels() if channel.is_used]

    def transmit_power(self) -> int:
        """Read the transmit power (``AT$CP?``).

        Raises:
            ProtocolError: the device terminated its answer without a usable value.

        """
        lines = self.execute("AT$CP?")
        # Both failures below mean the dialogue itself was fine — execute() got its
        # terminator — only the payload is not what the protocol describes. Hence
        # ProtocolError rather than a timeout, and never a bare ValueError: everything this
        # library raises must stay under NeosolError.
        if not lines:
            raise ProtocolError("no value in the response to AT$CP?")
        try:
            return int(lines[0])
        except ValueError as error:
            raise ProtocolError(f"unexpected transmit power {lines[0]!r}") from error

    # ------------------------------------------------------------------ transmitting

    def send(self, channel: int, action: Action) -> None:
        """Transmit ``action`` on ``channel`` (``AT$SF``).

        Success only means the dongle accepted and transmitted the frame. The device cannot
        tell whether a motor acted on it: the link is one-way.
        """
        self.execute(f"AT$SF={channel},{int(action)}")

    def open_shutter(self, channel: int) -> None:
        """Start opening. The motor runs until its end stop, or until :meth:`stop`."""
        self.send(channel, Action.OPEN)

    def close_shutter(self, channel: int) -> None:
        """Start closing. The motor runs until its end stop, or until :meth:`stop`."""
        self.send(channel, Action.CLOSE)

    def stop(self, channel: int) -> None:
        """Stop the motor where it is."""
        self.send(channel, Action.STOP)

    def favourite(self, channel: int) -> None:
        """Send the shutter to its favourite position.

        The position is stored in the motor, and is recorded from the original remote, not
        through the dongle. Calling this on a motor with no favourite set does nothing.
        """
        self.send(channel, Action.FAVOURITE)

    def register(self, channel: int) -> None:
        """Start pairing ``channel`` with a motor.

        This opens a window of roughly sixty seconds. Pairing only completes if, during that
        window, the motor is driven through its learning sequence **from its own remote** —
        which is also what selects the shutter, leaving the others untouched. See
        ``docs/SPEC-PROTOCOLE-AT.md`` for the sequence.
        """
        self.send(channel, Action.REGISTER)

    # ------------------------------------------------------------------ lifecycle

    def close(self) -> None:
        """Release the serial port."""
        self._transport.close()

    def __enter__(self) -> Dongle:
        """Return self, for use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the port on exit."""
        self.close()
