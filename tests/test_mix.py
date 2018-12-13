import asyncio
import pytest

from asyncio_iter_tools import mix


async def gen(r, t):
    for i in r:
        yield await asyncio.sleep(t, i)


async def error_gen():
    yield 0
    raise RuntimeError("Oops")


async def test_mix_streams():

    gen1 = gen(range(3), .07)
    gen2 = gen('abc', .05)

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


async def test_mix_streams2():
    gen1 = gen(range(3), 0.07)
    gen2 = gen('abc', 0.05)

    res = []
    async for obj in mix(gen1, gen2):
        res.append(obj)
    assert res == ['a', 0, 'b', 1, 'c', 2]


async def test_mix_stream__stop():
    gen1 = gen('abc', 0.1)
    gen2 = error_gen()

    it = mix(gen1, gen2)
    aiter = it.__aiter__()
    assert await aiter.__anext__() == 0
    assert await aiter.__anext__() == 'a'
    assert await aiter.__anext__() == 'b'
    assert await aiter.__anext__() == 'c'
    with pytest.raises(StopAsyncIteration):
        assert await aiter.__anext__() is None


async def test_mix_stream__break():
    gen1 = gen('abc', 0.1)
    gen2 = error_gen()

    it = mix(gen1, gen2)
    async for _ in it:  # noqa
        break
    res = [obj async for obj in it]
    assert res == ['a', 'b', 'c']


async def test_mix_many_streams():
    gen1 = gen('abc', 0)
    gen2 = gen([1, 2, 3], 0)
    gen3 = gen('!@#', 0)

    res = [obj async for obj in mix(gen1, gen2, gen3)]
    assert res == ['a', 1, '!', 'b', 2, '@', 'c', 3, '#']
