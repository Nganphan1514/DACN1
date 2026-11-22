from functools import wraps
import time

from flask import g, jsonify, redirect, request, session
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from database.mysql_service import kiem_tra_tai_khoan_hoat_dong

_ACCOUNT_STATUS_CACHE = {}
_ACCOUNT_CACHE_TTL = 20.0


def _is_account_active(user_id):
    now = time.time()
    cached = _ACCOUNT_STATUS_CACHE.get(user_id)
    if cached and (now - cached[1]) < _ACCOUNT_CACHE_TTL:
        return cached[0]

    active = kiem_tra_tai_khoan_hoat_dong(user_id)
    _ACCOUNT_STATUS_CACHE[user_id] = (active, now)
    return active


def invalidate_account_cache(user_id):
    _ACCOUNT_STATUS_CACHE.pop(user_id, None)


def _is_api_request():
    return request.path.startswith("/api/")


def get_current_user():
    """
    Lay thong tin nguoi dung da xac thuc tu JWT (uu tien) hoac Flask session.
    Kiem tra tai khoan chua bi khoa (P0-5: thu hoi hieu luc JWT/Session ngay khi khoa).
    """
    user = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            verify_jwt_in_request(optional=False)
            identity = get_jwt_identity()
            claims = get_jwt()
            user = {
                "id": int(identity),
                "ten_dang_nhap": claims.get("ten_dang_nhap"),
                "vai_tro": claims.get("vai_tro"),
                "tai_xe_id": claims.get("tai_xe_id"),
            }
        except Exception:
            return None
    else:
        sess_user = session.get("user")
        if isinstance(sess_user, dict) and sess_user.get("id") and sess_user.get("vai_tro"):
            user = sess_user

    if not user:
        return None

    if not _is_account_active(user["id"]):
        session.clear()
        return None

    return user


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            if _is_api_request():
                return jsonify({
                    "success": False,
                    "message": "Vui lòng đăng nhập để tiếp tục."
                }), 401
            return redirect("/login")

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def require_role(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                if _is_api_request():
                    return jsonify({
                        "success": False,
                        "message": "Vui lòng đăng nhập để tiếp tục."
                    }), 401
                return redirect("/login")

            if user.get("vai_tro") not in allowed_roles:
                if _is_api_request():
                    return jsonify({
                        "success": False,
                        "message": "Bạn không có quyền truy cập chức năng này."
                    }), 403
                if user.get("vai_tro") == "quan_ly":
                    return redirect("/admin/dashboard")
                tai_xe_id = user.get("tai_xe_id")
                if tai_xe_id:
                    return redirect(f"/driver/dashboard?tai_xe_id={tai_xe_id}")
                return redirect("/login")

            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def resolve_driver_id(requested_tai_xe_id=None):
    """
    Chong IDOR:
    - Neu la tai_xe: bat buoc dung tai_xe_id cua chinh tai khoan dang nhap.
      Neu truyen tai_xe_id khac cua nguoi khac -> tra ve (None, False).
    - Neu la quan_ly: cho phep xem theo requested_tai_xe_id.
    """
    user = getattr(g, "current_user", None) or get_current_user()
    if not user:
        return None, False

    if user.get("vai_tro") == "quan_ly":
        if requested_tai_xe_id in (None, ""):
            return None, False
        try:
            return int(requested_tai_xe_id), True
        except (TypeError, ValueError):
            return None, False

    own_driver_id = user.get("tai_xe_id")
    if own_driver_id is None:
        return None, False

    if requested_tai_xe_id not in (None, ""):
        try:
            if int(requested_tai_xe_id) != int(own_driver_id):
                return None, False
        except (TypeError, ValueError):
            return None, False

    return int(own_driver_id), True
