from flask import Blueprint, render_template, jsonify

from database.mysql_service import lay_admin_dashboard
from database.mysql_service import (
    lay_admin_dashboard,
    lay_danh_sach_tai_xe,
    cap_nhat_tai_xe_va_thong_bao,
    lay_danh_sach_xe_admin,
    cap_nhat_xe,
)
admin_bp = Blueprint("admin_bp", __name__)


@admin_bp.route("/admin/dashboard")
def admin_dashboard_page():
    return render_template("admin/dashboard.html")


@admin_bp.route("/admin/reports")
def admin_reports_page():
    return render_template("admin/reports.html")


@admin_bp.route("/api/admin/dashboard")
def api_admin_dashboard():
    data = lay_admin_dashboard()

    return jsonify({
        "success": True,
        "data": data
    })
@admin_bp.route("/admin/drivers")
def admin_drivers_page():
    return render_template("admin/drivers.html")


@admin_bp.route("/api/admin/drivers", methods=["GET"])
def api_admin_drivers():
    data = lay_danh_sach_tai_xe()

    return jsonify({
        "success": True,
        "data": data
    })


@admin_bp.route("/api/admin/drivers/<int:tai_xe_id>", methods=["PUT"])
def api_update_driver(tai_xe_id):
    from flask import request

    data = request.get_json()

    ok = cap_nhat_tai_xe_va_thong_bao(
        tai_xe_id=tai_xe_id,
        ho_ten=data.get("ho_ten"),
        so_dien_thoai=data.get("so_dien_thoai"),
        so_gplx=data.get("so_gplx"),
        dia_chi=data.get("dia_chi"),
        trang_thai=data.get("trang_thai"),
        quan_ly_id=data.get("quan_ly_id", 1)
    )

    return jsonify({
        "success": ok,
        "message": "Đã cập nhật tài xế và gửi thông báo" if ok else "Cập nhật thất bại"
    })
@admin_bp.route("/admin/vehicles")
def admin_vehicles_page():
    return render_template("admin/vehicles.html")


@admin_bp.route("/api/admin/vehicles", methods=["GET"])
def api_admin_vehicles():
    data = lay_danh_sach_xe_admin()

    return jsonify({
        "success": True,
        "data": data
    })


@admin_bp.route("/api/admin/vehicles/<int:xe_id>", methods=["PUT"])
def api_update_vehicle(xe_id):
    from flask import request

    data = request.get_json()

    ok = cap_nhat_xe(
        xe_id=xe_id,
        bien_so=data.get("bien_so"),
        model=data.get("model"),
        trang_thai=data.get("trang_thai"),
        tai_xe_mac_dinh_id=data.get("tai_xe_mac_dinh_id")
    )

    return jsonify({
        "success": ok,
        "message": "Đã cập nhật xe" if ok else "Cập nhật xe thất bại"
    })