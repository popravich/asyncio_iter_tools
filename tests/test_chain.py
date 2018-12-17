import pytest

import asyncio_iter_tools as aiter


@pytest.mark.asyncio
async def test_chain(simple_gen):
    it = aiter.chain(simple_gen('abc'), simple_gen('def'))
    res = [i async for i in it]
    assert res == list('abcdef')


@pytest.mark.asyncio
async def test_chain__error(simple_gen):

    async def error_gen():
        yield 0
        raise RuntimeError("err")

    it = aiter.chain(simple_gen('abc'), error_gen())
    with pytest.raises(RuntimeError):
        assert [i async for i in it] is None

    partial_result = []
    with pytest.raises(RuntimeError):
        async for i in aiter.chain(simple_gen('abc'), error_gen()):
            partial_result.append(i)
    assert partial_result == ['a', 'b', 'c', 0]
