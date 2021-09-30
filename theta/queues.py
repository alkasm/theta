import collections
import threading
from typing import Deque, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class QueueTimeout(Exception):
    """Raised when a timeout has expired for a blocking get."""

    pass


class QueueStopped(Exception):
    """Raised when a queue has been flagged to stop."""

    pass


class EvictingQueue(Generic[T]):
    """
    Thread-safe FIFO queue with blocking gets and evicting, non-blocking puts.

    Basic reads are as simple as using `get()` or iterating over the queue.
    Iteration will exhaust once `stop()` is called. Can also be used as a
    buffer with `flush()`.

    .. code-block::

        from theta import EvictingQueue

        q = EvictingQueue(5)
        ...

        first_item = q.get()
        for item in q:
            process(item)

    To break iteration on a timeout between gets, use `iter_timeout()`.

    .. code-block::

        for item in q.iter_timeout(1.5):
            # will end after 1.5 seconds has elapsed without a new value
            process(item)
        cleanup()

    To handle timeouts and stopping separately, manually `get()` in a loop.

    .. code-block::

        while True:
            try:
                item = q.get(timeout=0.1)
                process(item)
            except QueueTimeout:
                handle_timeout()
            except QueueStopped:
                cleanup()
                break

    Use as a buffer by flushing the queue on demand.

    .. code-block::

        # some other thread adding items with `q.put()`
        while True:
            time.sleep(1)
            process_many(q.flush())
    """

    def __init__(self, size: Optional[int] = None):
        """If size is None, the queue is unbounded."""
        self._q: Deque[T] = collections.deque(maxlen=size)
        self._cv: threading.Condition = threading.Condition()
        self._stop_event: threading.Event = threading.Event()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return len(self) == 0

    def flush(self) -> List[T]:
        """Consume and return all values currently in the queue."""
        return list(self.iter_timeout(0))

    def get(self, timeout: Optional[float] = None) -> T:
        """
        Blocking get with an optional timeout, in seconds. Pops the oldest item
        off the queue. Blocks indefinitely if the timeout is None.

        Raises:
            QueueStopped: if the queue has been stopped.
            QueueTimeout: if the timeout expires before an item is available.
        """
        with self._cv:
            unblocked = self._cv.wait_for(self._unblocked, timeout)
            if unblocked:
                if self.stopped():
                    raise QueueStopped
                return self._q.popleft()
            raise QueueTimeout

    def iter_timeout(self, timeout: Optional[float] = None) -> Iterator[T]:
        """
        Iterate over values as they become available in FIFO order. The
        iterator exhausts if the timeout (in seconds) expires before a new
        value is put on the queue, or if the queue is stopped. If the timeout
        is None, this method is equivalent to `__iter__()`.
        """

        while True:
            try:
                yield self.get(timeout=timeout)
            except (QueueStopped, QueueTimeout):
                break

    def peek(self) -> T:
        """Peek at the newest value in the queue, without removing it from the queue.

        Raises:
            IndexError: if the queue is empty.
        """
        return self._q[-1]

    def peekleft(self) -> T:
        """Peek at the oldest value in the queue, without removing it from the queue.

        Raises:
            IndexError: if the queue is empty.
        """
        return self._q[0]

    def put(self, value: T) -> None:
        """
        Put an item on the queue, evicting the oldest item if the queue is
        full. This method is non-blocking.
        """
        with self._cv:
            self._q.append(value)
            self._cv.notify_all()

    def stop(self) -> None:
        """Propogate a QueueStopped exception to all threads blocking on `get()`."""
        with self._cv:
            self._stop_event.set()
            self._cv.notify_all()

    def stopped(self) -> bool:
        """Check if the queue has been stopped."""
        return self._stop_event.is_set()

    def _unblocked(self) -> bool:
        return self.stopped() or not self.empty()

    def __len__(self) -> int:
        return len(self._q)

    def __iter__(self) -> Iterator[T]:
        """
        Iterate over values as they become available. May block for an
        arbitrarily long time. The iterator will be exhausted if the queue is
        stopped.
        """
        while True:
            try:
                yield self.get()
            except QueueStopped:
                break
