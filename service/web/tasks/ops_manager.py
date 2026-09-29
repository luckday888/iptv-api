import asyncio
import threading


class OpsManager:
    """频道操作（重测/截图）执行器：独立线程事件循环，操作彼此互斥。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._snapshot = {
            "running": False, "kind": "", "title": "",
            "percent": 0, "error": None,
        }

    def snapshot(self):
        with self._lock:
            return dict(self._snapshot)

    def _progress(self, title, percent, **kwargs):
        with self._lock:
            self._snapshot.update(title=str(title), percent=int(percent))

    def run(self, kind, coro_factory):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("已有频道操作在执行")
            self._snapshot = {
                "running": True, "kind": kind, "title": "开始",
                "percent": 0, "error": None,
            }
            self._thread = threading.Thread(
                target=self._run, args=(coro_factory,), daemon=True)
            self._thread.start()

    def _run(self, coro_factory):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro_factory(self._progress))
            with self._lock:
                self._snapshot.update(running=False, percent=100)
        except Exception as exc:
            with self._lock:
                self._snapshot.update(running=False, error=str(exc))
        finally:
            loop.close()

    def wait_idle(self, timeout=10):
        if self._thread:
            self._thread.join(timeout)


ops_manager = OpsManager()
