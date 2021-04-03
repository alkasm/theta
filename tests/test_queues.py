import threading
import pytest
import theoryshop

EQ = theoryshop.EvictingQueue


def test_evicting_queue_basic():
    q = EQ(size=0)
    assert q.empty()
    assert len(q) == 0
    assert not q
    with pytest.raises(IndexError):
        q.peek()
        q.peekleft()

    for size in range(1, 4):
        q = EQ(size=size)
        for i in range(size):
            q.put(i)
        assert not q.empty()
        assert len(q) == size
        assert q
        assert q.peek() == size - 1
        for i in range(size):
            assert i == q.peekleft() == q.get()
        assert q.empty()
        assert not q

    q.stop()
    assert q.stopped()


def test_evicting_queue_fifo():
    q = EQ(size=2)
    q.put(0)
    assert q.peek() == 0
    q.put(1)
    assert q.peek() == 1
    q.put(2)
    assert 1 == q.peekleft() == q.get()
    assert 2 == q.peekleft() == q.get()
    assert q.empty()


def test_evicting_queue_iter():
    q = EQ(size=2)
    q.put(0)
    q.put(1)
    values = []
    for i, item in enumerate(q):
        values.append(item)
        if i >= 1:
            q.stop()
    assert [0, 1] == values
    assert q.empty()


def test_evicting_queue_flush():
    q = EQ(size=2)
    q.put(0)
    q.put(1)
    assert [0, 1] == q.flush()
    assert q.empty()


def test_evicting_queue_iter_timeout():
    q = EQ(size=2)
    q.put(0)
    q.put(1)
    assert [0, 1] == list(q.iter_timeout(0))
    assert q.empty()


def test_evicting_queue_blocking_get():
    q = EQ()
    t = threading.Thread(target=q.get)
    t.start()
    assert t.is_alive()  # thread has not finished / is currently blocking
    q.put("value")
    t.join()  # thread has been joined / is no longer blocking
    assert not t.is_alive()


def test_evicting_queue_blocking_iter():
    q = EQ()
    t = threading.Thread(target=lambda: next(q.__iter__()))
    t.start()
    assert t.is_alive()
    q.put("value")
    t.join()
    assert not t.is_alive()


def test_evicting_queue_blocking_iter_timeout():
    q = EQ()
    t = threading.Thread(target=lambda: next(q.iter_timeout(0)))
    q.put(0)
    t.start()
    q.put(1)
    t.join()
    assert not t.is_alive()
    assert 1 == q.get()
    assert q.empty()


def test_evicting_queue_stop():
    q = EQ()
    t = threading.Thread(target=q.get)
    t.start()
    assert t.is_alive()
    q.stop()
    t.join()
    assert q.stopped()
    assert not t.is_alive()


def test_evicting_queue_stop_iter():
    q = EQ()
    t = threading.Thread(target=lambda: next(q.__iter__()))
    t.start()
    assert t.is_alive()
    q.stop()
    t.join()
    assert q.stopped()
    assert not t.is_alive()


def test_evicting_queue_stop_iter_timeout():
    q = EQ()
    t = threading.Thread(target=lambda: next(q.iter_timeout(100)))
    t.start()
    assert t.is_alive()
    q.stop()
    t.join()
    assert q.stopped()
    assert not t.is_alive()
