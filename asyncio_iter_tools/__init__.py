import inspect

from .queue import ClosableQueue
from .mix import mix

__all__ = [
    'ClosableQueue',
    'mix',
    'chain',
    'filter',
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
