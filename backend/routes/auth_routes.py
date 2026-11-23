from flask import Blueprint, g, jsonify, redirect, render_template, request, session
from flask_jwt_extended import create_access_token

from backend.middleware.auth_guard import require_auth
from core.ops_rules import ROLE_LABELS, lay_menu_theo_vai_tro, lay_quyen_theo_vai_tro
from database.mysql_service import (
    kiem_tra_dang_nhap,
    lay_tai_xe_theo_tai_khoan_id,
)
from database.org_service import doi_mat_khau_tai_khoan, lay_pham_vi_tai_khoan

auth_bp = Blueprint("auth_bp", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")


@auth_bp.route("/api/login", methods=["POST"])
@auth_bp.route("/api/auth/login", methods=["POST"])
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
    doi_xe_id = user.get("doi_xe_id")
    if user["vai_tro"] == "tai_xe":
        tai_xe = lay_tai_xe_theo_tai_khoan_id(user["id"])
        if tai_xe:
            tai_xe_id = tai_xe["id"]
            if doi_xe_id is None:
                doi_xe_id = tai_xe.get("doi_xe_id")

    token_version = int(user.get("token_version") or 1)
    user_payload = {
        "id": user["id"],
        "ten_dang_nhap": user["ten_dang_nhap"],
        "vai_tro": user["vai_tro"],
        "vai_tro_label": ROLE_LABELS.get(user["vai_tro"], user["vai_tro"]),
        "tai_xe_id": tai_xe_id,
        "cong_ty_id": user.get("cong_ty_id"),
        "chi_nhanh_id": user.get("chi_nhanh_id"),
        "doi_xe_id": doi_xe_id,
        "scope": {
            "cong_ty_id": user.get("cong_ty_id"),
            "chi_nhanh_id": user.get("chi_nhanh_id"),
            "doi_xe_id": doi_xe_id,
        },
        "permissions": lay_quyen_theo_vai_tro(user["vai_tro"]),
        "menu": lay_menu_theo_vai_tro(user["vai_tro"]),
    }

    token = create_access_token(
        identity=str(user["id"]),
        additional_claims={
            "ten_dang_nhap": user["ten_dang_nhap"],
            "vai_tro": user["vai_tro"],
            "tai_xe_id": tai_xe_id,
            "cong_ty_id": user.get("cong_ty_id"),
            "chi_nhanh_id": user.get("chi_nhanh_id"),
            "doi_xe_id": doi_xe_id,
            "tv": token_version,
        },
    )

    session["user"] = user_payload

    return jsonify({
        "success": True,
        "message": "Đăng nhập thành công",
        "token": token,
        "user": user_payload,
    })


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth
def api_auth_me():
    user = g.current_user
    fresh = lay_pham_vi_tai_khoan(user["id"]) or user
    role_val = fresh.get("vai_tro", user.get("vai_tro"))
    cty_id = fresh.get("cong_ty_id", user.get("cong_ty_id"))
    cn_id = fresh.get("chi_nhanh_id", user.get("chi_nhanh_id"))
    dx_id = fresh.get("doi_xe_id", user.get("doi_xe_id"))
    payload = {
        "id": fresh.get("id", user["id"]),
        "ten_dang_nhap": fresh.get("ten_dang_nhap", user.get("ten_dang_nhap")),
        "vai_tro": role_val,
        "vai_tro_label": ROLE_LABELS.get(role_val, ""),
        "tai_xe_id": fresh.get("tai_xe_id", user.get("tai_xe_id")),
        "cong_ty_id": cty_id,
        "chi_nhanh_id": cn_id,
        "doi_xe_id": dx_id,
        "scope": {
            "cong_ty_id": cty_id,
            "chi_nhanh_id": cn_id,
            "doi_xe_id": dx_id,
        },
        "permissions": lay_quyen_theo_vai_tro(role_val),
        "menu": lay_menu_theo_vai_tro(role_val),
    }
    return jsonify({"success": True, "user": payload})


@auth_bp.route("/api/auth/change-password", methods=["POST"])
@require_auth
def api_change_password():
    data = request.get_json(silent=True) or {}
    ok, msg = doi_mat_khau_tai_khoan(
        tai_khoan_id=g.current_user["id"],
        mat_khau_cu=data.get("mat_khau_cu"),
        mat_khau_moi=data.get("mat_khau_moi"),
    )
    return jsonify({"success": ok, "message": msg}), 200 if ok else 400


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
