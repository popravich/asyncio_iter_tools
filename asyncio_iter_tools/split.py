import asyncio
import weakref

from .queue import MultiConsumerQueue


def split(stream):

    split = _StreamSplitter(stream)

    async def _split_iter():
        async for obj in split:
            yield obj
    return _split_iter(), _split_iter()


class _StreamSplitter:

    _EndOfStream = object()

    def __init__(self, stream, buffer_size=1):
        self._stream = stream
        self._queue = MultiConsumerQueue(buffer_size)
        self._done = False

    def __aiter__(self):
        loop = asyncio.get_running_loop()
        if self._running <= 0:
            self._running += 1
            self._task = loop.create_task(self._reader(self.stream))
            self._task.add_done_callback(self._on_done)
            self._stream = None
        key = self._queue.register()
        it = _TaskCleaner(self, key)
        weakref.finilize(it, self._queue.unregister, key)
        return it

    async def _next(self, key):
        obj = await self._queue.get(key)
        if obj is self._EndOfStream:
            raise StopAsyncIteration
        return obj

    async def _reader(self):
        async for obj in self._stream:
            await self._queue.put(obj)

    def _on_done(self, task):
        self._task = None
        self._done = True


class _TaskCleaner:

    def __init__(self, parent, key):
        self._parent = parent
        self._key = key

    async def __anext__(self):
        return await self._parent._next(self._key)


class _SplitStreams:

    _EndOfStream = object()

    def __init__(self, stream, buffer_size=1):
        self._stream = stream
        self._done = False
        self._exception = None
        self._queue = MultiConsumerQueue(buffer_size)
        task = asyncio.get_running_loop().create_task(self._reader())
        fin = weakref.finalize(self, task.cancel)
        task.add_done_callback(lambda x: fin.detach())

    async def pull_one(self, idx):
        if self._done and self._queue.empty(idx):
            raise StopAsyncIteration
        if self._exception is not None:
            raise self._exception from None
        obj = await self._queue.get(idx)
        if obj is self._EndOfStream:
            if self._exception is not None:
                raise self._exception from None
            raise StopAsyncIteration
        return obj

    def __aiter__(self):
        key = self._queue.register()
        it = _SplitIter(self, key)
        weakref.finalize(it, self._queue.unregister, key)
        return it

    async def _reader(self):
        try:
            async for obj in self._stream:
                await self._queue.put(obj)
        except Exception as err:
            self._exception = err
            raise
        finally:
            self._queue.put_nowait(self._EndOfStream, force=True)
            self._done = True


class _SplitIter:
    def __init__(self, parent, idx):
        self._parent = parent
        self._idx = idx

    async def __anext__(self):
        return await self._parent.pull_one(self._idx)
