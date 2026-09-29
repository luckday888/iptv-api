from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from service.web.tasks.manager import task_manager
from utils import channel_repository as repo
from utils.constants import channel_results_path


def _page_args():
    # 解析分页参数，page 至少为 1，page_size 限制在 1~200
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(200, max(1, request.args.get("page_size", 50, type=int)))
    return page, page_size


def build_dashboard_blueprint():
    bp = Blueprint("admin_dashboard", __name__, url_prefix="/api/admin/dashboard")

    @bp.get("/metrics")
    @admin_required
    def metrics():
        # 汇总频道总量、有效结果数与任务运行状态
        channels = repo.list_channels(channel_results_path)
        channel_total = len(channels)
        valid_total = sum(int(row.get("valid_results") or 0) for row in channels)
        snap = task_manager.snapshot()
        return jsonify({
            "run_status": snap["status"],
            "channel_total": channel_total,
            "valid_total": valid_total,
            "service_status": "unknown",
            "service_url": "",
            "next_run_at": None,
        })

    @bp.get("/channels")
    @admin_required
    def channels():
        # 支持分页与关键字搜索，按内存切片返回当前页
        page, page_size = _page_args()
        search = request.args.get("search", "", type=str)
        rows = repo.list_channels(channel_results_path, search=search)
        total = len(rows)
        start = (page - 1) * page_size
        items = rows[start:start + page_size]
        return jsonify({"items": items, "total": total,
                        "page": page, "page_size": page_size})

    return bp
