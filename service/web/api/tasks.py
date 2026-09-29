from flask import Blueprint


def build_tasks_blueprint():
    # 任务管理蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_tasks", __name__, url_prefix="/api/admin/tasks")
