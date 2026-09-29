from flask import Blueprint


def build_sources_blueprint():
    # 订阅源管理蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_sources", __name__, url_prefix="/api/admin/sources")
