import pytest
import asyncio

from asyncio_iter_tools import MultiConsumerQueue


@pytest.mark.asyncio
async def test_simple():
    q = MultiConsumerQueue()
    assert q.buffer_maxsize == 1
    assert q.buffer_size() == 0
    assert not q.full()

    await q.put(1)
    assert q.buffer_size() == 1
    assert q.full()

    key1 = q.register()
    assert key1 is not None
    assert not q.empty(key1)
    assert q.qsize(key1) == 1
    assert await q.get(key1) == 1
    assert q.buffer_size() == 0
    assert not q.full()

    key2 = q.register()
    assert key2 is not None
    assert q.empty(key2)
    assert q.qsize(key2) == 0

    await q.put(2)

    assert await q.get(key2) == 2
    assert q.buffer_size() == 1
    assert q.full()
    assert q.qsize(key2) == 0
    assert q.qsize(key1) == 1
    assert await q.get(key1) == 2
    assert q.buffer_size() == 0
    assert not q.full()
    assert q.qsize(key2) == 0
    assert q.qsize(key1) == 0

    await q.put(3)
    assert await q.get(key1) == 3
    q.unregister(key2)
    assert q.buffer_size() == 0
    assert not q.full()


@pytest.mark.asyncio
async def test_put():
    q = MultiConsumerQueue(1)
    await q.put(1)
    assert q.buffer_size() == q.buffer_maxsize
    assert q.full()

    task = asyncio.ensure_future(q.put(2))
    await asyncio.sleep(0)
    assert not task.done()
    assert q.full()

    key = q.register()
    await asyncio.sleep(0)
    assert not task.done()
    assert q.full()

    assert await q.get(key) == 1
    await asyncio.sleep(0)
    assert task.done()
    assert q.full()
    await task

    task = asyncio.ensure_future(q.put(2))
    await asyncio.sleep(0)
    assert not task.done()
    assert q.full()

    key = q.register()
    await asyncio.sleep(0)
    assert not task.done()
    assert q.full()

    q.unregister(key)
    await asyncio.sleep(0)
    assert not task.done()
    assert q.full()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_get():
    q = MultiConsumerQueue()
    key = q.register()
    task = asyncio.ensure_future(q.get(key))
    await asyncio.sleep(0)
    assert not task.done()
    await q.put(1)
    await asyncio.sleep(0)
    assert task.done()
    assert await task == 1


def test_register_unregister():
    q = MultiConsumerQueue()
    key = q.register()
    assert q.qsize(key) == 0
    with pytest.raises(AssertionError):
        q.register(key)

    q.unregister(key)
    with pytest.raises(KeyError):
        q.qsize(key)
    with pytest.raises(KeyError):
        q.unregister(key)
