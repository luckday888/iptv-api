from flask import Blueprint


def build_update_blueprint():
    # 更新操作蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_update", __name__, url_prefix="/api/admin/update")
