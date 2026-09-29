import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil

import pytest
from flask import Flask

from service.web.api import channels as channels_mod
from service.web.api.channels import build_channels_blueprint
from service.web.auth.session import COOKIE_NAME, create_session
from utils import channel_repository as repo


def _client():
    # 构建仅挂载频道蓝图并带登录会话的测试客户端
    app = Flask(__name__)
    app.register_blueprint(build_channels_blueprint())
    client = app.test_client()
    client.set_cookie(COOKIE_NAME, create_session(), domain="localhost")
    return client


@pytest.fixture
def temp_db(monkeypatch):
    # 使用项目 tmp 目录下的独立数据库，避免污染真实 channel_results.db
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp", "b5-test"
    )
    os.makedirs(base, exist_ok=True)
    db_path = os.path.join(base, "channel_results.db")
    repo.ensure_channel_repository(db_path)
    monkeypatch.setattr(channels_mod, "channel_results_path", db_path)
    yield db_path
    shutil.rmtree(base, ignore_errors=True)


def test_categories():
    res = _client().get("/api/admin/channels/categories")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_channels_paginated():
    res = _client().get("/api/admin/channels?page=1&page_size=20")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) == {"items", "total", "page", "page_size"}


def test_results_of_missing_channel():
    res = _client().get("/api/admin/channels/nope/results")
    assert res.status_code == 404


def test_detail_of_missing_channel():
    res = _client().get("/api/admin/channels/nope")
    assert res.status_code == 404


def test_routes_require_auth():
    # 未登录访问各类路由必须返回 401
    client = Flask(__name__)
    client.register_blueprint(build_channels_blueprint())
    c = client.test_client()
    assert c.get("/api/admin/channels").status_code == 401
    assert c.post("/api/admin/channels", json={"name": "x"}).status_code == 401
    assert c.delete("/api/admin/channels", json={"channel_keys": ["x"]}).status_code == 401
    assert c.get("/api/admin/channels/k/results").status_code == 401
    assert c.get("/api/admin/channels/k/selection").status_code == 401
    assert c.put("/api/admin/channels/k/logo", json={"logo": ""}).status_code == 401
    assert c.put("/api/admin/channels/k/selection", json={"result_keys": []}).status_code == 401


def test_list_empty_path_no_trailing_slash(temp_db):
    # 空路径规则必须能被无尾斜杠 URL 命中，且不发生重定向
    res = _client().get("/api/admin/channels")
    assert res.status_code == 200
    assert res.get_json()["items"] == []


def test_create_channel_validation(temp_db):
    client = _client()
    assert client.post("/api/admin/channels", json={"name": "  "}).status_code == 400
    res = client.post(
        "/api/admin/channels", json={"name": "CCTV-TEST", "category": "自定义"}
    )
    assert res.status_code == 200
    assert res.get_json()["channel_key"]


def test_channel_lifecycle(temp_db):
    client = _client()
    key = client.post(
        "/api/admin/channels", json={"name": "我的频道"}
    ).get_json()["channel_key"]
    # 详情可查
    assert client.get(f"/api/admin/channels/{key}").status_code == 200
    # 列表能检索到
    rows = client.get("/api/admin/channels?search=我的频道").get_json()
    assert rows["total"] == 1
    # 批量删除
    res = client.delete("/api/admin/channels", json={"channel_keys": [key]})
    assert res.get_json()["deleted"] == 1
    assert client.get(f"/api/admin/channels/{key}").status_code == 404


def test_delete_channels_validation(temp_db):
    client = _client()
    assert client.delete("/api/admin/channels", json={"channel_keys": []}).status_code == 400
    assert client.delete("/api/admin/channels", json={}).status_code == 400


def test_result_lifecycle(temp_db):
    client = _client()
    key = client.post("/api/admin/channels", json={"name": "结果频道"}).get_json()[
        "channel_key"
    ]
    # 新增结果
    assert (
        client.post(f"/api/admin/channels/{key}/results", json={}).status_code == 400
    )
    rkey = client.post(
        f"/api/admin/channels/{key}/results", json={"url": "http://example.com/a.m3u8"}
    ).get_json()["result_key"]
    rows = client.get(f"/api/admin/channels/{key}/results").get_json()
    assert any(r["result_key"] == rkey for r in rows)
    # 删除结果
    res = client.delete(
        f"/api/admin/channels/{key}/results", json={"result_keys": [rkey]}
    )
    assert res.status_code == 200
    assert res.get_json()["deleted"] == [rkey]


def test_add_result_to_missing_channel(temp_db):
    client = _client()
    res = client.post(
        "/api/admin/channels/nope/results", json={"url": "http://example.com/a"}
    )
    assert res.status_code == 404


def test_logo_update(temp_db):
    client = _client()
    key = client.post("/api/admin/channels", json={"name": "台标频道"}).get_json()[
        "channel_key"
    ]
    res = client.put(
        f"/api/admin/channels/{key}/logo", json={"logo": "/logo/x.png"}
    )
    assert res.status_code == 200
    assert res.get_json() == {"ok": True}
    detail = client.get(f"/api/admin/channels/{key}").get_json()
    assert detail.get("logo") == "/logo/x.png"


def test_selection_put_and_reset(temp_db):
    client = _client()
    key = client.post("/api/admin/channels", json={"name": "选择频道"}).get_json()[
        "channel_key"
    ]
    rkey = client.post(
        f"/api/admin/channels/{key}/results", json={"url": "http://example.com/s.m3u8"}
    ).get_json()["result_key"]
    # 入参必须是非空列表
    assert (
        client.put(f"/api/admin/channels/{key}/selection", json={}).status_code == 400
    )
    assert (
        client.put(
            f"/api/admin/channels/{key}/selection", json={"result_keys": []}
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/admin/channels/{key}/selection", json={"result_keys": "x"}
        ).status_code
        == 400
    )
    res = client.put(
        f"/api/admin/channels/{key}/selection", json={"result_keys": [rkey]}
    )
    assert res.status_code == 200
    assert res.get_json() == {"ok": True}
    detail = client.get(f"/api/admin/channels/{key}").get_json()
    assert detail.get("selection_mode") == "manual"
    # 读取手动选择，items 按 rank 升序且元素含 result_key/rank
    res = client.get(f"/api/admin/channels/{key}/selection")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) == {"mode", "items"}
    assert data["mode"] == "manual"
    assert data["items"] == [{"result_key": rkey, "rank": 1}]
    # 不存在的频道返回 404
    assert client.get("/api/admin/channels/nope/selection").status_code == 404
    # 重置为自动
    res = client.post(f"/api/admin/channels/{key}/selection/reset")
    assert res.status_code == 200
    assert res.get_json() == {"ok": True}
    detail = client.get(f"/api/admin/channels/{key}").get_json()
    assert detail.get("selection_mode") == "auto"
    # 自动模式下无手动选择项
    data = client.get(f"/api/admin/channels/{key}/selection").get_json()
    assert data == {"mode": "auto", "items": []}


def test_selection_get_ranks_order(temp_db):
    # GET selection 必须按 selected_rank 升序返回已选接口
    client = _client()
    key = client.post(
        "/api/admin/channels", json={"name": "排序频道"}
    ).get_json()["channel_key"]
    r1 = client.post(
        f"/api/admin/channels/{key}/results", json={"url": "http://example.com/1"}
    ).get_json()["result_key"]
    r2 = client.post(
        f"/api/admin/channels/{key}/results", json={"url": "http://example.com/2"}
    ).get_json()["result_key"]
    # 反序提交，校验返回仍按 rank 升序
    client.put(
        f"/api/admin/channels/{key}/selection", json={"result_keys": [r2, r1]}
    )
    data = client.get(f"/api/admin/channels/{key}/selection").get_json()
    assert data["mode"] == "manual"
    assert data["items"] == [
        {"result_key": r2, "rank": 1},
        {"result_key": r1, "rank": 2},
    ]
