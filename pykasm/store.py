# Callback interface

from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, DefaultDict, Dict
from uuid import uuid4

Callback = Callable[[datetime, Any], Any]


class Writer:
    """A writer for a specific key

    Not meant to be instantiated directly, but via `store.writer(key)`.
    """

    def __init__(self, key: Any, submit: Callback):
        self.key = key
        self.submit: Callback = submit

    def write(self, val: Any):
        self.submit(datetime.now(), val)

    def __repr__(self):
        return f"<{self.__class__.__qualname__} for key {self.key!r}>"


class Store:
    """Store for arbitrary data with an executor for submitting callback tasks.

    You can get a writer for a `key` with `writer(key)`. Only one writer can be
    created per `key` on each store.

    The callback functions provided should take two positional arguments, the first
    being a `datetime` when the data was added to the store, and the second being the
    value added to the store.

    .. code-block:: python

        store = Store(ThreadPoolExecutor())

        # q holds a queue of data, d holds the most recent value
        q = deque()
        d = {'value': None}

        q_name = store.add_callback("data", lambda ts, val: q.append(val), "q")
        store.add_callback("data", lambda ts, val: d.update(value=val))
        # name not used, so return value ignored

        writer = store.writer("data")
        for i in range(5):
            writer.write(i)
        store.remove_callback("data", "q")
        writer.write(5)  # value of 5 was only sent to the unnamed callback

        print("q", q)
        print("d", d)

    .. code-block::

        deque([0, 1, 2, 3, 4])
        {'value': 5}
    """

    def __init__(self, executor: ThreadPoolExecutor):
        self.executor: ThreadPoolExecutor = executor
        self.writers: Dict[Any, Writer] = {}
        self.callbacks: DefaultDict[Any, Dict[str, Callback]] = defaultdict(dict)

    def _submitter(self, key: Any) -> Callback:
        def submit(ts: datetime, val: Any):
            for f in self.callbacks[key].values():
                self.executor.submit(f, ts, val)

        return submit

    def add_callback(self, key: Any, f: Callback) -> str:
        """Add a callback to execute on new values written under the key.

        The returned value is a string id for the callback which can be used to
        remove it later with `remove_callback()`.

        Args:
            key: The key which links the callback to the writer. The key can be
                any immutable type (same restriction as a dictionary key).
            f: Callable that will be executed as f(datetime, value) for each new
                value written to the store under this key. The return value will
                be discarded.

        Returns:
            str: An id for the callback, which can be used for unregistering the callback.
        """
        id = f"{f.__name__}::{key}::{uuid4().hex}"
        self.callbacks[key][id] = f
        return id

    def remove_callback(self, key: Any, id: str):
        """Removes a callback for the specified (key, id) pair.

        Raises:
            KeyError: If there aren't any callbacks associated with the (key, id) pair.

        Args:
            key: The key the callback is registered under.
            id: The unique identifier for the callback, returned by `add_callback()`
        """
        del self.callbacks[key][id]

    def writer(self, key: Any) -> Writer:
        if key in self.writers:
            raise ValueError(f"Already created a writer for key {key}")
        w = Writer(key, self._submitter(key))
        self.writers[key] = w
        return w

    def __repr__(self):
        # ignore for vscode Pylance: https://github.com/microsoft/pylance-release/issues/658
        return f"<{self.__class__.__qualname__} for keys {*(k for k in self.writers),}>"  # type: ignore[code]


store = Store(ThreadPoolExecutor())
writer = store.writer(int)
print(store)
