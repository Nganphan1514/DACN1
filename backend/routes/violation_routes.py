"""
DACN1 V3.0 - Sprint 4: Routes Xac minh Su kien AI -> Vi pham
va Phan he Khieu nai vi pham bat buoc.
"""

from flask import Blueprint, g, jsonify, request

from backend.middleware.auth_guard import get_current_scope, require_role
from core.ops_rules import (
    ADMIN_PANEL_ROLES,
    MANAGER_CONTROL_ROLES,
    MONITOR_ROLES,
    ROLE_TAI_XE,
)
from database.violation_appeal_service import (
    lay_danh_sach_khieu_nai,
    lay_danh_sach_su_kien_ai_v3,
    lay_danh_sach_vi_pham,
    lay_lich_su_khieu_nai,
    quan_ly_bac_bo_su_kien_ai,
    quan_ly_xac_minh_vi_pham,
    quan_ly_xu_ly_khieu_nai,
    tai_xe_bo_sung_khieu_nai,
    tai_xe_gui_khieu_nai,
)

violation_bp = Blueprint("violation_bp", __name__)


# ============================================================
# QUAN LY & GIAM SAT: SU KIEN AI -> XAC MINH VI PHAM
# ============================================================

@violation_bp.route("/api/admin/ai-events", methods=["GET"])
@require_role(*MONITOR_ROLES)
def api_admin_ai_events():
    trang_thai = request.args.get("trang_thai")
    limit = min(int(request.args.get("limit", 50) or 50), 200)
    rows = lay_danh_sach_su_kien_ai_v3(
        scope=get_current_scope(),
        trang_thai=trang_thai,
        limit=limit,
    )
    return jsonify({"success": True, "data": rows})


@violation_bp.route("/api/admin/ai-events/<int:su_kien_id>/verify-violation", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_verify_violation(su_kien_id):
    data = request.get_json(silent=True) or {}
    ly_do = data.get("ly_do_xac_minh") or data.get("ly_do")
    vp_id, status_code, message = quan_ly_xac_minh_vi_pham(
        su_kien_id=su_kien_id,
        ly_do_xac_minh=ly_do,
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    if vp_id is None:
        return jsonify({"success": False, "message": message}), status_code
    return jsonify({"success": True, "message": message, "vi_pham_id": vp_id}), 201


@violation_bp.route("/api/admin/ai-events/<int:su_kien_id>/reject", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_reject_ai_event(su_kien_id):
    data = request.get_json(silent=True) or {}
    trang_thai = data.get("trang_thai", "REJECTED")
    ly_do = data.get("ly_do") or data.get("ghi_chu_xu_ly")
    ok, status_code, message = quan_ly_bac_bo_su_kien_ai(
        su_kien_id=su_kien_id,
        ly_do=ly_do,
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
        trang_thai=trang_thai,
    )
    return jsonify({"success": ok, "message": message}), status_code


@violation_bp.route("/api/admin/violations", methods=["GET"])
@require_role(*ADMIN_PANEL_ROLES)
def api_admin_violations():
    trang_thai = request.args.get("trang_thai")
    rows = lay_danh_sach_vi_pham(scope=get_current_scope(), trang_thai=trang_thai)
    return jsonify({"success": True, "data": rows})


# ============================================================
# QUAN LY: XU LY KHIEU NAI VI PHAM
# ============================================================

@violation_bp.route("/api/admin/appeals", methods=["GET"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_appeals():
    trang_thai = request.args.get("trang_thai")
    rows = lay_danh_sach_khieu_nai(scope=get_current_scope(), trang_thai=trang_thai)
    return jsonify({"success": True, "data": rows})


@violation_bp.route("/api/admin/appeals/<int:khieu_nai_id>/history", methods=["GET"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_appeal_history(khieu_nai_id):
    rows = lay_lich_su_khieu_nai(khieu_nai_id)
    return jsonify({"success": True, "data": rows})


@violation_bp.route("/api/admin/appeals/<int:khieu_nai_id>/decide", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_decide_appeal(khieu_nai_id):
    data = request.get_json(silent=True) or {}
    ok, status_code, message = quan_ly_xu_ly_khieu_nai(
        khieu_nai_id=khieu_nai_id,
        quyet_dinh=data.get("quyet_dinh"),
        ly_do_ket_luan=data.get("ly_do_ket_luan") or data.get("ly_do"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": message}), status_code


# ============================================================
# TAI XE: XEM CANH BAO AI, XEM VI PHAM DA XAC MINH & KHIEU NAI
# ============================================================

@violation_bp.route("/api/driver/ai-events", methods=["GET"])
@require_role(ROLE_TAI_XE)
def api_driver_ai_events():
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400
    rows = lay_danh_sach_su_kien_ai_v3(tai_xe_id=tai_xe_id, limit=50)
    return jsonify({"success": True, "data": rows})


@violation_bp.route("/api/driver/violations", methods=["GET"])
@require_role(ROLE_TAI_XE)
def api_driver_verified_violations():
    """Tra ve danh sach VI PHAM DA XAC MINH (tach biet voi canh bao AI tho)."""
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400
    rows = lay_danh_sach_vi_pham(tai_xe_id=tai_xe_id)
    return jsonify({"success": True, "data": rows})


@violation_bp.route("/api/driver/violations/<int:vi_pham_id>/appeals", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_create_appeal(vi_pham_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    kn_id, status_code, message = tai_xe_gui_khieu_nai(
        vi_pham_id=vi_pham_id,
        tai_xe_id=tai_xe_id,
        noi_dung_giai_trinh=data.get("noi_dung_giai_trinh"),
        minh_chung_urls=data.get("minh_chung_urls") or [],
        actor_id=g.current_user["id"],
    )
    if kn_id is None:
        return jsonify({"success": False, "message": message}), status_code
    return jsonify({"success": True, "message": message, "id": kn_id}), 201


@violation_bp.route("/api/driver/appeals", methods=["GET"])
@require_role(ROLE_TAI_XE)
def api_driver_list_appeals():
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400
    rows = lay_danh_sach_khieu_nai(tai_xe_id=tai_xe_id)
    return jsonify({"success": True, "data": rows})


@violation_bp.route("/api/driver/appeals/<int:khieu_nai_id>/supplement", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_supplement_appeal(khieu_nai_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    ok, status_code, message = tai_xe_bo_sung_khieu_nai(
        khieu_nai_id=khieu_nai_id,
        tai_xe_id=tai_xe_id,
        ghi_chu_bo_sung=data.get("ghi_chu_bo_sung"),
        minh_chung_urls=data.get("minh_chung_urls") or [],
        actor_id=g.current_user["id"],
    )
    return jsonify({"success": ok, "message": message}), status_code
