# 更新控制与进度接口测试：先登录再访问，未登录一律 401
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.update import build_update_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    # 构造已登录的测试客户端：写入有效会话 Cookie
    app = Flask(__name__)
    app.register_blueprint(build_update_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_progress_requires_auth():
    # 未登录访问进度接口必须 401
    app = Flask(__name__)
    app.register_blueprint(build_update_blueprint())
    res = app.test_client().get("/api/admin/update/progress")
    assert res.status_code == 401


def test_progress_shape():
    # 空闲态快照字段齐全
    res = _client().get("/api/admin/update/progress")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) >= {"status", "title", "percent", "finished"}


def test_pause_when_idle():
    # 空闲时暂停为 no-op，仍返回 200
    res = _client().post("/api/admin/update/pause")
    assert res.status_code == 200
