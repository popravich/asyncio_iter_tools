import pytest
import asyncio

import asyncio_iter_tools as aiter


@pytest.mark.asyncio
async def test_simple(simple_gen, event_loop):
    gen = simple_gen('abcdef', 0)

    stream1, stream2 = aiter.split(gen)

    async def read(stream):
        return [obj async for obj in stream]
    t1 = event_loop.create_task(read(stream1))
    t2 = event_loop.create_task(read(stream2))

    done, pending = await asyncio.wait([t1, t2])
    assert not pending
    res = await t1, await t2
    assert res == (
        ['a', 'b', 'c', 'd', 'e', 'f'], ['a', 'b', 'c', 'd', 'e', 'f'])
