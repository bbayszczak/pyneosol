"""Serial transport, behind a narrow interface so the dongle can be tested without hardware."""

from __future__ import annotations

import asyncio
import contextlib
from functools import partial
from typing import Protocol, runtime_checkable

import serial_asyncio_fast

from .exceptions import DongleNotFoundError, TransportError
from .protocol import BAUDRATE, redact_port


@runtime_checkable
class Transport(Protocol):
    """Minimal byte pipe towards the device."""

    async def write(self, data: bytes) -> None:
        """Send bytes to the device."""
        ...

    async def readline(self) -> bytes:
        """Return the next line, its terminator included, waiting for as long as it takes.

        Bounding that wait belongs to the caller: the driver wraps it in
        :func:`asyncio.timeout`, since only it knows what the command is worth waiting for.
        """
        ...

    def reset_input(self) -> None:
        """Drop anything still buffered, so a reply cannot be mistaken for the next one."""
        ...

    async def close(self) -> None:
        """Release the underlying resource."""
        ...


class _LineReader(asyncio.Protocol):
    """Collects what the device sends and hands it back one line at a time.

    A hand-written protocol rather than :func:`serial_asyncio_fast.open_serial_connection`
    and its :class:`asyncio.StreamReader`: the driver drops whatever is buffered before every
    command, and a stream reader offers no way to empty itself.
    """

    def __init__(self, port: str) -> None:
        """Start with an empty buffer, on a link that is still up."""
        self._port = port
        self._buffer = bytearray()
        # Set whenever something changed for a waiting reader: bytes arrived, or the link
        # went away. The reader clears it and waits without awaiting in between, so no
        # wake-up can slip through: nothing else runs on the loop during that window.
        self._wakeup = asyncio.Event()
        self._closed = False
        self._error: Exception | None = None

    # ------------------------------------------------------------------ asyncio.Protocol

    def data_received(self, data: bytes) -> None:
        """Buffer the incoming bytes and wake whoever waits for a line."""
        self._buffer += data
        self._wakeup.set()

    def connection_lost(self, exc: Exception | None) -> None:
        """Record that the link is gone; the reader turns it into a :class:`TransportError`."""
        self._closed = True
        self._error = exc
        self._wakeup.set()

    # ------------------------------------------------------------------ reading

    async def readline(self) -> bytes:
        """Return the next complete line, waiting for as long as it takes.

        Raises:
            TransportError: the link went away before the line was complete.

        """
        while (index := self._buffer.find(b"\n")) < 0:
            if self._closed:
                reason = f": {self._error}" if self._error is not None else ""
                raise TransportError(f"serial link on {redact_port(self._port)} went away{reason}")
            self._wakeup.clear()
            await self._wakeup.wait()
        line = bytes(self._buffer[: index + 1])
        del self._buffer[: index + 1]
        return line

    def discard(self) -> None:
        """Forget the buffered bytes."""
        self._buffer.clear()


class SerialTransport:
    """:class:`Transport` backed by pyserial-asyncio-fast."""

    def __init__(
        self, port: str, transport: serial_asyncio_fast.SerialTransport, reader: _LineReader
    ) -> None:
        """Wrap an already connected serial link. Build one with :meth:`open`."""
        self.port = port
        self._transport = transport
        self._reader = reader

    @classmethod
    async def open(cls, port: str, baudrate: int = BAUDRATE) -> SerialTransport:
        """Open ``port``.

        Raises:
            DongleNotFoundError: if the port cannot be opened.

        """
        loop = asyncio.get_running_loop()
        try:
            # pyserial-asyncio-fast opens the port in a worker thread, so the event loop is
            # never held by the syscall; afterwards the loop reads it through a file watcher.
            transport, reader = await serial_asyncio_fast.create_serial_connection(
                loop, partial(_LineReader, port), port, baudrate=baudrate
            )
        except OSError as error:
            # serial.SerialException derives from OSError, like everything the OS layer
            # raises when the device is missing, busy, or not a serial port at all. The path
            # is masked here too: an exception message is quoted in bug reports just like a
            # log line, and it may name the unit.
            raise DongleNotFoundError(f"cannot open {redact_port(port)}: {error}") from error
        return cls(port, transport, reader)

    async def write(self, data: bytes) -> None:
        """Send bytes to the device.

        Raises:
            TransportError: the port is already gone.

        """
        if self._transport.is_closing():
            raise TransportError(f"write failed on {redact_port(self.port)}: the port is closed")
        # No flow control to wait for: an AT command is a few dozen bytes, which the transport
        # hands to the port straight away. A write failure surfaces as a lost connection, and
        # from there as a TransportError on the next read.
        self._transport.write(data)

    async def readline(self) -> bytes:
        """Return the next line sent by the device, its terminator included."""
        return await self._reader.readline()

    def reset_input(self) -> None:
        """Discard buffered input, on both sides of the loop's reader.

        Ours holds what has already been delivered, the driver's what the port received but
        the loop has not read yet. Best effort: flushing must never be fatal.
        """
        self._reader.discard()
        with contextlib.suppress(Exception):
            self._transport.serial.reset_input_buffer()

    async def close(self) -> None:
        """Close the serial port. Closing twice stays harmless."""
        with contextlib.suppress(Exception):
            self._transport.close()
