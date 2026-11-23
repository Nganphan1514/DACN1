from datetime import datetime, timedelta
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from core.ops_rules import (
    ROLE_DIEU_PHOI_VIEN,
    ROLE_GIAM_SAT,
    ROLE_QUAN_LY,
    ROLE_TAI_XE,
    lay_quyen_theo_vai_tro,
    normalize_schedule_status,
    phan_loai_suc_khoe_thiet_bi,
)
from core.reauth_guard import ReauthGuard
from database.violation_appeal_service import danh_gia_quyen_khieu_nai


def _make_jwt(app, user_id, vai_tro, tv=1, tai_xe_id=None):
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
                "tv": tv,
            },
        )


def test_permissions_matrix_returned_on_login_and_me():
    """FIX-01: dieu_phoi_vien & giam_sat khong co quyen drivers:register_face hay reports:resolve."""
    dpv_perms = lay_quyen_theo_vai_tro(ROLE_DIEU_PHOI_VIEN)
    gs_perms = lay_quyen_theo_vai_tro(ROLE_GIAM_SAT)
    ql_perms = lay_quyen_theo_vai_tro(ROLE_QUAN_LY)

    assert "drivers:register_face" not in dpv_perms
    assert "reports:resolve" not in dpv_perms
    assert "drivers:register_face" not in gs_perms
    assert "reports:resolve" not in gs_perms
    assert "drivers:register_face" in ql_perms
    assert "reports:resolve" in ql_perms

    from backend.app import app

    client = app.test_client()
    tok_dpv = _make_jwt(app, 61, ROLE_DIEU_PHOI_VIEN)
    with patch("backend.middleware.auth_guard._is_account_active", return_value=True), \
         patch("backend.middleware.auth_guard._is_token_version_valid", return_value=True), \
         patch("backend.routes.auth_routes.lay_pham_vi_tai_khoan", return_value=None):
        res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_dpv}"})
        assert res_me.status_code == 200
        body = res_me.get_json()["user"]
        assert "permissions" in body
        assert "drivers:register_face" not in body["permissions"]

        # Chan 403 tai endpoint register-face va resolve report
        assert client.post(
            "/api/admin/drivers/register-face",
            json={"tai_xe_id": 1, "images": []},
            headers={"Authorization": f"Bearer {tok_dpv}"},
        ).status_code == 403
        assert client.put(
            "/api/admin/reports/1",
            json={"trang_thai": "DA_XU_LY"},
            headers={"Authorization": f"Bearer {tok_dpv}"},
        ).status_code == 403


def test_token_version_revokes_jwt_immediately():
    """FIX-10: Tang token_version khien JWT cu lap tuc nhan 401 khong le thuoc cache TTL."""
    from backend.app import app

    client = app.test_client()
    tok_old = _make_jwt(app, 62, ROLE_QUAN_LY, tv=1)

    with patch("backend.middleware.auth_guard._is_account_active", return_value=True), \
         patch("database.mysql_service.db.fetch_one", return_value={"trang_thai": "hoat_dong", "token_version": 2}):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_old}"})
        assert res.status_code == 401


def test_appeal_limit_and_deadline_enforced():
    """FIX-04: Chan khieu nai lan 2 (409) va chan qua han 72h (400)."""
    now = datetime(2026, 11, 23, 12, 0, 0)
    vp_recent = {"id": 1, "trang_thai": "GIU_NGUYEN", "xac_minh_at": now - timedelta(hours=10)}
    vp_expired = {"id": 2, "trang_thai": "HIEU_LUC", "xac_minh_at": now - timedelta(hours=80)}

    # Lan 1 trong han -> cho phep
    can1, reason1, code1 = danh_gia_quyen_khieu_nai(vp_recent, so_khieu_nai_da_gui=0, max_appeals=1, deadline_hours=72, now=now)
    assert can1 is True and reason1 is None and code1 == 200

    # Lan 2 khi max_appeals=1 -> 409
    can2, reason2, code2 = danh_gia_quyen_khieu_nai(vp_recent, so_khieu_nai_da_gui=1, max_appeals=1, deadline_hours=72, now=now)
    assert can2 is False and code2 == 409 and "giới hạn" in reason2

    # Qua han 72h -> 400
    can3, reason3, code3 = danh_gia_quyen_khieu_nai(vp_expired, so_khieu_nai_da_gui=0, max_appeals=1, deadline_hours=72, now=now)
    assert can3 is False and code3 == 400 and "thời hạn" in reason3


def test_retroactive_link_session_to_trip_on_late_start():
    """FIX-05: Khi tai xe bam Bat dau chuyen muon, phien_lai_xe & lich_su_ket_noi_camera duoc noi vao chuyen moi."""
    from contextlib import contextmanager
    from database.trip_camera_service import tai_xe_bat_dau_chuyen

    executed_sqls = []

    class FakeCursor:
        def __init__(self):
            self._queue = [
                {"id": 10, "tai_xe_id": 501, "xe_id": 3, "doi_xe_id": 1, "trang_thai": "DA_XAC_NHAN"},  # lich_chay
                None,  # checklist
                {"id": 3, "bien_so": "51A-11111", "trang_thai": "hoat_dong"},  # xe
                None,  # dang_chay
                None,  # existing 1-1
                {"id": 99},  # INSERT chuyen_thuc_te RETURNING id
            ]

        def execute(self, sql, params=None):
            executed_sqls.append(sql)

        def fetchone(self):
            return self._queue.pop(0) if self._queue else None

    @contextmanager
    def _fake_tx():
        yield FakeCursor()

    with patch("database.trip_camera_service.db.transaction", _fake_tx), \
         patch("database.trip_camera_service._lock_driver_and_vehicle"), \
         patch("database.trip_camera_service.ghi_lich_su_thao_tac"):
        cid, code, _ = tai_xe_bat_dau_chuyen(10, 501, actor_id=20)
        assert cid == 99 and code == 201
        assert any("UPDATE phien_lai_xe" in s and "chuyen_thuc_te_id" in s for s in executed_sqls)
        assert any("UPDATE lich_su_ket_noi_camera" in s and "chuyen_thuc_te_id" in s for s in executed_sqls)


def test_camera_paused_during_active_trip_triggers_alert():
    """FIX-02: Heartbeat PAUSED > 120s trong khi co chuyen DANG_CHAY sinh canh bao CAMERA_TAMPER_OR_PAUSED."""
    from backend.app import app
    from config.app_config import INTERNAL_API_KEY

    client = app.test_client()
    fake_tamper = {
        "type": "CAMERA_TAMPER_OR_PAUSED",
        "device_id": "cam-xe-1",
        "xe_id": 1,
        "tai_xe_id": 501,
        "chuyen_thuc_te_id": 77,
        "paused_secs": 150,
        "message": "Camera cam-xe-1 bị tạm dừng 150s trong khi chuyến #77 đang chạy!",
    }

    with patch("backend.routes.realtime_routes.cap_nhat_heartbeat_thiet_bi", return_value=True), \
         patch("backend.routes.realtime_routes.ghi_nhan_camera_heartbeat_va_lich_su", return_value=fake_tamper), \
         patch("backend.routes.realtime_routes.tao_su_kien_canh_bao") as mock_evt, \
         patch("backend.routes.realtime_routes.broadcast_event") as mock_sse, \
         patch("backend.routes.realtime_routes.send_alert_push_to_managers_async") as mock_push:
        res = client.post(
            "/api/internal/device-heartbeat",
            json={"device_id": "cam-xe-1", "xe_id": 1, "status": "PAUSED", "fps": 0},
            headers={"X-Internal-Key": INTERNAL_API_KEY},
        )
        assert res.status_code == 200
        mock_evt.assert_called_once()
        assert mock_evt.call_args.kwargs["loai_canh_bao"] == "CAMERA_TAMPER_OR_PAUSED"
        mock_sse.assert_called_once()
        mock_push.assert_called_once()


def test_camera_flapping_marks_device_degraded():
    """FIX-07: Rot/noi lai >= 3 lan trong 10 phut hoac PAUSED > 300s -> ONLINE_DEGRADED."""
    assert phan_loai_suc_khoe_thiet_bi(10, camera_ok=True, fps=20.0, flapping_count_10m=0) == "ONLINE_HEALTHY"
    assert phan_loai_suc_khoe_thiet_bi(10, camera_ok=True, fps=20.0, flapping_count_10m=3) == "ONLINE_DEGRADED"
    assert phan_loai_suc_khoe_thiet_bi(10, camera_ok=True, fps=20.0, paused_seconds=305) == "ONLINE_DEGRADED"


def test_reauthentication_detects_driver_swap_mid_trip():
    """FIX-06: Sau 60s mat mat, 3 frame lien tiep khong khop khuon mat -> DRIVER_CHANGED_MID_TRIP."""
    guard = ReauthGuard(missing_trigger_sec=60.0, reauth_interval_sec=900.0, consecutive_mismatch_limit=3)
    guard.reset(now=100.0)

    # Mat mat 65 giay
    guard.on_face_missing(now=110.0)
    guard.on_face_missing(now=175.0)

    # Goc mat lech (|yaw| >= 20) -> khong trich xuat de chong bao sai
    assert guard.should_check_face(now=176.0, yaw=25.0, pitch=0.0) is False
    # Mat nhin thang -> kich hoat kiem tra
    assert guard.should_check_face(now=177.0, yaw=5.0, pitch=2.0) is True

    # 3 lan lien tiep khop nguoi khac (driver 999 thay vi 501)
    assert guard.record_verification_result(501, 999, now=177.0) is None
    assert guard.record_verification_result(501, 999, now=178.0) is None
    assert guard.record_verification_result(501, 999, now=179.0) == "DRIVER_CHANGED_MID_TRIP"


def test_schedule_status_enum_normalization():
    """FIX-09: Chuan hoa trang thai legacy chu thuong -> 6 gia tri chuan V3 CHU HOA."""
    assert normalize_schedule_status("sap_chay") == "CHO_XAC_NHAN"
    assert normalize_schedule_status("dang_chay") == "DANG_THUC_HIEN"
    assert normalize_schedule_status("hoan_thanh") == "HOAN_THANH"
    assert normalize_schedule_status("da_huy") == "DA_HUY"
    assert normalize_schedule_status("huy") == "DA_HUY"
    assert normalize_schedule_status("DA_XAC_NHAN") == "DA_XAC_NHAN"
