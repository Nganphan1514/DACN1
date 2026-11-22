from unittest.mock import patch

from flask_jwt_extended import create_access_token

from core.ops_rules import ROLE_DIEU_PHOI_VIEN, ROLE_QUAN_LY, ROLE_TAI_XE
from database.trip_camera_service import (
    quan_ly_ket_thuc_chuyen_ngoai_le,
    tai_xe_bat_dau_chuyen,
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


def test_trip_validation_guards():
    # Thieu ma lich -> 400
    cid, code, _ = tai_xe_bat_dau_chuyen(None, 10, 100)
    assert cid is None and code == 400

    # Ket thuc ngoai le thieu ly do hoac qua ngan -> 400 (TRIP-03)
    ok, code, _ = quan_ly_ket_thuc_chuyen_ngoai_le(1, "", actor_id=1, actor_role=ROLE_QUAN_LY)
    assert ok is False and code == 400
    ok, code, _ = quan_ly_ket_thuc_chuyen_ngoai_le(1, "abc", actor_id=1, actor_role=ROLE_QUAN_LY)
    assert ok is False and code == 400


def test_camera_offline_dispatches_two_way_alerts_without_ending_trip():
    from backend.routes.realtime_routes import dispatch_camera_offline_alerts

    fake_offline = [
        {
            "device_id": "cam-xe-1",
            "xe_id": 1,
            "bien_so": "51A-99999",
            "chuyen_thuc_te_id": 77,
            "tai_xe_id": 500,
            "ten_tai_xe": "Nguyen Van A",
            "tai_khoan_tai_xe_id": 88,
        }
    ]

    with patch("backend.routes.realtime_routes.broadcast_event") as mock_sse, \
         patch("backend.routes.realtime_routes.send_alert_push_to_managers_async") as mock_mgr_push, \
         patch("backend.routes.realtime_routes.them_ghi_chu") as mock_note, \
         patch("backend.routes.realtime_routes.send_push_to_account_async") as mock_driver_push:
        dispatch_camera_offline_alerts(fake_offline)

        # Phia Quan ly & Giam sat
        mock_sse.assert_called_once()
        assert mock_sse.call_args[0][0]["type"] == "CAMERA_OFFLINE"
        assert mock_sse.call_args[0][0]["chuyen_thuc_te_id"] == 77
        mock_mgr_push.assert_called_once()

        # Phia Tai xe
        mock_note.assert_called_once()
        assert mock_note.call_args.kwargs["tai_xe_id"] == 500
        mock_driver_push.assert_called_once()
        assert mock_driver_push.call_args.kwargs["tai_khoan_id"] == 88


def test_sprint3_trip_and_camera_api_rbac():
    from backend.app import app

    client = app.test_client()
    tok_dpv = _make_jwt(app, 31, ROLE_DIEU_PHOI_VIEN)
    tok_ql = _make_jwt(app, 32, ROLE_QUAN_LY)
    tok_tx = _make_jwt(app, 33, ROLE_TAI_XE, tai_xe_id=501)

    with patch("backend.middleware.auth_guard._is_account_active", return_value=True):
        # 1. Dieu phoi vien khong duoc ket thuc chuyen ngoai le (403)
        res_dpv = client.post(
            "/api/admin/trips/10/force-complete",
            json={"ly_do_ngoai_le": "Xe gap su co"},
            headers={"Authorization": f"Bearer {tok_dpv}"},
        )
        assert res_dpv.status_code == 403

        # 2. Quan ly ket thuc ngoai le thieu ly do -> 400
        res_ql_no_reason = client.post(
            "/api/admin/trips/10/force-complete",
            json={"ly_do_ngoai_le": ""},
            headers={"Authorization": f"Bearer {tok_ql}"},
        )
        assert res_ql_no_reason.status_code == 400

        # 3. Quan ly ket thuc ngoai le co ly do -> 200
        with patch(
            "backend.routes.trip_routes.quan_ly_ket_thuc_chuyen_ngoai_le",
            return_value=(True, 200, "Đã kết thúc chuyến đi ngoại lệ."),
        ):
            res_ql_ok = client.post(
                "/api/admin/trips/10/force-complete",
                json={"ly_do_ngoai_le": "Điện thoại tài xế hỏng sau khi hoàn thành giao hàng"},
                headers={"Authorization": f"Bearer {tok_ql}"},
            )
            assert res_ql_ok.status_code == 200

        # 4. Quan ly khong duoc bat dau chuyen thay tai xe (403)
        assert client.post(
            "/api/driver/trips/start",
            json={"lich_chay_id": 5},
            headers={"Authorization": f"Bearer {tok_ql}"},
        ).status_code == 403

        # 5. Tai xe bat dau chuyen khi lich chua xac nhan -> 409
        with patch(
            "backend.routes.trip_routes.tai_xe_bat_dau_chuyen",
            return_value=(None, 409, "Tài xế bắt buộc xác nhận lịch (DA_XAC_NHAN)."),
        ):
            res_unconfirmed = client.post(
                "/api/driver/trips/start",
                json={"lich_chay_id": 5},
                headers={"Authorization": f"Bearer {tok_tx}"},
            )
            assert res_unconfirmed.status_code == 409

        # 6. Tai xe xem trang thai camera xe minh -> 200
        with patch(
            "backend.routes.trip_routes.lay_trang_thai_camera_cho_tai_xe",
            return_value={"device_id": "cam-xe-1", "health_status": "ONLINE_HEALTHY", "online": True},
        ):
            res_cam = client.get(
                "/api/driver/camera-status",
                headers={"Authorization": f"Bearer {tok_tx}"},
            )
            assert res_cam.status_code == 200
            assert res_cam.get_json()["data"]["online"] is True
