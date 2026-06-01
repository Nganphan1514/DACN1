from flask import Blueprint, render_template, jsonify


from database.mysql_service import (
    lay_dashboard_tai_xe,
    lay_lich_chay_tai_xe,
    lay_thong_bao_tai_xe,
    lay_lich_su_vi_pham_tai_xe,
    lay_lich_su_chay_tai_xe,
)

driver_bp = Blueprint("driver_bp", __name__)


# @driver_bp.route("/driver/dashboard")
# def driver_dashboard():
#     return render_template("driver/dashboard.html")


# @driver_bp.route("/driver/schedules")
# def driver_schedules_page():
#     return render_template("driver/schedules.html")


# @driver_bp.route("/driver/notifications")
# def driver_notifications_page():
#     return render_template("driver/notifications.html")


@driver_bp.route("/driver/reports")
def driver_reports_page():
    return render_template("driver/reports.html")


@driver_bp.route("/api/driver/dashboard/<int:tai_xe_id>")
def api_driver_dashboard(tai_xe_id):
    data = lay_dashboard_tai_xe(tai_xe_id)
    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/schedules/<int:tai_xe_id>")
def api_driver_schedules(tai_xe_id):
    data = lay_lich_chay_tai_xe(tai_xe_id)
    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/notifications/<int:tai_xe_id>")
def api_driver_notifications(tai_xe_id):
    data = lay_thong_bao_tai_xe(tai_xe_id)
    return jsonify({
        "success": True,
        "data": data
    })

@driver_bp.route("/driver/violations")
def driver_violations_page():
    return render_template("driver/violations.html")


@driver_bp.route("/driver/history")
def driver_history_page():
    return render_template("driver/history.html")


@driver_bp.route("/api/driver/violations/<int:tai_xe_id>")
def api_driver_violations(tai_xe_id):
    data = lay_lich_su_vi_pham_tai_xe(tai_xe_id)

    return jsonify({
        "success": True,
        "data": data
    })


@driver_bp.route("/api/driver/history/<int:tai_xe_id>")
def api_driver_history(tai_xe_id):
    data = lay_lich_su_chay_tai_xe(tai_xe_id)

    return jsonify({
        "success": True,
        "data": data
    })