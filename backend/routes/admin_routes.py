from datetime import datetime
import os

from flask import Blueprint, g, jsonify, render_template, request, send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.middleware.auth_guard import require_role
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

admin_bp = Blueprint("admin_bp", __name__)


@admin_bp.route("/admin/dashboard")
@require_role("quan_ly")
def admin_dashboard_page():
    return render_template("admin/dashboard.html")


@admin_bp.route("/admin/reports")
@require_role("quan_ly")
def admin_reports_page():
    return render_template("admin/reports.html")


@admin_bp.route("/api/admin/dashboard")
@require_role("quan_ly")
def api_admin_dashboard():
    data = lay_admin_dashboard()

    return jsonify({
        "success": True,
        "data": data
    })


@admin_bp.route("/admin/drivers")
@require_role("quan_ly")
def admin_drivers_page():
    return render_template("admin/drivers.html")


@admin_bp.route("/api/admin/drivers", methods=["GET"])
@require_role("quan_ly")
def api_admin_drivers():
    data = lay_danh_sach_tai_xe()

    return jsonify({
        "success": True,
        "data": data
    })


@admin_bp.route("/api/admin/drivers", methods=["POST"])
@require_role("quan_ly")
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
        quan_ly_id=g.current_user["id"],
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
@require_role("quan_ly")
def api_update_driver(tai_xe_id):
    data = request.get_json(silent=True) or {}

    ok = cap_nhat_tai_xe_va_thong_bao(
        tai_xe_id=tai_xe_id,
        ho_ten=data.get("ho_ten"),
        so_dien_thoai=data.get("so_dien_thoai"),
        so_gplx=data.get("so_gplx"),
        dia_chi=data.get("dia_chi"),
        trang_thai=data.get("trang_thai"),
        quan_ly_id=g.current_user["id"],
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
@require_role("quan_ly")
def admin_vehicles_page():
    return render_template("admin/vehicles.html")


@admin_bp.route("/api/admin/vehicles", methods=["GET"])
@require_role("quan_ly")
def api_admin_vehicles():
    data = lay_danh_sach_xe_admin()

    return jsonify({
        "success": True,
        "data": data
    })


@admin_bp.route("/api/admin/vehicles", methods=["POST"])
@require_role("quan_ly")
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
        quan_ly_id=g.current_user["id"],
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
@require_role("quan_ly")
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
        quan_ly_id=g.current_user["id"],
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
@require_role("quan_ly")
def admin_analytics_page():
    return render_template("admin/analytics.html")


@admin_bp.route("/api/admin/analytics")
@require_role("quan_ly")
def api_admin_analytics():
    data = lay_admin_analytics()

    return jsonify({
        "success": True,
        "data": data
    })


def _register_unicode_fonts(base_dir):
    """
    Tim va dang ky font Unicode (ho tro day du tieng Viet co dau).
    Uu tien assets/fonts -> Windows Fonts -> Linux DejaVu -> fallback Helvetica.
    """
    candidates = [
        (
            os.path.join(base_dir, "assets", "fonts", "DejaVuSans.ttf"),
            os.path.join(base_dir, "assets", "fonts", "DejaVuSans-Bold.ttf"),
        ),
        (
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ),
        (
            r"C:\Windows\Fonts\tahoma.ttf",
            r"C:\Windows\Fonts\tahomabd.ttf",
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
    ]

    for regular_path, bold_path in candidates:
        if os.path.isfile(regular_path):
            try:
                if "VNFont" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("VNFont", regular_path))
                bold_name = "VNFont"
                if os.path.isfile(bold_path):
                    if "VNFont-Bold" not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont("VNFont-Bold", bold_path))
                    bold_name = "VNFont-Bold"
                return "VNFont", bold_name
            except Exception:
                continue

    return "Helvetica", "Helvetica-Bold"


@admin_bp.route("/api/admin/export-pdf")
@require_role("quan_ly")
def export_admin_pdf():
    data = lay_admin_analytics()
    tu_ngay = request.args.get("from")
    den_ngay = request.args.get("to")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    export_dir = os.path.join(base_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)

    file_path = os.path.join(export_dir, "bao_cao_thong_ke.pdf")
    font_regular, font_bold = _register_unicode_fonts(base_dir)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "VNTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
    )
    heading_style = ParagraphStyle(
        "VNHeading",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#1e293b"),
    )
    normal_style = ParagraphStyle(
        "VNNormal",
        parent=styles["Normal"],
        fontName=font_regular,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("BÁO CÁO THỐNG KÊ HỆ THỐNG GIÁM SÁT TÀI XẾ", title_style),
        Spacer(1, 0.2 * cm),
        Paragraph(
            f"Thời gian xuất báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            normal_style,
        ),
    ]

    if tu_ngay or den_ngay:
        elements.append(
            Paragraph(
                f"Phạm vi lọc: {tu_ngay or '...'} đến {den_ngay or '...'}",
                normal_style,
            )
        )

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("1. Tổng quan hệ thống", heading_style))

    overview_table = Table(
        [
            ["Chỉ số", "Giá trị"],
            ["Tổng cảnh báo AI", str(data.get("tong_canh_bao", 0))],
            ["Số lần buồn ngủ", str(data.get("tong_buon_ngu", 0))],
            ["Số lần mệt mỏi", str(data.get("tong_met_moi", 0))],
            ["Tổng báo cáo sự cố", str(data.get("tong_bao_cao_su_co", 0))],
        ],
        colWidths=[11 * cm, 5.5 * cm],
    )
    overview_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
    ]))
    elements.append(overview_table)

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("2. Top tài xế nguy cơ cao", heading_style))

    driver_rows = [["Tài xế", "Tổng cảnh báo", "Buồn ngủ", "Mệt mỏi"]]
    for item in data.get("top_tai_xe", []):
        driver_rows.append([
            str(item.get("ho_ten") or "Chưa xác định"),
            str(item.get("tong_canh_bao") or 0),
            str(item.get("so_lan_buon_ngu") or 0),
            str(item.get("so_lan_met_moi") or 0),
        ])
    if len(driver_rows) == 1:
        driver_rows.append(["Chưa có dữ liệu", "0", "0", "0"])

    driver_table = Table(driver_rows, colWidths=[7.5 * cm, 3 * cm, 3 * cm, 3 * cm])
    driver_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    elements.append(driver_table)

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("3. Báo cáo sự cố theo loại", heading_style))

    incident_rows = [["Loại sự cố", "Số lượng"]]
    for item in data.get("bao_cao_su_co_theo_loai", []):
        incident_rows.append([
            str(item.get("loai_su_co") or "KHAC"),
            str(item.get("tong") or 0),
        ])
    if len(incident_rows) == 1:
        incident_rows.append(["Chưa có dữ liệu", "0"])

    incident_table = Table(incident_rows, colWidths=[11 * cm, 5.5 * cm])
    incident_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_regular),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
    ]))
    elements.append(incident_table)

    doc.build(elements)

    return send_file(
        file_path,
        as_attachment=True,
        download_name="bao_cao_thong_ke.pdf"
    )