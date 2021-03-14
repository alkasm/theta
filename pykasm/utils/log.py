import functools
import logging
import time
from typing import Callable


def timed(func: Callable) -> Callable:
    """Log the execution time for the decorated function as a DEBUG message.

    .. code-block:: python

        from time import sleep
        import logging

        logging.basicConfig(level=logging.DEBUG)

        @timed
        def takes_a_second():
            time.sleep(1)

        takes_a_second()

    .. code-block::

        DEBUG:root:takes_a_second took 1004.352 ms

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logging.debug("{} took {:2.3f} ms".format(func.__name__, 1000 * (end - start)))
        return result

    return wrapper
