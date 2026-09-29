import secrets
import threading
import time

from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from service.web.auth.session import COOKIE_NAME, create_session, verify_session
from utils.config import config

# 内存中的登录失败计数：{ip: [timestamp, ...]}
_failures = {}
_lock = threading.Lock()


def _rate_limited(ip: str) -> bool:
    # 仅统计 60 秒窗口内的失败次数，达到配置阈值即拦截
    limit = config.admin_login_rate_limit
    now = time.time()
    with _lock:
        recent = [t for t in _failures.get(ip, []) if now - t < 60]
        _failures[ip] = recent
        return len(recent) >= limit


def _record_failure(ip: str):
    with _lock:
        _failures.setdefault(ip, []).append(time.time())


def _clear_failures(ip: str):
    # 登录成功后清除该 IP 的历史失败计数
    with _lock:
        _failures.pop(ip, None)


def _password_matches(password) -> bool:
    # 按 UTF-8 字节做常量时间比较，兼容非 ASCII 密码
    return secrets.compare_digest(
        str(password).encode("utf-8"),
        config.admin_password.encode("utf-8"),
    )


def build_auth_blueprint():
    bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin/auth")

    @bp.post("/login")
    def login():
        # 密码未初始化（首启逻辑理论上已兜底）时拒绝签发会话
        if not config.admin_password:
            return jsonify({"error": "管理密码未初始化"}), 403
        # 以直连对端地址作为限流维度，不采信可伪造的转发头
        ip = request.remote_addr or "?"
        if _rate_limited(ip):
            return jsonify({"error": "失败次数过多，请稍后再试"}), 429
        password = (request.get_json(silent=True) or {}).get("password", "")
        if not _password_matches(password):
            _record_failure(ip)
            return jsonify({"error": "密码错误"}), 401
        _clear_failures(ip)
        token = create_session()
        days = config.admin_session_days
        resp = jsonify({"username": "admin",
                        "expires_at": time.time() + days * 86400})
        # 固定 Path=/，保证 cookie 在全部管理蓝图间共享
        resp.set_cookie(COOKIE_NAME, token, max_age=days * 86400,
                        path="/", httponly=True, samesite="Lax")
        return resp

    @bp.post("/logout")
    def logout():
        resp = jsonify({"ok": True})
        resp.delete_cookie(COOKIE_NAME, path="/")
        return resp

    @bp.get("/session")
    def session():
        # 无需登录即可访问，供前端判断登录状态与是否已配置管理密码
        token = request.cookies.get(COOKIE_NAME, "")
        if verify_session(token):
            return jsonify({"logged_in": True,
                            "expires_at": time.time() + config.admin_session_days * 86400})
        return jsonify({"logged_in": False,
                        "password_configured": bool(config.admin_password)})

    @bp.put("/password")
    @admin_required
    def change_password():
        body = request.get_json(silent=True) or {}
        old_password = body.get("old_password", "")
        new_password = body.get("new_password", "")
        if not _password_matches(old_password):
            return jsonify({"error": "原密码错误"}), 401
        if not isinstance(new_password, str) or not new_password:
            return jsonify({"error": "新密码不能为空"}), 400
        # 持久化新密码到用户配置文件
        config.set("Settings", "admin_password", new_password)
        config.save()
        # 密钥随密码变更，旧会话失效，删除 cookie 要求重新登录
        resp = jsonify({"ok": True})
        resp.delete_cookie(COOKIE_NAME, path="/")
        return resp

    return bp
