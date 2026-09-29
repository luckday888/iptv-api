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
            if key == "admin_password":
                # 管理密码不回显，仅允许通过专用改密接口变更
                continue
            if _kind_label(rule) == "resolution_speed_map":
                # property 返回 dict（str 后为 Python repr），直接取 ini 原文保证回填/保存闭环
                value = config.config.get(_SECTION, key, fallback="")
            else:
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
            if key == "admin_password":
                # 管理密码只能走专用改密接口，不允许随通用设置提交
                details[key] = "请通过修改密码功能变更"
                continue
            if key not in CONFIG_SCHEMA:
                details[key] = "未知配置项"
                continue
            if key in env_locked:
                details[key] = "该配置被环境变量锁定"
        if details:
            return jsonify({"error": "存在无法保存的配置", "details": details}), 400

        # 写入前先快照各键原始字符串，供保存失败时回滚内存
        original_values = {}
        for entry in items:
            key = entry["key"]
            original_values[key] = config.config.get(_SECTION, key, fallback="")

        # 全量预校验：任一值非法即整体拒绝，保证内存零改动
        for entry in items:
            key = entry["key"]
            raw = entry.get("value", "")
            value = "" if raw is None else str(raw)
            issues = config._validate_value(
                _SECTION, key, value, CONFIG_SCHEMA[key]
            )
            if issues:
                details[key] = issues[0].message
        if details:
            return jsonify({"error": "存在无法保存的配置", "details": details}), 400

        # 预校验通过后逐个写入再统一落盘；落盘失败时回滚全部内存改动
        try:
            for entry in items:
                # 前端表单值按字符串提交；None 视为清空
                raw = entry.get("value", "")
                value = "" if raw is None else str(raw)
                config.set(_SECTION, entry["key"], value)
            config.save()
        except Exception as exc:  # 校验失败时 config.save 抛出异常
            for key, value in original_values.items():
                config.config.set(_SECTION, key, value)
            return jsonify({"error": str(exc), "details": {}}), 400
        return jsonify({"ok": True})

    return bp
