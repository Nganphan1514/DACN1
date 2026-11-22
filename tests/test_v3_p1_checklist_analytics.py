from unittest.mock import patch

from flask_jwt_extended import create_access_token

from core.ops_rules import ROLE_QUAN_LY, ROLE_TAI_XE
from database.p1_service import DEFAULT_CHECKLIST_ITEMS, danh_gia_checklist


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


def test_p1_checklist_evaluation_rules():
    # Tat ca DAT -> DAT
    all_ok = [{"ma_hang_muc": x["ma_hang_muc"], "ket_qua": "DAT"} for x in DEFAULT_CHECKLIST_ITEMS]
    parsed, failed = danh_gia_checklist(all_ok)
    assert parsed is not None
    assert parsed[0] == "DAT"
    assert failed == []

    # 1 hang muc bat buoc KHONG_DAT -> KHONG_DAT
    one_fail = list(all_ok)
    one_fail[1] = {"ma_hang_muc": "PHANH", "ket_qua": "KHONG_DAT", "ghi_chu": "Phanh ăn kém"}
    parsed2, failed2 = danh_gia_checklist(one_fail)
    assert parsed2 is not None
    assert parsed2[0] == "KHONG_DAT"
    assert len(failed2) == 1 and "phanh" in failed2[0].lower()

    # Hang muc tuy chon (bat_buoc=False) KHONG_DAT -> van DAT
    opt_fail = list(all_ok) + [{"ma_hang_muc": "VE_SINH", "ten_hang_muc": "Vệ sinh cabin", "bat_buoc": False, "ket_qua": "KHONG_DAT"}]
    parsed3, failed3 = danh_gia_checklist(opt_fail)
    assert parsed3 is not None and parsed3[0] == "DAT" and failed3 == []

    # Danh sach rong -> loi
    parsed_empty, _ = danh_gia_checklist([])
    assert parsed_empty is None


def test_p1_checklist_and_analytics_api():
    from backend.app import app

    client = app.test_client()
    tok_ql = _make_jwt(app, 51, ROLE_QUAN_LY)
    tok_tx = _make_jwt(app, 52, ROLE_TAI_XE, tai_xe_id=501)

    with patch("backend.middleware.auth_guard._is_account_active", return_value=True):
        # 1. Lay danh muc checklist chuan
        res_tpl = client.get("/api/driver/checklist/template", headers={"Authorization": f"Bearer {tok_tx}"})
        assert res_tpl.status_code == 200
        assert len(res_tpl.get_json()["data"]) == len(DEFAULT_CHECKLIST_ITEMS)

        # 2. Quan ly khong duoc nop checklist thay tai xe (403)
        assert client.post(
            "/api/driver/schedules/10/checklist",
            json={"items": []},
            headers={"Authorization": f"Bearer {tok_ql}"},
        ).status_code == 403

        # 3. Tai xe nop checklist KHONG_DAT -> 201 kem bao_cao_su_co_id
        with patch(
            "backend.routes.p1_routes.tai_xe_gui_checklist_truoc_chuyen",
            return_value=({"id": 3, "ket_qua_tong": "KHONG_DAT", "bao_cao_su_co_id": 88}, 201, "Checklist KHÔNG ĐẠT"),
        ):
            res_sub = client.post(
                "/api/driver/schedules/10/checklist",
                json={"items": [{"ma_hang_muc": "PHANH", "ket_qua": "KHONG_DAT"}]},
                headers={"Authorization": f"Bearer {tok_tx}"},
            )
            assert res_sub.status_code == 201
            assert res_sub.get_json()["data"]["bao_cao_su_co_id"] == 88

        # 4. Priority alerts & Analytics V3 (chan tai_xe 403, cho quan_ly 200)
        assert client.get("/api/admin/priority-alerts", headers={"Authorization": f"Bearer {tok_tx}"}).status_code == 403
        with patch(
            "backend.routes.p1_routes.lay_thong_ke_da_cap_v3",
            return_value={"tong_vi_pham": 5, "ty_le_khieu_nai_chap_nhan_pct": 20.0, "tong_giay_camera_offline": 120},
        ):
            res_an = client.get("/api/admin/analytics/v3", headers={"Authorization": f"Bearer {tok_ql}"})
            assert res_an.status_code == 200
            assert res_an.get_json()["data"]["ty_le_khieu_nai_chap_nhan_pct"] == 20.0
