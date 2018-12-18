import weakref

from .queue import ClosableQueue
from ._compat import get_running_loop


async def mix(streamA, streamB, *streamN):
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
    async for obj in _MixIter(streamA, streamB, *streamN):
        yield obj


class _MixIter:

    def __init__(self, streamA, streamB, *streamN):
        self._streams = (streamA, streamB) + streamN
        self._tasks = set()
        self._running = 0
        self._done = len(self._streams)
        self._queue = ClosableQueue(maxsize=len(self._streams))

    def __aiter__(self):
        loop = get_running_loop()
        if self._running <= 0:
            self._running += 1
            for stream in self._streams:
                task = loop.create_task(self._reader(stream))
                task.add_done_callback(self._on_done)
                self._tasks.add(task)
            self._streams = ()
        return _TaskCleaner(self)

    async def _next(self):
        obj = await self._queue.get()
        if obj is self._queue.EndOfStream:
            raise StopAsyncIteration
        return obj

    async def _reader(self, stream):
        async for obj in stream:
            await self._queue.put(obj)

    def _on_done(self, task):
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

    def _cleanup(self):
        self._running -= 1
        if self._running <= 0:
            while self._tasks:
                task = self._tasks.pop()
                task.cancel()


class _TaskCleaner:
    def __init__(self, parent):
        self._parent = parent
        weakref.finalize(self, parent._cleanup)

    async def __anext__(self):
        return await self._parent._next()
