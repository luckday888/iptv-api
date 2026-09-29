from flask import Blueprint, jsonify

from service.web.auth.decorators import admin_required
from utils import channel_repository as repo
from utils.constants import channel_results_path


def build_screenshots_blueprint():
    # 截图元数据独立资源：按 result_key 查询，路径前缀 /api/admin/screenshots
    bp = Blueprint("admin_screenshots", __name__, url_prefix="/api/admin/screenshots")

    @bp.get("/<result_key>")
    @admin_required
    def screenshot_metadata(result_key):
        row = repo.get_stream_screenshot(channel_results_path, result_key)
        if row is None:
            return jsonify({"error": "截图不存在"}), 404
        return jsonify(row)

    return bp
