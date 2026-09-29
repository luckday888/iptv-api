from flask import Blueprint


def build_channels_blueprint():
    # 频道管理蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_channels", __name__, url_prefix="/api/admin/channels")
