import inspect

from .queue import ClosableQueue, MultiConsumerQueue
from .mix import mix
from .split import split


__all__ = [
    'ClosableQueue',
    'MultiConsumerQueue',
    'Iterator',
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


class Iterator:
    """An async iterator builder.

    Example:
    >>> async def simple_stream(seq, delay):
    ...     for obj in seq:
    ...         yield await asyncio.sleep(delay, obj)
    >>> it = Iterator(simple_stream('abc123', 0.01))
    >>> it.map(str.upper)
    >>> num = it.split()
    >>> it.filter(str.isalpha)
    >>> num.filter(str.isnumeric).map(int)
    >>> it.chain(num)
    >>> res = [obj async for obj in it]
    >>> assert res == ['A', 'B', 'C', 1, 2, 3]
    """

    def __init__(self, stream):
        self._stream = stream

    async def __aiter__(self):
        async for obj in self._stream:
            yield obj

    def chain(self, streamB, *streamN):
        self._stream = chain(self._stream, streamB, *streamN)
        return self

    def filter(self, func):
        self._stream = filter(func, self._stream)
        return self

    def map(self, func):
        self._stream = map(func, self._stream)
        return self

    def mix(self, streamB, *streamN):
        self._stream = mix(self._stream, streamB, *streamN)
        return self

    def split(self, *, buffer_size=1):
        self._stream, streamB = split(self._stream)
        return streamB
