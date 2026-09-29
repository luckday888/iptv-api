import asyncio
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.channels import build_channels_blueprint
from service.web.api.screenshots import build_screenshots_blueprint
from service.web.auth.session import create_session, COOKIE_NAME
from service.web.tasks.ops_manager import ops_manager
from utils import channel_operations
from utils import channel_repository as repo


# 三个操作 POST：(kind, 路径, 请求体)
OPERATION_POSTS = [
    ("retest_channel", "/api/admin/channels/c1/retest", None),
    ("retest_results", "/api/admin/channels/c1/results/retest", {"result_keys": ["r1"]}),
    ("screenshot", "/api/admin/channels/c1/results/screenshot", {"result_keys": ["r1"]}),
]


def _app():
    app = Flask(__name__)
    app.register_blueprint(build_channels_blueprint())
    app.register_blueprint(build_screenshots_blueprint())
    return app


def _client(authenticated=True):
    client = _app().test_client()
    if authenticated:
        client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def _patch_channel(monkeypatch, exists=True):
    # 控制频道存在性，避免依赖真实数据库内容
    monkeypatch.setattr(
        repo,
        "get_channel",
        lambda db_path, key: {"channel_key": key, "name": "c1"} if exists else None,
    )


def _patch_operation_records(monkeypatch, op_id="op-1"):
    # 操作记录读写全部假化，不触碰真实 DB
    monkeypatch.setattr(repo, "begin_operation", lambda *a, **k: op_id)
    monkeypatch.setattr(repo, "finish_operation", lambda *a, **k: None)


def _patch_fake_ops(monkeypatch, behavior):
    """注入假 ChannelOperations；三个操作方法统一执行 behavior(progress, operation_id)。"""

    class FakeOperations:
        def __init__(self, db_path):
            self.db_path = db_path

        async def retest_channel(self, channel_key, progress=None, operation_id=None):
            return await behavior(progress, operation_id)

        async def retest_results(
            self, channel_key, result_keys, progress=None, operation_id=None
        ):
            return await behavior(progress, operation_id)

        async def capture_result_screenshots(
            self, channel_key, result_keys, progress=None, operation_id=None
        ):
            return await behavior(progress, operation_id)

    # channels.py 在请求时执行 from utils.channel_operations import ChannelOperations
    monkeypatch.setattr(channel_operations, "ChannelOperations", FakeOperations)


# ---------- 既有保留用例 ----------

def test_screenshot_metadata_missing():
    # 不存在的 result_key 返回 404
    res = _client().get("/api/admin/screenshots/nope-key")
    assert res.status_code == 404


def test_screenshot_metadata_found(monkeypatch):
    # 命中处理器时返回截图元数据，证明路径真实可达
    from service.web.api import screenshots as shots
    monkeypatch.setattr(
        shots.repo, "get_stream_screenshot",
        lambda db_path, result_key: {"result_key": result_key, "image_path": "x.png"})
    res = _client().get("/api/admin/screenshots/k1")
    assert res.status_code == 200
    assert res.get_json()["result_key"] == "k1"


def test_retest_missing_channel():
    res = _client().post("/api/admin/channels/nope/retest")
    assert res.status_code == 404


# ---------- 新增：results 操作的频道存在性校验 ----------

def test_results_retest_missing_channel_404(monkeypatch):
    _patch_channel(monkeypatch, exists=False)
    res = _client().post(
        "/api/admin/channels/nope/results/retest", json={"result_keys": ["r1"]}
    )
    assert res.status_code == 404
    assert res.get_json()["error"] == "频道不存在"


def test_results_screenshot_missing_channel_404(monkeypatch):
    _patch_channel(monkeypatch, exists=False)
    res = _client().post(
        "/api/admin/channels/nope/results/screenshot", json={"result_keys": ["r1"]}
    )
    assert res.status_code == 404
    assert res.get_json()["error"] == "频道不存在"


# ---------- ops_manager：互斥 / 异常 / 正常 ----------

def test_operation_conflict_409(monkeypatch):
    _patch_channel(monkeypatch)
    ids = iter(["op-first", "op-second"])
    monkeypatch.setattr(repo, "begin_operation", lambda *a, **k: next(ids))
    finished = []
    monkeypatch.setattr(
        repo, "finish_operation", lambda db_path, op_id, status, *a: finished.append((op_id, status))
    )

    started = threading.Event()
    release = threading.Event()

    async def blocking(progress, operation_id):
        started.set()
        # 用 to_thread 等待，不依赖事件循环归属
        await asyncio.to_thread(release.wait)

    _patch_fake_ops(monkeypatch, blocking)
    client = _client()

    res = client.post("/api/admin/channels/c1/retest")
    assert res.status_code == 200
    assert res.get_json()["operation_id"] == "op-first"
    # 确保后台协程确实占住执行器
    assert started.wait(5)

    res2 = client.post("/api/admin/channels/c1/retest")
    assert res2.status_code == 409

    # 释放阻塞协程并回收工作线程，避免污染后续用例
    release.set()
    ops_manager.wait_idle(5)
    snap = ops_manager.snapshot()
    assert snap["running"] is False
    # 第二次未实际执行，预创建记录以 cancelled 收尾
    assert ("op-second", "cancelled") in finished


def test_operation_error_snapshot(monkeypatch):
    _patch_channel(monkeypatch)
    _patch_operation_records(monkeypatch, "op-err")

    async def boom(progress, operation_id):
        raise ValueError("boom")

    _patch_fake_ops(monkeypatch, boom)
    res = _client().post(
        "/api/admin/channels/c1/results/retest", json={"result_keys": ["r1"]}
    )
    assert res.status_code == 200
    ops_manager.wait_idle(5)
    snap = ops_manager.snapshot()
    assert snap["running"] is False
    assert snap["error"]
    assert "boom" in snap["error"]
    # 失败时进度归零，不残留半截进度
    assert snap["percent"] == 0


def test_operation_success_snapshot(monkeypatch):
    _patch_channel(monkeypatch)
    _patch_operation_records(monkeypatch, "op-ok")

    async def ok(progress, operation_id):
        progress(1, 1, "c1")

    _patch_fake_ops(monkeypatch, ok)
    res = _client().post("/api/admin/channels/c1/retest")
    assert res.status_code == 200
    ops_manager.wait_idle(5)
    snap = ops_manager.snapshot()
    assert snap["running"] is False
    assert snap["percent"] == 100
    assert snap["error"] is None


# ---------- 三个操作 POST 响应含 operation_id ----------

@pytest.mark.parametrize("kind,path,body", OPERATION_POSTS)
def test_operation_id_in_response(monkeypatch, kind, path, body):
    _patch_channel(monkeypatch)
    op_id = f"id-{kind}"
    _patch_operation_records(monkeypatch, op_id)

    seen = {}

    async def ok(progress, operation_id):
        seen["operation_id"] = operation_id

    _patch_fake_ops(monkeypatch, ok)
    res = _client().post(path, json=body)
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data["operation_id"], str)
    assert data["operation_id"] == op_id
    ops_manager.wait_idle(5)
    # 确认 id 真正透传到 service 方法
    assert seen["operation_id"] == op_id


# ---------- 未登录 401 ----------

@pytest.mark.parametrize("method,path", [
    ("post", "/api/admin/channels/c1/retest"),
    ("post", "/api/admin/channels/c1/results/retest"),
    ("post", "/api/admin/channels/c1/results/screenshot"),
    ("get", "/api/admin/screenshots/r1"),
])
def test_unauthenticated_401(method, path):
    client = _client(authenticated=False)
    res = getattr(client, method)(path)
    assert res.status_code == 401
