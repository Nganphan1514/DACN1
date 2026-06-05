

from flask import Blueprint, render_template, request

from database.mysql_service import lay_dashboard_tai_xe

dashboard_bp = Blueprint("dashboard", __name__)

from database.mysql_service import (
    lay_dashboard_tai_xe,
    lay_lich_chay_tai_xe,
    lay_thong_bao_tai_xe,
    danh_dau_da_doc,
    lay_profile_tai_xe,
    cap_nhat_profile_tai_xe,
    
)



# DRIVER DASHBOARD

@dashboard_bp.route("/driver/dashboard")
def driver_dashboard():

    tai_xe_id = request.args.get("tai_xe_id")

    if not tai_xe_id:

        return "Thiếu tai_xe_id"

    data = lay_dashboard_tai_xe(tai_xe_id)

    return render_template("driver/dashboard.html", data=data)



# ADMIN DASHBOARD

# @dashboard_bp.route("/admin/dashboard")
# def admin_dashboard():

#     return render_template("admin/dashboard.html")



# DRIVER SCHEDULES

@dashboard_bp.route("/driver/schedules")
def driver_schedules():

    tai_xe_id = request.args.get("tai_xe_id")

    schedules = lay_lich_chay_tai_xe(tai_xe_id)


    return render_template(
        "driver/schedules.html", schedules=schedules, tai_xe_id=tai_xe_id
    )

# DRIVER NOTIFICATIONS

@dashboard_bp.route("/driver/notifications")
def driver_notifications():

    tai_xe_id = request.args.get("tai_xe_id")

    notifications = lay_thong_bao_tai_xe(tai_xe_id)


    return render_template(
        "driver/notifications.html", notifications=notifications, tai_xe_id=tai_xe_id
    )

# DOC THONG BAO

@dashboard_bp.route("/driver/read-note/<int:note_id>", methods=["POST"])
def read_note(note_id):

    success = danh_dau_da_doc(note_id)

    return {"success": success}



# DRIVER PROFILE

@dashboard_bp.route("/driver/profile")
def driver_profile():

    tai_xe_id = request.args.get("tai_xe_id")

    profile = lay_profile_tai_xe(tai_xe_id)


    return render_template("driver/profile.html", profile=profile, tai_xe_id=tai_xe_id)

# UPDATE PROFILE

@dashboard_bp.route("/driver/update-profile", methods=["POST"])
def update_profile():

    tai_xe_id = request.form.get("tai_xe_id")

    so_dien_thoai = request.form.get("so_dien_thoai")

    dia_chi = request.form.get("dia_chi")

    success = cap_nhat_profile_tai_xe(tai_xe_id, so_dien_thoai, dia_chi)

    profile = lay_profile_tai_xe(tai_xe_id)


    return render_template(
        "driver/profile.html", profile=profile, tai_xe_id=tai_xe_id, success=success
    )