import threading
from collections import deque


class ThreadStopped(Exception):
    """For use by any stoppable threads as a mechanism for signalling.

    Useful for private methods to raise back to the main run() method.
    """

    pass


class StoppableThread(threading.Thread):
    """A thread which can be requested to stop running externally.

    Stop requests are handled by a stop event which can be shared externally.

    This class can be subclassed, or can just be used like a normal thread with
    a target function to run. If subclassed, this class provides methods to
    interact with the stop event. If constructed with a target function to run,
    the stop event can be constructed externally and passed in, so the target
    function can use the stop event.

    Note that stoppable threads require cooperation. Subclasses that implement
    the usual `run()` method should check if the thread is `running()` often,
    and should use `sleep(interval)` which will wake if the stop event is set.
    """

    def __init__(self, *args, stop_event=None, **kwargs):
        """
        Args:
            stop_event: Thread stopping event, which can be externally set.
                If None, creates a new threading.Event().
        """
        super().__init__(*args, **kwargs)
        self.stop_event = stop_event if stop_event is not None else threading.Event()

    def running(self) -> bool:
        """Checks if the thread has not been requested to stop."""
        return not self.stopped()

    def sleep(self, interval: float) -> bool:
        """Sleeps using the stop event, which will wake up if the thread is asked to stop.

        Args:
            interval: Length of time to sleep, in seconds.
        """
        return bool(self.stop_event.wait(interval))

    def stop(self):
        """Set the stop flag for the thread.

        Raises:
            RuntimeError: if the thread has already been requested to stop.
        """
        if self.stop_event.is_set():
            raise RuntimeError("This thread has already been requested to stop.")
        self.stop_event.set()

    def stopped(self) -> bool:
        """Checks if the thread has been requested to stop."""
        return bool(self.stop_event.is_set())


class StreamBuffer(StoppableThread):
    """Buffers live stream data in a separate thread to be flushed on-demand.

    Start and stop the collection with `start()` and `stop()`.
    Dump the collected data to a list with `flush()`.

    .. warning::

        When you stop the buffer thread, the most recent call to `next()` on the
        stream cannot be cancelled. So streams that may indefinitely block should
        not be passed into the stream buffer. Instead, make the streams cancellable
        via a timeout or similar to avoid this thread running indefinitely.

    .. code-block:: python

        import time
        buf = StreamBuffer(iterable)
        buf.start()
        time.sleep(1)       # buffer collects data during this second
        print(buf.peek())   # prints the newest value buffered
        print(buf.flush())  # dump all the data from the buffer
    """

    def __init__(self, stream, maxlen=None):
        super().__init__(daemon=True)
        self.stream = iter(stream)
        self.maxlen = maxlen
        self.q = deque(maxlen=maxlen)
        self.lock = threading.Lock()

    def run(self):
        while self.running():
            val = next(self.stream)
            with self.lock:
                self.q.append(val)

    def copy(self):
        """Returns a shallow copy of the inner queue without flushing the data.

        Similar to a peek but over all data currently buffered.
        """
        return self.q.copy()

    def clear(self):
        """Removes all data from the buffer."""
        self.q.clear()

    def flush(self):
        """Every call returns all the data currently in the buffer and then clears it."""
        with self.lock:
            vals = list(self.q)
            self.clear()
        return vals

    def peek(self):
        """Preview the most recent element in the buffer without removing it.

        Raises:
            IndexError: If the buffer is empty.
        """
        return self.q[-1]

    def peekleft(self):
        """Preview the least recent element in the buffer without removing it.

        Raises:
            IndexError: If the buffer is empty.
        """
        return self.q[0]

    def popleft(self):
        """Remove and retrieve the least recent element in the buffer.

        Since the buffer is appended to on the right side, it makes the most sense
        to treat the buffer as a FIFO queue, and only allow popping on the left.
        Hence, only popleft() is implemented, and not pop().

        Raises:
            IndexError: If the buffer is empty.
        """
        return self.q.popleft()

    def __bool__(self):
        """True if the buffer is nonempty, False otherwise."""
        return bool(self.q)

    def __len__(self):
        """Number of items currently buffered."""
        return len(self.q)

    def __contains__(self, val):
        """Checks if a value is present in the buffer."""
        return val in self.q
