import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from flask import Flask, jsonify
from service.web.auth.session import COOKIE_NAME
from service.web.auth.decorators import admin_required
from service.web.api.auth import build_auth_blueprint
from utils.config import config


def _client(with_probe=False):
    app = Flask(__name__)
    app.register_blueprint(build_auth_blueprint())
    if with_probe:
        # 临时探针路由，用于验证会话 cookie 对受保护端点的实际效力
        @app.get("/probe/protected")
        @admin_required
        def _probe():
            return jsonify({"ok": True})
    return app.test_client()


def _extract_token(set_cookie_header):
    # 从 Set-Cookie 头中取出会话令牌值
    prefix = COOKIE_NAME + "="
    for part in set_cookie_header.split(";"):
        part = part.strip()
        if part.startswith(prefix):
            return part[len(prefix):]
    return ""


def _login(client):
    res = client.post("/api/admin/auth/login",
                      json={"password": config.admin_password})
    assert res.status_code == 200
    return _extract_token(res.headers.get("Set-Cookie", ""))


def test_session_when_not_login():
    res = _client().get("/api/admin/auth/session")
    assert res.status_code == 200
    assert res.get_json()["logged_in"] is False


def test_login_wrong_password():
    res = _client().post("/api/admin/auth/login", json={"password": "wrong"})
    assert res.status_code == 401


def test_login_non_ascii_wrong_password():
    # 非 ASCII 密码校验失败应返回 401，不能抛 TypeError 导致 500
    res = _client().post("/api/admin/auth/login", json={"password": "错误密码"})
    assert res.status_code == 401


def test_login_then_logout():
    client = _client()
    res = client.post("/api/admin/auth/login",
                      json={"password": config.admin_password})
    # 默认密码为空串时同样可登录
    assert res.status_code == 200
    set_cookie = res.headers.get("Set-Cookie", "")
    assert COOKIE_NAME in set_cookie
    # cookie 固定 Path=/，保证可发往其它管理蓝图
    assert "Path=/" in set_cookie
    out = client.post("/api/admin/auth/logout")
    assert out.status_code == 200
    # 登出删除 cookie 时路径必须与写入时一致
    assert "Path=/" in out.headers.get("Set-Cookie", "")


def test_login_rate_limit_returns_429():
    # 使用独立对端 IP 并清空计数，避免受其它用例的失败记录影响
    from service.web.api import auth as auth_module
    ip = "198.51.100.77"
    auth_module._failures.pop(ip, None)
    client = _client()
    statuses = [
        client.post(
            "/api/admin/auth/login",
            json={"password": "wrong"},
            environ_overrides={"REMOTE_ADDR": ip},
        ).status_code
        for _ in range(config.admin_login_rate_limit)
    ]
    # 前 limit-1 次为 401，达到阈值后的请求返回 429
    assert statuses[-1] == 401
    blocked = client.post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
        environ_overrides={"REMOTE_ADDR": ip},
    )
    assert blocked.status_code == 429
    auth_module._failures.pop(ip, None)


def test_rate_limit_per_x_real_ip():
    # 同一 X-Real-IP 连续失败达到阈值后被限流
    from service.web.api import auth as auth_module
    ip = "203.0.113.77"
    auth_module._failures.pop(ip, None)
    client = _client()
    for _ in range(config.admin_login_rate_limit):
        res = client.post(
            "/api/admin/auth/login",
            json={"password": "wrong"},
            headers={"X-Real-IP": ip},
        )
        assert res.status_code == 401
    blocked = client.post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
        headers={"X-Real-IP": ip},
    )
    assert blocked.status_code == 429
    auth_module._failures.pop(ip, None)


def test_rate_limit_buckets_isolated_per_x_real_ip():
    # 两个不同 X-Real-IP 的失败计数互不影响
    from service.web.api import auth as auth_module
    ip_a = "203.0.113.10"
    ip_b = "203.0.113.20"
    auth_module._failures.pop(ip_a, None)
    auth_module._failures.pop(ip_b, None)
    client = _client()
    # A 先累计 limit-1 次失败
    for _ in range(config.admin_login_rate_limit - 1):
        assert client.post(
            "/api/admin/auth/login",
            json={"password": "wrong"},
            headers={"X-Real-IP": ip_a},
        ).status_code == 401
    # B 独立累计到被限流
    for _ in range(config.admin_login_rate_limit):
        assert client.post(
            "/api/admin/auth/login",
            json={"password": "wrong"},
            headers={"X-Real-IP": ip_b},
        ).status_code == 401
    assert client.post(
        "/api/admin/auth/login",
        json={"password": "wrong"},
        headers={"X-Real-IP": ip_b},
    ).status_code == 429
    # A 的桶未受 B 影响，正确密码仍可登录成功
    ok = client.post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
        headers={"X-Real-IP": ip_a},
    )
    assert ok.status_code == 200
    auth_module._failures.pop(ip_a, None)
    auth_module._failures.pop(ip_b, None)


def test_rate_limit_fallback_to_remote_addr():
    # 无 X-Real-IP（直连）时限流回退到对端地址
    from service.web.api import auth as auth_module
    ip = "198.51.100.88"
    auth_module._failures.pop(ip, None)
    client = _client()
    for _ in range(config.admin_login_rate_limit):
        assert client.post(
            "/api/admin/auth/login",
            json={"password": "wrong"},
            environ_overrides={"REMOTE_ADDR": ip},
        ).status_code == 401
    assert client.post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
        environ_overrides={"REMOTE_ADDR": ip},
    ).status_code == 429
    auth_module._failures.pop(ip, None)


def test_login_cookie_secure_over_https():
    # nginx 透传 X-Forwarded-Proto: https 时 cookie 带 Secure
    res = _client().post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert res.status_code == 200
    assert "Secure" in res.headers.get("Set-Cookie", "")


def test_login_cookie_not_secure_over_http():
    # 未透传 https（即 http 请求）时 cookie 不带 Secure
    res = _client().post(
        "/api/admin/auth/login",
        json={"password": config.admin_password},
    )
    assert res.status_code == 200
    assert "Secure" not in res.headers.get("Set-Cookie", "")



@pytest.fixture
def password_change_ctx(monkeypatch):
    # 屏蔽配置落盘，用例结束后恢复原管理密码，避免污染其它测试
    monkeypatch.setattr(config, "save", lambda: None)
    original_password = config.admin_password
    yield
    config.set("Settings", "admin_password", original_password)


def test_change_password_requires_login(password_change_ctx):
    res = _client().put(
        "/api/admin/auth/password",
        json={"old_password": config.admin_password, "new_password": "newpass"},
    )
    assert res.status_code == 401


def test_change_password_wrong_old(password_change_ctx):
    client = _client()
    _login(client)
    res = client.put(
        "/api/admin/auth/password",
        json={"old_password": "旧密码错误", "new_password": "newpass"},
    )
    # 原密码错误（含非 ASCII）返回 401 而非 500
    assert res.status_code == 401


def test_change_password_empty_new(password_change_ctx):
    client = _client()
    _login(client)
    res = client.put(
        "/api/admin/auth/password",
        json={"old_password": config.admin_password, "new_password": ""},
    )
    assert res.status_code == 400


def test_change_password_success_invalidates_old_token(password_change_ctx):
    client = _client(with_probe=True)
    token = _login(client)
    # 改密前旧 cookie 可正常访问受保护端点
    assert client.get("/probe/protected").status_code == 200
    res = client.put(
        "/api/admin/auth/password",
        json={"old_password": config.admin_password,
              "new_password": "new-password-123"},
    )
    assert res.status_code == 200
    set_cookie = res.headers.get("Set-Cookie", "")
    # 成功后删除 cookie，路径与登录 cookie 一致
    assert COOKIE_NAME in set_cookie
    assert "Path=/" in set_cookie
    # 用独立客户端携带旧令牌访问探针，旧会话须立即失效
    fresh = _client(with_probe=True)
    probe = fresh.get(
        "/probe/protected",
        headers={"Cookie": f"{COOKIE_NAME}={token}"},
    )
    assert probe.status_code == 401
