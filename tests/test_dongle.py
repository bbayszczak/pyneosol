"""Driver behaviour, against the fake dongle."""

from __future__ import annotations

import logging

import pytest

from pyneosol import Action, Dongle
from pyneosol import dongle as dongle_module
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


async def test_ping(dongle):
    assert await dongle.ping() is True


async def test_info(dongle):
    info = await dongle.info()
    assert info.software_version == "Rev10"
    assert info.hardware_version == "0"
    assert info.return_code_active is True


async def test_info_repr_hides_the_serial_number(dongle):
    assert "00001234" not in repr(await dongle.info())


async def test_channels_returns_the_whole_table(dongle):
    channels = await dongle.channels()
    assert len(channels) == CHANNEL_COUNT
    assert [channel.index for channel in channels] == list(range(CHANNEL_COUNT))


async def test_used_channels_are_the_ones_that_transmitted(dongle):
    assert [channel.index for channel in await dongle.used_channels()] == [0, 1]


async def test_channel_repr_hides_the_key(dongle):
    channel = await dongle.channel(0)
    assert channel.key not in repr(channel)
    assert "***" in repr(channel)


async def test_channel_rejects_an_unknown_index(dongle):
    with pytest.raises(UnknownChannelError):
        await dongle.channel(999)


async def test_transmit_power(dongle):
    assert await dongle.transmit_power() == 14


@pytest.mark.parametrize(
    ("method", "action"),
    [
        ("open_shutter", Action.OPEN),
        ("close_shutter", Action.CLOSE),
        ("stop", Action.STOP),
        ("favourite", Action.FAVOURITE),
        ("register", Action.REGISTER),
        ("unregister", Action.UNREGISTER),
    ],
)
async def test_movement_commands_transmit_the_right_code(dongle, fake, method, action):
    await getattr(dongle, method)(2)
    assert fake.sent == [(2, int(action))]


async def test_sync_counter_increments_on_every_frame(dongle, fake):
    before = (await dongle.channel(2)).sync
    await dongle.close_shutter(2)
    await dongle.stop(2)
    assert (await dongle.channel(2)).sync == before + 2
    # Channels that were not addressed must stay untouched.
    assert fake.sync[0] == 0x29


async def test_unknown_command_raises_its_own_error(dongle):
    # A bare KO means the firmware does not know the verb at all.
    with pytest.raises(UnknownCommandError):
        await dongle.execute("ATI")


async def test_rejected_command_is_distinguished_from_an_unknown_one(dongle):
    # A prefixed KO means the verb exists but this form does not.
    with pytest.raises(CommandRejectedError):
        await dongle.execute("AT$CW?")


async def test_timeout_when_the_device_stays_silent():
    dongle = Dongle(SilentDongle())
    with pytest.raises(ResponseTimeoutError):
        await dongle.execute("AT&V", timeout=0.05)


async def test_ping_is_false_when_the_device_stays_silent():
    assert await Dongle(SilentDongle()).ping() is False


async def test_info_refuses_a_device_that_is_not_a_dongle():
    class Impostor(SilentDongle):
        def __init__(self) -> None:
            super().__init__()
            self._buffer = b""

        async def write(self, data: bytes) -> None:
            self._buffer = b"\r\nsome other device\r\n\r\nAT&V:OK\r\n"

        async def readline(self) -> bytes:
            index = self._buffer.find(b"\n")
            line, self._buffer = self._buffer[: index + 1], self._buffer[index + 1 :]
            return line

    with pytest.raises(NotADongleError):
        await Dongle(Impostor()).info()


async def test_context_manager_closes_the_transport(fake):
    async with Dongle(fake) as dongle:
        await dongle.ping()
    assert fake.closed is True


async def test_connect_opens_and_closes_around_the_block(fake, monkeypatch):
    # The ergonomic entry point: no `async with await`, and the port is released on the way
    # out. The serial layer is stubbed, so no hardware is involved.
    async def fake_open(port: str) -> FakeDongle:
        assert port == "/dev/fake"
        return fake

    monkeypatch.setattr(dongle_module.SerialTransport, "open", fake_open)

    async with Dongle.connect("/dev/fake", startup_delay=0) as dongle:
        assert (await dongle.info()).software_version == "Rev10"
    assert fake.closed is True


async def test_read_protection_makes_the_table_unavailable():
    dongle = Dongle(FakeDongle(read_protection=True))
    assert (await dongle.info()).read_protection is True
    with pytest.raises(CommandRejectedError):
        await dongle.channels()


async def test_debug_logging_never_leaks_a_key_or_a_serial_number(dongle, fake, caplog):
    # A debug trace is exactly what gets pasted into a bug report, so it must stay safe to
    # share whatever the driver was doing. Guards the redaction in Dongle.execute().
    with caplog.at_level(logging.DEBUG, logger="pyneosol"):
        await dongle.info()
        await dongle.channels()

    logged = caplog.text
    assert "AT$C?" in logged  # the dialogue is traced at all
    assert "00001234" not in logged  # the unit's serial number, from AT&V
    for index in range(CHANNEL_COUNT):
        assert fake.key_of(index) not in logged
        assert fake.serial_of(index) not in logged


async def test_a_raw_command_carrying_a_key_leaks_neither_to_the_logs_nor_to_the_error(
    dongle, caplog
):
    # execute() takes raw commands, so the outgoing direction needs the same guarantee as the
    # incoming one: AT$C= carries the key in the command itself.
    key, serial = "00112233445566AA", "000AAAA1"
    with (
        caplog.at_level(logging.DEBUG, logger="pyneosol"),
        pytest.raises(CommandRejectedError) as raised,
    ):
        await dongle.execute(f"AT$C=0,{serial},0029,{key}")

    assert "AT$C" in caplog.text  # the dialogue is still traced
    for secret in (key, serial):
        assert secret not in caplog.text
        assert secret not in str(raised.value)
        assert secret not in raised.value.command
