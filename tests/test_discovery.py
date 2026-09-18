"""Port discovery, with the USB layer stubbed out."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyneosol import USB_PID, USB_VID, discovery


@dataclass
class StubPort:
    device: str
    vid: int | None
    pid: int | None
    manufacturer: str | None = None
    product: str | None = None


@pytest.fixture
def ports(monkeypatch):
    """Replace the USB enumeration with a controllable list."""
    listed: list[StubPort] = []
    monkeypatch.setattr(discovery.list_ports, "comports", lambda: listed)
    return listed


def test_finds_a_matching_port(ports):
    ports.append(
        StubPort("/dev/ttyACM0", USB_VID, USB_PID, "PROFALUX", "KEELOQ USB Device"),
    )
    found = discovery.find_ports()
    assert [port.device for port in found] == ["/dev/ttyACM0"]
    assert found[0].manufacturer == "PROFALUX"


def test_ignores_other_devices(ports):
    # Same Silicon Labs vendor id, different product: a plain USB-serial adapter.
    ports.append(StubPort("/dev/ttyUSB0", USB_VID, 0xEA60, "Silicon Labs"))
    ports.append(StubPort("/dev/ttyS0", None, None))
    assert discovery.find_ports() == []


def test_returns_every_match(ports):
    ports.append(StubPort("/dev/ttyACM0", USB_VID, USB_PID))
    ports.append(StubPort("/dev/ttyACM1", USB_VID, USB_PID))
    assert len(discovery.find_ports()) == 2
