import asyncio
import weakref
from typing import (
    cast,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    TypeVar,
    Union,
    Generic,
    Sequence,
    Set,
)

from .queue import ClosableQueue
from ._compat import get_running_loop

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')

TT = Union[T, U, V]


async def mix(streamA: AsyncIterable[T],
              streamB: AsyncIterable[U],
              *streamN: AsyncIterable[V]) -> AsyncIterable[Union[T, U, V]]:
    """Mix two or more async-iterators into one.

    >>> async def generate(seq, timeout):
    ...     for obj in seq:
    ...         yield await asyncio.sleep(timeout, obj)
    >>> stream = mix(
    ...     generate(range(3), 0.5),
    ...     generate('abcd', 0.7),
    ... )
    >>> res = [obj async for obj in stream]
    >>> assert res == [0, 'a', 1, 'b', 2, 'c', 'd']
    """
    obj: Union[T, U, V]
    async for obj in _MixIter(streamA, streamB, *streamN):
        yield obj


class _MixIter(Generic[T, U, V]):

    def __init__(self,
                 streamA: AsyncIterable[T],
                 streamB: AsyncIterable[U],
                 *streamN: AsyncIterable[V]) -> None:
        self._streams = (streamA, streamB) + streamN
        self._tasks: Set[asyncio.Task] = set()
        self._running = 0
        self._done = len(self._streams)
        self._queue: ClosableQueue[TT] = ClosableQueue(
            maxsize=len(self._streams))

    def __aiter__(self) -> AsyncIterator[TT]:
        loop = get_running_loop()
        if self._running <= 0:
            self._running += 1
            stream: AsyncIterable[TT]
            for stream in cast(Sequence[AsyncIterable[TT]], self._streams):
                task = loop.create_task(self._reader(stream))
                task.add_done_callback(self._on_done)
                self._tasks.add(task)
            self._streams = ()
        return _TaskCleaner(self)

    async def _next(self) -> TT:
        obj = await self._queue.get()
        if obj is self._queue.EndOfStream:
            raise StopAsyncIteration
        return obj

    async def _reader(self, stream: AsyncIterable[TT]) -> None:
        async for obj in stream:
            await self._queue.put(obj)

    def _on_done(self, task: asyncio.Task) -> None:
        if task in self._tasks:
            # Probably task was removed from _cleanup
            self._tasks.remove(task)
        self._done -= 1
        if self._done <= 0:
            self._queue.close()
        if not task.cancelled():
            try:
                task.result()
            except Exception:
                pass    # TODO: log exception

    def _cleanup(self) -> None:
        self._running -= 1
        if self._running <= 0:
            while self._tasks:
                task = self._tasks.pop()
                task.cancel()


class _TaskCleaner(AsyncIterable[Union[T, U, V]]):
    def __init__(self, parent: _MixIter[T, U, V]) -> None:
        self._parent = parent
        weakref.finalize(self, parent._cleanup)

    def __aiter__(self) -> AsyncIterator[TT]:
        return self

    async def __anext__(self) -> Awaitable[TT]:
        return await self._parent._next()
