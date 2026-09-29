from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from utils.config import CONFIG_SCHEMA, config

# CONFIG_SCHEMA 中的配置键全部位于 config.ini 的 [Settings] 段
_SECTION = "Settings"

# config._sources 中环境变量来源的前缀，完整形如 "环境变量 APP_PORT"
_ENV_SOURCE_PREFIX = "环境变量"


def _env_locked_keys():
    # 扫描配置来源，返回 [Settings] 段被环境变量锁定的键及其环境变量名
    locked = {}
    for (section, key), source in getattr(config, "_sources", {}).items():
        if section != _SECTION or not isinstance(source, str):
            continue
        if source.startswith(_ENV_SOURCE_PREFIX):
            env_name = source[len(_ENV_SOURCE_PREFIX):].strip()
            locked[key] = env_name or None
    return locked


def _kind_label(rule):
    # 返回配置项类型，缺省按字符串处理
    return getattr(rule, "kind", "string") or "string"


def build_settings_blueprint():
    bp = Blueprint("admin_settings", __name__, url_prefix="/api/admin/settings")
    # 蓝图构建时绑定环境变量锁定键，运行期保持只读判断一致
    env_locked = _env_locked_keys()

    @bp.get("")
    @admin_required
    def get_settings():
        # 读取配置元数据与当前值，供前端渲染设置表单
        items = []
        for key, rule in CONFIG_SCHEMA.items():
            value = getattr(config, key, None)
            items.append(
                {
                    "key": key,
                    "value": "" if value is None else str(value),
                    "kind": _kind_label(rule),
                    "description": "",
                    "options": list(getattr(rule, "choices", None) or []),
                    "advanced": False,
                    "read_only": key in env_locked,
                    "env_name": env_locked.get(key),
                }
            )
        return jsonify({"items": items})

    @bp.put("")
    @admin_required
    def save_settings():
        # 批量校验并保存配置，校验（含未知键、环境变量锁定）在落盘前完成
        payload = request.get_json(silent=True) or {}
        items = payload.get("items", [])
        if not isinstance(items, list):
            return jsonify({"error": "items 必须为数组"}), 400

        details = {}
        for entry in items:
            if not isinstance(entry, dict):
                return jsonify({"error": "items 条目必须为对象", "details": {}}), 400
            key = entry.get("key", "")
            if key not in CONFIG_SCHEMA:
                details[key] = "未知配置项"
                continue
            if key in env_locked:
                details[key] = "该配置被环境变量锁定"
        if details:
            return jsonify({"error": "存在无法保存的配置", "details": details}), 400

        try:
            for entry in items:
                # 前端表单值按字符串提交；None 视为清空
                raw = entry.get("value", "")
                value = "" if raw is None else str(raw)
                config.set(_SECTION, entry["key"], value)
            config.save()
        except Exception as exc:  # 校验失败时 config.save 抛出异常
            return jsonify({"error": str(exc), "details": {}}), 400
        return jsonify({"ok": True})

    return bp
