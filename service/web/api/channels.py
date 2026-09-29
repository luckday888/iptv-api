from flask import Blueprint, jsonify, request

from service.web.auth.decorators import admin_required
from utils import channel_repository as repo
from utils.constants import channel_results_path


def _page_args():
    # 分页参数归一化：页码最小 1，单页上限 200
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(200, max(1, request.args.get("page_size", 50, type=int)))
    return page, page_size


def build_channels_blueprint():
    bp = Blueprint("admin_channels", __name__, url_prefix="/api/admin/channels")

    @bp.get("/categories")
    @admin_required
    def categories():
        # 分类侧栏数据，支持名称模糊搜索
        return jsonify(
            repo.list_categories(
                channel_results_path, request.args.get("search", "", type=str)
            )
        )

    @bp.get("")
    @admin_required
    def list_all():
        # 频道分页列表，支持按分类、健康状态与名称过滤
        page, page_size = _page_args()
        rows = repo.list_channels(
            channel_results_path,
            category=request.args.get("category") or None,
            health=request.args.get("health") or None,
            search=request.args.get("search", "", type=str),
        )
        total = len(rows)
        start = (page - 1) * page_size
        return jsonify(
            {
                "items": rows[start : start + page_size],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )

    @bp.post("")
    @admin_required
    def create_channel():
        # 手动新增频道，默认归入“自定义”分类
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "").strip()
        category = (body.get("category") or "自定义").strip()
        if not name:
            return jsonify({"error": "频道名不能为空"}), 400
        key = repo.upsert_manual_channel(channel_results_path, category, name)
        return jsonify({"channel_key": key})

    @bp.delete("")
    @admin_required
    def remove_channels():
        # 批量删除频道及其关联数据
        keys = (request.get_json(silent=True) or {}).get("channel_keys", [])
        if not isinstance(keys, list) or not keys:
            return jsonify({"error": "未选择频道"}), 400
        deleted = repo.delete_channel_records(channel_results_path, keys)
        return jsonify({"deleted": deleted})

    @bp.get("/<channel_key>")
    @admin_required
    def channel_detail(channel_key):
        # 单个频道详情，不存在时返回 404
        row = repo.get_channel(channel_results_path, channel_key)
        if row is None:
            return jsonify({"error": "频道不存在"}), 404
        return jsonify(row)

    @bp.get("/<channel_key>/results")
    @admin_required
    def channel_results(channel_key):
        # 频道的全部接口结果，频道不存在时返回 404
        if repo.get_channel(channel_results_path, channel_key) is None:
            return jsonify({"error": "频道不存在"}), 404
        return jsonify(repo.list_channel_results(channel_results_path, channel_key))

    @bp.post("/<channel_key>/results")
    @admin_required
    def add_result(channel_key):
        # 为指定频道手动新增接口结果
        body = request.get_json(silent=True) or {}
        url = (body.get("url") or "").strip()
        if not url:
            return jsonify({"error": "URL 不能为空"}), 400
        if repo.get_channel(channel_results_path, channel_key) is None:
            return jsonify({"error": "频道不存在"}), 404
        result_key = repo.add_manual_result(channel_results_path, channel_key, url)
        return jsonify({"result_key": result_key})

    @bp.delete("/<channel_key>/results")
    @admin_required
    def remove_results(channel_key):
        # 批量删除指定频道下的接口结果
        keys = (request.get_json(silent=True) or {}).get("result_keys", [])
        if not isinstance(keys, list):
            return jsonify({"error": "result_keys 必须是数组"}), 400
        deleted = repo.delete_channel_results(
            channel_results_path, channel_key, keys
        )
        return jsonify({"deleted": deleted})

    @bp.get("/<channel_key>/selection")
    @admin_required
    def get_selection(channel_key):
        # 读取当前输出选择：mode 为 auto/manual，items 为按 rank 升序的已选接口
        channel = repo.get_channel(channel_results_path, channel_key)
        if channel is None:
            return jsonify({"error": "频道不存在"}), 404
        rows = repo.list_channel_results(channel_results_path, channel_key)
        items = [
            {"result_key": row["result_key"], "rank": row["selected_rank"]}
            for row in rows
            if row.get("selected_rank") is not None
        ]
        items.sort(key=lambda item: item["rank"])
        return jsonify({"mode": channel["selection_mode"], "items": items})

    @bp.put("/<channel_key>/selection")
    @admin_required
    def update_selection(channel_key):
        # 设置手动输出选择，入参为按 rank 排序的非空 result_keys
        if repo.get_channel(channel_results_path, channel_key) is None:
            return jsonify({"error": "频道不存在"}), 404
        keys = (request.get_json(silent=True) or {}).get("result_keys")
        if not isinstance(keys, list) or not keys:
            return jsonify({"error": "至少选择一个接口"}), 400
        rows = repo.list_channel_results(channel_results_path, channel_key)
        by_key = {row["result_key"]: row for row in rows}
        selected = [
            {"url": by_key[key]["url"], "headers": by_key[key].get("headers")}
            for key in keys
            if key in by_key
        ]
        # 过滤未知 key 后为空时直接拒绝，避免频道进入 manual 零输出状态
        if not selected:
            return jsonify({"error": "至少选择一个有效接口"}), 400
        repo.set_channel_selection(
            channel_results_path, channel_key, selected, mode="manual"
        )
        return jsonify({"ok": True})

    @bp.post("/<channel_key>/selection/reset")
    @admin_required
    def reset_selection(channel_key):
        # 清除手动选择并重置为自动选择
        if repo.get_channel(channel_results_path, channel_key) is None:
            return jsonify({"error": "频道不存在"}), 404
        repo.reset_channel_selection(channel_results_path, channel_key)
        return jsonify({"ok": True})

    @bp.put("/<channel_key>/logo")
    @admin_required
    def update_logo(channel_key):
        # 设置频道台标（URL 或上传后的路径）
        if repo.get_channel(channel_results_path, channel_key) is None:
            return jsonify({"error": "频道不存在"}), 404
        logo = (request.get_json(silent=True) or {}).get("logo", "")
        repo.set_channel_logo(channel_results_path, channel_key, logo)
        return jsonify({"ok": True})

    from utils.channel_operations import ChannelOperations
    from service.web.tasks.ops_manager import ops_manager

    def _operations():
        return ChannelOperations(channel_results_path)

    @bp.post("/<channel_key>/retest")
    @admin_required
    def retest_channel(channel_key):
        if repo.get_channel(channel_results_path, channel_key) is None:
            return jsonify({"error": "频道不存在"}), 404
        operations = _operations()
        try:
            ops_manager.run(
                "retest_channel",
                lambda progress: operations.retest_channel(channel_key, progress),
            )
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True})

    @bp.post("/<channel_key>/results/retest")
    @admin_required
    def retest_results(channel_key):
        keys = (request.get_json(silent=True) or {}).get("result_keys", [])
        operations = _operations()
        try:
            ops_manager.run(
                "retest_results",
                lambda progress: operations.retest_results(
                    channel_key, keys, progress),
            )
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True})

    @bp.post("/<channel_key>/results/screenshot")
    @admin_required
    def screenshot_results(channel_key):
        keys = (request.get_json(silent=True) or {}).get("result_keys", [])
        operations = _operations()
        try:
            ops_manager.run(
                "screenshot",
                lambda progress: operations.capture_result_screenshots(
                    channel_key, keys, progress),
            )
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True})

    return bp
