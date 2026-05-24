from flask import Blueprint, request, jsonify, render_template

from backend.services.auth_service import login_user

from database.mysql_service import db

auth_bp = Blueprint("auth", __name__)


# ==========================
# LOGIN PAGE
# ==========================
@auth_bp.route("/login")
def login_page():

    return render_template("auth/login.html")


# ==========================
# LOGIN API
# ==========================
@auth_bp.route("/api/login", methods=["POST"])
def login():

    try:

        data = request.json

        username = data.get("username")

        password = data.get("password")

        result = login_user(username, password)

        print(result)

        # ==========================
        # LOGIN FAIL
        # ==========================
        if not result.get("success"):

            return jsonify(result)

        role = result.get("role")

        username = result.get("username")

        # ==========================
        # QUAN LY
        # ==========================
        if role == "quan_ly":

            return jsonify({"success": True, "redirect": "/admin/dashboard"})

        # ==========================
        # TAI XE
        # ==========================
        query = """
        SELECT
            tx.id
        FROM tai_xe tx
        INNER JOIN tai_khoan tk
        ON tx.tai_khoan_id = tk.id
        WHERE tk.ten_dang_nhap=%s
        LIMIT 1
        """

        tai_xe = db.fetch_one(query, (username,))

        if not tai_xe:

            return jsonify({"success": False, "message": "Không tìm thấy tài xế"})

        return jsonify(
            {"success": True, "redirect": f"/driver/dashboard?tai_xe_id={tai_xe['id']}"}
        )

    except Exception as e:

        print("Login error:", e)

        return jsonify({"success": False, "message": "Lỗi server"})
