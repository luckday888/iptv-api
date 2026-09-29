from flask import Blueprint, jsonify

from service.web.auth.decorators import admin_required
from service.web.tasks.manager import TaskRunningError, task_manager


def build_update_blueprint():
    # 更新控制与进度查询接口，全部需要管理员登录
    bp = Blueprint("admin_update", __name__, url_prefix="/api/admin/update")

    @bp.post("/run")
    @admin_required
    def run():
        # 启动更新任务；已有任务运行时返回 409
        try:
            task_manager.start()
        except TaskRunningError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True})

    @bp.post("/pause")
    @admin_required
    def pause():
        # 暂停更新；空闲时为 no-op
        task_manager.pause()
        return jsonify({"ok": True})

    @bp.post("/resume")
    @admin_required
    def resume():
        # 恢复更新；空闲时为 no-op
        task_manager.resume()
        return jsonify({"ok": True})

    @bp.post("/cancel")
    @admin_required
    def cancel():
        # 取消更新；空闲时为 no-op
        task_manager.cancel()
        return jsonify({"ok": True})

    @bp.get("/progress")
    @admin_required
    def progress():
        # 返回当前进度快照（status/title/percent/finished 等）
        return jsonify(task_manager.snapshot())

    return bp
