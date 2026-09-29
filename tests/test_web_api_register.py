import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web import register_web


def test_register_routes():
    app = Flask(__name__)
    register_web(app)
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/admin/auth/session" in rules


def test_session_payload_without_login():
    # /session 无需登录即可访问，返回登录状态与是否已配置管理密码
    app = Flask(__name__)
    register_web(app)
    client = app.test_client()
    resp = client.get("/api/admin/auth/session")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["logged_in"] is False
    assert isinstance(data["password_configured"], bool)
