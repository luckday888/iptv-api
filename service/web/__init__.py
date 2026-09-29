from service.web.api import register_api


def register_web(app):
    # 注册全部管理 REST API 蓝图
    register_api(app)
