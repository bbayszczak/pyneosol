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

#: Label carrying the unit's own serial number in the ``AT&V`` response.
_SERIAL_LABEL: Final = "S/N"

# The two commands whose arguments carry a secret. The driver implements neither — writing an
# identity is out of scope and unvalidated — but ``Dongle.execute()`` takes raw commands, so a
# caller can still form one and it would otherwise reach the logs in clear.
_WRITE_CHANNEL_RE: Final = re.compile(
    r"^AT\$C=\d+,(?P<serial>[^,]*),[^,]*,(?P<key>.*)$", re.IGNORECASE
)
_WRITE_SERIAL_RE: Final = re.compile(r"^AT\$SN=(?P<serial>.*)$", re.IGNORECASE)

# A long run of digits in a port path is the USB serial number the host baked into the device
# node: macOS names it "/dev/cu.usbmodem0000000012341", Linux "/dev/serial/by-id/usb-..._0001".
# Four digits is the threshold that leaves the Linux index alone — "/dev/ttyACM0" identifies
# nothing and is exactly what one needs to read a trace.
_PORT_SERIAL_RE: Final = re.compile(r"\d{4,}")

#: Stands in for every secret in a line meant to be logged, like the models' ``__repr__``.
_MASK: Final = "***"

_INFO_FIELDS: Final = {
    "Hardware Version": "hardware_version",
    "Software Version": "software_version",
    _SERIAL_LABEL: "serial_number",
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


def redact(lines: list[str]) -> list[str]:
    """Return ``lines`` with every secret masked, so a response can safely be logged.

    Two things a response carries must never reach a log file: the KeeLoq keys of the channel
    table, which command the shutters, and the serial numbers identifying the user's own
    hardware — logs routinely end up pasted into bug reports. Everything else is left alone,
    since the channel index, the sync counter and the identification fields are what makes a
    protocol trace worth reading.
    """
    return [_redact_line(line) for line in lines]


def _redact_line(line: str) -> str:
    """Mask the secrets of a single response line, leaving anything else untouched."""
    if (match := _CHANNEL_RE.match(line)) is not None:
        # Masking in place, right to left so the offsets stay valid, keeps the original
        # spacing — including the space before the key, a quirk worth still seeing in a trace.
        for start, end in sorted([match.span("serial"), match.span("key")], reverse=True):
            line = f"{line[:start]}{_MASK}{line[end:]}"
        return line
    label, separator, _ = line.partition(":")
    if separator and label.strip() == _SERIAL_LABEL:
        return f"{label}:{_MASK}"
    return line


def redact_command(command: str) -> str:
    """Return ``command`` with every secret masked, so it can safely be logged.

    The outgoing counterpart of :func:`redact`. Masking only the responses would leave a hole:
    a raw ``AT$C=`` or ``AT$SN=`` carries its secret in the command itself, and a trace is
    worth nothing if it cannot be pasted into a bug report as it stands.
    """
    if (match := _WRITE_CHANNEL_RE.match(command)) is not None:
        # Same rule as the channel table: the index and the sync counter stay readable, the
        # identity does not. Right to left, so the offsets stay valid.
        for start, end in sorted([match.span("serial"), match.span("key")], reverse=True):
            command = f"{command[:start]}{_MASK}{command[end:]}"
        return command
    if (match := _WRITE_SERIAL_RE.match(command)) is not None:
        start, end = match.span("serial")
        return f"{command[:start]}{_MASK}{command[end:]}"
    return command


def redact_port(port: str) -> str:
    """Return a port path safe to log, with the serial number it may carry masked.

    The third direction, next to :func:`redact` and :func:`redact_command`: the device node
    itself names the unit on some hosts. The rest of the path is left alone, so a trace still
    says which kind of port was opened, and how many matched.
    """
    return _PORT_SERIAL_RE.sub(_MASK, port)


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
