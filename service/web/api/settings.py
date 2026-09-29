from flask import Blueprint


def build_settings_blueprint():
    # 系统设置蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_settings", __name__, url_prefix="/api/admin/settings")
