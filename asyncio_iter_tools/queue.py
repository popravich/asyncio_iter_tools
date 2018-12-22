import collections
import asyncio
import enum

from typing import (
    Generic,
    Any,
    Union,
    Optional,
    List,
    Deque,
    Dict,
    ContextManager,
    Type,
    TypeVar,
)
from types import TracebackType


T = TypeVar('T')
Key = Any

OptionalEventLoop = Optional[asyncio.AbstractEventLoop]


class EndOfStreamMarker(enum.Enum):
    token = 0


class ClosableQueue(Generic[T]):
    """Closable queue.

    Example:

    >>> from contextlib import closable
    >>>
    >>> queue = ClosableQueue()
    >>>
    >>> async def iterate(queue):
    ...     obj = await queue.get()
    ...     while obj is not queue.EndOfStream:
    ...         yield obj
    ...         obj = await queue.get()
    >>>
    >>> async def produce(queue):
    ...     with open('some-file', 'rt') as f, closable(queue):
    ...         await queue.put(f.readline())
    >>> asyncio.ensure_future(product(queue))
    >>>
    >>> async for obj in iterate(queue):
    ...     print(obj)
    """

    EndOfStream = EndOfStreamMarker.token

    def __init__(self, maxsize: int = 0, *,
                 loop: OptionalEventLoop = None) -> None:
        self._queue: Deque[T] = collections.deque()  # XXX:
        self._maxsize = maxsize
        self._closed = False
        self._event_full = asyncio.Event(loop=loop)
        self._event_empty = asyncio.Event(loop=loop)

    async def put(self, item: T) -> bool:
        """Put an item into queue.

        The method will block until some items are popped from queue if it
        is full.

        Return value indicates whether an item has been put into queue
        (``True``) or dropped because queue is (or has just been) closed
        (``False``).
        """
        if self._closed:
            return False
        while self.full() and not self._closed:
            await self._event_empty.wait()
            # TODO: check when this event may not get cleared
        if self._closed:
            return False
        self._event_empty.clear()
        self._queue.append(item)
        self._event_full.set()
        return True

    async def get(self) -> Union[T, EndOfStreamMarker]:
        """Wait and get an item from queue.

        If queue is closed and there is no more items in queue
        the ``ClosableQueue.EndOfStream`` marker is returned.
        """
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

    def close(self) -> None:
        """Mark queue as closed."""
        self._closed = True
        self._event_empty.set()
        self._event_full.set()

    @property
    def closed(self) -> bool:
        """True if queue is closed."""
        return self._closed

    @property
    def exhausted(self) -> bool:
        """True if queue is empty and closed."""
        return self.closed and self.empty()

    def qsize(self) -> int:
        """Queue size."""
        return len(self._queue)

    @property
    def maxsize(self) -> int:
        """Max size of queue."""
        return self._maxsize

    def empty(self) -> bool:
        """True if queue is empty."""
        return not self._queue

    def full(self) -> bool:
        """
        True if ``maxsize`` is greater then 0 and queue size has reached
        this limit.
        """
        if self._maxsize <= 0:
            return False
        return self.qsize() >= self._maxsize

    def __repr__(self) -> str:
        closed = 'closed' if self._closed else 'open'
        return f'<{type(self).__name__} {closed} size:{len(self._queue)}>'


class MultiConsumerQueue(Generic[T]):
    """Multi-consumer closable queue.

    """

    EndOfStream = EndOfStreamMarker.token

    def __init__(self, buffer_size: int = 1, *,
                 loop: OptionalEventLoop = None) -> None:
        self._maxsize = buffer_size
        self._queue: List[T] = []
        self._offsets: Dict[Key, int] = {}
        self._keys = 0
        self._closed = False
        self._event_full = asyncio.Event(loop=loop)
        self._event_empty = asyncio.Event(loop=loop)

    def register(self, key: Optional[Key] = None) -> Key:
        if key is None:
            key = self._keys
            self._keys += 1
        assert key not in self._offsets, (
            "Key already registered", key, self._offsets)
        self._offsets[key] = 0
        return key

    def unregister(self, key: Key) -> None:
        # TODO: wake up waiters
        self._offsets.pop(key)
        self._shift_offsets()

    def close(self) -> None:
        """Close queue."""
        self._closed = True
        self._event_full.set()
        self._event_empty.set()

    @property
    def closed(self) -> bool:
        """True if queue is closed."""
        return self._closed

    async def put(self, item: T) -> bool:
        """Put an item into queue."""
        if self._closed:
            return False
        while self.full() and not self._closed:
            await self._event_empty.wait()
            self._event_empty.clear()
        if self._closed:
            return False
        self._queue.append(item)
        self._event_full.set()
        return True

    async def get(self, key: Key) -> Union[T, EndOfStreamMarker]:
        """Wait and get an item from queue."""
        while self.empty(key) and not self._closed:
            await self._event_full.wait()
            self._event_full.clear()
        # TODO: assert
        if not self.qsize(key) and self._closed:
            return self.EndOfStream
        idx = self._offsets[key]
        item = self._queue[idx]
        self._offsets[key] += 1
        self._shift_offsets()
        return item

    def _shift_offsets(self) -> None:
        consumed = min(self._offsets.values(), default=0)
        del self._queue[:consumed]
        for key in self._offsets:
            self._offsets[key] -= consumed
        self._event_empty.set()
        if not self._queue:
            self._event_full.clear()

    def full(self) -> bool:
        """True if shared buffer is full."""
        return self.buffer_size() >= self._maxsize

    def buffer_size(self) -> int:
        """Shared buffer size."""
        return len(self._queue)

    def qsize(self, key: Key) -> int:
        """Size of queue."""
        idx = self._offsets[key]
        return len(self._queue) - idx

    def empty(self, key: Key) -> bool:
        """True if queue is empty."""
        idx = self._offsets[key]
        return idx >= self.qsize(key)

    @property
    def buffer_maxsize(self) -> int:
        """Max size of shared buffer."""
        return self._maxsize

    def consumer(self) -> '_Consumer':
        return _Consumer(self)


class _Consumer(Generic[T], ContextManager['_Consumer']):
    def __init__(self, queue: 'MultiConsumerQueue[T]') -> None:
        self._queue = queue
        self._key: Optional[Key] = None

    def __enter__(self) -> '_Consumer':
        self._key = self._queue.register()
        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_value: Optional[BaseException],
                 tb: Optional[TracebackType]) -> Optional[bool]:
        key, self._key = self._key, None
        self._queue.unregister(key)

    async def get(self) -> Union[T, EndOfStreamMarker]:
        return await self._queue.get(self._key)

    def qsize(self) -> int:
        return self._queue.qsize(self._key)

    def empty(self) -> bool:
        return self._queue.empty(self._key)

    def full(self) -> bool:
        # XXX: consumer may have read all its queue and
        #   `empty()` will return True, as well as `full()` will do.
        return self._queue.full()
