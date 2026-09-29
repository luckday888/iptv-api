from flask import Blueprint, current_app, jsonify, request

from service.web.auth.decorators import admin_required
from utils import channel_repository as repo
from utils.constants import channel_results_path
from utils.rtmp_stats import fetch_rtmp_snapshot


def build_rtmp_blueprint():
    # RTMP 转推管理蓝图：运行时快照、可转推频道、批量转推控制
    bp = Blueprint("admin_rtmp", __name__, url_prefix="/api/admin/rtmp")

    @bp.get("/runtime")
    @admin_required
    def runtime():
        # 拉取 RTMP 服务快照；服务不可用时 fetch 内部已兜底，这里再防一层异常
        try:
            return jsonify(fetch_rtmp_snapshot())
        except Exception as exc:  # RTMP 服务不可用
            # 兜底前先记录完整异常堆栈，便于排查服务不可用原因
            current_app.logger.exception("获取 RTMP 运行时快照失败")
            return jsonify({
                "available": False,
                "status": "unavailable",
                "error": str(exc),
                "streams": [],
            })

    @bp.get("/channels")
    @admin_required
    def channels():
        # 返回已选接口（可转推）的频道结果列表，支持按频道名模糊搜索
        search = request.args.get("search", "", type=str)
        rows = repo.list_streamable_results(channel_results_path)
        if search:
            keyword = search.lower()
            rows = [
                row
                for row in rows
                if keyword in str(row.get("channel_name", "")).lower()
            ]
        return jsonify(rows)

    @bp.post("/streams/control")
    @admin_required
    def control():
        # 批量 start/stop/restart 控制，逐条执行并收集成功数与错误明细
        body = request.get_json(silent=True) or {}
        action = body.get("action")
        keys = body.get("channel_keys", [])
        if action not in ("start", "stop", "restart"):
            return jsonify({"error": "非法动作"}), 400
        if not isinstance(keys, list):
            return jsonify({"error": "channel_keys 必须是列表"}), 400
        # 延迟导入，避免 import service.rtmp 在模块加载时产生额外副作用
        from service import rtmp as rtmp_service

        # 转推目标：本机 RTMP 服务的 hls 应用
        host = f"{rtmp_service.app_rtmp_url}/hls"
        success, errors = 0, []
        for key in keys:
            try:
                if action in ("start", "restart"):
                    if action == "restart":
                        # restart 先停掉旧转推，再走与 start 相同的启动流程
                        rtmp_service.stop_stream(key)
                    # service 以返回值（而非异常）表达容量不足/参数非法等结果，必须检查 accepted
                    result = rtmp_service.start_hls_to_rtmp_async(host, key)
                    if not result.get("accepted"):
                        errors.append({
                            "channel_key": key,
                            "message": result.get("status", "unknown"),
                        })
                        continue
                else:
                    rtmp_service.stop_stream(key)
                success += 1
            except Exception as exc:
                errors.append({"channel_key": key, "message": str(exc)})
        return jsonify({"success": success, "total": len(keys), "errors": errors})

    return bp
