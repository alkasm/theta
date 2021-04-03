import pytest
import theoryshop
import concurrent.futures


@pytest.fixture
def store():
    return theoryshop.Store(concurrent.futures.ThreadPoolExecutor())


def test_writer():
    l = []
    w = theoryshop.Writer("key", l.append)
    w.write(1)
    assert l == [1]
    w.write("2")
    assert l == [1, "2"]


def test_store_writer(store):
    l = []
    w = store.writer("key")
    store.add_callback("key", l.append)
    fs1 = w.write(1)
    concurrent.futures.wait(fs1)
    assert l == [1]
    fs2 = w.write("2")
    concurrent.futures.wait(fs2)
    assert l == [1, "2"]


def test_multiple_writers(store):
    l = []
    w1 = store.writer("key")
    w2 = store.writer("key")
    store.add_callback("key", l.append)
    fs1 = w1.write(1)
    concurrent.futures.wait(fs1)
    assert l == [1]
    fs2 = w2.write("2")
    concurrent.futures.wait(fs2)
    assert l == [1, "2"]


def test_multiple_callbacks(store):
    l = []
    d = {"value": None}
    w = store.writer("key")
    store.add_callback("key", l.append)
    store.add_callback("key", lambda v: d.update(value=v))
    fs1 = w.write(1)
    concurrent.futures.wait(fs1)
    assert l == [1]
    assert d == {"value": 1}
    fs2 = w.write("2")
    concurrent.futures.wait(fs2)
    assert l == [1, "2"]
    assert d == {"value": "2"}


def test_multiple_callbacks_multiple_writers(store):
    l = []
    d = {"value": None}
    w1 = store.writer("key")
    w2 = store.writer("key")
    store.add_callback("key", l.append)
    store.add_callback("key", lambda v: d.update(value=v))
    fs1 = w1.write(1)
    concurrent.futures.wait(fs1)
    assert l == [1]
    assert d == {"value": 1}
    fs2 = w2.write("2")
    concurrent.futures.wait(fs2)
    assert l == [1, "2"]
    assert d == {"value": "2"}


def test_remove_callback(store):
    l = []
    w = store.writer("key")
    cb = store.add_callback("key", l.append)
    w.write(1)
    assert l == [1]
    store.remove_callback(cb)
    w.write(1)
    assert l == [1]


def test_remove_callback_multiple_times_errors(store):
    w = store.writer("key")
    cb = store.add_callback("key", lambda: None)
    store.remove_callback(cb)
    with pytest.raises(KeyError):
        store.remove_callback(cb)


def test_callback_error_logged(store, caplog):
    l = []
    w = store.writer("key")
    store.add_callback("key", l.insert)  # insert requires 2 args
    w.write(1)
    assert [
        "Writer for key 'key' encountered an exception during callback execution:"
    ] == [rec.message for rec in caplog.records]
    assert ["ERROR"] == [rec.levelname for rec in caplog.records]
