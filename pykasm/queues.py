import collections
import threading
from typing import Generic, Iterable, List, Optional, TypeVar

_T = TypeVar("_T")


class TimeoutError(Exception):
    pass


class QueueStopped(Exception):
    pass


class EvictingQueue(Generic[_T]):
    """Thread-safe FIFO queue with blocking gets and evicting, non-blocking puts.

    Basic reads of this queue with blocking gets is as simple as using `get()` or
    iterating over the queue. Iteration will immediately stop if the queue's `stop()`
    method is called. Can also be used as a buffer with `flush()`.

    .. code-block::

        first_item = q.get()
        for item in q:
            process(item)

    If you want to iterate with timeouts, you can use `iter_timeout()`.

    .. code-block::

        for item in q.iter_timeout(1.5):
            # will end after 1.5 seconds has elapsed without a new value
            process(item)
        cleanup()

    To handle timeouts and stopping separately, you can manually `get()` in a loop.

    .. code-block::

        try:
            while True:
                try:
                    item = q.get(timeout=0.1)
                    process(item)
                except TimeoutError:
                    handle_timeout()
        except QueueStopped:
            cleanup()

    Use as a buffer by flushing the data in the queue on demand.

    .. code-block::

        # some other thread adding items with `q.put()`
        while True:
            time.sleep(1)
            process_many(q.flush())

    """

    q: collections.deque
    cv: threading.Condition
    stop_event: threading.Event

    def __init__(self, size: Optional[int] = None):
        self.q = collections.deque(maxlen=size)
        self.cv = threading.Condition()
        self.stop_event = threading.Event()

    def empty(self) -> bool:
        """Equivalent to `len(q) == 0`"""
        return len(self) == 0

    def flush(self) -> List[_T]:
        """Consume and return all the items currently available in the queue."""
        return list(self.iter_timeout(0))

    def get(self, timeout: Optional[float] = None) -> _T:
        """Blocking get with an optional timeout. Pops the oldest item in the queue.

        Raises a `queue.TimeoutError` if the timeout expires before an item is available.
        Raises a `queue.QueueStopped` if the queue has been stopped.
        """
        with self.cv:
            unblocked = self.cv.wait_for(self._unblocked, timeout)
            if unblocked:
                if self.stopped():
                    raise QueueStopped
                return self.q.popleft()
            raise TimeoutError

    def iter_timeout(self, timeout: Optional[float] = None) -> Iterable[_T]:
        """Iterate over values as they become available. Will block for at most `timeout` seconds.

        If `timeout` is `None`, this is equivalent to `__iter__()`.
        Will be interrupted if the queue has been stopped.
        """

        try:
            while True:
                try:
                    yield self.get(timeout=timeout)
                except TimeoutError:
                    return
        except QueueStopped:
            return

    def peek(self) -> _T:
        """Retrieve the newest value in the queue, without removing it from the queue.

        Raises an `IndexError` if the queue is empty.
        """
        return self.q[-1]

    def peekleft(self) -> _T:
        """Retrieve the oldest value in the queue, without removing it from the queue.

        Raises an `IndexError` if the queue is empty.
        """
        return self.q[0]

    def put(self, value: _T) -> None:
        """Put an item on the queue, evicting the oldest item if the queue is full.

        This method is non-blocking.
        """
        with self.cv:
            self.q.append(value)
            self.cv.notify_all()

    def stop(self) -> None:
        """Propogate a queue.QueueStopped exception to all threads blocking on `get()`."""
        with self.cv:
            self.stop_event.set()
            self.cv.notify_all()

    def stopped(self) -> bool:
        return self.stop_event.is_set()

    def _unblocked(self) -> bool:
        return self.stopped() or not self.empty()

    def __len__(self) -> int:
        return len(self.q)

    def __iter__(self) -> Iterable[_T]:
        """Iterate over values as they become available. May block for an arbitrarily long time.

        Will be interrupted if the queue has been stopped."""
        while True:
            try:
                yield self.get()
            except QueueStopped:
                return
