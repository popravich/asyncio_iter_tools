import pytest

import asyncio_iter_tools as aiter


async def _filter(x):
    return x % 2


@pytest.mark.parametrize('function,input,output', [
    pytest.param(
        None,
        range(3),
        [1, 2],
        id='none-function'),
    pytest.param(
        lambda x: x % 2,
        range(5),
        [1, 3],
        id='even-number-filter'),
    pytest.param(
        _filter,
        range(5),
        [1, 3],
        id='even-number-coro-filter'),
])
@pytest.mark.asyncio
async def test_filter(simple_gen, input, function, output):
    res = [obj async for obj in aiter.filter(function, simple_gen(input))]
    assert res == output


# TODO: test errors
