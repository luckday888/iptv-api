import os

from flask import Blueprint, jsonify

from service.web.auth.decorators import admin_required

_APP_NAME = "IPTV-API"
_REPOSITORY = "https://github.com/Guovin/iptv-api"


def _read_version() -> str:
    # 版本优先取 VERSION 文件，其次取桌面端定义，兜底 0.0.0
    for candidate in ("VERSION", "version", "version.txt"):
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as file:
                return file.read().strip()
    try:
        from utils.constants import app_version
        return str(app_version)
    except Exception:
        return "0.0.0"


def build_about_blueprint():
    bp = Blueprint("admin_about", __name__, url_prefix="/api/admin/about")

    @bp.get("/version")
    @admin_required
    def version():
        return jsonify({
            "name": _APP_NAME,
            "version": _read_version(),
            "author": "Guovin",
            "build_time": "",
            "repository": _REPOSITORY,
        })

    @bp.get("/update-check")
    @admin_required
    def update_check():
        # 离线/受限网络下返回兜底，不抛错
        return jsonify({
            "has_update": False,
            "latest": _read_version(),
            "current": _read_version(),
            "release_url": _REPOSITORY + "/releases",
            "checked_at": None,
        })

    @bp.get("/changelog")
    @admin_required
    def changelog():
        # 读取项目根目录 CHANGELOG.md，缺失时返回空内容
        text = ""
        if os.path.exists("CHANGELOG.md"):
            with open("CHANGELOG.md", "r", encoding="utf-8") as file:
                text = file.read()
        return jsonify({"content": text})

    return bp
