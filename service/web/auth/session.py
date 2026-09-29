import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from utils.config import config

COOKIE_NAME = "iptv_admin_session"

# 签名密钥：优先使用环境变量，否则基于管理密码派生，密码变更后旧会话失效
def _secret_key() -> str:
    env_key = os.getenv("IPTV_ADMIN_SECRET", "")
    if env_key:
        return env_key
    return f"iptv-admin::{config.admin_password}"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret_key(), salt="iptv-admin-session")


def create_session() -> str:
    """签发会话令牌，有效期由 admin_session_days 配置决定。"""
    max_age = config.admin_session_days * 86400
    return _serializer().dumps({"iat_marker": 1})


def verify_session(token: str) -> bool:
    """校验会话令牌是否有效且未过期。"""
    if not token:
        return False
    max_age = config.admin_session_days * 86400
    try:
        _serializer().loads(token, max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False
