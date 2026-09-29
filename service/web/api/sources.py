from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from service.web.files.source_files import (
    SUPPORTED_KINDS, read_raw, resolve_path, write_raw,
)


def build_sources_blueprint():
    # 订阅源管理蓝图：提供源文件读取与保存接口，均需登录
    bp = Blueprint("admin_sources", __name__, url_prefix="/api/admin/sources")

    @bp.get("/<kind>")
    @admin_required
    def get_source(kind):
        # 读取指定类型源文件的原始内容与路径，未知类型返回 404
        if kind not in SUPPORTED_KINDS:
            return jsonify({"error": "不支持的源类型"}), 404
        return jsonify({"path": resolve_path(kind), "raw": read_raw(kind), "rows": []})

    @bp.put("/<kind>")
    @admin_required
    def save_source(kind):
        # 保存指定类型源文件的原始内容，校验类型与入参，未知类型返回 404
        if kind not in SUPPORTED_KINDS:
            return jsonify({"error": "不支持的源类型"}), 404
        raw = (request.get_json(silent=True) or {}).get("raw")
        if not isinstance(raw, str):
            return jsonify({"error": "raw 必须为字符串"}), 400
        try:
            path = write_raw(kind, raw)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True, "path": path})

    return bp
