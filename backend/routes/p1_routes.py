"""
DACN1 V3.0 - P1: Routes Checklist kiem tra xe truoc chuyen,
Canh bao uu tien (5 nhom) & Thong ke da cap V3.
"""

from flask import Blueprint, g, jsonify, request

from backend.middleware.auth_guard import get_current_scope, require_auth, require_role
from core.ops_rules import ADMIN_PANEL_ROLES, ROLE_TAI_XE
from database.p1_service import (
    DEFAULT_CHECKLIST_ITEMS,
    lay_canh_bao_uu_tien,
    lay_checklist_theo_lich,
    lay_thong_ke_da_cap_v3,
    tai_xe_gui_checklist_truoc_chuyen,
)

p1_bp = Blueprint("p1_bp", __name__)


@p1_bp.route("/api/driver/checklist/template", methods=["GET"])
@require_auth
def api_checklist_template():
    return jsonify({"success": True, "data": DEFAULT_CHECKLIST_ITEMS})


@p1_bp.route("/api/driver/schedules/<int:lich_chay_id>/checklist", methods=["GET"])
@require_auth
def api_get_schedule_checklist(lich_chay_id):
    rows = lay_checklist_theo_lich(lich_chay_id)
    return jsonify({"success": True, "data": rows})


@p1_bp.route("/api/driver/schedules/<int:lich_chay_id>/checklist", methods=["POST"])
@require_role(ROLE_TAI_XE)
def api_submit_schedule_checklist(lich_chay_id):
    tai_xe_id = g.current_user.get("tai_xe_id")
    if not tai_xe_id:
        return jsonify({"success": False, "message": "Tài khoản chưa liên kết hồ sơ tài xế."}), 400

    data = request.get_json(silent=True) or {}
    res_data, status_code, message = tai_xe_gui_checklist_truoc_chuyen(
        lich_chay_id=lich_chay_id,
        tai_xe_id=tai_xe_id,
        items=data.get("items") or [],
        ghi_chu=data.get("ghi_chu"),
        actor_id=g.current_user["id"],
    )
    if res_data is None:
        return jsonify({"success": False, "message": message}), status_code
    return jsonify({"success": True, "message": message, "data": res_data}), 201


@p1_bp.route("/api/admin/priority-alerts", methods=["GET"])
@require_role(*ADMIN_PANEL_ROLES)
def api_admin_priority_alerts():
    data = lay_canh_bao_uu_tien(scope=get_current_scope())
    return jsonify({"success": True, "data": data})


@p1_bp.route("/api/admin/analytics/v3", methods=["GET"])
@require_role(*ADMIN_PANEL_ROLES)
def api_admin_analytics_v3():
    data = lay_thong_ke_da_cap_v3(scope=get_current_scope())
    return jsonify({"success": True, "data": data})
