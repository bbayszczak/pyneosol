"""Encoding and parsing of the AT dialogue.

Pure functions only: nothing here touches a serial port, which keeps the protocol layer
testable without hardware. See ``docs/SPEC-PROTOCOLE-AT.md`` for the observations these rules
are derived from.
"""

from __future__ import annotations

import re
from typing import Final

from .exceptions import ProtocolError
from .models import Channel, DongleInfo

BAUDRATE: Final = 115200
LINE_TERMINATOR: Final = b"\r\n"

#: Marker identifying a compatible dongle in the ``AT&V`` response.
IDENTIFICATION_MARKER: Final = "PFX KEELOQ"

#: Number of channels the dongle exposes.
CHANNEL_COUNT: Final = 50

# Responses end with "<COMMAND>:OK" / "<COMMAND>:KO", or a bare "KO" when the firmware does
# not know the command at all. The command name echoed back is not always the one sent:
# "AT$C?" answers "AT$C:OK" while "AT?" answers "AT?:OK". We therefore match the shape rather
# than an expected name.
_TERMINATOR_RE: Final = re.compile(r"^(?P<command>AT[^\s:]*):(?P<status>OK|KO)$")

# "0,000AAAA1,0029, 00112233445566AA" — note the space before the key, absent elsewhere.
_CHANNEL_RE: Final = re.compile(
    r"^\s*(?P<index>\d+)\s*,\s*(?P<serial>[0-9A-Fa-f]+)\s*,"
    r"\s*(?P<sync>[0-9A-Fa-f]+)\s*,\s*(?P<key>[0-9A-Fa-f]+)\s*$"
)

_INFO_FIELDS: Final = {
    "Hardware Version": "hardware_version",
    "Software Version": "software_version",
    "S/N": "serial_number",
    "Frame Repeat Nb": "frame_repeat",
}


def encode(command: str) -> bytes:
    """Turn a command into the bytes to write on the wire."""
    return command.encode("ascii") + LINE_TERMINATOR


def split_lines(raw: str) -> list[str]:
    """Split a raw response into meaningful lines.

    The device separates every useful line with a blank one, so empty lines carry no meaning
    and are dropped.
    """
    return [line.strip() for line in raw.splitlines() if line.strip()]


def is_terminator(line: str) -> tuple[str | None, str] | None:
    """Return ``(command, status)`` if ``line`` terminates a response, else ``None``.

    ``command`` is ``None`` for a bare ``KO``, which means the firmware did not recognise the
    command — as opposed to recognising it and refusing the form or the parameters.
    """
    if line == "KO":
        return None, "KO"
    if match := _TERMINATOR_RE.match(line):
        return match["command"], match["status"]
    return None


def find_terminator(lines: list[str]) -> tuple[str | None, str] | None:
    """Return the terminator of a complete response, or ``None`` if it has not arrived yet."""
    for line in lines:
        if (terminator := is_terminator(line)) is not None:
            return terminator
    return None


def payload(lines: list[str]) -> list[str]:
    """Return the informative lines of a response, without its terminator."""
    return [line for line in lines if is_terminator(line) is None]


def parse_channel_line(line: str) -> Channel | None:
    """Parse one line of the ``AT$C?`` table, or return ``None`` if it is not one."""
    match = _CHANNEL_RE.match(line)
    if match is None:
        return None
    return Channel(
        index=int(match["index"]),
        serial=match["serial"].upper(),
        sync=int(match["sync"], 16),
        key=match["key"].upper(),
    )


def parse_channel_table(lines: list[str]) -> list[Channel]:
    """Parse the channel table, sorted by index.

    Non-matching lines are ignored: the response also carries its terminator, and possibly
    firmware chatter we do not model.
    """
    channels = [channel for line in lines if (channel := parse_channel_line(line)) is not None]
    return sorted(channels, key=lambda channel: channel.index)


def parse_info(lines: list[str]) -> DongleInfo:
    """Parse the ``AT&V`` response.

    Raises:
        ProtocolError: if the identification marker is absent.

    """
    if IDENTIFICATION_MARKER not in lines:
        raise ProtocolError(f"missing {IDENTIFICATION_MARKER!r} marker in identification response")

    values: dict[str, str] = {}
    flags: dict[str, bool] = {}
    for line in lines:
        label, separator, value = line.partition(":")
        if not separator:
            continue
        label, value = label.strip(), value.strip()
        if (field := _INFO_FIELDS.get(label)) is not None:
            values[field] = value
        elif label == "Return Code Active":
            flags["return_code_active"] = value == "1"
        elif label == "Read Protection Active":
            flags["read_protection"] = value == "1"

    return DongleInfo(
        hardware_version=values.get("hardware_version", ""),
        software_version=values.get("software_version", ""),
        serial_number=values.get("serial_number", ""),
        frame_repeat=values.get("frame_repeat", ""),
        return_code_active=flags.get("return_code_active", True),
        read_protection=flags.get("read_protection", False),
    )
