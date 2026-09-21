"""A fake dongle, so the whole driver can be exercised without hardware.

Responses reproduce what a real MAI-DONGLE868-1A returns: the blank line between every useful
line, the ``<COMMAND>:OK`` terminators, the bare ``KO`` for an unknown command, and the sync
counter incrementing on every transmitted frame.

All serial numbers and keys below are made up.
"""

from __future__ import annotations

import asyncio
import re
from typing import NoReturn

CHANNEL_COUNT = 50
FIRST_SERIAL = 0x000AAAA1

# Two channels are pre-used, as on a dongle with two shutters already paired.
INITIAL_SYNC = {0: 0x29, 1: 0x09}

IDENTIFICATION = [
    "PFX KEELOQ",
    "Hardware Version:  0",
    "Software Version: Rev10",
    "S/N: 00001234",
    "ACTIVE CONFIG :",
    "Return Code Active : 1",
    "Frame Repeat Nb : T0=25,T1=15,T2=70,T3=70",
    "Read Protection Active : 0",
]

COMMAND_LIST = [
    "AT",
    "A/",
    "AT?",
    "ATQ<n>",
    "ATZ",
    "AT&V",
    "AT$C=<channel>,<serial number>,<sync>,<key>",
    "AT$P=<code>,<value>",
    "AT$SF=<channel>,<code>",
    "AT$SN=<serialNb>",
    "AT$CW=<mode>",
    "AT$TR=<T0>,<T1>,<T2>,<T3>",
    "AT$CP=<power>",
]

_SEND_FRAME_RE = re.compile(r"^AT\$SF=(\d+),(\d+)$")


def _frame(lines: list[str], terminator: str) -> bytes:
    """Encode a response the way the device does, blank line between each."""
    return "".join(f"\r\n{line}\r\n" for line in [*lines, terminator]).encode()


async def _never() -> NoReturn:
    """Block for good.

    What a real device does between two commands: it says nothing until asked again. Waiting
    on an event nobody sets leaves the driver's asyncio.timeout free to fire.
    """
    await asyncio.Event().wait()
    raise AssertionError("an event nobody sets cannot fire")


class FakeDongle:
    """In-memory stand-in for the serial link.

    Implements the :class:`pyneosol.Transport` interface.
    """

    def __init__(self, *, read_protection: bool = False) -> None:
        """Build a dongle with a factory-provisioned channel table."""
        self.read_protection = read_protection
        self.sync: dict[int, int] = {
            index: INITIAL_SYNC.get(index, 0) for index in range(CHANNEL_COUNT)
        }
        #: Every frame transmitted, as ``(channel, action)`` — what the tests assert on.
        self.sent: list[tuple[int, int]] = []
        self.transmit_power = 14
        self._buffer = b""
        self.closed = False

    # -------------------------------------------------- Transport interface

    async def write(self, data: bytes) -> None:
        """Receive a command and queue its response."""
        command = data.decode().strip()
        self._buffer += self._respond(command)

    async def readline(self) -> bytes:
        """Return the next queued line, or wait for ever once the response is exhausted."""
        index = self._buffer.find(b"\n")
        if index < 0:
            await _never()
        line, self._buffer = self._buffer[: index + 1], self._buffer[index + 1 :]
        return line

    def reset_input(self) -> None:
        """Drop anything queued."""
        self._buffer = b""

    async def close(self) -> None:
        """Mark the link as closed."""
        self.closed = True

    # -------------------------------------------------- behaviour

    def serial_of(self, index: int) -> str:
        """Serial number provisioned on ``index``."""
        return f"{FIRST_SERIAL + index:08X}"

    def key_of(self, index: int) -> str:
        """Fake key provisioned on ``index``, distinct per channel."""
        return f"00112233445566{index:02X}"

    def _channel_table(self) -> list[str]:
        return [
            f"{index},{self.serial_of(index)},{self.sync[index]:04X}, {self.key_of(index)}"
            for index in range(CHANNEL_COUNT)
        ]

    def _respond(self, command: str) -> bytes:
        if command == "AT":
            return _frame([], "AT:OK")

        if command == "AT?":
            return _frame(COMMAND_LIST, "AT?:OK")

        if command == "AT&V":
            lines = list(IDENTIFICATION)
            if self.read_protection:
                lines[-1] = "Read Protection Active : 1"
            return _frame(lines, "AT&V:OK")

        if command == "AT$C?":
            # Note the terminator drops the '?', unlike AT? which keeps it.
            if self.read_protection:
                return _frame([], "AT$C:KO")
            return _frame(self._channel_table(), "AT$C:OK")

        if command == "AT$CP?":
            return _frame([str(self.transmit_power)], "AT$CP:OK")

        if match := _SEND_FRAME_RE.match(command):
            channel, action = int(match[1]), int(match[2])
            if channel not in self.sync:
                return _frame([], "AT$SF:KO")
            self.sync[channel] += 1
            self.sent.append((channel, action))
            return _frame([], "AT$SF:OK")

        # Known verb, unsupported form: prefixed KO. Anything else: bare KO.
        for verb in ("AT$CW", "AT$P", "AT$SN", "AT$TR", "AT$CP", "AT$C", "AT$SF", "AT&V", "ATQ"):
            if command.startswith(verb):
                return _frame([], f"{verb}:KO")
        return _frame([], "KO")


class SilentDongle:
    """A device that never answers, to exercise the timeout path."""

    def __init__(self) -> None:
        """Nothing to set up."""
        self.closed = False

    async def write(self, data: bytes) -> None:
        """Swallow the command."""

    async def readline(self) -> bytes:
        """Never answer."""
        return await _never()

    def reset_input(self) -> None:
        """Nothing buffered."""

    async def close(self) -> None:
        """Mark as closed."""
        self.closed = True
