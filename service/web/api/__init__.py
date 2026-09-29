from service.web.api.auth import build_auth_blueprint
from service.web.api.dashboard import build_dashboard_blueprint
from service.web.api.update import build_update_blueprint
from service.web.api.channels import build_channels_blueprint
from service.web.api.screenshots import build_screenshots_blueprint
from service.web.api.sources import build_sources_blueprint
from service.web.api.rtmp import build_rtmp_blueprint
from service.web.api.logs import build_logs_blueprint
from service.web.api.tasks import build_tasks_blueprint
from service.web.api.settings import build_settings_blueprint
from service.web.api.about import build_about_blueprint


def register_api(app):
    # 遍历 11 个蓝图 builder 统一注册到 Flask 应用
    for builder in (
        build_auth_blueprint, build_dashboard_blueprint, build_update_blueprint,
        build_channels_blueprint, build_screenshots_blueprint,
        build_sources_blueprint, build_rtmp_blueprint,
        build_logs_blueprint, build_tasks_blueprint, build_settings_blueprint,
        build_about_blueprint,
    ):
        app.register_blueprint(builder())
