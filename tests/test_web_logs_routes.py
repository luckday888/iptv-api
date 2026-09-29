import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.logs import build_logs_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    app = Flask(__name__)
    app.register_blueprint(build_logs_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_read_runtime():
    res = _client().get("/api/admin/logs/runtime")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) >= {"lines", "offset", "path"}


def test_unknown_kind():
    assert _client().get("/api/admin/logs/evil").status_code == 404
