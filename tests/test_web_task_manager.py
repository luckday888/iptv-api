import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from service.web.tasks.manager import UpdateTaskManager, TaskRunningError


async def _fake_run(progress, event):
    progress("步骤1", 50)
    await asyncio.sleep(0.05)
    progress("完成", 100, finished=True)


def _make():
    mgr = UpdateTaskManager()
    mgr.set_run_coroutine(_fake_run)
    return mgr


def test_lifecycle():
    mgr = _make()
    mgr.start()
    mgr.wait_idle(timeout=5)
    snap = mgr.snapshot()
    assert snap["status"] == "idle"
    assert snap["percent"] == 100


def test_conflict():
    mgr = _make()

    async def slow(progress, event):
        await asyncio.sleep(0.5)

    mgr.set_run_coroutine(slow)
    mgr.start()
    try:
        import pytest
        with pytest.raises(TaskRunningError):
            mgr.start()
    finally:
        mgr.wait_idle(timeout=5)
