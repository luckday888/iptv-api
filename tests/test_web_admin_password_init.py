import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask

from service.web.api.auth import build_auth_blueprint
from utils.config import ConfigManager, config


def test_empty_password_generated_and_persisted(tmp_path):
    # 默认配置密码为空时，构造即生成随机密码并落盘到 user_config.ini
    user_config = tmp_path / "user_config.ini"
    cm = ConfigManager(user_config_path=str(user_config))
    password = cm.admin_password
    assert isinstance(password, str)
    assert password != ""
    assert user_config.exists()
    assert password in user_config.read_text(encoding="utf-8")

    # 再次用同一 user_config_path 构造时沿用已落盘密码，不重新生成
    cm_again = ConfigManager(user_config_path=str(user_config))
    assert cm_again.admin_password == password


def test_env_password_skips_generation(tmp_path):
    # 环境变量注入密码时不生成随机密码，也不落盘
    user_config = tmp_path / "user_config.ini"
    cm = ConfigManager(
        user_config_path=str(user_config),
        environ={"ADMIN_PASSWORD": "env-secret-123"},
    )
    assert cm.admin_password == "env-secret-123"
    assert not user_config.exists()


def test_blank_env_password_keeps_persisted(tmp_path):
    # Compose 占位产生的空字符串环境变量视为未设置，
    # 不得清空已落盘的管理密码并触发重新生成
    user_config = tmp_path / "user_config.ini"
    cm = ConfigManager(user_config_path=str(user_config))
    password = cm.admin_password

    cm_again = ConfigManager(
        user_config_path=str(user_config),
        environ={"ADMIN_PASSWORD": ""},
    )
    assert cm_again.admin_password == password


def test_login_blocked_when_password_empty(monkeypatch):
    # monkeypatch 使管理密码为空：任意登录输入均被拒，且不签发会话 cookie
    monkeypatch.setattr(
        type(config), "admin_password", property(lambda self: "")
    )
    app = Flask(__name__)
    app.register_blueprint(build_auth_blueprint())
    client = app.test_client()

    for payload in ({"password": ""}, {"password": "anything"}):
        res = client.post("/api/admin/auth/login", json=payload)
        assert res.status_code != 200
        assert res.status_code == 403
        assert "Set-Cookie" not in res.headers
