"""Locating the dongle among the serial ports of the host."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from serial.tools import list_ports

_LOGGER = logging.getLogger(__name__)

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
    ports = list(list_ports.comports())
    matching = [
        PortInfo(device=port.device, manufacturer=port.manufacturer, product=port.product)
        for port in ports
        if (port.vid, port.pid) == (USB_VID, USB_PID)
    ]
    # What one needs when discovery comes up empty: whether any port was enumerated at all,
    # and which of them carried the expected identifiers.
    _LOGGER.debug(
        "%d of %d serial ports match %04X:%04X: %s",
        len(matching),
        len(ports),
        USB_VID,
        USB_PID,
        [port.device for port in matching],
    )
    return matching
