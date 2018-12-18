import inspect

from .queue import ClosableQueue, MultiConsumerQueue
from .mix import mix
from .split import split


__all__ = [
    'ClosableQueue',
    'MultiConsumerQueue',
    'mix',
    'split',
    'chain',
    'filter',
    'map',
]


async def chain(streamA, streamB, *streamN):
    """Chain two or more async-iterators."""
    for stream in (streamA, streamB) + streamN:
        async for obj in stream:
            yield obj


async def filter(func, stream):
    """Return an async iterator yielding those items of stream for which
    func(item) is true.

    If func is None, return items that are true.
    If func may be either simple callable or coroutine.
    """
    if func is None:
        async for obj in stream:
            if obj:
                yield obj
    else:
        assert callable(func), "Expected callable object"
        if inspect.iscoroutinefunction(func):
            async for obj in stream:
                if await func(obj):
                    yield obj
        else:
            async for obj in stream:
                if func(obj):
                    yield obj


async def map(func, stream):
    """Return async iterator applying func to each value of stream."""
    if not callable(func):
        raise ValueError("Excpected callable object", func)
        if inspect.iscoroutinefunction(func):
            async for obj in stream:
                yield await func(obj)
        else:
            async for obj in stream:
                yield func(obj)
