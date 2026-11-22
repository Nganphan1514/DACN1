"""
DACN1 V3.0 - Sprint 3: Routes Chuyen thuc te (chuyen_thuc_te),
Ket thuc ngoai le & Lich su ket noi Camera.
"""

from flask import Blueprint, g, jsonify, request

from backend.middleware.auth_guard import get_current_scope, require_role
from core.ops_rules import (
    ADMIN_PANEL_ROLES,
    MANAGER_CONTROL_ROLES,
    MONITOR_ROLES,
    ROLE_TAI_XE,
)
from database.trip_camera_service import (
    lay_danh_sach_chuyen_thuc_te,
    lay_lich_su_ket_noi_camera,
    lay_trang_thai_camera_cho_tai_xe,
    quan_ly_ket_thuc_chuyen_ngoai_le,
    tai_xe_bat_dau_chuyen,
    tai_xe_ket_thuc_chuyen,
)

trip_bp = Blueprint("trip_bp", __name__)


# ============================================================
# TAI XE: BAT DAU / KET THUC CHUYEN & TRANG THAI CAMERA
# ============================================================

@trip_bp.route("/api/driver/trips", methods=["GET"])
@require_role(ROLE_TAI_XE)
def api_driver_trips():
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400
    rows = lay_danh_sach_chuyen_thuc_te(tai_xe_id=tai_xe_id)
    return jsonify({"success": True, "data": rows})


@trip_bp.route("/api/driver/trips/start", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_start_trip():
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    chuyen_id, status_code, message = tai_xe_bat_dau_chuyen(
        lich_chay_id=data.get("lich_chay_id"),
        tai_xe_id=tai_xe_id,
        actor_id=g.current_user["id"],
        ghi_chu=data.get("ghi_chu"),
    )
    if chuyen_id is None:
        return jsonify({"success": False, "message": message}), status_code

    camera_status = lay_trang_thai_camera_cho_tai_xe(tai_xe_id)
    return jsonify({
        "success": True,
        "message": message,
        "id": chuyen_id,
        "camera_status": camera_status,
    }), 201


@trip_bp.route("/api/driver/trips/<int:chuyen_id>/complete", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_complete_trip(chuyen_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    ok, status_code, message = tai_xe_ket_thuc_chuyen(
        chuyen_id=chuyen_id,
        tai_xe_id=tai_xe_id,
        actor_id=g.current_user["id"],
        ghi_chu=data.get("ghi_chu"),
    )
    return jsonify({"success": ok, "message": message}), status_code


@trip_bp.route("/api/driver/camera-status", methods=["GET"])
@require_role(ROLE_TAI_XE)
def api_driver_camera_status():
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400
    status = lay_trang_thai_camera_cho_tai_xe(tai_xe_id)
    return jsonify({"success": True, "data": status})


# ============================================================
# QUAN LY & GIAM SAT: CHUYEN THUC TE, KET THUC NGOAI LE & LOG CAMERA
# ============================================================

@trip_bp.route("/api/admin/trips", methods=["GET"])
@require_role(*ADMIN_PANEL_ROLES)
def api_admin_trips():
    trang_thai = request.args.get("trang_thai")
    rows = lay_danh_sach_chuyen_thuc_te(scope=get_current_scope(), trang_thai=trang_thai)
    return jsonify({"success": True, "data": rows})


@trip_bp.route("/api/admin/trips/<int:chuyen_id>/force-complete", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_force_complete_trip(chuyen_id):
    data = request.get_json(silent=True) or {}
    ly_do = data.get("ly_do_ngoai_le") or data.get("ly_do")
    ok, status_code, message = quan_ly_ket_thuc_chuyen_ngoai_le(
        chuyen_id=chuyen_id,
        ly_do_ngoai_le=ly_do,
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": message}), status_code


@trip_bp.route("/api/admin/devices/<device_id>/connection-logs", methods=["GET"])
@require_role(*MONITOR_ROLES)
def api_admin_device_connection_logs(device_id):
    chuyen_id = request.args.get("chuyen_thuc_te_id")
    limit = min(int(request.args.get("limit", 50) or 50), 200)
    rows = lay_lich_su_ket_noi_camera(
        device_id=device_id,
        chuyen_thuc_te_id=int(chuyen_id) if chuyen_id else None,
        limit=limit,
    )
    return jsonify({"success": True, "data": rows})
