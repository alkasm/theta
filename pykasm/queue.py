from collections import deque
from threading import Condition, Event
from typing import Generic, Iterable, Optional, TypeVar

_T = TypeVar("_T")


class TimeoutError(Exception):
    pass


class QueueStopped(Exception):
    pass


class EvictingQueue(Generic[_T]):
    """Thread-safe FIFO queue with blocking gets and evicting, non-blocking puts.

    Basic reads of this queue with blocking gets is as simple as iterating over it.
    Iteration will immediately stop if the queue's `stop()` method is called.

    .. code-block::

        for item in q:
            process(item)
        cleanup()

    If you want to use blocking gets but with timeouts, you'll need need to explicitly
    handle timeout and stopped exceptions, like so:

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
    """

    def __init__(self, size: Optional[int] = None):
        self._q: deque = deque(maxlen=size)
        self._cv: Condition = Condition()
        self._stop: Event = Event()

    def empty(self) -> bool:
        """Equivalent to `len(q) == 0`"""
        return len(self) == 0

    def get(self, timeout: Optional[float] = None) -> _T:
        """Blocking get with an optional timeout.

        Raises a `queue.TimeoutError` if the timeout expires before an item is available.
        Raises a `queue.QueueStopped` if the queue has been stopped.
        """
        with self._cv:
            unblocked = self._cv.wait_for(self._unblocked, timeout)
            if unblocked:
                if self.stopped():
                    raise QueueStopped
                return self._q.popleft()
            raise TimeoutError

    def peek(self) -> _T:
        """Retrieve the newest value in the queue, without removing it from the queue.

        Raises an `IndexError` if the queue is empty
        """
        return self._q[0]

    def put(self, value: _T) -> None:
        """Put an item on the queue, evicting the oldest item if the queue is full.

        This method is non-blocking.
        """
        with self._cv:
            self._q.append(value)
            self._cv.notify_all()

    def stop(self) -> None:
        """Propogate a queue.QueueStopped exception to all threads blocking on `get()`."""
        with self._cv:
            self._stop.set()
            self._cv.notify_all()

    def stopped(self) -> bool:
        return self._stop.is_set()

    def _unblocked(self) -> bool:
        return self.stopped() or not self.empty()

    def __len__(self) -> int:
        return len(self._q)

    def __iter__(self) -> Iterable[_T]:
        """Iterate over values as they become available. May block for an arbitrarily long time.

        Will be interrupted if the queue has been stopped."""
        while True:
            try:
                yield self.get()
            except QueueStopped:
                break
