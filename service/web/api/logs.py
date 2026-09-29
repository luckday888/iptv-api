import os

from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from utils import constants

# 5 类日志类型到磁盘文件路径的映射
_KIND_PATHS = {
    "runtime": constants.log_path,
    "result": constants.result_log_path,
    "speed": constants.speed_test_log_path,
    "statistics": constants.statistic_log_path,
    "unmatch": constants.unmatch_log_path,
}


def build_logs_blueprint():
    # 日志查看/清空蓝图，支持按类型增量读取与清空
    bp = Blueprint("admin_logs", __name__, url_prefix="/api/admin/logs")

    @bp.get("/<kind>")
    @admin_required
    def read_log(kind):
        # 校验日志类型
        path = _KIND_PATHS.get(kind)
        if path is None:
            return jsonify({"error": "不支持的日志类型"}), 404
        # 解析查询参数：offset 起始字节、limit 返回行数上限、search 过滤关键字
        offset = max(0, request.args.get("offset", 0, type=int))
        limit = min(2000, max(1, request.args.get("limit", 500, type=int)))
        search = request.args.get("search", "", type=str)
        # 文件不存在时按空内容兜底，保留原 offset
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as file:
                file.seek(offset)
                text = file.read()
                new_offset = file.tell()
        except FileNotFoundError:
            text, new_offset = "", offset
        # 仅返回末尾 limit 行，可按关键字过滤
        lines = text.splitlines()[-limit:]
        if search:
            lines = [line for line in lines if search in line]
        return jsonify({"path": path, "offset": new_offset,
                        "truncated": False, "lines": lines})

    @bp.delete("/<kind>")
    @admin_required
    def clear_log(kind):
        # 校验日志类型
        path = _KIND_PATHS.get(kind)
        if path is None:
            return jsonify({"error": "不支持的日志类型"}), 404
        # 以写模式打开即截断文件内容
        open(path, "w", encoding="utf-8").close()
        return jsonify({"ok": True})

    return bp
