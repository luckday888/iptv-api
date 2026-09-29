# 任务历史合并查询接口测试
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.tasks import build_tasks_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    app = Flask(__name__)
    app.register_blueprint(build_tasks_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_tasks_paginated():
    res = _client().get("/api/admin/tasks?page=1&page_size=20")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) == {"items", "total", "page", "page_size"}
    for item in data["items"]:
        assert item["source"] in ("run", "operation")
