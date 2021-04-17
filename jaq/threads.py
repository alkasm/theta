import threading
from typing import Any, Optional


class StoppableThread(threading.Thread):
    """A thread which can be requested to stop running externally.

    Stop requests are handled by a stop event which can be shared externally.

    This class can be subclassed, or can just be used like a normal thread with
    a target function to run. If subclassed, this class provides methods to
    interact with the stop event. If constructed with a target function to run,
    the stop event can be constructed externally and passed in, so the target
    function can use the stop event.

    Note that stoppable threads require cooperation. Subclasses that implement
    the usual `run()` method for long-running tasks can check if the thread is
    `running()` or can use `wait(interval)` for tasks that run on an interval.
    """

    stop_event: threading.Event

    def __init__(
        self, *args: Any, stop_event: Optional[threading.Event] = None, **kwargs: Any
    ):
        """Initializes a thread, passing on the args and kwargs to the superclass,
        except `stop_event`.

        Args:
            stop_event: Thread stopping event, which can be externally set.
                If None, creates a new threading.Event().
        """
        super().__init__(*args, **kwargs)
        self.stop_event = stop_event if stop_event is not None else threading.Event()

    def running(self) -> bool:
        """Checks if the thread has not been requested to stop."""
        return not self.stopped()

    def wait(self, interval: float) -> bool:
        """Sleeps using the stop event, which will wake up if the thread is asked to stop.

        Args:
            interval: Length of time to sleep, in seconds.
        """
        return self.stop_event.wait(interval)

    def stop(self) -> None:
        """Set the stop flag for the thread. Safe to call multiple times."""
        self.stop_event.set()

    def stopped(self) -> bool:
        """Checks if the thread has been requested to stop."""
        return self.stop_event.is_set()
