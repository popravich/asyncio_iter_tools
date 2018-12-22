import inspect

from typing import (
    cast,
    Awaitable,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

from .queue import ClosableQueue, MultiConsumerQueue
from .mix import mix
from .split import split, _StreamSplitter


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

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')

FilterCallback = Optional[Callable[[T], Union[bool, Awaitable[bool]]]]
MapCallback = Callable[[T], Union[U, Awaitable[U]]]


async def chain(streamA: AsyncIterable[T],
                streamB: AsyncIterable[U],
                *streams: AsyncIterable[T]) -> AsyncIterable[Union[T, U, V]]:
    """Chain two or more async-iterators."""
    obj: Union[T, U, V]
    async for obj in streamA:
        yield obj
    async for obj in streamB:
        yield obj
    for stream in streams:
        async for obj in stream:
            yield obj


async def filter(func: FilterCallback,
                 stream: AsyncIterable[T]) -> AsyncIterable[T]:
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
            func = cast(Callable[[T], Awaitable[bool]], func)
            async for obj in stream:
                if await func(obj):
                    yield obj
        else:
            func = cast(Callable[[T], bool], func)
            async for obj in stream:
                if func(obj):
                    yield obj


async def map(func: MapCallback, stream: AsyncIterable[T]) -> AsyncIterable[U]:
    """Return async iterator applying func to each value of stream."""
    if not callable(func):
        raise ValueError("Excpected callable object", func)
    if inspect.iscoroutinefunction(func):
        func = cast(Callable[[T], Awaitable[U]], func)
        async for obj in stream:
            yield await func(obj)
    else:
        func = cast(Callable[[T], U], func)
        async for obj in stream:
            yield cast(U, func(obj))


async def collect(stream: AsyncIterable[T]) -> List[T]:
    return [obj async for obj in stream]


class Iterator(Generic[T]):
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

    def __init__(self, stream: AsyncIterable[T]) -> None:
        self._stream = stream

    async def __aiter__(self) -> AsyncIterator[T]:
        async for obj in self._stream:
            yield obj

    def chain(self,
              streamB: AsyncIterable[U],
              *streamN: AsyncIterable[V]) -> 'Iterator[Union[T, U, V]]':
        return type(self)(chain(self, streamB, *streamN))

    def filter(self, func: FilterCallback) -> 'Iterator[T]':
        return type(self)(filter(func, self))

    def map(self, func: MapCallback) -> 'Iterator[U]':
        return type(self)(map(func, self))

    def mix(self,
            streamB: AsyncIterable[U],
            *streamN: AsyncIterable[V]) -> 'Iterator[Union[T, U, V]]':
        return type(self)(mix(self, streamB, *streamN))

    def split(self, *, buffer_size: int = 1) -> 'Iterator[T]':
        if not isinstance(self._stream, _StreamSplitter):
            self._stream, copy = split(self._stream, buffer_size=buffer_size)
        return type(self)(copy)
