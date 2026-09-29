from functools import wraps

from flask import jsonify, request

from service.web.auth.session import COOKIE_NAME, verify_session


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME, "")
        if not verify_session(token):
            return jsonify({"error": "未登录或会话已过期"}), 401
        return view(*args, **kwargs)
    return wrapper
