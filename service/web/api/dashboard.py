from flask import Blueprint


def build_dashboard_blueprint():
    # 仪表盘蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_dashboard", __name__, url_prefix="/api/admin/dashboard")
