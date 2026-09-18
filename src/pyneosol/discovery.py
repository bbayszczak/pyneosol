"""Locating the dongle among the serial ports of the host."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from serial.tools import list_ports

#: USB identifiers reported by the dongle. The vendor id belongs to Silicon Labs and is
#: shared by many unrelated serial adapters, so matching on it is a filter, never a proof:
#: only the ``PFX KEELOQ`` answer to ``AT&V`` confirms the device.
USB_VID: Final = 0x10C4
USB_PID: Final = 0x0003


@dataclass(frozen=True, slots=True)
class PortInfo:
    """A serial port that looks like a dongle."""

    device: str
    manufacturer: str | None = None
    product: str | None = None


def find_ports() -> list[PortInfo]:
    """Return the serial ports whose USB identifiers match the dongle.

    An empty list means none was found; it does not mean none is connected, since a device
    reached through a plain serial adapter carries no USB metadata.
    """
    return [
        PortInfo(device=port.device, manufacturer=port.manufacturer, product=port.product)
        for port in list_ports.comports()
        if (port.vid, port.pid) == (USB_VID, USB_PID)
    ]
