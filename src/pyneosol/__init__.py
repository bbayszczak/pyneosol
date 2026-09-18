"""Python driver for 868 MHz roller shutter USB dongles speaking the PFX AT serial protocol.

Compatible with Profalux Neosol roller shutters and the MAI-DONGLE868-1A. Independent project,
not affiliated with any manufacturer — see the README.

Example:
    >>> from pyneosol import Dongle
    >>> with Dongle.open() as dongle:  # doctest: +SKIP
    ...     print(dongle.info().software_version)
    ...     dongle.close_shutter(0)

"""

from __future__ import annotations

from .discovery import USB_PID, USB_VID, PortInfo, find_ports
from .dongle import Dongle
from .exceptions import (
    CommandRejectedError,
    DongleNotFoundError,
    NeosolError,
    NotADongleError,
    ProtocolError,
    ResponseTimeoutError,
    TransportError,
    UnknownChannelError,
    UnknownCommandError,
)
from .models import Action, Channel, DongleInfo
from .transport import SerialTransport, Transport

__version__ = "0.1.0"  # x-release-please-version

__all__ = [
    "USB_PID",
    "USB_VID",
    "Action",
    "Channel",
    "CommandRejectedError",
    "Dongle",
    "DongleInfo",
    "DongleNotFoundError",
    "NeosolError",
    "NotADongleError",
    "PortInfo",
    "ProtocolError",
    "ResponseTimeoutError",
    "SerialTransport",
    "Transport",
    "TransportError",
    "UnknownChannelError",
    "UnknownCommandError",
    "find_ports",
]
