import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask

from service import rtmp as rtmp_service
from service.web.api.rtmp import build_rtmp_blueprint
from service.web.auth.session import COOKIE_NAME, create_session


def _client():
    # 构建仅挂载转推蓝图并带登录会话的测试客户端
    app = Flask(__name__)
    app.register_blueprint(build_rtmp_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_runtime():
    # 运行时快照始终返回 200 与 dict（无 RTMP 服务时兜底 available:False）
    res = _client().get("/api/admin/rtmp/runtime")
    assert res.status_code == 200
    assert isinstance(res.get_json(), dict)


def test_channels():
    # 可转推频道列表返回 list（空库时为 []）
    res = _client().get("/api/admin/rtmp/channels")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_routes_require_auth():
    # 未登录访问转推相关路由必须返回 401
    app = Flask(__name__)
    app.register_blueprint(build_rtmp_blueprint())
    client = app.test_client()
    assert client.get("/api/admin/rtmp/runtime").status_code == 401
    assert client.get("/api/admin/rtmp/channels").status_code == 401
    assert client.post("/api/admin/rtmp/streams/control", json={}).status_code == 401


def test_control_invalid_action():
    # 非法 action 返回 400
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "pause", "channel_keys": ["a"]},
    )
    assert res.status_code == 400


def test_control_keys_not_list():
    # channel_keys 非列表返回 400
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "start", "channel_keys": "a"},
    )
    assert res.status_code == 400


def test_control_empty_keys(monkeypatch):
    # 空 keys 时 success:0、total:0，且不应调用 service
    called = []
    monkeypatch.setattr(rtmp_service, "start_hls_to_rtmp_async", lambda *a: called.append(a))
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "start", "channel_keys": []},
    )
    assert res.status_code == 200
    assert res.get_json() == {"success": 0, "total": 0, "errors": []}
    assert called == []


def test_control_start_host(monkeypatch):
    # start 传给 service 的 host 必须指向本机 RTMP 服务的 hls 应用
    captured = []

    def fake_start(host, key):
        captured.append(host)
        return {"accepted": True, "status": "starting"}

    monkeypatch.setattr(rtmp_service, "start_hls_to_rtmp_async", fake_start)
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "start", "channel_keys": ["ch1"]},
    )
    assert res.status_code == 200
    assert len(captured) == 1
    host = captured[0]
    assert host.startswith("rtmp://")
    assert host.endswith("/hls")


def test_control_start_rejected(monkeypatch):
    # service 返回 accepted:False（如 capacity）时不计成功，错误明细带状态
    monkeypatch.setattr(
        rtmp_service,
        "start_hls_to_rtmp_async",
        lambda host, key: {"accepted": False, "status": "capacity"},
    )
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "start", "channel_keys": ["ch1"]},
    )
    data = res.get_json()
    assert data["success"] == 0
    assert data["total"] == 1
    assert data["errors"] == [{"channel_key": "ch1", "message": "capacity"}]


def test_control_start_exception_isolated(monkeypatch):
    # 单个 key 抛异常不影响后续 key，最终计数与错误明细正确
    def fake_start(host, key):
        if key == "bad":
            raise RuntimeError("ffmpeg boom")
        return {"accepted": True, "status": "starting"}

    monkeypatch.setattr(rtmp_service, "start_hls_to_rtmp_async", fake_start)
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "start", "channel_keys": ["a", "bad", "b"]},
    )
    data = res.get_json()
    assert data["success"] == 2
    assert data["total"] == 3
    assert data["errors"] == [{"channel_key": "bad", "message": "ffmpeg boom"}]


def test_control_restart_stop_before_start(monkeypatch):
    # restart 必须对同一 key 先调 stop_stream 再调 start_hls_to_rtmp_async
    calls = []

    def fake_start(host, key):
        calls.append(("start", key, host))
        return {"accepted": True, "status": "starting"}

    def fake_stop(key):
        calls.append(("stop", key))

    monkeypatch.setattr(rtmp_service, "start_hls_to_rtmp_async", fake_start)
    monkeypatch.setattr(rtmp_service, "stop_stream", fake_stop)
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "restart", "channel_keys": ["ch1", "ch2"]},
    )
    data = res.get_json()
    assert data["success"] == 2
    assert data["errors"] == []
    for key in ("ch1", "ch2"):
        stop_idx = next(i for i, c in enumerate(calls) if c[0] == "stop" and c[1] == key)
        start_idx = next(i for i, c in enumerate(calls) if c[0] == "start" and c[1] == key)
        assert stop_idx < start_idx
    # start 收到的 host 同样指向 hls 应用
    assert all(c[2].startswith("rtmp://") and c[2].endswith("/hls") for c in calls if c[0] == "start")


def test_control_stop(monkeypatch):
    # stop 动作只调用 stop_stream，不调用启动函数
    stopped = []
    monkeypatch.setattr(rtmp_service, "stop_stream", lambda key: stopped.append(key))
    monkeypatch.setattr(
        rtmp_service,
        "start_hls_to_rtmp_async",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("stop 不应启动转推")),
    )
    res = _client().post(
        "/api/admin/rtmp/streams/control",
        json={"action": "stop", "channel_keys": ["ch1", "ch2"]},
    )
    data = res.get_json()
    assert data["success"] == 2
    assert data["total"] == 2
    assert data["errors"] == []
    assert stopped == ["ch1", "ch2"]
