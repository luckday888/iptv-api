from flask import Blueprint


def build_about_blueprint():
    # 关于信息蓝图骨架，具体路由在后续任务追加
    return Blueprint("admin_about", __name__, url_prefix="/api/admin/about")
