from flask import Blueprint, jsonify, redirect, render_template, request, session
from flask_jwt_extended import create_access_token

from database.mysql_service import (
    kiem_tra_dang_nhap,
    lay_tai_xe_theo_tai_khoan_id,
)

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}

    ten_dang_nhap = data.get("ten_dang_nhap")
    mat_khau = data.get("mat_khau")

    user = kiem_tra_dang_nhap(ten_dang_nhap, mat_khau)

    if not user:
        return jsonify({
            "success": False,
            "message": "Sai tài khoản, mật khẩu hoặc tài khoản đã bị khóa"
        }), 401

    tai_xe_id = None
    if user["vai_tro"] == "tai_xe":
        tai_xe = lay_tai_xe_theo_tai_khoan_id(user["id"])
        if tai_xe:
            tai_xe_id = tai_xe["id"]

    user_payload = {
        "id": user["id"],
        "ten_dang_nhap": user["ten_dang_nhap"],
        "vai_tro": user["vai_tro"],
        "tai_xe_id": tai_xe_id,
    }

    token = create_access_token(
        identity=str(user["id"]),
        additional_claims={
            "ten_dang_nhap": user["ten_dang_nhap"],
            "vai_tro": user["vai_tro"],
            "tai_xe_id": tai_xe_id,
        },
    )

    session["user"] = user_payload

    return jsonify({
        "success": True,
        "message": "Đăng nhập thành công",
        "token": token,
        "user": user_payload,
    })


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
