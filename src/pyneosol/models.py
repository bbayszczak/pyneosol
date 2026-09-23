"""Value objects describing a dongle and its channels."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Action(IntEnum):
    """Action codes accepted by ``AT$SF=<channel>,<code>``.

    Only the codes validated on real hardware are exposed. The firmware accepts more
    (unassigned codes) but they are deliberately left out: probing the unassigned range risks
    altering the motor end-stop settings.
    """

    OPEN = 0
    CLOSE = 1
    STOP = 2
    FAVOURITE = 4
    REGISTER = 11
    UNREGISTER = 14


@dataclass(frozen=True, slots=True)
class DongleInfo:
    """Identification and active configuration, as reported by ``AT&V``."""

    hardware_version: str
    software_version: str
    serial_number: str
    frame_repeat: str
    return_code_active: bool
    read_protection: bool

    def __repr__(self) -> str:
        """Hide the serial number, which identifies the user's own unit."""
        return (
            f"DongleInfo(hardware_version={self.hardware_version!r}, "
            f"software_version={self.software_version!r}, serial_number='***')"
        )


@dataclass(frozen=True, slots=True)
class Channel:
    """One entry of the channel table returned by ``AT$C?``.

    The dongle ships with every channel pre-provisioned at the factory: each one already
    carries a serial number and a distinct KeeLoq key. Pairing does not create a key, it
    makes a motor accept one of these existing identities.
    """

    index: int
    serial: str
    sync: int
    key: str

    @property
    def is_used(self) -> bool:
        """Whether this channel has ever transmitted.

        The counter increments on every frame sent, so a non-zero value means the channel has
        been used. It proves a frame was emitted, never that a motor acted on it: a paired
        channel is always used, but a used channel may be unpaired — failed pairing, or
        unregistered since.
        """
        return self.sync != 0

    def __repr__(self) -> str:
        """Mask the key.

        The channel table is the secret that commands the shutters. Logs and exception
        messages routinely end up pasted into bug reports, so the key never appears here.
        """
        return f"Channel(index={self.index}, serial={self.serial!r}, sync={self.sync}, key='***')"
