from flask import Blueprint, request, jsonify, render_template, redirect, session
from flask_jwt_extended import create_access_token
from database.mysql_service import kiem_tra_dang_nhap

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()

    ten_dang_nhap = data.get("ten_dang_nhap")
    mat_khau = data.get("mat_khau")

    user = kiem_tra_dang_nhap(ten_dang_nhap, mat_khau)

    if not user:
        return jsonify({
            "success": False,
            "message": "Sai tài khoản hoặc mật khẩu"
        }), 401

    token = create_access_token(identity=str(user["id"]))

    return jsonify({
        "success": True,
        "message": "Đăng nhập thành công",
        "token": token,
        "user": {
            "id": user["id"],
            "ten_dang_nhap": user["ten_dang_nhap"],
            "vai_tro": user["vai_tro"]
        }
    })


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")