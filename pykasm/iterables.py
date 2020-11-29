from concurrent.futures import ThreadPoolExecutor, TimeoutError


class TimeoutIterable:
    """Iterable that exhausts if it takes longer than `timeout` seconds to obtain the next value."""

    def __init__(self, iterable, timeout=None):
        self.it = iter(iterable)
        self.timeout = timeout

    def __iter__(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                try:
                    future = executor.submit(next, self.it)
                    val = future.result(self.timeout)
                except (TimeoutError, StopIteration):
                    return
                yield val
