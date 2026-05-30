from flask import Blueprint, request, jsonify

from database.mysql_service import (
    tao_bao_cao_su_co,
    lay_bao_cao_su_co_tai_xe,
    lay_tat_ca_bao_cao_su_co,
    cap_nhat_trang_thai_bao_cao,
)

report_bp = Blueprint("report_bp", __name__)


@report_bp.route("/api/driver/reports/<int:tai_xe_id>", methods=["GET"])
def api_driver_reports(tai_xe_id):
    data = lay_bao_cao_su_co_tai_xe(tai_xe_id)

    return jsonify({
        "success": True,
        "data": data
    })


@report_bp.route("/api/driver/reports", methods=["POST"])
def api_create_driver_report():
    data = request.get_json()

    ok = tao_bao_cao_su_co(
        tai_xe_id=data.get("tai_xe_id"),
        xe_id=data.get("xe_id"),
        lich_chay_id=data.get("lich_chay_id"),
        tieu_de=data.get("tieu_de"),
        loai_su_co=data.get("loai_su_co"),
        noi_dung=data.get("noi_dung"),
        hinh_anh=data.get("hinh_anh")
    )

    return jsonify({
        "success": ok,
        "message": "Đã gửi báo cáo sự cố" if ok else "Gửi báo cáo thất bại"
    })


@report_bp.route("/api/admin/reports", methods=["GET"])
def api_admin_reports():
    data = lay_tat_ca_bao_cao_su_co()

    return jsonify({
        "success": True,
        "data": data
    })


@report_bp.route("/api/admin/reports/<int:bao_cao_id>", methods=["PUT"])
def api_update_report(bao_cao_id):
    data = request.get_json()

    ok = cap_nhat_trang_thai_bao_cao(
        bao_cao_id=bao_cao_id,
        trang_thai=data.get("trang_thai"),
        phan_hoi_quan_ly=data.get("phan_hoi_quan_ly")
    )

    return jsonify({
        "success": ok,
        "message": "Đã cập nhật báo cáo" if ok else "Cập nhật thất bại"
    })