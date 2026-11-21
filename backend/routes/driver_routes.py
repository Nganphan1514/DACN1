from flask import Blueprint, jsonify, render_template

from backend.middleware.auth_guard import require_role, resolve_driver_id
from database.mysql_service import (
    lay_dashboard_tai_xe,
    lay_lich_chay_tai_xe,
    lay_thong_bao_tai_xe,
    lay_lich_su_vi_pham_tai_xe,
    lay_lich_su_chay_tai_xe,
)

driver_bp = Blueprint("driver_bp", __name__)


@driver_bp.route("/driver/reports")
@require_role("tai_xe", "quan_ly")
def driver_reports_page():
    return render_template("driver/reports.html")


@driver_bp.route("/driver/violations")
@require_role("tai_xe", "quan_ly")
def driver_violations_page():
    return render_template("driver/violations.html")


@driver_bp.route("/driver/history")
@require_role("tai_xe", "quan_ly")
def driver_history_page():
    return render_template("driver/history.html")


@driver_bp.route("/api/driver/dashboard/<int:tai_xe_id>")
@require_role("tai_xe", "quan_ly")
def api_driver_dashboard(tai_xe_id):
    resolved_id, allowed = resolve_driver_id(tai_xe_id)
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Bạn không có quyền xem dữ liệu của tài xế khác."
        }), 403

    data = lay_dashboard_tai_xe(resolved_id)
    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/schedules/<int:tai_xe_id>")
@require_role("tai_xe", "quan_ly")
def api_driver_schedules(tai_xe_id):
    resolved_id, allowed = resolve_driver_id(tai_xe_id)
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Bạn không có quyền xem lịch chạy của tài xế khác."
        }), 403

    data = lay_lich_chay_tai_xe(resolved_id)
    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/notifications/<int:tai_xe_id>")
@require_role("tai_xe", "quan_ly")
def api_driver_notifications(tai_xe_id):
    resolved_id, allowed = resolve_driver_id(tai_xe_id)
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Bạn không có quyền xem thông báo của tài xế khác."
        }), 403

    data = lay_thong_bao_tai_xe(resolved_id)
    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/violations/<int:tai_xe_id>")
@require_role("tai_xe", "quan_ly")
def api_driver_violations(tai_xe_id):
    resolved_id, allowed = resolve_driver_id(tai_xe_id)
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Bạn không có quyền xem vi phạm của tài xế khác."
        }), 403

    data = lay_lich_su_vi_pham_tai_xe(resolved_id)
    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/history/<int:tai_xe_id>")
@require_role("tai_xe", "quan_ly")
def api_driver_history(tai_xe_id):
    resolved_id, allowed = resolve_driver_id(tai_xe_id)
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Bạn không có quyền xem lịch sử của tài xế khác."
        }), 403

    data = lay_lich_su_chay_tai_xe(resolved_id)
    return jsonify({
        "success": True,
        "data": data
    })
