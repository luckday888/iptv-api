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

    def _progress(self, title, percent, finished=False, url=None, now=None):
        self._update(title=str(title), percent=int(percent), finished=bool(finished))

    def _event(self, payload):
        message = str(payload.get("message") or "").strip()
        if not message:
            return
        level = str(payload.get("level") or "INFO").upper()
        self._update(last_event={"level": level, "message": message})

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise TaskRunningError("已有更新任务在运行")
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
        try:
            if self._run_coroutine is not None:
                task = self._run_coroutine(self._progress, self._event)
            else:
                task = self._source.run_once(self._progress, self._event)
            self._loop.run_until_complete(task)
            self._update(status="idle", finished=True, percent=100)
        except asyncio.CancelledError:
            self._update(status="idle", finished=True)
        except Exception as exc:  # 更新异常
            self._update(
                status="idle", finished=True,
                last_event={"level": "ERROR", "message": str(exc)},
            )
        finally:
            self._loop.close()
            self._loop = None

    def pause(self):
        if self._source:
            self._source.pause()
            self._update(status="paused")

    def resume(self):
        if self._source:
            self._source.resume()
            self._update(status="running")

    def cancel(self):
        if self._source:
            self._update(status="cancelling")
            self._source.stop()

    def wait_idle(self, timeout=5):
        if self._thread:
            self._thread.join(timeout)


# 模块级单例
task_manager = UpdateTaskManager()
