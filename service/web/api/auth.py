from flask import Blueprint, jsonify, request

from service.web.auth.session import COOKIE_NAME, verify_session
from utils.config import config


def build_auth_blueprint():
    bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin/auth")

    @bp.get("/session")
    def get_session():
        # 读取请求 cookie 判断当前登录状态，无需登录即可访问
        logged_in = verify_session(request.cookies.get(COOKIE_NAME, ""))
        return jsonify({
            "logged_in": logged_in,
            "password_configured": bool(config.admin_password),
        })

    return bp
