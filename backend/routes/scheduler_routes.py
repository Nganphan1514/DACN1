from flask import Blueprint, g, jsonify, render_template, request

from backend.middleware.auth_guard import get_current_scope, require_role
from core.ops_rules import DISPATCH_ROLES, MANAGER_CONTROL_ROLES, ROLE_TAI_XE
from database.mysql_service import (
    lay_danh_sach_tai_xe,
    lay_danh_sach_xe_admin,
)
from database.schedule_service import (
    cap_nhat_lich_chay_v3,
    huy_lich_chay_v3,
    lay_danh_sach_lich_chay_v3,
    lay_danh_sach_yeu_cau_doi_lich,
    quan_ly_xu_ly_yeu_cau_doi_lich,
    tai_xe_gui_yeu_cau_doi_lich,
    tai_xe_rut_yeu_cau_doi_lich,
    tai_xe_tu_choi_lich,
    tai_xe_xac_nhan_lich,
    tao_lich_chay_v3,
)

scheduler_bp = Blueprint("scheduler_bp", __name__)


# ============================================================
# TRANG QUAN LY & DIEU PHOI LICH CHAY
# ============================================================

@scheduler_bp.route("/admin/scheduler")
@require_role(*DISPATCH_ROLES)
def admin_scheduler_page():
    return render_template("admin/scheduler.html")


@scheduler_bp.route("/api/admin/schedules", methods=["GET"])
@scheduler_bp.route("/api/dispatch/schedules", methods=["GET"])
@require_role(*DISPATCH_ROLES)
def api_admin_schedules():
    trang_thai = request.args.get("trang_thai")
    data = lay_danh_sach_lich_chay_v3(scope=get_current_scope(), trang_thai=trang_thai)
    return jsonify({
        "success": True,
        "data": data,
    })


@scheduler_bp.route("/api/admin/schedules/options", methods=["GET"])
@scheduler_bp.route("/api/dispatch/schedules/options", methods=["GET"])
@require_role(*DISPATCH_ROLES)
def api_schedule_options():
    drivers = lay_danh_sach_tai_xe()
    vehicles = lay_danh_sach_xe_admin()

    drivers = [item for item in drivers if item.get("trang_thai") == "dang_lam"]
    vehicles = [item for item in vehicles if item.get("trang_thai") == "hoat_dong"]

    return jsonify({
        "success": True,
        "drivers": drivers,
        "vehicles": vehicles,
    })


@scheduler_bp.route("/api/admin/schedules", methods=["POST"])
@scheduler_bp.route("/api/dispatch/schedules", methods=["POST"])
@require_role(*DISPATCH_ROLES)
def api_create_schedule():
    data = request.get_json(silent=True) or {}

    lich_id, status_code, message = tao_lich_chay_v3(
        tai_xe_id=data.get("tai_xe_id"),
        xe_id=data.get("xe_id"),
        tuyen_duong=data.get("tuyen_duong"),
        gio_bat_dau=data.get("gio_bat_dau"),
        gio_ket_thuc=data.get("gio_ket_thuc"),
        ghi_chu=data.get("ghi_chu"),
        trang_thai_ban_dau=data.get("trang_thai", "CHO_XAC_NHAN"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
        scope=get_current_scope(),
    )

    if lich_id is None:
        return jsonify({"success": False, "message": message}), status_code

    return jsonify({
        "success": True,
        "message": message,
        "id": lich_id,
    }), 201


@scheduler_bp.route("/api/admin/schedules/<int:lich_id>", methods=["PUT"])
@scheduler_bp.route("/api/dispatch/schedules/<int:lich_id>", methods=["PUT"])
@require_role(*DISPATCH_ROLES)
def api_update_schedule(lich_id):
    data = request.get_json(silent=True) or {}

    ok, status_code, message = cap_nhat_lich_chay_v3(
        lich_id=lich_id,
        tai_xe_id=data.get("tai_xe_id"),
        xe_id=data.get("xe_id"),
        tuyen_duong=data.get("tuyen_duong"),
        gio_bat_dau=data.get("gio_bat_dau"),
        gio_ket_thuc=data.get("gio_ket_thuc"),
        trang_thai=data.get("trang_thai"),
        ghi_chu=data.get("ghi_chu"),
        ly_do=data.get("ly_do"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )

    return jsonify({"success": ok, "message": message}), status_code


@scheduler_bp.route("/api/admin/schedules/<int:lich_id>", methods=["DELETE"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_delete_schedule(lich_id):
    data = request.get_json(silent=True) or {}
    ly_do_huy = data.get("ly_do_huy") or data.get("ly_do") or request.args.get("ly_do_huy")

    ok, status_code, message = huy_lich_chay_v3(
        lich_id=lich_id,
        ly_do_huy=ly_do_huy,
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": message}), status_code


# ============================================================
# TAI XE XAC NHAN / TU CHOI LICH & YEU CAU DOI LICH/XE (SCH-03, REQ-01)
# ============================================================

@scheduler_bp.route("/api/driver/schedules/<int:lich_id>/confirm", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_confirm_schedule(lich_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    ok, status_code, message = tai_xe_xac_nhan_lich(
        lich_id=lich_id,
        tai_xe_id=tai_xe_id,
        actor_id=g.current_user["id"],
    )
    return jsonify({"success": ok, "message": message}), status_code


@scheduler_bp.route("/api/driver/schedules/<int:lich_id>/reject", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_reject_schedule(lich_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    ok, status_code, message = tai_xe_tu_choi_lich(
        lich_id=lich_id,
        tai_xe_id=tai_xe_id,
        ly_do=data.get("ly_do"),
        actor_id=g.current_user["id"],
    )
    return jsonify({"success": ok, "message": message}), status_code


@scheduler_bp.route("/api/driver/schedules/<int:lich_id>/change-requests", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_create_change_request(lich_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    yc_id, status_code, message = tai_xe_gui_yeu_cau_doi_lich(
        lich_id=lich_id,
        tai_xe_id=tai_xe_id,
        loai_yeu_cau=data.get("loai_yeu_cau"),
        du_lieu_de_xuat=data.get("du_lieu_de_xuat") or {},
        ly_do=data.get("ly_do"),
        actor_id=g.current_user["id"],
    )
    if yc_id is None:
        return jsonify({"success": False, "message": message}), status_code
    return jsonify({"success": True, "message": message, "id": yc_id}), 201


@scheduler_bp.route("/api/driver/change-requests", methods=["GET"])
@require_role(ROLE_TAI_XE)
def api_driver_list_change_requests():
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400
    rows = lay_danh_sach_yeu_cau_doi_lich(tai_xe_id=tai_xe_id)
    return jsonify({"success": True, "data": rows})


@scheduler_bp.route("/api/driver/change-requests/<int:yeu_cau_id>/withdraw", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_driver_withdraw_change_request(yeu_cau_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    ok, status_code, message = tai_xe_rut_yeu_cau_doi_lich(
        yeu_cau_id=yeu_cau_id,
        tai_xe_id=tai_xe_id,
        actor_id=g.current_user["id"],
    )
    return jsonify({"success": ok, "message": message}), status_code


# ============================================================
# QUAN LY PHE DUYET YEU CAU DOI LICH / DOI XE
# ============================================================

@scheduler_bp.route("/api/admin/change-requests", methods=["GET"])
@require_role(*DISPATCH_ROLES)
def api_admin_list_change_requests():
    trang_thai = request.args.get("trang_thai")
    rows = lay_danh_sach_yeu_cau_doi_lich(scope=get_current_scope(), trang_thai=trang_thai)
    return jsonify({"success": True, "data": rows})


@scheduler_bp.route("/api/admin/change-requests/<int:yeu_cau_id>/decide", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_decide_change_request(yeu_cau_id):
    data = request.get_json(silent=True) or {}
    ok, status_code, message = quan_ly_xu_ly_yeu_cau_doi_lich(
        yeu_cau_id=yeu_cau_id,
        quyet_dinh=data.get("quyet_dinh"),
        ly_do_tu_choi=data.get("ly_do_tu_choi") or data.get("ly_do"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": message}), status_code


@scheduler_bp.route("/api/admin/change-requests/<int:yeu_cau_id>/approve", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_approve_change_request(yeu_cau_id):
    ok, status_code, message = quan_ly_xu_ly_yeu_cau_doi_lich(
        yeu_cau_id=yeu_cau_id,
        quyet_dinh="DA_DUYET",
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": message}), status_code


@scheduler_bp.route("/api/admin/change-requests/<int:yeu_cau_id>/reject", methods=["POST"])
@require_role(*MANAGER_CONTROL_ROLES)
def api_admin_reject_change_request(yeu_cau_id):
    data = request.get_json(silent=True) or {}
    ok, status_code, message = quan_ly_xu_ly_yeu_cau_doi_lich(
        yeu_cau_id=yeu_cau_id,
        quyet_dinh="TU_CHOI",
        ly_do_tu_choi=data.get("ly_do_tu_choi") or data.get("ly_do"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": message}), status_code
