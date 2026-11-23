from flask import Blueprint, jsonify, render_template, request

from backend.middleware.auth_guard import require_permission, require_role, resolve_driver_id
from database.mysql_service import (
    lay_trang_thai_khuon_mat,
    luu_anh_khuon_mat,
    luu_nhieu_vector_khuon_mat,
)
from face_auth.embedding_service import (
    decode_base64_image,
    extract_face_embedding,
)

face_bp = Blueprint("face_bp", __name__)


@face_bp.route("/driver/register-face", methods=["GET"])
@face_bp.route("/admin/drivers/<int:tai_xe_id>/register-face", methods=["GET"])
@require_permission("drivers:register_face")
def register_face_page(tai_xe_id=None):
    target_id = tai_xe_id or request.args.get("tai_xe_id")
    resolved_id, allowed = resolve_driver_id(target_id)
    if not allowed:
        return "Thiếu mã tài xế hợp lệ để đăng ký khuôn mặt.", 400

    face_status = lay_trang_thai_khuon_mat(resolved_id)
    return render_template(
        "driver/register_face.html",
        tai_xe_id=resolved_id,
        face_status=face_status,
    )


@face_bp.route("/api/driver/face-status/<int:tai_xe_id>", methods=["GET"])
@require_role("tai_xe", "quan_ly")
def api_face_status(tai_xe_id):
    resolved_id, allowed = resolve_driver_id(tai_xe_id)
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Bạn không có quyền xem trạng thái khuôn mặt của tài xế khác."
        }), 403

    status = lay_trang_thai_khuon_mat(resolved_id)
    return jsonify({
        "success": True,
        "data": status,
    })


@face_bp.route("/api/driver/register-face", methods=["POST"])
@face_bp.route("/api/admin/drivers/register-face", methods=["POST"])
@face_bp.route("/api/register-face", methods=["POST"])
@require_permission("drivers:register_face")
def api_register_face():
    """
    Chi QUAN LY moi duoc dang ky hoac dang ky lai khuon mat 128D cho tai xe
    (chong tai xe tu dang ky khuon mat nguoi khac).
    """
    data = request.get_json(silent=True) or {}

    resolved_id, allowed = resolve_driver_id(data.get("tai_xe_id"))
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Vui lòng chọn tài xế hợp lệ để đăng ký khuôn mặt."
        }), 400

    raw_images = data.get("images")
    if not raw_images and data.get("image"):
        raw_images = [data.get("image")]

    if not raw_images or not isinstance(raw_images, list):
        return jsonify({
            "success": False,
            "message": "Vui lòng gửi ít nhất 1 ảnh khuôn mặt."
        }), 400

    raw_images = raw_images[:5]

    embeddings = []
    first_raw_bytes = None
    last_error = "Không trích xuất được đặc trưng khuôn mặt."

    for data_url in raw_images:
        frame, raw_bytes = decode_base64_image(data_url)
        if frame is None:
            last_error = "Định dạng ảnh gửi lên không hợp lệ."
            continue

        embedding, err = extract_face_embedding(frame, require_single_face=True)
        if err:
            last_error = err
            continue

        embeddings.append(embedding)
        if first_raw_bytes is None and raw_bytes:
            first_raw_bytes = raw_bytes

    if not embeddings:
        return jsonify({
            "success": False,
            "message": last_error,
        }), 400

    saved_vectors = luu_nhieu_vector_khuon_mat(
        tai_xe_id=resolved_id,
        embeddings=embeddings,
        mo_ta="Quản lý đăng ký",
    )

    if not saved_vectors:
        return jsonify({
            "success": False,
            "message": "Lưu dữ liệu khuôn mặt vào cơ sở dữ liệu thất bại."
        }), 500

    if first_raw_bytes:
        luu_anh_khuon_mat(resolved_id, first_raw_bytes)

    return jsonify({
        "success": True,
        "message": f"Đăng ký khuôn mặt thành công ({len(embeddings)} mẫu).",
        "data": lay_trang_thai_khuon_mat(resolved_id),
    }), 200
