from unittest.mock import patch

from flask_jwt_extended import create_access_token
import numpy as np

from core.ops_rules import (
    ROLE_DIEU_PHOI_VIEN,
    ROLE_GIAM_SAT,
    ROLE_QUAN_LY,
    ROLE_TAI_XE,
)
from database.violation_appeal_service import (
    quan_ly_bac_bo_su_kien_ai,
    quan_ly_xac_minh_vi_pham,
    quan_ly_xu_ly_khieu_nai,
    tai_xe_gui_khieu_nai,
)


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


def test_violation_and_appeal_validation_guards():
    # Xac minh vi pham thieu ly do -> 400
    vp_id, code, _ = quan_ly_xac_minh_vi_pham(1, "", actor_id=1, actor_role=ROLE_QUAN_LY)
    assert vp_id is None and code == 400

    # Bac bo su kien AI thieu ly do -> 400
    ok, code, _ = quan_ly_bac_bo_su_kien_ai(1, "", actor_id=1, actor_role=ROLE_QUAN_LY, trang_thai="REJECTED")
    assert ok is False and code == 400

    # Tai xe gui khieu nai thieu giai trinh -> 400
    kn_id, code, _ = tai_xe_gui_khieu_nai(1, 500, "  ", [], actor_id=10)
    assert kn_id is None and code == 400

    # Quan ly chap nhan / bac bo khieu nai thieu ly do ket luan -> 400 (APP-02)
    ok, code, _ = quan_ly_xu_ly_khieu_nai(1, "ACCEPTED", ly_do_ket_luan="", actor_id=1)
    assert ok is False and code == 400
    ok, code, _ = quan_ly_xu_ly_khieu_nai(1, "REJECTED", ly_do_ket_luan="abc", actor_id=1)
    assert ok is False and code == 400


def test_mobile_backup_drowsy_creates_su_kien_canh_bao():
    from backend.routes.ai_monitor_routes import _handle_mobile_drowsy_side_effects

    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    with patch("backend.routes.ai_monitor_routes.save_snapshot", return_value="snapshots/test.jpg"), \
         patch("backend.routes.ai_monitor_routes.upload_snapshot_to_supabase", return_value="https://cdn.example/test.jpg"), \
         patch("backend.routes.ai_monitor_routes.luu_anh_canh_bao"), \
         patch("backend.routes.ai_monitor_routes.tao_su_kien_canh_bao", return_value=99) as mock_event, \
         patch("backend.routes.ai_monitor_routes.broadcast_event") as mock_sse, \
         patch("backend.routes.ai_monitor_routes.send_alert_push_to_managers_async"):
        _handle_mobile_drowsy_side_effects(
            dummy_frame, tai_xe_id=501, xe_id=3, driver_name="Tai xe A", vehicle_name="51A-12345", risk_score=9, reasons=["NHAM MAT LAU"]
        )
        mock_event.assert_called_once()
        kwargs = mock_event.call_args.kwargs
        assert kwargs["nguon"] == "mobile_backup"
        assert kwargs["loai_canh_bao"] == "BUON_NGU"
        assert kwargs["event_id"]
        mock_sse.assert_called_once()
        assert mock_sse.call_args[0][0]["id"] == 99


def test_sprint4_violation_and_appeal_api_rbac():
    from backend.app import app

    client = app.test_client()
    tok_dpv = _make_jwt(app, 41, ROLE_DIEU_PHOI_VIEN)
    tok_gs = _make_jwt(app, 42, ROLE_GIAM_SAT)
    tok_ql = _make_jwt(app, 43, ROLE_QUAN_LY)
    tok_tx = _make_jwt(app, 44, ROLE_TAI_XE, tai_xe_id=501)

    with patch("backend.middleware.auth_guard._is_account_active", return_value=True):
        # 1. Dieu phoi vien & Giam sat bi chan 403 khi xac minh vi pham hoac xu ly khieu nai
        for tok in (tok_dpv, tok_gs):
            assert client.post(
                "/api/admin/ai-events/1/verify-violation",
                json={"ly_do_xac_minh": "Anh ro rang tai xe ngu gat"},
                headers={"Authorization": f"Bearer {tok}"},
            ).status_code == 403
            assert client.post(
                "/api/admin/appeals/1/decide",
                json={"quyet_dinh": "ACCEPTED", "ly_do_ket_luan": "Chap nhan minh chung"},
                headers={"Authorization": f"Bearer {tok}"},
            ).status_code == 403

        # 2. Quan ly xac minh vi pham -> 201; xac minh lai cung su kien -> 409
        with patch(
            "backend.routes.violation_routes.quan_ly_xac_minh_vi_pham",
            return_value=(12, 201, "Đã xác minh sự kiện AI thành vi phạm."),
        ):
            res_ok = client.post(
                "/api/admin/ai-events/1/verify-violation",
                json={"ly_do_xac_minh": "Đối chiếu ảnh mắt nhắm > 2s"},
                headers={"Authorization": f"Bearer {tok_ql}"},
            )
            assert res_ok.status_code == 201
            assert res_ok.get_json()["vi_pham_id"] == 12

        with patch(
            "backend.routes.violation_routes.quan_ly_xac_minh_vi_pham",
            return_value=(None, 409, "Sự kiện AI này đã được xác minh thành vi phạm trước đó."),
        ):
            res_dup = client.post(
                "/api/admin/ai-events/1/verify-violation",
                json={"ly_do_xac_minh": "Bam lai"},
                headers={"Authorization": f"Bearer {tok_ql}"},
            )
            assert res_dup.status_code == 409

        # 3. Tai xe xem vi pham da xac minh, canh bao AI va gui khieu nai
        with patch("backend.routes.violation_routes.lay_danh_sach_vi_pham", return_value=[{"id": 12}]):
            res_vp = client.get("/api/driver/violations", headers={"Authorization": f"Bearer {tok_tx}"})
            assert res_vp.status_code == 200
            assert len(res_vp.get_json()["data"]) == 1

        with patch(
            "backend.routes.violation_routes.tai_xe_gui_khieu_nai",
            return_value=(5, 201, "Đã gửi khiếu nại thành công."),
        ):
            res_kn = client.post(
                "/api/driver/violations/12/appeals",
                json={"noi_dung_giai_trinh": "Lúc đó xe đã tấp vào lề dừng nghỉ an toàn"},
                headers={"Authorization": f"Bearer {tok_tx}"},
            )
            assert res_kn.status_code == 201
            assert res_kn.get_json()["id"] == 5

        # 4. Quan ly chap nhan khieu nai -> 200
        with patch(
            "backend.routes.violation_routes.quan_ly_xu_ly_khieu_nai",
            return_value=(True, 200, "Đã xử lý khiếu nại (ACCEPTED)."),
        ):
            res_dec = client.post(
                "/api/admin/appeals/5/decide",
                json={"quyet_dinh": "ACCEPTED", "ly_do_ket_luan": "Đã kiểm tra ảnh và thời điểm xe đang dừng nghỉ"},
                headers={"Authorization": f"Bearer {tok_ql}"},
            )
            assert res_dec.status_code == 200
