import pytest

from cidc_api.utils.migrations import RollbackableQueue, PieceOfWork


def test_rollbackable_queue():
    # Queue works on a well-behaved example
    tasks = RollbackableQueue()
    state = {"a": 1, "b": 2}
    orig = state.copy()
    t1 = PieceOfWork(lambda: state.pop("a"), lambda: state.__setitem__("a", 1))
    t2 = PieceOfWork(
        lambda: state.__setitem__("b", 1), lambda: state.__setitem__("b", 2)
    )
    tasks.schedule(t1)
    tasks.schedule(t2)
    tasks.run_all()
    assert state == {"b": 1}

    # Queue rolls back when a task errors
    state = orig.copy()
    t3_keyerror = PieceOfWork(lambda: state["foo"], lambda: state.__setitem__("c", 3))
    tasks.schedule(t3_keyerror)
    with pytest.raises(KeyError):
        tasks.run_all()
    assert state == orig
