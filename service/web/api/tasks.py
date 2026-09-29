# 任务历史蓝图：合并运行历史与操作历史，按开始时间倒序分页
from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from utils import channel_repository as repo
from utils.constants import channel_results_path


def build_tasks_blueprint():
    bp = Blueprint("admin_tasks", __name__, url_prefix="/api/admin/tasks")

    @bp.get("")
    @admin_required
    def list_all():
        # 解析分页参数：page 从 1 开始，page_size 限制在 [1, 200]
        page = max(1, request.args.get("page", 1, type=int))
        page_size = min(200, max(1, request.args.get("page_size", 50, type=int)))
        # 读取运行历史与操作历史（上限 500 防止内存膨胀）
        runs = repo.list_runs(channel_results_path, limit=500)
        operations = repo.list_operations(channel_results_path, limit=500)

        items = []
        # 运行历史映射为统一结构
        for run in runs:
            started = run.get("started_at")
            finished = run.get("finished_at")
            items.append({
                "id": run.get("run_id"),
                "source": "run",
                "started_at": started,
                "finished_at": finished,
                "status": run.get("status"),
                "task": "full_update",
                "target": "完整更新",
                # duration 仅在起止时间齐全时计算
                "duration": (finished - started) if started and finished else None,
                "details": run.get("error"),
            })
        # 操作历史映射为统一结构
        for op in operations:
            started = op.get("started_at")
            finished = op.get("finished_at")
            items.append({
                "id": op.get("operation_id"),
                "source": "operation",
                "started_at": started,
                "finished_at": finished,
                "status": op.get("status"),
                "task": op.get("operation"),
                "target": op.get("target_key"),
                "duration": (finished - started) if started and finished else None,
                "details": op.get("message"),
            })

        # 按开始时间倒序，缺失开始时间的排到最后
        items.sort(key=lambda row: row.get("started_at") or 0, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return jsonify({"items": items[start:start + page_size], "total": total,
                        "page": page, "page_size": page_size})

    return bp
