"""Python extensions by alkasm"""

__version__ = "0.1.0"


from concurrent.futures import ThreadPoolExecutor, TimeoutError


class TimeoutIterable:
    """Iterable that exhausts if it takes longer than `timeout` seconds to obtain the next value."""

    def __init__(self, iterable, timeout=None):
        self._it = iter(iterable)
        self.timeout = timeout

    def __iter__(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                try:
                    future = executor.submit(next, self._it)
                    val = future.result(self.timeout)
                except (TimeoutError, StopIteration):
                    return
                yield val


import threading
import queue


class StreamBuffer:
    """Buffers live stream data in a separate thread to be flushed on-demand.
    Use a context manager to start enqueueing the data from the stream. 

    Note: background thread may block indefinitely if the stream does, as well.
    
    Example
    -------
    import time
    with StreamBuffer(iterable) as buf:
        time.sleep(1)               # fill buffer for a second
        print(list(buf.flush()))    # dump all the data from the buffer
    """

    def __init__(self, stream, maxsize=None):
        self.stream = iter(stream)
        self.q = queue.Queue(maxsize) if maxsize is not None else queue.Queue()
        self._stop_event = threading.Event()
        self._t = threading.Thread(target=self._enqueue)

    def _enqueue(self):
        # TODO: any way to guarantee stopping?
        for val in self.stream:
            if self._stop_event.is_set():  # thread stopping condition
                break
            self.q.put(val)

    def __enter__(self):
        """Starts collecting values from the stream into the buffer."""
        self._t.start()
        return self

    def __exit__(self, *args, **kwargs):
        """Stops collecting values from the stream."""
        self._stop_event.set()
        self._t.join()

    def flush(self):
        """Every call to .flush() yields all the data from the buffer and clears it."""
        while True:
            try:
                yield self.q.get_nowait()
            except queue.Empty:
                return


import functools
import logging
import time


def timed(func):
    """Log the execution time for the decorated function."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logging.debug("{} took {:2.3f} ms".format(func.__name__, 1000 * (end - start)))
        return result

    return wrapper
