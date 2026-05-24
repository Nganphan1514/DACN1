from flask import Blueprint, render_template, request

from database.mysql_service import lay_dashboard_tai_xe

dashboard_bp = Blueprint("dashboard", __name__)


# ==========================
# DRIVER DASHBOARD
# ==========================
@dashboard_bp.route("/driver/dashboard")
def driver_dashboard():

    tai_xe_id = request.args.get("tai_xe_id")

    if not tai_xe_id:

        return "Thiếu tai_xe_id"

    data = lay_dashboard_tai_xe(tai_xe_id)

    return render_template("driver/dashboard.html", data=data)


# ==========================
# ADMIN DASHBOARD
# ==========================
@dashboard_bp.route("/admin/dashboard")
def admin_dashboard():

    return render_template("admin/dashboard.html")
