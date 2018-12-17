import collections
import asyncio


class ClosableQueue:

    EndOfStream = object()

    def __init__(self, maxsize=0, *, loop=None):
        self._queue = collections.deque()
        self._maxsize = maxsize
        self._closed = False
        self._event_full = asyncio.Event(loop=loop)
        self._event_empty = asyncio.Event(loop=loop)

    async def put(self, item):
        if self._closed:
            return False
        while self.full() and not self._closed:
            await self._event_empty.wait()
        if self._closed:
            return False
        self._event_empty.clear()
        self._queue.append(item)
        self._event_full.set()
        return True

    async def get(self):
        while self.empty() and not self._closed:
            await self._event_full.wait()
        assert self._queue or self._closed, (
            "Unexpected queue state", self._queue, self._closed)
        if not self._queue and self._closed:
            return self.EndOfStream
        item = self._queue.popleft()
        self._event_empty.set()
        if not self._queue:
            self._event_full.clear()
        return item

    def close(self):
        """Mark queue as closed and notify all waiters."""
        self._closed = True
        self._event_empty.set()
        self._event_full.set()

    @property
    def closed(self):
        return self._closed

    @property
    def exhausted(self):
        return self._closed and not self._queue

    def qsize(self):
        return len(self._queue)

    @property
    def maxsize(self):
        return self._maxsize

    def empty(self):
        return not self._queue

    def full(self):
        if self._maxsize <= 0:
            return False
        return self.qsize() >= self._maxsize

    def __repr__(self):
        closed = 'closed' if self._closed else 'open'
        return f'<{type(self).__name__} {closed} size:{len(self._queue)}>'


class MultiConsumerQueue:

    def __init__(self, buffer_size=1):
        self._maxsize = buffer_size
        self._queue = []
        self._offsets = {}
        self._keys = 0
        self._event_full = asyncio.Event()
        self._event_empty = asyncio.Event()

    def register(self, key=None):
        if key is None:
            key = self._keys
            self._keys += 1
        assert key not in self._offsets, (
            "Key already registered", key, self._offsets)
        self._offsets[key] = 0
        return key

    def unregister(self, key):
        # TODO: wake up waiters
        self._offsets.pop(key)
        self._shift_offsets()

    async def put(self, item):
        while self.full():
            await self._event_empty.wait()
            self._event_empty.clear()
        self._queue.append(item)
        self._event_full.set()

    async def get(self, key):
        while self.empty(key):
            await self._event_full.wait()
        idx = self._offsets[key]
        item = self._queue[idx]
        self._offsets[key] += 1
        self._shift_offsets()
        return item

    def _shift_offsets(self):
        consumed = min(self._offsets.values(), default=0)
        del self._queue[:consumed]
        for key in self._offsets:
            self._offsets[key] -= consumed
        self._event_empty.set()
        if not self._queue:
            self._event_full.clear()

    def full(self):
        return self.buffer_size() >= self._maxsize

    def buffer_size(self):
        return len(self._queue)

    def qsize(self, key):
        idx = self._offsets[key]
        return len(self._queue) - idx

    def empty(self, key):
        idx = self._offsets[key]
        return idx >= self.qsize(key)

    @property
    def buffer_maxsize(self):
        return self._maxsize

    def consumer(self):
        return _Consumer(self)


class _Consumer:
    def __init__(self, queue):
        self._queue = queue
        self._key = None

    def __enter__(self):
        self._key = self._queue.register()
        return self

    def __exit__(self, *exc_info):
        key, self._key = self._key, None
        self._queue.unregister(key)

    async def get(self):
        return await self._queue.get(self._key)

    def qsize(self):
        return self._queue.qsize(self._key)

    def empty(self):
        return self._queue.empty(self._key)

    def full(self):
        # XXX: consumer may have read all its queue and
        #   `empty()` will return True, as well as `full()` will do.
        return self._queue.full()
