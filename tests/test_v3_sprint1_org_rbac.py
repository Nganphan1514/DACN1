from unittest.mock import patch

from flask_jwt_extended import create_access_token

from core.ops_rules import (
    ROLE_ADMIN_HE_THONG,
    ROLE_DIEU_PHOI_VIEN,
    ROLE_GIAM_SAT,
    ROLE_QUAN_LY,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_TAI_XE,
    co_quyen_trong_pham_vi,
    la_vai_tro_hop_le,
    lay_menu_theo_vai_tro,
)
from database.org_service import build_scope_filter_sql


def test_rbac_6_roles_and_data_scope_isolation():
    for r in (
        ROLE_ADMIN_HE_THONG,
        ROLE_QUAN_TRI_CONG_TY,
        ROLE_QUAN_LY,
        ROLE_DIEU_PHOI_VIEN,
        ROLE_GIAM_SAT,
        ROLE_TAI_XE,
    ):
        assert la_vai_tro_hop_le(r) is True
    assert la_vai_tro_hop_le("hacker_role") is False

    target_cn_a_dx1 = {"cong_ty_id": 1, "chi_nhanh_id": 10, "doi_xe_id": 100, "tai_xe_id": 500}
    target_cn_b_dx2 = {"cong_ty_id": 1, "chi_nhanh_id": 20, "doi_xe_id": 200, "tai_xe_id": 600}
    target_cty2 = {"cong_ty_id": 2, "chi_nhanh_id": 30, "doi_xe_id": 300, "tai_xe_id": 700}

    # Admin he thong: toan he thong
    admin = {"vai_tro": ROLE_ADMIN_HE_THONG}
    assert co_quyen_trong_pham_vi(admin, target_cn_a_dx1) is True
    assert co_quyen_trong_pham_vi(admin, target_cty2) is True

    # Quan tri cong ty 1: duoc xem moi chi nhanh cua cong ty 1, chan cong ty 2
    qt_cty1 = {"vai_tro": ROLE_QUAN_TRI_CONG_TY, "cong_ty_id": 1}
    assert co_quyen_trong_pham_vi(qt_cty1, target_cn_a_dx1) is True
    assert co_quyen_trong_pham_vi(qt_cty1, target_cn_b_dx2) is True
    assert co_quyen_trong_pham_vi(qt_cty1, target_cty2) is False

    # Quan ly Chi nhanh A: duoc xem Chi nhanh A, bi chan Chi nhanh B
    ql_cn_a = {"vai_tro": ROLE_QUAN_LY, "cong_ty_id": 1, "chi_nhanh_id": 10, "doi_xe_id": None}
    assert co_quyen_trong_pham_vi(ql_cn_a, target_cn_a_dx1) is True
    assert co_quyen_trong_pham_vi(ql_cn_a, target_cn_b_dx2) is False

    # Dieu phoi vien Doi xe 100: chi duoc xem Doi xe 100
    dpv_dx1 = {"vai_tro": ROLE_DIEU_PHOI_VIEN, "cong_ty_id": 1, "chi_nhanh_id": 10, "doi_xe_id": 100}
    assert co_quyen_trong_pham_vi(dpv_dx1, target_cn_a_dx1) is True
    assert co_quyen_trong_pham_vi(dpv_dx1, target_cn_b_dx2) is False

    # Tai xe 500: chi xem du lieu cua chinh minh
    tx500 = {"vai_tro": ROLE_TAI_XE, "tai_xe_id": 500}
    assert co_quyen_trong_pham_vi(tx500, target_cn_a_dx1) is True
    assert co_quyen_trong_pham_vi(tx500, target_cn_b_dx2) is False


def test_build_scope_filter_sql():
    sql_sys, params_sys = build_scope_filter_sql({"vai_tro": ROLE_ADMIN_HE_THONG})
    assert sql_sys == "1=1" and params_sys == []

    sql_dx, params_dx = build_scope_filter_sql(
        {"vai_tro": ROLE_DIEU_PHOI_VIEN, "cong_ty_id": 1, "chi_nhanh_id": 10, "doi_xe_id": 100},
        doi_xe_col="lc.doi_xe_id",
    )
    assert sql_dx == "lc.doi_xe_id = %s"
    assert params_dx == [100]

    sql_cn, params_cn = build_scope_filter_sql(
        {"vai_tro": ROLE_QUAN_LY, "cong_ty_id": 1, "chi_nhanh_id": 10, "doi_xe_id": None},
        doi_xe_col="lc.doi_xe_id",
    )
    assert "chi_nhanh_id = %s" in sql_cn
    assert params_cn == [10]


def _make_jwt(app, user_id, vai_tro, cong_ty_id=1, chi_nhanh_id=10, doi_xe_id=100, tai_xe_id=None):
    with app.app_context():
        return create_access_token(
            identity=str(user_id),
            additional_claims={
                "ten_dang_nhap": f"user_{user_id}",
                "vai_tro": vai_tro,
                "tai_xe_id": tai_xe_id,
                "cong_ty_id": cong_ty_id,
                "chi_nhanh_id": chi_nhanh_id,
                "doi_xe_id": doi_xe_id,
            },
        )


def test_api_rbac_separation_dispatcher_monitor_company_admin_driver():
    from backend.app import app

    client = app.test_client()
    tok_dpv = _make_jwt(app, 11, ROLE_DIEU_PHOI_VIEN)
    tok_gs = _make_jwt(app, 12, ROLE_GIAM_SAT)
    tok_qtcty = _make_jwt(app, 13, ROLE_QUAN_TRI_CONG_TY, chi_nhanh_id=None, doi_xe_id=None)
    tok_tx = _make_jwt(app, 14, ROLE_TAI_XE, tai_xe_id=500)

    with patch("backend.middleware.auth_guard._is_account_active", return_value=True):
        # 1. Dieu phoi vien: xem duoc lich, bi chan 403 khi xac minh canh bao / huy lich / tao chi nhanh
        with patch("backend.routes.scheduler_routes.lay_tat_ca_lich_chay", return_value=[]):
            assert client.get("/api/admin/schedules", headers={"Authorization": f"Bearer {tok_dpv}"}).status_code == 200
        assert client.put(
            "/api/admin/alerts/1",
            json={"trang_thai": "DA_DONG"},
            headers={"Authorization": f"Bearer {tok_dpv}"},
        ).status_code == 403
        assert client.delete(
            "/api/admin/schedules/1",
            headers={"Authorization": f"Bearer {tok_dpv}"},
        ).status_code == 403
        assert client.post(
            "/api/admin/branches",
            json={"ma_chi_nhanh": "CN2", "ten": "Chi nhanh 2"},
            headers={"Authorization": f"Bearer {tok_dpv}"},
        ).status_code == 403

        # 2. Giam sat: xem duoc thiet bi camera, bi chan 403 khi tao lich hoac xac minh canh bao
        with patch("backend.routes.admin_routes.lay_danh_sach_thiet_bi_camera", return_value=[]):
            assert client.get("/api/admin/devices", headers={"Authorization": f"Bearer {tok_gs}"}).status_code == 200
        assert client.post(
            "/api/admin/schedules",
            json={"tai_xe_id": 1, "xe_id": 1, "tuyen_duong": "A-B", "gio_bat_dau": "2026-11-24 08:00:00"},
            headers={"Authorization": f"Bearer {tok_gs}"},
        ).status_code == 403
        assert client.put(
            "/api/admin/alerts/1",
            json={"trang_thai": "DA_DONG"},
            headers={"Authorization": f"Bearer {tok_gs}"},
        ).status_code == 403

        # 3. Quan tri cong ty: khong duoc tao tai khoan admin_he_thong (403)
        assert client.post(
            "/api/admin/accounts",
            json={"ten_dang_nhap": "super", "mat_khau": "123456", "vai_tro": ROLE_ADMIN_HE_THONG},
            headers={"Authorization": f"Bearer {tok_qtcty}"},
        ).status_code == 403

        # 4. Tai xe: bi chan 403 tai API quan tri, nhung goi duoc /api/auth/me
        assert client.get("/api/admin/drivers", headers={"Authorization": f"Bearer {tok_tx}"}).status_code == 403
        with patch("backend.routes.auth_routes.lay_pham_vi_tai_khoan", return_value=None):
            res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_tx}"})
            assert res_me.status_code == 200
            assert res_me.get_json()["user"]["vai_tro"] == ROLE_TAI_XE

    # Menu theo vai tro
    assert "audit" in lay_menu_theo_vai_tro(ROLE_QUAN_LY)
    assert "audit" not in lay_menu_theo_vai_tro(ROLE_DIEU_PHOI_VIEN)
    assert "scheduler" in lay_menu_theo_vai_tro(ROLE_DIEU_PHOI_VIEN)
    assert "scheduler" not in lay_menu_theo_vai_tro(ROLE_GIAM_SAT)
