"""Parsing rules, exercised on the exact shapes the device produces."""

from __future__ import annotations

import pytest

from pyneosol import protocol
from pyneosol.exceptions import ProtocolError


def test_split_lines_drops_the_blank_line_between_each():
    raw = "\r\nPFX KEELOQ\r\n\r\nHardware Version:  0\r\n\r\nAT&V:OK\r\n"
    assert protocol.split_lines(raw) == ["PFX KEELOQ", "Hardware Version:  0", "AT&V:OK"]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("AT&V:OK", ("AT&V", "OK")),
        ("AT$SF:OK", ("AT$SF", "OK")),
        ("AT?:OK", ("AT?", "OK")),  # AT? keeps its question mark
        ("AT$C:OK", ("AT$C", "OK")),  # AT$C? drops it
        ("AT$CW:KO", ("AT$CW", "KO")),
        ("KO", (None, "KO")),  # bare KO: the verb itself is unknown
    ],
)
def test_is_terminator_recognises_both_rejection_forms(line, expected):
    assert protocol.is_terminator(line) == expected


@pytest.mark.parametrize("line", ["PFX KEELOQ", "0,000AAAA1,0029, 00112233445566AA", "14"])
def test_is_terminator_ignores_payload_lines(line):
    assert protocol.is_terminator(line) is None


def test_find_terminator_returns_none_while_the_response_is_incomplete():
    assert protocol.find_terminator(["PFX KEELOQ", "Hardware Version:  0"]) is None


def test_payload_strips_the_terminator():
    assert protocol.payload(["14", "AT$CP:OK"]) == ["14"]


def test_parse_channel_line_handles_the_space_before_the_key():
    channel = protocol.parse_channel_line("2,000AAAA3,0029, 00112233445566CC")
    assert channel is not None
    assert channel.index == 2
    assert channel.serial == "000AAAA3"
    assert channel.sync == 0x29  # hexadecimal, so 41
    assert channel.key == "00112233445566CC"


def test_parse_channel_line_rejects_anything_else():
    assert protocol.parse_channel_line("AT$C:OK") is None
    assert protocol.parse_channel_line("PFX KEELOQ") is None


def test_parse_channel_table_sorts_and_ignores_the_terminator():
    lines = [
        "1,000AAAA2,0009, 00112233445566BB",
        "0,000AAAA1,0029, 00112233445566AA",
        "AT$C:OK",
    ]
    channels = protocol.parse_channel_table(lines)
    assert [channel.index for channel in channels] == [0, 1]


def test_parse_info_reads_identification_and_flags():
    lines = [
        "PFX KEELOQ",
        "Hardware Version:  0",
        "Software Version: Rev10",
        "S/N: 00001234",
        "ACTIVE CONFIG :",
        "Return Code Active : 1",
        "Frame Repeat Nb : T0=25,T1=15,T2=70,T3=70",
        "Read Protection Active : 0",
    ]
    info = protocol.parse_info(lines)
    assert info.hardware_version == "0"
    assert info.software_version == "Rev10"
    assert info.frame_repeat == "T0=25,T1=15,T2=70,T3=70"
    assert info.return_code_active is True
    assert info.read_protection is False


def test_parse_info_requires_the_identification_marker():
    with pytest.raises(ProtocolError):
        protocol.parse_info(["Hardware Version:  0", "Software Version: Rev10"])


def test_encode_appends_the_line_terminator():
    assert protocol.encode("AT&V") == b"AT&V\r\n"


def test_redact_masks_the_key_and_the_serial_of_a_channel_line():
    assert protocol.redact(["2,000AAAA3,0029, 00112233445566CC"]) == ["2,***,0029, ***"]


def test_redact_masks_the_serial_number_of_the_identification():
    assert protocol.redact(["S/N: 00001234"]) == ["S/N:***"]


@pytest.mark.parametrize(
    "line",
    [
        "PFX KEELOQ",
        "Software Version: Rev10",
        "Frame Repeat Nb : T0=25,T1=15,T2=70,T3=70",
        "Read Protection Active : 0",
        "AT$C:OK",
        "14",
    ],
)
def test_redact_leaves_everything_else_readable(line):
    assert protocol.redact([line]) == [line]


def test_redact_command_masks_the_identity_written_by_at_c():
    assert protocol.redact_command("AT$C=0,000AAAA1,0029,00112233445566AA") == "AT$C=0,***,0029,***"


def test_redact_command_masks_the_serial_written_by_at_sn():
    assert protocol.redact_command("AT$SN=00001234") == "AT$SN=***"


@pytest.mark.parametrize(
    "command",
    ["AT", "AT&V", "AT$C?", "AT$CP?", "AT$SF=0,1", "AT$CP=14", "AT$TR=25,15,70,70"],
)
def test_redact_command_leaves_harmless_commands_readable(command):
    # Masking too much would make a trace useless: only the two commands that carry a secret
    # are touched, and AT$C? must not be mistaken for AT$C=.
    assert protocol.redact_command(command) == command


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        # macOS names the node after the USB serial number of the unit.
        ("/dev/cu.usbmodem0000000012341", "/dev/cu.usbmodem***"),
        ("/dev/tty.usbmodem0000000012341", "/dev/tty.usbmodem***"),
        (
            "/dev/serial/by-id/usb-Silicon_Labs_KEELOQ_0000000012341-if00",
            "/dev/serial/by-id/usb-Silicon_Labs_KEELOQ_***-if00",
        ),
        # Side effect of a threshold kept deliberately low: the TCP port of a pyserial URL
        # goes with it. Harmless — it is a development transport, and erring towards masking
        # is the right way round for a serial number that can be as short as four digits.
        ("socket://127.0.0.1:8080", "socket://127.0.0.1:***"),
    ],
)
def test_redact_port_masks_the_serial_number_a_path_carries(port, expected):
    assert protocol.redact_port(port) == expected


@pytest.mark.parametrize("port", ["/dev/ttyACM0", "/dev/ttyUSB12", "COM3"])
def test_redact_port_leaves_a_plain_index_readable(port):
    # An enumeration index names nothing and is exactly what one reads a trace for; only runs
    # long enough to be a serial number are masked.
    assert protocol.redact_port(port) == port
