"""Exceptions raised by pyneosol."""

from __future__ import annotations


class NeosolError(Exception):
    """Base class for every error raised by this library."""


class DongleNotFoundError(NeosolError):
    """No dongle could be located, or the requested port does not exist."""


class TransportError(NeosolError):
    """The underlying serial link failed."""


class NotADongleError(NeosolError):
    """The device answered, but did not identify itself as a compatible dongle.

    The identification marker is the ``PFX KEELOQ`` line returned by ``AT&V``. The USB
    vendor id alone is not conclusive: it belongs to Silicon Labs and is shared by many
    unrelated serial devices.
    """


class ProtocolError(NeosolError):
    """The device answered something the protocol does not describe."""


class ResponseTimeoutError(ProtocolError):
    """No terminating line arrived before the deadline.

    Responses always end with ``<COMMAND>:OK``, ``<COMMAND>:KO`` or a bare ``KO``, so a
    timeout means the device stopped mid-answer or never replied at all.
    """


class CommandRejectedError(ProtocolError):
    """The firmware knows the command but refused this form or these parameters.

    Reported by the device as ``<COMMAND>:KO``.
    """

    def __init__(self, command: str) -> None:
        """Record which command was rejected."""
        self.command = command
        super().__init__(f"command rejected by the dongle: {command}")


class UnknownCommandError(ProtocolError):
    """The firmware does not know this command at all.

    Reported by the device as a bare ``KO``, without the command prefix. The distinction
    from :class:`CommandRejectedError` is what makes it possible to probe which commands a
    given firmware revision supports.
    """

    def __init__(self, command: str) -> None:
        """Record which command was not recognised."""
        self.command = command
        super().__init__(f"command unknown to the dongle: {command}")


class UnknownChannelError(NeosolError):
    """The requested channel index is outside the range the dongle exposes."""
