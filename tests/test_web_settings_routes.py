import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask

from service.web.api.settings import build_settings_blueprint
from service.web.auth.session import COOKIE_NAME, create_session

# 设置页管理的配置段
_SECTION = "Settings"


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


@pytest.fixture
def env_locked_open_update():
    # 伪造 open_update 被环境变量锁定，用例结束恢复 _sources 避免污染
    from service.web.api import settings as settings_mod

    sources = settings_mod.config._sources
    marker = (_SECTION, "open_update")
    existed = marker in sources
    original = sources.get(marker)
    sources[marker] = "环境变量 APP_PORT"
    try:
        yield
    finally:
        if existed:
            sources[marker] = original
        else:
            sources.pop(marker, None)


def test_get_env_locked_key_read_only(env_locked_open_update):
    # 环境变量锁定键在 GET 中标记只读并回填环境变量名
    res = _client().get("/api/admin/settings")
    assert res.status_code == 200
    item = next(i for i in res.get_json()["items"] if i["key"] == "open_update")
    assert item["read_only"] is True
    assert item["env_name"] == "APP_PORT"


def test_save_env_locked_key_rejected(env_locked_open_update, monkeypatch):
    # 环境变量锁定键保存前被拒绝，不触发 config.set/save
    from service.web.api import settings as settings_mod

    touched = []
    monkeypatch.setattr(
        settings_mod.config,
        "set",
        lambda section, key, value: touched.append((section, key, value)),
    )
    monkeypatch.setattr(settings_mod.config, "save", lambda: touched.append("save"))

    res = _client().put(
        "/api/admin/settings",
        json={"items": [{"key": "open_update", "value": "True"}]},
    )
    assert res.status_code == 400
    assert res.get_json()["details"]["open_update"] == "该配置被环境变量锁定"
    assert touched == []


def test_get_resolution_speed_map_raw():
    # 该配置 property 返回 dict，GET 必须返回 ini 原始逗号串，保证回填保存闭环
    from service.web.api import settings as settings_mod

    res = _client().get("/api/admin/settings")
    item = next(i for i in res.get_json()["items"]
                if i["key"] == "resolution_speed_map")
    expected = settings_mod.config.config.get(_SECTION, "resolution_speed_map")
    assert item["value"] == expected
    assert "{" not in item["value"]


def test_get_settings_requires_login():
    # 未登录访问设置接口返回 401
    app = Flask(__name__)
    app.register_blueprint(build_settings_blueprint())
    res = app.test_client().get("/api/admin/settings")
    assert res.status_code == 401
