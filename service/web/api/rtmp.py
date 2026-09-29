from flask import Blueprint


def build_rtmp_blueprint():
    # RTMP 推流管理蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_rtmp", __name__, url_prefix="/api/admin/rtmp")
