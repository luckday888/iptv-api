import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask

from service.web.api.settings import build_settings_blueprint
from service.web.auth.session import COOKIE_NAME, create_session


def _client():
    # 构建仅挂载设置蓝图并带登录会话的测试客户端
    app = Flask(__name__)
    app.register_blueprint(build_settings_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


def test_get_settings():
    # 读取设置元数据与当前值，open_update 为布尔型配置项
    res = _client().get("/api/admin/settings")
    assert res.status_code == 200
    items = res.get_json()["items"]
    keys = {item["key"] for item in items}
    assert "open_update" in keys
    sample = next(item for item in items if item["key"] == "open_update")
    assert set(sample) >= {"key", "value", "kind"}
    assert sample["kind"] == "boolean"


def test_save_unknown_key():
    # 未知配置项在保存前被拒绝，不会产生任何落盘副作用
    res = _client().put(
        "/api/admin/settings",
        json={"items": [{"key": "not_exist", "value": "1"}]},
    )
    assert res.status_code == 400


def test_save_settings(monkeypatch):
    # 合法配置批量保存：统一写入 [Settings] 段，config.save 被打桩不落盘
    from service.web.api import settings as settings_mod

    calls = []
    monkeypatch.setattr(
        settings_mod.config,
        "set",
        lambda section, key, value: calls.append((section, key, value)),
    )
    monkeypatch.setattr(settings_mod.config, "save", lambda: None)

    res = _client().put(
        "/api/admin/settings",
        json={
            "items": [
                {"key": "open_update", "value": "False"},
                {"key": "language", "value": "en"},
            ]
        },
    )
    assert res.status_code == 200
    assert res.get_json()["ok"] is True
    assert calls == [
        ("Settings", "open_update", "False"),
        ("Settings", "language", "en"),
    ]
