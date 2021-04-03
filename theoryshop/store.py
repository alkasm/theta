import collections
import concurrent.futures
import logging
import threading
from typing import Any, Callable, DefaultDict, Dict, List
import uuid


logger = logging.getLogger(__name__)

Callback = Callable[[Any], Any]
Submitter = Callable[[Any], List[concurrent.futures.Future]]


class Store:
    """Store for arbitrary data with an executor for submitting callback tasks.

    Register callbacks and create writers associated to a key; when a writer
    writes to the store, it will submit tasks to the executor to invoke all the
    callbacks for that key with the newly written value.

    Retrieve a writer for some `key` with `store.writer(key)`.

    The callback functions provided must take a single positional argument,
    and will be called with the new value added to the store.

    .. code-block:: python

        executor = ThreadPoolExecutor()
        store = Store(executor)

        # q holds a queue of data, d holds the most recent value
        q = deque()
        d = {'value': None}

        # store a reference to the callback to remove later
        q_id = store.add_callback("data", q.append)

        # reference not needed since this callback won't be removed
        store.add_callback("data", lambda val: d.update(value=val))

        writer = store.writer("data")
        for i in range(5):
            writer.write(i)

        store.remove_callback(q_id)
        writer.write(5)  # value of 5 was only sent to the unnamed callback

        print("q", q)
        print("d", d)

    .. code-block::

        deque([0, 1, 2, 3, 4])
        {'value': 5}
    """

    executor: concurrent.futures.ThreadPoolExecutor
    writers: Dict[Any, "Writer"]
    callbacks: DefaultDict[Any, Dict[str, Callback]]
    _callback_keys: Dict[str, Any]
    _callback_lock: threading.Lock

    def __init__(self, executor: concurrent.futures.ThreadPoolExecutor):
        self.executor = executor
        self.writers = {}
        self.callbacks = collections.defaultdict(dict)
        self._callback_keys = {}
        self._callback_lock = threading.Lock()

    def add_callback(self, key: Any, f: Callback) -> str:
        """Add a callback to execute on new values written under the key.

        The returned value is a string id for the callback which can be used to
        remove it later with `remove_callback(id)`.

        Args:
            key: The key which links the callback to the writer. The key can be
                any immutable type (same restriction as a dictionary key).
            f: Callable executed as f(value) for each new value written to the
                store under this key. Return values are available via futures
                that the writer returns. Exceptions encountered while running
                are logged, then ignored.

        Returns:
            str: An id for the callback, which can be used for unregistering
                the callback. The id has the form "<key>::<f.__name__>::<uuid>".
        """
        id = f"{key}::{f.__name__}::{uuid.uuid4().hex}"
        with self._callback_lock:
            self.callbacks[key][id] = f
            self._callback_keys[id] = key
        return id

    def remove_callback(self, id: str) -> None:
        """Removes the specified callback.

        Raises:
            KeyError: If there is no callback with the given id.

        Args:
            id: The identifier for the callback, returned by `add_callback()`.
        """
        with self._callback_lock:
            key = self._callback_keys[id]
            del self._callback_keys[id]
            del self.callbacks[key][id]

    def writer(self, key: Any) -> "Writer":
        """Creates or retrieves a writer for the specified key.

        Args:
            key: A key to associate writers and callbacks. Any dictionary key
                is valid.

        Returns:
            A writer for the specified key.
        """
        try:
            return self.writers[key]
        except KeyError:
            w = Writer(key, self._submitter(key))
            self.writers[key] = w
            return w

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__} for keys {*(k for k in self.writers),}>"

    def _submitter(self, key: Any) -> Submitter:
        def submit(val: Any) -> List[concurrent.futures.Future]:
            fs = []
            with self._callback_lock:
                callbacks = list(self.callbacks[key].values())
            for callback in callbacks:
                future = self.executor.submit(callback, val)
                future.add_done_callback(_log_exception(key))
                fs.append(future)
            return fs

        return submit


class Writer:
    """A writer for a specific key in the Store.

    Should be instantiated via `writer = store.writer(key)`.
    """

    def __init__(self, key: Any, submit: Submitter):
        self.key = key
        self.submit: Submitter = submit

    def write(self, value: Any) -> List[concurrent.futures.Future]:
        """Writes a value to the store, executing any registered callbacks.

        This method is non-blocking, however the futures to the callbacks
        are returned to wait on, if desired.

        Args:
            value: Value to write to the store.

        Returns:
            Futures for the submitted callbacks.
        """
        return self.submit(value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__} for key {self.key!r}>"


def _log_exception(key: Any) -> Callable[[concurrent.futures.Future], None]:
    def f(future: concurrent.futures.Future) -> None:
        e = future.exception()
        if e is not None:
            logger.error(
                "Writer for key '%s' encountered an exception during callback execution:",
                key,
                exc_info=e,
            )

    return f
