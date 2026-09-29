from flask import Blueprint


def build_logs_blueprint():
    # 日志查看蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_logs", __name__, url_prefix="/api/admin/logs")
