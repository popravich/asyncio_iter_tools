import asyncio

from asyncio_iter_tools import ClosableQueue


async def test_simple():
    q = ClosableQueue()

    await q.put(1)
    assert not q.empty()
    assert not q.full()
    assert q.qsize() == 1
    assert not q.closed

    assert await q.get() == 1
    assert q.empty()
    assert not q.full()
    assert q.qsize() == 0
    assert not q.closed


async def test_close_queue_on_get():
    loop = asyncio.get_running_loop()
    q = ClosableQueue()
    assert q.empty()

    loop.call_soon(q.close)
    assert await q.get() is q.EndOfStream
    assert q.empty()
    assert q.closed
    assert await q.get() is q.EndOfStream


async def test_close_queue_on_put():
    loop = asyncio.get_running_loop()
    q = ClosableQueue(maxsize=1)
    assert q.empty()
    assert not q.full()
    await q.put(1)
    assert q.full()
    assert q.qsize() == 1

    loop.call_soon(q.close)
    assert await q.put(2) is None
    assert not q.empty()
    assert q.full()
    assert q.qsize() == 1
    assert q.closed
    assert await q.put(3) is None


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
