import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.auth.session import COOKIE_NAME
from service.web.api.auth import build_auth_blueprint
from utils.config import config


def _client():
    app = Flask(__name__)
    app.register_blueprint(build_auth_blueprint())
    return app.test_client()


def test_session_when_not_login():
    res = _client().get("/api/admin/auth/session")
    assert res.status_code == 200
    assert res.get_json()["logged_in"] is False


def test_login_wrong_password():
    res = _client().post("/api/admin/auth/login", json={"password": "wrong"})
    assert res.status_code == 401


def test_login_then_logout():
    client = _client()
    res = client.post("/api/admin/auth/login",
                      json={"password": config.admin_password})
    # 默认密码为空串时同样可登录
    assert res.status_code == 200
    assert COOKIE_NAME in res.headers.get("Set-Cookie", "")
    out = client.post("/api/admin/auth/logout")
    assert out.status_code == 200


def test_login_rate_limit_returns_429():
    # 使用独立 IP 并清空计数，避免受其它用例的失败记录影响
    from service.web.api import auth as auth_module
    ip = "198.51.100.77"
    auth_module._failures.pop(ip, None)
    client = _client()
    statuses = [
        client.post(
            "/api/admin/auth/login",
            json={"password": "wrong"},
            headers={"X-Forwarded-For": ip},
        ).status_code
        for _ in range(config.admin_login_rate_limit)
    ]
    # 前 limit-1 次为 401，达到阈值后的请求返回 429
    assert statuses[-1] == 401
    blocked = client.post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
        headers={"X-Forwarded-For": ip},
    )
    assert blocked.status_code == 429
    auth_module._failures.pop(ip, None)
