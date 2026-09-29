import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.sources import build_sources_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    # 构建仅挂载订阅源蓝图并已登录的测试客户端
    app = Flask(__name__)
    app.register_blueprint(build_sources_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_read_subscribe():
    res = _client().get("/api/admin/sources/subscribe")
    assert res.status_code == 200
    data = res.get_json()
    assert "raw" in data and "path" in data


def test_unknown_kind():
    assert _client().get("/api/admin/sources/evil").status_code == 404


def test_write_roundtrip():
    client = _client()
    # 先备份原始内容，测试结束还原，避免污染真实订阅源
    original = client.get("/api/admin/sources/subscribe").get_json()["raw"]
    try:
        res = client.put("/api/admin/sources/subscribe", json={"raw": "# test\n"})
        assert res.status_code == 200
        assert client.get("/api/admin/sources/subscribe").get_json()["raw"] == "# test\n"
    finally:
        client.put("/api/admin/sources/subscribe", json={"raw": original})
