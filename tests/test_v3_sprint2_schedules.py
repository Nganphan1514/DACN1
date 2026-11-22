from datetime import datetime
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from core.ops_rules import (
    ROLE_DIEU_PHOI_VIEN,
    ROLE_QUAN_LY,
    ROLE_TAI_XE,
    can_xac_nhan_lai_lich,
    kiem_tra_khoang_thoi_gian_giao_nhau,
)
from database.schedule_service import (
    huy_lich_chay_v3,
    quan_ly_xu_ly_yeu_cau_doi_lich,
    tai_xe_gui_yeu_cau_doi_lich,
    tai_xe_tu_choi_lich,
    tao_lich_chay_v3,
)


def test_sch02_half_open_interval_overlap_rules():
    t08 = datetime(2026, 11, 24, 8, 0)
    t10 = datetime(2026, 11, 24, 10, 0)
    t12 = datetime(2026, 11, 24, 12, 0)
    t0930 = datetime(2026, 11, 24, 9, 30)
    t11 = datetime(2026, 11, 24, 11, 0)

    # Hai lich noi tiep [08:00, 10:00) va [10:00, 12:00) -> khong trung
    assert kiem_tra_khoang_thoi_gian_giao_nhau(t08, t10, t10, t12) is False
    assert kiem_tra_khoang_thoi_gian_giao_nhau(t10, t12, t08, t10) is False

    # Hai lich giao nhau [08:00, 10:00) va [09:30, 11:00) -> trung
    assert kiem_tra_khoang_thoi_gian_giao_nhau(t08, t10, t0930, t11) is True


def test_sch04_reconfirm_required_when_modifying_confirmed_schedule():
    lich_da_xac_nhan = {
        "id": 1,
        "tai_xe_id": 10,
        "xe_id": 20,
        "gio_bat_dau": "2026-11-24 08:00:00",
        "gio_ket_thuc": "2026-11-24 12:00:00",
        "trang_thai": "DA_XAC_NHAN",
    }

    # Doi tai xe / doi xe / doi gio -> bat buoc xac nhan lai
    assert can_xac_nhan_lai_lich(lich_da_xac_nhan, 11, 20, "2026-11-24 08:00:00", "2026-11-24 12:00:00") is True
    assert can_xac_nhan_lai_lich(lich_da_xac_nhan, 10, 21, "2026-11-24 08:00:00", "2026-11-24 12:00:00") is True
    assert can_xac_nhan_lai_lich(lich_da_xac_nhan, 10, 20, "2026-11-24 09:00:00", "2026-11-24 12:00:00") is True

    # Khong doi tai xe/xe/gio -> khong can xac nhan lai
    assert can_xac_nhan_lai_lich(lich_da_xac_nhan, 10, 20, "2026-11-24 08:00:00", "2026-11-24 12:00:00") is False

    # Lich chua xac nhan -> khong ap dung co che reset
    lich_cho = dict(lich_da_xac_nhan, trang_thai="CHO_XAC_NHAN")
    assert can_xac_nhan_lai_lich(lich_cho, 11, 20, "2026-11-24 08:00:00", "2026-11-24 12:00:00") is False


def test_sch01_and_validation_guards_without_db():
    # gio_ket_thuc <= gio_bat_dau -> bi chan 400
    lich_id, code, _ = tao_lich_chay_v3(
        tai_xe_id=1,
        xe_id=1,
        tuyen_duong="HCM - Dong Nai",
        gio_bat_dau="2026-11-24 10:00:00",
        gio_ket_thuc="2026-11-24 09:00:00",
    )
    assert lich_id is None and code == 400

    # Tu choi lich thieu ly do -> 400
    ok, code, _ = tai_xe_tu_choi_lich(lich_id=1, tai_xe_id=10, ly_do="   ", actor_id=100)
    assert ok is False and code == 400

    # Huy lich thieu ly do -> 400
    ok, code, _ = huy_lich_chay_v3(lich_id=1, ly_do_huy="", actor_id=1, actor_role=ROLE_QUAN_LY)
    assert ok is False and code == 400

    # Gui yeu cau doi lich thieu ly do hoac sai loai -> 400
    yc_id, code, _ = tai_xe_gui_yeu_cau_doi_lich(1, 10, "INVALID_TYPE", {}, "ly do", 100)
    assert yc_id is None and code == 400
    yc_id, code, _ = tai_xe_gui_yeu_cau_doi_lich(1, 10, "DOI_XE", {"xe_id": 2}, "", 100)
    assert yc_id is None and code == 400

    # Quan ly tu choi yeu cau doi lich thieu ly do -> 400
    ok, code, _ = quan_ly_xu_ly_yeu_cau_doi_lich(1, "TU_CHOI", ly_do_tu_choi="", actor_id=1)
    assert ok is False and code == 400


def _make_jwt(app, user_id, vai_tro, tai_xe_id=None):
    with app.app_context():
        return create_access_token(
            identity=str(user_id),
            additional_claims={
                "ten_dang_nhap": f"u_{user_id}",
                "vai_tro": vai_tro,
                "tai_xe_id": tai_xe_id,
                "cong_ty_id": 1,
                "chi_nhanh_id": 10,
                "doi_xe_id": 100,
            },
        )


def test_sprint2_api_endpoints_and_role_guards():
    from backend.app import app

    client = app.test_client()
    tok_dpv = _make_jwt(app, 21, ROLE_DIEU_PHOI_VIEN)
    tok_ql = _make_jwt(app, 22, ROLE_QUAN_LY)
    tok_tx = _make_jwt(app, 23, ROLE_TAI_XE, tai_xe_id=501)

    with patch("backend.middleware.auth_guard._is_account_active", return_value=True):
        # 1. Trung lich tra ve 409 Conflict qua /api/dispatch/schedules
        with patch(
            "backend.routes.scheduler_routes.tao_lich_chay_v3",
            return_value=(None, 409, "Trùng khung giờ với lịch chạy #5."),
        ):
            res = client.post(
                "/api/dispatch/schedules",
                json={"tai_xe_id": 1, "xe_id": 1, "tuyen_duong": "A-B", "gio_bat_dau": "2026-11-24 08:00:00"},
                headers={"Authorization": f"Bearer {tok_dpv}"},
            )
            assert res.status_code == 409

        # 2. Tai xe xac nhan lich thanh cong
        with patch(
            "backend.routes.scheduler_routes.tai_xe_xac_nhan_lich",
            return_value=(True, 200, "Đã xác nhận lịch chạy thành công."),
        ):
            res = client.post(
                "/api/driver/schedules/10/confirm",
                headers={"Authorization": f"Bearer {tok_tx}"},
            )
            assert res.status_code == 200

        # 3. Quan ly khong duoc goi API xac nhan lich thay tai xe (403)
        res_ql_confirm = client.post(
            "/api/driver/schedules/10/confirm",
            headers={"Authorization": f"Bearer {tok_ql}"},
        )
        assert res_ql_confirm.status_code == 403

        # 4. Dieu phoi vien bi chan 403 khi duyet yeu cau doi lich; Quan ly duoc phep (200)
        res_dpv_approve = client.post(
            "/api/admin/change-requests/7/approve",
            headers={"Authorization": f"Bearer {tok_dpv}"},
        )
        assert res_dpv_approve.status_code == 403

        with patch(
            "backend.routes.scheduler_routes.quan_ly_xu_ly_yeu_cau_doi_lich",
            return_value=(True, 200, "Đã xử lý yêu cầu (DA_DUYET)."),
        ):
            res_ql_approve = client.post(
                "/api/admin/change-requests/7/approve",
                headers={"Authorization": f"Bearer {tok_ql}"},
            )
            assert res_ql_approve.status_code == 200
