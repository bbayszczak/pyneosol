"""Serial transport, behind a narrow interface so the dongle can be tested without hardware."""

from __future__ import annotations

import contextlib
from typing import Protocol, runtime_checkable

import serial

from .exceptions import DongleNotFoundError, TransportError
from .protocol import BAUDRATE, redact_port


@runtime_checkable
class Transport(Protocol):
    """Minimal byte pipe towards the device."""

    def write(self, data: bytes) -> None:
        """Send bytes to the device."""
        ...

    def read_available(self) -> bytes:
        """Return the bytes received so far, possibly empty. Must not block."""
        ...

    def reset_input(self) -> None:
        """Drop anything still buffered, so a reply cannot be mistaken for the next one."""
        ...

    def close(self) -> None:
        """Release the underlying resource."""
        ...


class SerialTransport:
    """:class:`Transport` backed by pyserial."""

    def __init__(self, port: str, baudrate: int = BAUDRATE, timeout: float = 1.0) -> None:
        """Open ``port``.

        Raises:
            DongleNotFoundError: if the port cannot be opened.

        """
        try:
            self._serial = serial.Serial(port, baudrate, timeout=timeout)
        except serial.SerialException as error:
            # Masked here too: an exception message is quoted in bug reports just like a
            # log line, and the path may name the unit.
            raise DongleNotFoundError(f"cannot open {redact_port(port)}: {error}") from error
        self.port = port

    def write(self, data: bytes) -> None:
        """Send bytes and flush, so the command leaves immediately."""
        try:
            self._serial.write(data)
            self._serial.flush()
        except serial.SerialException as error:
            raise TransportError(f"write failed on {redact_port(self.port)}: {error}") from error

    def read_available(self) -> bytes:
        """Return whatever is buffered, without waiting."""
        try:
            waiting = self._serial.in_waiting
            return self._serial.read(waiting) if waiting else b""
        except serial.SerialException as error:
            raise TransportError(f"read failed on {redact_port(self.port)}: {error}") from error

    def reset_input(self) -> None:
        """Discard buffered input. Best effort: flushing must never be fatal."""
        with contextlib.suppress(Exception):
            self._serial.reset_input_buffer()

    def close(self) -> None:
        """Close the serial port. Closing twice stays harmless."""
        with contextlib.suppress(Exception):
            self._serial.close()
