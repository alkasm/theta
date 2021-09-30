import threading
from typing import Any, Optional


class StoppableThread(threading.Thread):
    """
    A thread which can be requested to stop running externally.

    Stop requests are handled by a stop event which can be shared externally.

    Note that stoppable threads require cooperation. Subclasses that implement
    the usual `run()` method for long-running tasks can check if the thread is
    `running()` or can use `wait()` for tasks that run on an interval.

    This class can be used like a normal thread with a target function to run.
    The stop event can be constructed externally and passed in, so the target
    function can utilize the event.

    .. code-block:: python

        import logging
        import threading
        import time
        from theta import StoppableThread

        logging.basicConfig(level=logging.INFO)

        def sleeper(stop_event):
            t = 0
            while not stop_event.wait(1):
                t += 1
            logging.info("Slept for between %d and %d seconds", t, t + 1)

        event = threading.Event()
        thread = StoppableThread(target=sleeper, args=(event,), stop_event=event)
        thread.start()
        time.sleep(2.1)
        thread.stop()
        thread.join()

    This class can also be subclassed. Methods are provided to interact with
    the stop event. Subclassing works the same as with a `threading.Thread`;
    implement the `run()` function, which gets called on `start()`.

    .. code-block:: python

        class SleeperThread(StoppableThread):
            def run(self):
                t = 0
                while not self.wait(1):
                    t += 1
                logging.info("Slept for between %d and %d seconds", t, t + 1)

        thread = SleeperThread()
        thread.start()
        time.sleep(2.1)
        thread.stop()
        thread.join()
    """

    stop_event: threading.Event

    def __init__(
        self, *args: Any, stop_event: Optional[threading.Event] = None, **kwargs: Any
    ):
        """
        Args:
            stop_event: Thread stopping event, which can be externally set.
                If None, creates a new `threading.Event`.
        """
        super().__init__(*args, **kwargs)
        self.stop_event = stop_event if stop_event is not None else threading.Event()

    def running(self) -> bool:
        """Checks if the thread has not been requested to stop."""
        return not self.stopped()

    def wait(self, interval: Optional[float]) -> bool:
        """
        Wait on the stop event for an interval (in seconds), waking up if set.
        If the interval is None, blocks indefinitely. Returns True if the flag
        was interrupted and set, otherwise False (i.e., a timeout occurred).
        """
        return self.stop_event.wait(interval)

    def stop(self) -> None:
        """Set the stop flag for the thread. Safe to call multiple times."""
        self.stop_event.set()

    def stopped(self) -> bool:
        """Checks if the thread has been requested to stop."""
        return self.stop_event.is_set()
