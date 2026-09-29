import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.channels import build_channels_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    app = Flask(__name__)
    app.register_blueprint(build_channels_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_screenshot_metadata_missing():
    # 不存在的 result_key 返回 404
    res = _client().get("/api/admin/screenshots/nope-key")
    assert res.status_code == 404


def test_retest_missing_channel():
    res = _client().post("/api/admin/channels/nope/retest")
    assert res.status_code == 404
