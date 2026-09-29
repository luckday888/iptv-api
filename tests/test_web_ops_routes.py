import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.channels import build_channels_blueprint
from service.web.api.screenshots import build_screenshots_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    app = Flask(__name__)
    app.register_blueprint(build_channels_blueprint())
    app.register_blueprint(build_screenshots_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_screenshot_metadata_missing():
    # 不存在的 result_key 返回 404
    res = _client().get("/api/admin/screenshots/nope-key")
    assert res.status_code == 404


def test_screenshot_metadata_found(monkeypatch):
    # 命中处理器时返回截图元数据，证明路径真实可达
    from service.web.api import screenshots as shots
    monkeypatch.setattr(
        shots.repo, "get_stream_screenshot",
        lambda db_path, result_key: {"result_key": result_key, "image_path": "x.png"})
    res = _client().get("/api/admin/screenshots/k1")
    assert res.status_code == 200
    assert res.get_json()["result_key"] == "k1"


def test_retest_missing_channel():
    res = _client().post("/api/admin/channels/nope/retest")
    assert res.status_code == 404
