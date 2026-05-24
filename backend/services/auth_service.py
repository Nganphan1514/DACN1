from database.mysql_service import db

from utils.jwt_helper import create_token


def login_user(username, password):

    query = """
    SELECT *
    FROM tai_khoan
    WHERE ten_dang_nhap=%s
    LIMIT 1
    """

    user = db.fetch_one(query, (username,))

    # Không tồn tại
    if not user:

        return {"success": False, "message": "Sai tài khoản"}

    # Sai password
    if user["mat_khau"] != password:

        return {"success": False, "message": "Sai mật khẩu"}

    # bị khóa
    if user["trang_thai"] == "khoa":

        return {"success": False, "message": "Tài khoản bị khóa"}

    token = create_token(user)

    return {
        "success": True,
        "message": "Đăng nhập thành công",
        "token": token,
        "role": user["vai_tro"],
        "username": user["ten_dang_nhap"],
    }
