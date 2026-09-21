"""The line reader behind the serial transport, fed by hand instead of by a port.

It is the only piece of the migration to asyncio with logic of its own: the driver waits for
lines, and this is what turns the bytes the event loop delivers into them.
"""

from __future__ import annotations

import asyncio

import pytest

from pyneosol.exceptions import TransportError
from pyneosol.transport import _LineReader


@pytest.fixture
def reader() -> _LineReader:
    return _LineReader("/dev/fake")


async def test_a_line_split_across_two_chunks_is_reassembled(reader):
    # The device sends CRLF-terminated lines, but the loop delivers whatever the port had.
    reader.data_received(b"\r\nPFX KE")
    reader.data_received(b"ELOQ\r\n\r\nAT&V:OK\r\n")
    assert [await reader.readline() for _ in range(4)] == [
        b"\r\n",
        b"PFX KEELOQ\r\n",
        b"\r\n",
        b"AT&V:OK\r\n",
    ]


async def test_readline_waits_until_the_line_is_complete(reader):
    reader.data_received(b"AT&V")
    pending = asyncio.ensure_future(reader.readline())
    await asyncio.sleep(0)
    assert not pending.done()  # no terminator yet: nothing to hand back

    reader.data_received(b":OK\r\n")
    assert await pending == b"AT&V:OK\r\n"


async def test_discard_drops_a_late_answer(reader):
    # What keeps a reply that arrived after its deadline from being read as the next one.
    reader.data_received(b"AT&V:OK\r\n")
    reader.discard()

    reader.data_received(b"AT:OK\r\n")
    assert await reader.readline() == b"AT:OK\r\n"


async def test_a_lost_link_surfaces_as_a_transport_error(reader):
    reader.connection_lost(OSError("device disconnected"))
    with pytest.raises(TransportError, match="/dev/fake"):
        await reader.readline()


async def test_a_lost_link_wakes_a_waiting_reader(reader):
    pending = asyncio.ensure_future(reader.readline())
    await asyncio.sleep(0)

    reader.connection_lost(None)
    with pytest.raises(TransportError):
        await pending
