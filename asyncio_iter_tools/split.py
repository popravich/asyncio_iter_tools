import asyncio
import weakref

from typing import (
    cast,
    AsyncIterable,
    AsyncIterator,
    Generic,
    Optional,
    Tuple,
    TypeVar,
)

from .queue import MultiConsumerQueue, Key
from ._compat import get_running_loop


T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')


def split(stream: AsyncIterable[T], *,
          buffer_size: int = 1
          ) -> Tuple[AsyncIterable[T], AsyncIterable[T]]:
    """Split a stream into two streams both reading same values.

    >>> async def generate(seq, timeout):
    ...     for obj in seq:
    ...         yield await asyncio.sleep(timeout, obj)
    >>> async def collect(stream):
    ...     return [obj async for obj in stream]
    >>> streamA, streamB = split(generate('abcd', 0))

    >>> loop = asyncio.get_running_loop()
    >>> taskA = loop.create_task(read(streamA))
    >>> taskB = loop.create_task(read(streamB))
    >>> await asyncio.wait([taskA, taskB])
    >>> res = await taskA, await taskB
    >>> assert res == (['a', 'b', 'c', 'd'], ['a', 'b', 'c', 'd'])
    """

    split = _StreamSplitter(stream, buffer_size=buffer_size)
    return split, split


class _StreamSplitter(Generic[T]):

    def __init__(self, stream: AsyncIterable[T], buffer_size: int = 1) -> None:
        self._stream = stream
        self._queue: MultiConsumerQueue[T] = MultiConsumerQueue(buffer_size)
        self._done = False
        self._running = 0
        self._task: Optional[asyncio.Task] = None

    def __aiter__(self) -> AsyncIterator[T]:
        loop = get_running_loop()
        if self._running <= 0:
            self._task = loop.create_task(self._reader(self._stream))
            self._task.add_done_callback(self._on_done)
        self._running += 1
        key = self._queue.register()
        return _TaskCleaner(self, key)

    async def _next(self, key: Key) -> T:
        obj = await self._queue.get(key)
        if obj is self._queue.EndOfStream:
            raise StopAsyncIteration
        return cast(T, obj)

    async def _reader(self, stream: AsyncIterable[T]) -> None:
        try:
            async for obj in stream:
                await self._queue.put(obj)
        finally:
            self._done = True
            self._task = None
            self._queue.close()

    def _on_done(self, task: asyncio.Task) -> None:
        if not task.cancelled():
            try:
                task.result()
            except Exception:
                pass    # TODO: log it or something...

    def _cleanup(self, key: Key) -> None:
        self._queue.unregister(key)
        self._running -= 1
        if self._running <= 0 and self._task is not None:
            self._task.cancel()


class _TaskCleaner(Generic[T]):

    def __init__(self, parent: _StreamSplitter[T], key: Key) -> None:
        self._parent = parent
        self._key = key
        weakref.finalize(self, parent._cleanup, key)

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        return await self._parent._next(self._key)
