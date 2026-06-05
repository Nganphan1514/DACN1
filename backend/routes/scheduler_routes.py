from flask import Blueprint, render_template, jsonify, request

from database.mysql_service import (
    tao_lich_chay,
    lay_tat_ca_lich_chay,
    cap_nhat_lich_chay,
    xoa_lich_chay,
    lay_danh_sach_tai_xe,
    lay_danh_sach_xe_admin,
)

scheduler_bp = Blueprint("scheduler_bp", __name__)



# TRANG QUAN LY LICH CHAY

@scheduler_bp.route("/admin/scheduler")
def admin_scheduler_page():
    return render_template("admin/scheduler.html")



# DANH SACH LICH CHAY

@scheduler_bp.route("/api/admin/schedules", methods=["GET"])
def api_admin_schedules():
    data = lay_tat_ca_lich_chay()

    return jsonify({
        "success": True,
        "data": data
    })



# OPTION TAO LICH
# Chi hien tai xe dang lam va xe dang hoat dong

@scheduler_bp.route("/api/admin/schedules/options", methods=["GET"])
def api_schedule_options():
    drivers = lay_danh_sach_tai_xe()
    vehicles = lay_danh_sach_xe_admin()

    drivers = [
        item
        for item in drivers
        if item.get("trang_thai") == "dang_lam"
    ]

    vehicles = [
        item
        for item in vehicles
        if item.get("trang_thai") == "hoat_dong"
    ]

    return jsonify({
        "success": True,
        "drivers": drivers,
        "vehicles": vehicles
    })



# TAO LICH MOI

@scheduler_bp.route("/api/admin/schedules", methods=["POST"])
def api_create_schedule():
    data = request.get_json(silent=True) or {}

    required_fields = [
        "tai_xe_id",
        "xe_id",
        "tuyen_duong",
        "gio_bat_dau",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return jsonify({
            "success": False,
            "message": (
                "Vui lòng chọn tài xế, xe, tuyến đường "
                "và giờ bắt đầu."
            )
        }), 400

    lich_id = tao_lich_chay(
        tai_xe_id=data.get("tai_xe_id"),
        xe_id=data.get("xe_id"),
        tuyen_duong=data.get("tuyen_duong"),
        gio_bat_dau=data.get("gio_bat_dau"),
        gio_ket_thuc=data.get("gio_ket_thuc"),
        quan_ly_id=data.get("quan_ly_id", 1)
    )

    if lich_id is None:
        return jsonify({
            "success": False,
            "message": (
                "Tạo lịch thất bại. "
                "Hãy kiểm tra xe có đang hoạt động "
                "và tài xế có đang làm việc hay không."
            )
        }), 400

    return jsonify({
        "success": True,
        "message": "Đã tạo lịch chạy.",
        "id": lich_id
    }), 201



# CAP NHAT LICH

@scheduler_bp.route(
    "/api/admin/schedules/<int:lich_id>",
    methods=["PUT"]
)
def api_update_schedule(lich_id):
    data = request.get_json(silent=True) or {}

    ok = cap_nhat_lich_chay(
        lich_id=lich_id,
        tai_xe_id=data.get("tai_xe_id"),
        xe_id=data.get("xe_id"),
        tuyen_duong=data.get("tuyen_duong"),
        gio_bat_dau=data.get("gio_bat_dau"),
        gio_ket_thuc=data.get("gio_ket_thuc"),
        trang_thai=data.get("trang_thai"),
        quan_ly_id=data.get("quan_ly_id", 1)
    )

    return jsonify({
        "success": ok,
        "message": (
            "Đã cập nhật lịch chạy."
            if ok
            else (
                "Cập nhật thất bại. "
                "Lịch đã hủy không thể kích hoạt lại. "
                "Xe và tài xế cũng phải đang hoạt động."
            )
        )
    }), 200 if ok else 400



# HUY LICH
# Chi cap nhat thanh da_huy, khong xoa ban ghi

@scheduler_bp.route(
    "/api/admin/schedules/<int:lich_id>",
    methods=["DELETE"]
)
def api_delete_schedule(lich_id):
    data = request.get_json(silent=True) or {}

    ok = xoa_lich_chay(
        lich_id=lich_id,
        quan_ly_id=data.get("quan_ly_id", 1)
    )

    return jsonify({
        "success": ok,
        "message": (
            "Đã hủy lịch chạy."
            if ok
            else "Hủy lịch thất bại."
        )
    }), 200 if ok else 400
# from flask import Blueprint, render_template, jsonify, request

# from database.mysql_service import (
#     tao_lich_chay,
#     lay_tat_ca_lich_chay,
#     cap_nhat_lich_chay,
#     xoa_lich_chay,
#     lay_danh_sach_tai_xe,
#     lay_danh_sach_xe_admin,
# )

# scheduler_bp = Blueprint("scheduler_bp", __name__)


# @scheduler_bp.route("/admin/scheduler")
# def admin_scheduler_page():
#     return render_template("admin/scheduler.html")


# @scheduler_bp.route("/api/admin/schedules", methods=["GET"])
# def api_admin_schedules():
#     data = lay_tat_ca_lich_chay()

#     return jsonify({
#         "success": True,
#         "data": data
#     })


# @scheduler_bp.route("/api/admin/schedules/options", methods=["GET"])
# def api_schedule_options():
#     drivers = lay_danh_sach_tai_xe()
#     vehicles = lay_danh_sach_xe_admin()

#     return jsonify({
#         "success": True,
#         "drivers": drivers,
#         "vehicles": vehicles
#     })


# @scheduler_bp.route("/api/admin/schedules", methods=["POST"])
# def api_create_schedule():
#     data = request.get_json()

#     lich_id = tao_lich_chay(
#         tai_xe_id=data.get("tai_xe_id"),
#         xe_id=data.get("xe_id"),
#         tuyen_duong=data.get("tuyen_duong"),
#         gio_bat_dau=data.get("gio_bat_dau"),
#         gio_ket_thuc=data.get("gio_ket_thuc"),
#         quan_ly_id=data.get("quan_ly_id", 1)
#     )

#     return jsonify({
#         "success": lich_id is not None,
#         "message": "Đã tạo lịch chạy" if lich_id else "Tạo lịch thất bại",
#         "id": lich_id
#     })


# @scheduler_bp.route("/api/admin/schedules/<int:lich_id>", methods=["PUT"])
# def api_update_schedule(lich_id):
#     data = request.get_json()

#     ok = cap_nhat_lich_chay(
#         lich_id=lich_id,
#         tai_xe_id=data.get("tai_xe_id"),
#         xe_id=data.get("xe_id"),
#         tuyen_duong=data.get("tuyen_duong"),
#         gio_bat_dau=data.get("gio_bat_dau"),
#         gio_ket_thuc=data.get("gio_ket_thuc"),
#         trang_thai=data.get("trang_thai"),
#         quan_ly_id=data.get("quan_ly_id", 1)
#     )

#     return jsonify({
#         "success": ok,
#         "message": "Đã cập nhật lịch chạy" if ok else "Cập nhật thất bại"
#     })


# @scheduler_bp.route("/api/admin/schedules/<int:lich_id>", methods=["DELETE"])
# def api_delete_schedule(lich_id):
#     data = request.get_json(silent=True) or {}

#     ok = xoa_lich_chay(
#         lich_id=lich_id,
#         quan_ly_id=data.get("quan_ly_id", 1)
#     )

#     return jsonify({
#         "success": ok,
#         "message": "Đã hủy lịch chạy" if ok else "Hủy lịch thất bại"
#     })