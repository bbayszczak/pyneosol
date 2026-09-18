"""Driver behaviour, against the fake dongle."""

from __future__ import annotations

import pytest

from pyneosol import Action, Dongle
from pyneosol.exceptions import (
    CommandRejectedError,
    NotADongleError,
    ResponseTimeoutError,
    UnknownChannelError,
    UnknownCommandError,
)

from .fake import CHANNEL_COUNT, FakeDongle, SilentDongle


@pytest.fixture
def fake() -> FakeDongle:
    return FakeDongle()


@pytest.fixture
def dongle(fake: FakeDongle) -> Dongle:
    return Dongle(fake)


def test_ping(dongle):
    assert dongle.ping() is True


def test_info(dongle):
    info = dongle.info()
    assert info.software_version == "Rev10"
    assert info.hardware_version == "0"
    assert info.return_code_active is True


def test_info_repr_hides_the_serial_number(dongle):
    assert "00001234" not in repr(dongle.info())


def test_channels_returns_the_whole_table(dongle):
    channels = dongle.channels()
    assert len(channels) == CHANNEL_COUNT
    assert [channel.index for channel in channels] == list(range(CHANNEL_COUNT))


def test_used_channels_are_the_ones_that_transmitted(dongle):
    assert [channel.index for channel in dongle.used_channels()] == [0, 1]


def test_channel_repr_hides_the_key(dongle):
    channel = dongle.channel(0)
    assert channel.key not in repr(channel)
    assert "***" in repr(channel)


def test_channel_rejects_an_unknown_index(dongle):
    with pytest.raises(UnknownChannelError):
        dongle.channel(999)


def test_transmit_power(dongle):
    assert dongle.transmit_power() == 14


@pytest.mark.parametrize(
    ("method", "action"),
    [
        ("open_shutter", Action.OPEN),
        ("close_shutter", Action.CLOSE),
        ("stop", Action.STOP),
        ("favourite", Action.FAVOURITE),
        ("register", Action.REGISTER),
    ],
)
def test_movement_commands_transmit_the_right_code(dongle, fake, method, action):
    getattr(dongle, method)(2)
    assert fake.sent == [(2, int(action))]


def test_sync_counter_increments_on_every_frame(dongle, fake):
    before = dongle.channel(2).sync
    dongle.close_shutter(2)
    dongle.stop(2)
    assert dongle.channel(2).sync == before + 2
    # Channels that were not addressed must stay untouched.
    assert fake.sync[0] == 0x29


def test_unknown_command_raises_its_own_error(dongle):
    # A bare KO means the firmware does not know the verb at all.
    with pytest.raises(UnknownCommandError):
        dongle.execute("ATI")


def test_rejected_command_is_distinguished_from_an_unknown_one(dongle):
    # A prefixed KO means the verb exists but this form does not.
    with pytest.raises(CommandRejectedError):
        dongle.execute("AT$CW?")


def test_timeout_when_the_device_stays_silent():
    dongle = Dongle(SilentDongle())
    with pytest.raises(ResponseTimeoutError):
        dongle.execute("AT&V", timeout=0.05)


def test_ping_is_false_when_the_device_stays_silent():
    assert Dongle(SilentDongle()).ping() is False


def test_info_refuses_a_device_that_is_not_a_dongle():
    class Impostor(SilentDongle):
        def __init__(self) -> None:
            super().__init__()
            self._buffer = b""

        def write(self, data: bytes) -> None:
            self._buffer = b"\r\nsome other device\r\n\r\nAT&V:OK\r\n"

        def read_available(self) -> bytes:
            buffered, self._buffer = self._buffer, b""
            return buffered

    with pytest.raises(NotADongleError):
        Dongle(Impostor()).info()


def test_context_manager_closes_the_transport(fake):
    with Dongle(fake) as dongle:
        dongle.ping()
    assert fake.closed is True


def test_read_protection_makes_the_table_unavailable():
    dongle = Dongle(FakeDongle(read_protection=True))
    assert dongle.info().read_protection is True
    with pytest.raises(CommandRejectedError):
        dongle.channels()
