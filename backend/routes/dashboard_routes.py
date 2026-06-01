import cv2
import numpy as np
import base64

from insightface.app import FaceAnalysis

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
    luu_vector_khuon_mat,
    luu_anh_khuon_mat,
)


# ==========================
# FACE AI
# ==========================
face_app = FaceAnalysis()

face_app.prepare(ctx_id=0, det_size=(640, 640))

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
# @dashboard_bp.route("/admin/dashboard")
# def admin_dashboard():

#     return render_template("admin/dashboard.html")


# ==========================
# DRIVER SCHEDULES
# ==========================
@dashboard_bp.route("/driver/schedules")
def driver_schedules():

    tai_xe_id = request.args.get("tai_xe_id")

    schedules = lay_lich_chay_tai_xe(tai_xe_id)


    return render_template(
        "driver/schedules.html", schedules=schedules, tai_xe_id=tai_xe_id
    )
# ==========================
# DRIVER NOTIFICATIONS
# ==========================
@dashboard_bp.route("/driver/notifications")
def driver_notifications():

    tai_xe_id = request.args.get("tai_xe_id")

    notifications = lay_thong_bao_tai_xe(tai_xe_id)


    return render_template(
        "driver/notifications.html", notifications=notifications, tai_xe_id=tai_xe_id
    )
# ==========================
# DOC THONG BAO
# ==========================
@dashboard_bp.route("/driver/read-note/<int:note_id>", methods=["POST"])
def read_note(note_id):

    success = danh_dau_da_doc(note_id)

    return {"success": success}


# ==========================
# DRIVER PROFILE
# ==========================
@dashboard_bp.route("/driver/profile")
def driver_profile():

    tai_xe_id = request.args.get("tai_xe_id")

    profile = lay_profile_tai_xe(tai_xe_id)


    return render_template("driver/profile.html", profile=profile, tai_xe_id=tai_xe_id)
# ==========================
# UPDATE PROFILE
# ==========================
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
# ==========================
# REGISTER FACE PAGE
# ==========================
@dashboard_bp.route("/driver/register-face")
def register_face_page():

    tai_xe_id = request.args.get("tai_xe_id")


    return render_template("driver/register_face.html", tai_xe_id=tai_xe_id)
# ==========================
# SAVE FACE
# ==========================
@dashboard_bp.route("/api/register-face", methods=["POST"])
def register_face():

    try:

        data = request.json

        tai_xe_id = data.get("tai_xe_id")

        image_base64 = data.get("image")

        image_data = image_base64.split(",")[1]

        image_bytes = base64.b64decode(image_data)

        np_arr = np.frombuffer(image_bytes, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        faces = face_app.get(frame)

        if len(faces) == 0:

            return {"success": False, "message": "Không tìm thấy mặt"}

        embedding = faces[0].embedding

        # save vector
        luu_vector_khuon_mat(tai_xe_id, embedding)

        # save image
        luu_anh_khuon_mat(tai_xe_id, image_bytes)

        return {"success": True, "message": "Đăng ký khuôn mặt thành công"}

    except Exception as e:

        print("Register face error:", e)

        return {"success": False, "message": "Lỗi server"}
