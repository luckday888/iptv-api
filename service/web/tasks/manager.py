import asyncio
import threading
import time

from main import UpdateSource


class TaskRunningError(Exception):
    """已有更新任务在运行。"""


class UpdateTaskManager:
    """进程内单例：在独立线程的事件循环中执行完整更新。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._loop = None
        self._source = None
        self._run_coroutine = None
        # 是否已请求取消；run_once 内部会吞掉 CancelledError，不能靠异常判定取消
        self._cancel_requested = False
        self._snapshot = {
            "status": "idle", "title": "", "percent": 0,
            "started_at": None, "finished": True, "last_event": None,
        }

    def set_run_coroutine(self, coro_func):
        # 测试用：注入自定义协程；生产默认使用 UpdateSource.run_once
        self._run_coroutine = coro_func

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._snapshot)

    def _update(self, **kwargs):
        with self._lock:
            self._snapshot.update(kwargs)

    def _is_running_locked(self) -> bool:
        # 运行态判定：后台线程存活即任务未结束（调用方须持锁）
        return self._thread is not None and self._thread.is_alive()

    def _progress(self, title, percent, finished=False, url=None):
        # url 为 run_once 回调约定的频道详情，当前快照不记录，仅保持签名兼容
        self._update(title=str(title), percent=int(percent), finished=bool(finished))

    def _event(self, payload):
        message = str(payload.get("message") or "").strip()
        if not message:
            return
        level = str(payload.get("level") or "INFO").upper()
        self._update(last_event={"level": level, "message": message})

    def start(self):
        with self._lock:
            if self._is_running_locked():
                raise TaskRunningError("已有更新任务在运行")
            self._cancel_requested = False
            self._snapshot = {
                "status": "running", "title": "准备中", "percent": 0,
                "started_at": time.time(), "finished": False, "last_event": None,
            }
            self._source = UpdateSource()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # 本次运行结果：success / cancelled / failed
        outcome = "success"
        error = None
        try:
            if self._run_coroutine is not None:
                task = self._run_coroutine(self._progress, self._event)
            else:
                task = self._source.run_once(self._progress, self._event)
            self._loop.run_until_complete(task)
        except asyncio.CancelledError:
            outcome = "cancelled"
        except Exception as exc:  # 更新异常
            outcome = "failed"
            error = exc
        finally:
            with self._lock:
                # run_once 可能吞掉 CancelledError 正常返回，以取消标志为最终依据
                if self._cancel_requested:
                    outcome = "cancelled"
            if outcome == "cancelled":
                # 已取消：结束但不置 percent=100，不表示成功
                self._update(status="cancelled", finished=True)
            elif outcome == "success":
                self._update(status="idle", finished=True, percent=100)
            else:
                self._update(
                    status="idle", finished=True,
                    last_event={"level": "ERROR", "message": str(error)},
                )
            self._loop.close()
            self._loop = None

    def pause(self):
        with self._lock:
            # 非运行态为 no-op，不改变快照
            if not self._is_running_locked():
                return
            source = self._source
        source.pause()
        self._update(status="paused")

    def resume(self):
        with self._lock:
            # 非运行态为 no-op，不改变快照
            if not self._is_running_locked():
                return
            source = self._source
        source.resume()
        self._update(status="running")

    def cancel(self):
        with self._lock:
            # 非运行态为 no-op，不改变快照
            if not self._is_running_locked():
                return
            self._cancel_requested = True
            self._snapshot.update(status="cancelling")
            source = self._source
        source.stop()

    def wait_idle(self, timeout=5) -> bool:
        # 返回任务线程是否已结束
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()


# 模块级单例
task_manager = UpdateTaskManager()
