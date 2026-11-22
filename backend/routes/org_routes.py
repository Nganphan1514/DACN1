"""
DACN1 V3.0 - Routes quan ly To chuc (Cong ty / Chi nhanh / Doi xe),
Tai khoan & Phan quyen RBAC 6 vai tro, Dieu chuyen doi xe & Audit Log.
"""

from flask import Blueprint, g, jsonify, request

from backend.middleware.auth_guard import (
    get_current_scope,
    invalidate_account_cache,
    require_role,
)
from core.ops_rules import (
    AUDIT_VIEW_ROLES,
    FLEET_MANAGE_ROLES,
    FLEET_VIEW_ROLES,
    ORG_ADMIN_ROLES,
    ROLE_ADMIN_HE_THONG,
    ROLE_LABELS,
    ROLE_QUAN_LY,
    ROLE_QUAN_TRI_CONG_TY,
)
from database.org_service import (
    cap_nhat_cau_hinh_cong_ty,
    cap_nhat_chi_nhanh,
    cap_nhat_doi_xe,
    cap_nhat_tai_khoan_va_quyen,
    chuyen_doi_xe_thuc_the,
    lay_danh_sach_chi_nhanh,
    lay_danh_sach_cong_ty,
    lay_danh_sach_doi_xe,
    lay_danh_sach_tai_khoan,
    lay_lich_su_thao_tac,
    tao_chi_nhanh,
    tao_doi_xe,
    tao_tai_khoan_he_thong,
)

org_bp = Blueprint("org_bp", __name__)


# ============================================================
# CONG TY & CAU HINH DOANH NGHIEP
# ============================================================

@org_bp.route("/api/admin/companies", methods=["GET"])
@require_role(*ORG_ADMIN_ROLES)
def api_list_companies():
    data = lay_danh_sach_cong_ty(scope=get_current_scope())
    return jsonify({"success": True, "data": data})


@org_bp.route("/api/admin/companies/<int:cong_ty_id>/config", methods=["PUT"])
@require_role(*ORG_ADMIN_ROLES)
def api_update_company_config(cong_ty_id):
    scope = get_current_scope()
    if scope["vai_tro"] != ROLE_ADMIN_HE_THONG and scope.get("cong_ty_id") and int(scope["cong_ty_id"]) != cong_ty_id:
        return jsonify({"success": False, "message": "Không có quyền sửa cấu hình công ty khác."}), 403

    data = request.get_json(silent=True) or {}
    ok = cap_nhat_cau_hinh_cong_ty(
        cong_ty_id=cong_ty_id,
        cau_hinh_dict=data,
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({
        "success": ok,
        "message": "Đã cập nhật cấu hình doanh nghiệp." if ok else "Cập nhật cấu hình thất bại.",
    }), 200 if ok else 400


# ============================================================
# CHI NHANH
# ============================================================

@org_bp.route("/api/admin/branches", methods=["GET"])
@require_role(*FLEET_VIEW_ROLES)
def api_list_branches():
    cong_ty_id = request.args.get("cong_ty_id")
    data = lay_danh_sach_chi_nhanh(scope=get_current_scope(), cong_ty_id=cong_ty_id)
    return jsonify({"success": True, "data": data})


@org_bp.route("/api/admin/branches", methods=["POST"])
@require_role(*ORG_ADMIN_ROLES)
def api_create_branch():
    data = request.get_json(silent=True) or {}
    scope = get_current_scope()
    cong_ty_id = data.get("cong_ty_id") or scope.get("cong_ty_id")
    if scope["vai_tro"] != ROLE_ADMIN_HE_THONG and scope.get("cong_ty_id") and int(cong_ty_id or 0) != int(scope["cong_ty_id"]):
        return jsonify({"success": False, "message": "Không thể tạo chi nhánh ngoài công ty quản lý."}), 403

    new_id = tao_chi_nhanh(
        cong_ty_id=cong_ty_id,
        ma_chi_nhanh=data.get("ma_chi_nhanh"),
        ten=data.get("ten"),
        dia_chi=data.get("dia_chi"),
        so_dien_thoai=data.get("so_dien_thoai"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    if not new_id:
        return jsonify({"success": False, "message": "Tạo chi nhánh thất bại (kiểm tra mã chi nhánh hoặc tên)."}), 400
    return jsonify({"success": True, "message": "Đã tạo chi nhánh mới.", "id": new_id}), 201


@org_bp.route("/api/admin/branches/<int:chi_nhanh_id>", methods=["PUT"])
@require_role(*ORG_ADMIN_ROLES)
def api_update_branch(chi_nhanh_id):
    data = request.get_json(silent=True) or {}
    ok = cap_nhat_chi_nhanh(
        chi_nhanh_id=chi_nhanh_id,
        ten=data.get("ten"),
        dia_chi=data.get("dia_chi"),
        so_dien_thoai=data.get("so_dien_thoai"),
        trang_thai=data.get("trang_thai"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({
        "success": ok,
        "message": "Đã cập nhật chi nhánh." if ok else "Cập nhật chi nhánh thất bại.",
    }), 200 if ok else 400


# ============================================================
# DOI XE & DIEU CHUYEN DOI XE (ORG-02)
# ============================================================

@org_bp.route("/api/admin/fleets", methods=["GET"])
@require_role(*FLEET_VIEW_ROLES)
def api_list_fleets():
    chi_nhanh_id = request.args.get("chi_nhanh_id")
    data = lay_danh_sach_doi_xe(scope=get_current_scope(), chi_nhanh_id=chi_nhanh_id)
    return jsonify({"success": True, "data": data})


@org_bp.route("/api/admin/fleets", methods=["POST"])
@require_role(*FLEET_MANAGE_ROLES)
def api_create_fleet():
    data = request.get_json(silent=True) or {}
    scope = get_current_scope()
    chi_nhanh_id = data.get("chi_nhanh_id") or scope.get("chi_nhanh_id")
    if scope["vai_tro"] == ROLE_QUAN_LY and scope.get("chi_nhanh_id") and int(chi_nhanh_id or 0) != int(scope["chi_nhanh_id"]):
        return jsonify({"success": False, "message": "Không thể tạo đội xe ngoài chi nhánh phụ trách."}), 403

    new_id = tao_doi_xe(
        chi_nhanh_id=chi_nhanh_id,
        ma_doi_xe=data.get("ma_doi_xe"),
        ten=data.get("ten"),
        mo_ta=data.get("mo_ta"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    if not new_id:
        return jsonify({"success": False, "message": "Tạo đội xe thất bại (kiểm tra mã đội xe hoặc tên)."}), 400
    return jsonify({"success": True, "message": "Đã tạo đội xe mới.", "id": new_id}), 201


@org_bp.route("/api/admin/fleets/<int:doi_xe_id>", methods=["PUT"])
@require_role(*FLEET_MANAGE_ROLES)
def api_update_fleet(doi_xe_id):
    data = request.get_json(silent=True) or {}
    ok = cap_nhat_doi_xe(
        doi_xe_id=doi_xe_id,
        ten=data.get("ten"),
        mo_ta=data.get("mo_ta"),
        trang_thai=data.get("trang_thai"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({
        "success": ok,
        "message": "Đã cập nhật đội xe." if ok else "Cập nhật đội xe thất bại.",
    }), 200 if ok else 400


@org_bp.route("/api/admin/transfer-fleet", methods=["POST"])
@require_role(*FLEET_MANAGE_ROLES)
def api_transfer_fleet():
    data = request.get_json(silent=True) or {}
    ok, msg = chuyen_doi_xe_thuc_the(
        entity_type=data.get("entity_type"),
        entity_id=data.get("entity_id"),
        doi_xe_moi_id=data.get("doi_xe_moi_id"),
        ly_do=data.get("ly_do"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    return jsonify({"success": ok, "message": msg}), 200 if ok else 400


# ============================================================
# TAI KHOAN & PHAN QUYEN RBAC
# ============================================================

@org_bp.route("/api/admin/roles", methods=["GET"])
@require_role(*FLEET_MANAGE_ROLES)
def api_list_roles():
    return jsonify({
        "success": True,
        "data": [{"code": k, "label": v} for k, v in ROLE_LABELS.items()],
    })


@org_bp.route("/api/admin/accounts", methods=["GET"])
@require_role(*FLEET_MANAGE_ROLES)
def api_list_accounts():
    data = lay_danh_sach_tai_khoan(scope=get_current_scope())
    return jsonify({"success": True, "data": data})


@org_bp.route("/api/admin/accounts", methods=["POST"])
@require_role(*ORG_ADMIN_ROLES)
def api_create_account():
    data = request.get_json(silent=True) or {}
    scope = get_current_scope()
    vai_tro = (data.get("vai_tro") or "").strip()

    # Quan tri cong ty khong duoc tao tai khoan admin_he_thong
    if scope["vai_tro"] == ROLE_QUAN_TRI_CONG_TY and vai_tro == ROLE_ADMIN_HE_THONG:
        return jsonify({"success": False, "message": "Bạn không có quyền tạo tài khoản Quản trị hệ thống."}), 403

    cong_ty_id = data.get("cong_ty_id") or scope.get("cong_ty_id")
    new_id, msg = tao_tai_khoan_he_thong(
        ten_dang_nhap=data.get("ten_dang_nhap"),
        mat_khau=data.get("mat_khau"),
        vai_tro=vai_tro,
        cong_ty_id=cong_ty_id,
        chi_nhanh_id=data.get("chi_nhanh_id"),
        doi_xe_id=data.get("doi_xe_id"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    if not new_id:
        return jsonify({"success": False, "message": msg}), 400
    return jsonify({"success": True, "message": msg, "id": new_id}), 201


@org_bp.route("/api/admin/accounts/<int:tai_khoan_id>", methods=["PUT"])
@require_role(*FLEET_MANAGE_ROLES)
def api_update_account(tai_khoan_id):
    data = request.get_json(silent=True) or {}
    scope = get_current_scope()
    vai_tro_moi = data.get("vai_tro")

    if scope["vai_tro"] != ROLE_ADMIN_HE_THONG and vai_tro_moi == ROLE_ADMIN_HE_THONG:
        return jsonify({"success": False, "message": "Không có quyền gán vai trò Quản trị hệ thống."}), 403

    ok, msg = cap_nhat_tai_khoan_va_quyen(
        tai_khoan_id=tai_khoan_id,
        vai_tro=vai_tro_moi,
        trang_thai=data.get("trang_thai"),
        cong_ty_id=data.get("cong_ty_id"),
        chi_nhanh_id=data.get("chi_nhanh_id"),
        doi_xe_id=data.get("doi_xe_id"),
        ly_do=data.get("ly_do"),
        actor_id=g.current_user["id"],
        actor_role=g.current_user["vai_tro"],
    )
    if ok:
        # Thu hoi cache ngay lap tuc khi khoa hoac doi quyen tai khoan (AUTH-01)
        invalidate_account_cache(tai_khoan_id)
    return jsonify({"success": ok, "message": msg}), 200 if ok else 400


# ============================================================
# NHAT KY KIEM TOAN (AUDIT LOG)
# ============================================================

@org_bp.route("/api/admin/audit-logs", methods=["GET"])
@require_role(*AUDIT_VIEW_ROLES)
def api_list_audit_logs():
    limit = min(int(request.args.get("limit", 100) or 100), 500)
    bang = request.args.get("bang_du_lieu")
    data = lay_lich_su_thao_tac(scope=get_current_scope(), limit=limit, bang_du_lieu=bang)
    return jsonify({"success": True, "data": data})
