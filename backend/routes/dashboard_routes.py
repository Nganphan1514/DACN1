from flask import Blueprint, jsonify, render_template, request

from backend.middleware.auth_guard import require_role, resolve_driver_id
from database.mysql_service import (
    lay_dashboard_tai_xe,
    lay_lich_chay_tai_xe,
    lay_thong_bao_tai_xe,
    danh_dau_da_doc,
    lay_profile_tai_xe,
    cap_nhat_profile_tai_xe,
)

dashboard_bp = Blueprint("dashboard", __name__)


# DRIVER DASHBOARD

@dashboard_bp.route("/driver/dashboard")
@require_role("tai_xe", "quan_ly")
def driver_dashboard():
    tai_xe_id, allowed = resolve_driver_id(request.args.get("tai_xe_id"))
    if not allowed:
        return "Không có quyền truy cập hồ sơ tài xế này.", 403

    data = lay_dashboard_tai_xe(tai_xe_id)
    return render_template("driver/dashboard.html", data=data)


# DRIVER SCHEDULES

@dashboard_bp.route("/driver/schedules")
@require_role("tai_xe", "quan_ly")
def driver_schedules():
    tai_xe_id, allowed = resolve_driver_id(request.args.get("tai_xe_id"))
    if not allowed:
        return "Không có quyền truy cập lịch chạy của tài xế này.", 403

    schedules = lay_lich_chay_tai_xe(tai_xe_id)
    return render_template(
        "driver/schedules.html", schedules=schedules, tai_xe_id=tai_xe_id
    )


# DRIVER NOTIFICATIONS

@dashboard_bp.route("/driver/notifications")
@require_role("tai_xe", "quan_ly")
def driver_notifications():
    tai_xe_id, allowed = resolve_driver_id(request.args.get("tai_xe_id"))
    if not allowed:
        return "Không có quyền truy cập thông báo của tài xế này.", 403

    notifications = lay_thong_bao_tai_xe(tai_xe_id)
    return render_template(
        "driver/notifications.html", notifications=notifications, tai_xe_id=tai_xe_id
    )


# DOC THONG BAO

@dashboard_bp.route("/driver/read-note/<int:note_id>", methods=["POST"])
@require_role("tai_xe", "quan_ly")
def read_note(note_id):
    success = danh_dau_da_doc(note_id)
    return jsonify({"success": success})


# DRIVER PROFILE

@dashboard_bp.route("/driver/profile")
@require_role("tai_xe", "quan_ly")
def driver_profile():
    tai_xe_id, allowed = resolve_driver_id(request.args.get("tai_xe_id"))
    if not allowed:
        return "Không có quyền truy cập hồ sơ tài xế này.", 403

    profile = lay_profile_tai_xe(tai_xe_id)
    return render_template("driver/profile.html", profile=profile, tai_xe_id=tai_xe_id)


# UPDATE PROFILE

@dashboard_bp.route("/driver/update-profile", methods=["POST"])
@require_role("tai_xe", "quan_ly")
def update_profile():
    tai_xe_id, allowed = resolve_driver_id(request.form.get("tai_xe_id"))
    if not allowed:
        return "Không có quyền cập nhật hồ sơ tài xế này.", 403

    so_dien_thoai = request.form.get("so_dien_thoai")
    dia_chi = request.form.get("dia_chi")

    success = cap_nhat_profile_tai_xe(tai_xe_id, so_dien_thoai, dia_chi)
    profile = lay_profile_tai_xe(tai_xe_id)

    return render_template(
        "driver/profile.html", profile=profile, tai_xe_id=tai_xe_id, success=success
    )
