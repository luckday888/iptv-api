import os, sys

# 保证可直接导入项目根下的 service 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask
from service.web.api.about import build_about_blueprint
from service.web.auth.session import create_session, COOKIE_NAME


def _client():
    # 构造仅挂载关于蓝图的测试应用，并注入管理员会话 Cookie
    app = Flask(__name__)
    app.register_blueprint(build_about_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_version():
    # 已登录管理员可读取版本信息
    res = _client().get("/api/admin/about/version")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) >= {"name", "version", "repository"}
