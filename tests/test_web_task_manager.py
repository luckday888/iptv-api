import asyncio, os, sys, threading
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


def test_cancel_reported_as_cancelled_not_success():
    # 取消即使被 run_once 内部吞掉，也不得显示为 percent=100 的成功
    mgr = UpdateTaskManager()
    started = threading.Event()

    async def swallow_cancel(progress, event):
        started.set()
        try:
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            # 模拟 main.py 中 main() 捕获取消且不 re-raise，协程正常返回
            pass

    mgr.set_run_coroutine(swallow_cancel)
    mgr.start()
    assert started.wait(5)
    mgr.cancel()
    assert mgr.wait_idle(timeout=5)
    snap = mgr.snapshot()
    assert snap["finished"] is True
    assert snap["status"] == "cancelled"
    assert snap["percent"] != 100


class _BoomSource:
    # 非运行态下若被调用即说明守卫失效
    def pause(self):
        raise AssertionError("idle 状态不应调用 pause")

    def resume(self):
        raise AssertionError("idle 状态不应调用 resume")

    def stop(self):
        raise AssertionError("idle 状态不应调用 stop")


def test_controls_noop_after_finished():
    # 任务结束后 pause/resume/cancel 应为 no-op：快照不变、不调用 source 方法
    mgr = _make()
    mgr.start()
    mgr.wait_idle(timeout=5)
    mgr._source = _BoomSource()
    before = mgr.snapshot()
    mgr.pause()
    mgr.resume()
    mgr.cancel()
    after = mgr.snapshot()
    assert after == before
    assert after["status"] == "idle"


def test_pause_resume_effective_while_running():
    # 守卫不得误伤运行态：运行中 pause/resume 仍应生效
    mgr = UpdateTaskManager()
    started = threading.Event()

    async def slow(progress, event):
        started.set()
        await asyncio.sleep(2)

    mgr.set_run_coroutine(slow)
    mgr.start()
    try:
        assert started.wait(5)
        mgr.pause()
        assert mgr.snapshot()["status"] == "paused"
        mgr.resume()
        assert mgr.snapshot()["status"] == "running"
        mgr.cancel()
        assert mgr.wait_idle(timeout=5)
        assert mgr.snapshot()["status"] == "cancelled"
    finally:
        mgr.wait_idle(timeout=5)
