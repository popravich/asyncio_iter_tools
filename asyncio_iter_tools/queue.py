import collections
import asyncio


class QueueClosed(Exception):
    pass


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
            return  # raise QueueClosed()
        while self.full() and not self._closed:
            await self._event_empty.wait()
        if self._closed:
            return
        self._event_empty.clear()
        self._queue.append(item)
        self._event_full.set()

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
