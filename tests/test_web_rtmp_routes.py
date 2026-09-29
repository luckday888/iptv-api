import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask

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
