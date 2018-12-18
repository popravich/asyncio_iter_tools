import asyncio
import pytest

from asyncio_iter_tools import mix

if hasattr(asyncio, 'all_tasks'):
    all_tasks = asyncio.all_tasks
else:
    all_tasks = asyncio.Task.all_tasks


async def error_gen():
    yield 0
    raise RuntimeError("Oops")


@pytest.mark.asyncio
async def test_mix_streams(simple_gen):

    gen1 = simple_gen(range(3), .07)
    gen2 = simple_gen('abc', .05)

    it = mix(gen1, gen2)
    aiter = it.__aiter__()
    assert await aiter.__anext__() == 'a'
    assert await aiter.__anext__() == 0
    assert await aiter.__anext__() == 'b'
    assert await aiter.__anext__() == 1
    assert await aiter.__anext__() == 'c'
    assert await aiter.__anext__() == 2
    with pytest.raises(StopAsyncIteration):
        assert await aiter.__anext__() is None

    aiter = it.__aiter__()
    with pytest.raises(StopAsyncIteration):
        assert await aiter.__anext__() is None


@pytest.mark.asyncio
async def test_mix_streams2(simple_gen):
    gen1 = simple_gen(range(3), 0.07)
    gen2 = simple_gen('abc', 0.05)

    res = [obj async for obj in mix(gen1, gen2)]
    assert res == ['a', 0, 'b', 1, 'c', 2]


@pytest.mark.asyncio
async def test_stop(simple_gen):
    gen1 = simple_gen('abc', 0.1)
    gen2 = error_gen()

    it = mix(gen1, gen2)
    aiter = it.__aiter__()
    assert await aiter.__anext__() == 0
    assert await aiter.__anext__() == 'a'
    assert await aiter.__anext__() == 'b'
    assert await aiter.__anext__() == 'c'
    with pytest.raises(StopAsyncIteration):
        assert await aiter.__anext__() is None


@pytest.mark.asyncio
async def test_break(simple_gen):
    gen1 = simple_gen('abc', 0.1)
    gen2 = error_gen()

    it = mix(gen1, gen2)
    async for _ in it:  # noqa
        break
    res = [obj async for obj in it]
    assert res == ['a', 'b', 'c']


@pytest.mark.asyncio
async def test_many_streams(simple_gen):
    gen1 = simple_gen('abc', 0)
    gen2 = simple_gen([1, 2, 3], 0)
    gen3 = simple_gen('!@#', 0)

    res = [obj async for obj in mix(gen1, gen2, gen3)]
    assert res == ['a', 1, '!', 'b', 2, '@', 'c', 3, '#']


@pytest.mark.asyncio
async def test_several_consumers(simple_gen):
    gen1 = simple_gen('abc', 0.05)
    gen2 = simple_gen('def', 0.07)

    async def read(it, t):
        res = []
        async for i in it:
            await asyncio.sleep(t)
            res.append(i)
        return res

    it = mix(gen1, gen2)
    t1 = asyncio.ensure_future(read(it, .05))
    t2 = asyncio.ensure_future(read(it, .07))
    await asyncio.wait([t1, t2], return_when=asyncio.ALL_COMPLETED)
    res1 = await t1
    res2 = await t2
    assert (res1, res2) == (['a', 'b', 'c'], ['d', 'e', 'f'])


@pytest.mark.asyncio
async def test_several_consumers__not_shared(simple_gen):
    gen1 = simple_gen('abc', 0.05)
    gen2 = simple_gen('def', 0.07)

    async def read(it, t):
        res = []
        async for i in it:
            res.append(i)
        return res

    it = mix(gen1, gen2)
    t1 = asyncio.ensure_future(read(it, .05))
    t2 = asyncio.ensure_future(read(it, .07))
    await asyncio.wait([t1, t2], return_when=asyncio.ALL_COMPLETED)
    res1 = await t1
    res2 = await t2
    assert (res1, res2) == (['a', 'd', 'b', 'e', 'c', 'f'], [])


@pytest.mark.asyncio
async def test_cleanup(simple_gen):
    gen1 = simple_gen('abc', .05)
    gen2 = simple_gen('def', .07)

    initial = all_tasks()
    async for i in mix(gen1, gen2):  # noqa: F841
        break
    pending = all_tasks() - initial
    assert pending

    # Wait for gen1 to yield value
    await asyncio.sleep(0.05)

    tasks = all_tasks() - initial
    cancelled = {t for t in tasks if t.cancelled()}
    pending = {t for t in tasks if t.done() and not t.cancelled()}
    assert len(cancelled) >= 0
    assert not pending
