import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.dashboard import build_dashboard_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    # 构建带登录会话的测试客户端
    app = Flask(__name__)
    app.register_blueprint(build_dashboard_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_metrics_requires_auth():
    # 未登录访问 metrics 必须返回 401
    app = Flask(__name__)
    app.register_blueprint(build_dashboard_blueprint())
    assert app.test_client().get("/api/admin/dashboard/metrics").status_code == 401


def test_metrics_shape():
    # 登录后返回字段形状应包含核心指标键
    data = _client().get("/api/admin/dashboard/metrics").get_json()
    assert set(data) >= {"run_status", "channel_total", "valid_total"}


def test_channels_paginated():
    # 分页频道表返回结构与请求参数保持一致
    res = _client().get("/api/admin/dashboard/channels?page=1&page_size=10")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) == {"items", "total", "page", "page_size"}
