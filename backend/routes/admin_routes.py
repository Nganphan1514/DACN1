from flask import Blueprint, render_template, jsonify, request

from database.mysql_service import (
    lay_admin_dashboard,
    lay_danh_sach_tai_xe,
    tao_tai_xe_va_tai_khoan,
    cap_nhat_tai_xe_va_thong_bao,
    lay_danh_sach_xe_admin,
    lay_xe_theo_id,
    tao_xe,
    cap_nhat_xe,
    lay_admin_analytics,
)
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
import os
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
@admin_bp.route("/api/admin/drivers", methods=["POST"])
def api_create_driver():
    data = request.get_json(silent=True) or {}

    required_fields = [
        "ten_dang_nhap",
        "mat_khau",
        "ho_ten",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not str(data.get(field, "")).strip()
    ]

    if missing_fields:
        return jsonify({
            "success": False,
            "message": "Vui lòng nhập đầy đủ tên đăng nhập, mật khẩu và họ tên."
        }), 400

    tai_xe_id = tao_tai_xe_va_tai_khoan(
        ten_dang_nhap=data.get("ten_dang_nhap"),
        mat_khau=data.get("mat_khau"),
        ho_ten=data.get("ho_ten"),
        so_dien_thoai=data.get("so_dien_thoai"),
        so_gplx=data.get("so_gplx"),
        dia_chi=data.get("dia_chi"),
        trang_thai=data.get("trang_thai", "dang_lam"),
        quan_ly_id=data.get("quan_ly_id", 1),
    )

    if tai_xe_id is None:
        return jsonify({
            "success": False,
            "message": (
                "Không thể thêm tài xế. "
                "Hãy kiểm tra tên đăng nhập hoặc số GPLX đã tồn tại hay chưa."
            )
        }), 400

    return jsonify({
        "success": True,
        "message": "Đã thêm tài xế mới.",
        "id": tai_xe_id,
    }), 201

@admin_bp.route("/api/admin/drivers/<int:tai_xe_id>", methods=["PUT"])
def api_update_driver(tai_xe_id):
    data = request.get_json(silent=True) or {}

    ok = cap_nhat_tai_xe_va_thong_bao(
        tai_xe_id=tai_xe_id,
        ho_ten=data.get("ho_ten"),
        so_dien_thoai=data.get("so_dien_thoai"),
        so_gplx=data.get("so_gplx"),
        dia_chi=data.get("dia_chi"),
        trang_thai=data.get("trang_thai"),
        quan_ly_id=data.get("quan_ly_id", 1),
    )

    return jsonify({
        "success": ok,
        "message": (
            "Đã cập nhật tài xế và gửi thông báo."
            if ok
            else "Cập nhật tài xế thất bại."
        )
    }), 200 if ok else 400
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

@admin_bp.route("/api/admin/vehicles", methods=["POST"])
def api_create_vehicle():
    data = request.get_json(silent=True) or {}

    bien_so = str(data.get("bien_so", "")).strip()

    if not bien_so:
        return jsonify({
            "success": False,
            "message": "Biển số xe không được để trống."
        }), 400

    xe_id = tao_xe(
        bien_so=bien_so,
        model=data.get("model"),
        loai_xe=data.get("loai_xe"),
        trang_thai=data.get("trang_thai", "hoat_dong"),
        ghi_chu=data.get("ghi_chu"),
        tai_xe_mac_dinh_id=data.get("tai_xe_mac_dinh_id"),
        quan_ly_id=data.get("quan_ly_id", 1),
    )

    if xe_id is None:
        return jsonify({
            "success": False,
            "message": (
                "Không thể thêm xe. "
                "Hãy kiểm tra biển số hoặc tài xế phụ trách."
            )
        }), 400

    return jsonify({
        "success": True,
        "message": "Đã thêm xe mới.",
        "id": xe_id,
    }), 201
@admin_bp.route("/api/admin/vehicles/<int:xe_id>", methods=["PUT"])
def api_update_vehicle(xe_id):
    data = request.get_json(silent=True) or {}

    xe_cu = lay_xe_theo_id(xe_id)

    if not xe_cu:
        return jsonify({
            "success": False,
            "message": "Không tìm thấy xe."
        }), 404

    ok = cap_nhat_xe(
        xe_id=xe_id,
        bien_so=data.get("bien_so", xe_cu.get("bien_so")),
        model=data.get("model", xe_cu.get("model")),
        loai_xe=data.get("loai_xe", xe_cu.get("loai_xe")),
        trang_thai=data.get("trang_thai", xe_cu.get("trang_thai")),
        ghi_chu=data.get("ghi_chu", xe_cu.get("ghi_chu")),
        tai_xe_mac_dinh_id=data.get(
            "tai_xe_mac_dinh_id",
            xe_cu.get("tai_xe_mac_dinh_id")
        ),
        quan_ly_id=data.get("quan_ly_id", 1),
    )

    return jsonify({
        "success": ok,
        "message": (
            "Đã cập nhật xe."
            if ok
            else "Cập nhật xe thất bại."
        )
    }), 200 if ok else 400
@admin_bp.route("/admin/analytics")
def admin_analytics_page():
    return render_template("admin/analytics.html")


@admin_bp.route("/api/admin/analytics")
def api_admin_analytics():
    data = lay_admin_analytics()

    return jsonify({
        "success": True,
        "data": data
    })
@admin_bp.route("/api/admin/export-pdf")
def export_admin_pdf():
    data = lay_admin_analytics()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    export_dir = os.path.join(base_dir, "exports")

    os.makedirs(export_dir, exist_ok=True)

    file_path = os.path.join(export_dir, "bao_cao_thong_ke.pdf")

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "BAO CAO THONG KE HE THONG GIAM SAT TAI XE")
    y -= 1 * cm

    c.setFont("Helvetica", 10)
    c.drawString(
        2 * cm,
        y,
        f"Thoi gian xuat bao cao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    y -= 1.2 * cm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(2 * cm, y, "1. Tong quan")
    y -= 0.8 * cm

    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, y, f"Tong canh bao AI: {data['tong_canh_bao']}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"So lan buon ngu: {data['tong_buon_ngu']}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"So lan met moi: {data['tong_met_moi']}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Tong bao cao su co: {data['tong_bao_cao_su_co']}")
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(2 * cm, y, "2. Top tai xe nguy co cao")
    y -= 0.8 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Tai xe")
    c.drawString(8 * cm, y, "Tong canh bao")
    c.drawString(12 * cm, y, "Buon ngu")
    c.drawString(15 * cm, y, "Met moi")
    y -= 0.5 * cm

    c.setFont("Helvetica", 10)

    for item in data["top_tai_xe"]:
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 10)

        c.drawString(2 * cm, y, str(item.get("ho_ten") or "Chua xac dinh"))
        c.drawString(8 * cm, y, str(item.get("tong_canh_bao") or 0))
        c.drawString(12 * cm, y, str(item.get("so_lan_buon_ngu") or 0))
        c.drawString(15 * cm, y, str(item.get("so_lan_met_moi") or 0))
        y -= 0.6 * cm

    y -= 0.5 * cm

    if y < 4 * cm:
        c.showPage()
        y = height - 2 * cm

    c.setFont("Helvetica-Bold", 13)
    c.drawString(2 * cm, y, "3. Bao cao su co theo loai")
    y -= 0.8 * cm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Loai su co")
    c.drawString(10 * cm, y, "So luong")
    y -= 0.5 * cm

    c.setFont("Helvetica", 10)

    for item in data["bao_cao_su_co_theo_loai"]:
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", 10)

        c.drawString(2 * cm, y, str(item.get("loai_su_co") or "KHAC"))
        c.drawString(10 * cm, y, str(item.get("tong") or 0))
        y -= 0.6 * cm

    c.save()

    return send_file(
        file_path,
        as_attachment=True,
        download_name="bao_cao_thong_ke.pdf"
    )