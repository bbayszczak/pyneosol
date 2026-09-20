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

import logging

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

# A library must not configure logging: the application owns the handlers and the levels.
# This only keeps the "no handler could be found" warning away when nothing is configured at
# all, as recommended for libraries. Never add a handler, a level or a formatter here.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "0.4.0"  # x-release-please-version

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
