import pytest

from asyncio_iter_tools import ClosableQueue


@pytest.mark.asyncio
async def test_simple():
    q = ClosableQueue()

    assert await q.put(1) is True
    assert not q.empty()
    assert not q.full()
    assert q.maxsize == 0
    assert q.qsize() == 1
    assert not q.closed
    assert not q.exhausted
    assert repr(q) == '<ClosableQueue open size:1>'

    assert await q.get() == 1
    assert q.empty()
    assert not q.full()
    assert q.qsize() == 0
    assert not q.closed
    assert not q.exhausted
    assert repr(q) == '<ClosableQueue open size:0>'


@pytest.mark.asyncio
async def test_close_queue_on_get(event_loop):
    q = ClosableQueue()
    assert q.empty()

    event_loop.call_soon(q.close)
    assert await q.get() is q.EndOfStream
    assert q.empty()
    assert q.closed
    assert await q.get() is q.EndOfStream
    assert q.exhausted
    assert repr(q) == '<ClosableQueue closed size:0>'


@pytest.mark.asyncio
async def test_close_queue_on_put(event_loop):
    q = ClosableQueue(maxsize=1)
    assert q.empty()
    assert not q.full()
    assert await q.put(1) is True
    assert q.full()
    assert q.qsize() == 1

    event_loop.call_soon(q.close)
    assert await q.put(2) is False
    assert not q.empty()
    assert q.full()
    assert q.qsize() == 1
    assert q.closed
    assert await q.put(3) is False


@pytest.mark.asyncio
async def test_put_and_close():
    q = ClosableQueue()
    await q.put(1)
    await q.put(2)
    q.close()

    assert q.qsize() == 2
    assert not q.empty()
    assert q.closed
    assert await q.get() == 1
    assert await q.get() == 2
    assert await q.get() is q.EndOfStream
