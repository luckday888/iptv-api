import os

from flask import send_from_directory

from service.web.api import register_api

# SPA 构建产物目录
_DIST_DIR = os.path.join(os.getcwd(), "web_admin", "dist")


def register_web(app):
    # 注册全部管理 REST API
    register_api(app)

    if not os.path.isdir(_DIST_DIR):
        # 未构建前端时仅提供 API，不托管静态资源
        return

    @app.get("/admin/")
    def admin_index():
        return send_from_directory(_DIST_DIR, "index.html")

    @app.get("/admin/<path:asset>")
    def admin_asset(asset):
        # 命中真实文件返回文件，其余回退 index.html（支持前端路由）
        full = os.path.join(_DIST_DIR, asset)
        if os.path.isfile(full):
            return send_from_directory(_DIST_DIR, asset)
        return send_from_directory(_DIST_DIR, "index.html")
