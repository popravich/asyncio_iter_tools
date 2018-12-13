import asyncio
import pytest


@pytest.fixture(scope='session')
def simple_gen():
    return _simple_gen


async def _simple_gen(sequence, delay=0):
    for item in sequence:
        yield await asyncio.sleep(delay, item)
