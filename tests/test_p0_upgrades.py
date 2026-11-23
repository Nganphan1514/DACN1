import sys
import types
from unittest.mock import MagicMock, patch

from core.ops_rules import (
    kiem_tra_chuyen_trang_thai_canh_bao,
    mask_sensitive_id,
    phan_loai_suc_khoe_thiet_bi,
)
from services.offline_outbox import OfflineOutbox
from services import realtime_client, storage_service


def test_offline_outbox_persists_retries_deduplicates_and_dead_letters(tmp_path):
    db_file = tmp_path / "outbox.db"
    outbox = OfflineOutbox(db_path=str(db_file))

    assert outbox.count_pending() == 0
    assert outbox.count_dead_letter() == 0

    # Enqueue 3 events, plus 1 duplicate event_id
    eid1 = outbox.enqueue("alert_event", {"event_type": "BUON_NGU", "risk_score": 8}, event_id="evt-001")
    eid1_dup = outbox.enqueue("alert_event", {"event_type": "BUON_NGU", "risk_score": 8}, event_id="evt-001")
    eid2 = outbox.enqueue("detection_log", {"tai_xe_id": 1, "status": "BUON NGU"}, event_id="evt-002")
    eid3 = outbox.enqueue("bad_event", {"invalid": True}, event_id="evt-003")

    assert eid1 == "evt-001"
    assert eid1_dup == "evt-001"
    assert eid2 == "evt-002"
    assert eid3 == "evt-003"
    assert outbox.count_pending() == 3

    # Simulate process restart: open a brand new OfflineOutbox on the same SQLite file
    reopened = OfflineOutbox(db_path=str(db_file))
    assert reopened.count_pending() == 3

    # First flush: bad_event -> DEAD_LETTER, others RETRY
    sent_first = reopened.flush(
        {
            "alert_event": lambda payload: "RETRY",
            "detection_log": lambda payload: False,
            "bad_event": lambda payload: "DEAD_LETTER",
        }
    )
    assert sent_first == 0
    assert reopened.count_pending() == 2
    assert reopened.count_dead_letter() == 1

    # Second flush succeeds for alert_event only -> detection_log remains
    dispatched = []

    def _ok_alert(payload):
        dispatched.append(payload.get("event_id"))
        return "OK"

    sent_partial = reopened.flush(
        {
            "alert_event": _ok_alert,
            "detection_log": lambda payload: False,
        }
    )
    assert sent_partial == 1
    assert dispatched == ["evt-001"]
    assert reopened.count_pending() == 1

    # Third flush succeeds for detection_log -> pending queue empty, 1 dead-letter remains
    sent_all = reopened.flush({"detection_log": lambda payload: True})
    assert sent_all == 1
    assert reopened.count_pending() == 0
    assert reopened.count_dead_letter() == 1


def test_realtime_client_event_contract_and_status_codes():
    ok_resp = MagicMock(status_code=200)
    bad_resp = MagicMock(status_code=400)
    err_resp = MagicMock(status_code=503)

    with patch("services.realtime_client.requests.post", return_value=ok_resp) as mock_post:
        res = realtime_client.push_realtime_alert_status(
            event_type="BUON_NGU",
            driver_name="Nguyen Van A",
            vehicle_name="51A-12345",
            message="Buon ngu",
            device_id="cam-xe-1",
            event_id="evt-contract-1",
        )
        assert res == "OK"
        sent_payload = mock_post.call_args.kwargs["json"]
        assert sent_payload["event_id"] == "evt-contract-1"
        assert sent_payload["device_id"] == "cam-xe-1"
        assert sent_payload["payload_version"] == "1.0"
        assert "occurred_at" in sent_payload and sent_payload["occurred_at"]

    with patch("services.realtime_client.requests.post", return_value=bad_resp):
        assert realtime_client.push_realtime_alert_status("BUON_NGU", "A", "Xe1", "msg") == "DEAD_LETTER"

    with patch("services.realtime_client.requests.post", return_value=err_resp):
        assert realtime_client.push_realtime_alert_status("BUON_NGU", "A", "Xe1", "msg") == "RETRY"


def test_storage_service_private_bucket_signed_url(monkeypatch):
    monkeypatch.setattr(storage_service, "SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setattr(storage_service, "SUPABASE_SERVICE_KEY", "sb_secret_test")
    monkeypatch.setattr(storage_service, "SUPABASE_SNAPSHOT_BUCKET", "snapshots")
    monkeypatch.setattr(storage_service, "SUPABASE_BUCKET_PRIVATE", True)

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"signedURL": "/object/sign/snapshots/a.jpg?token=abc123"}

    with patch("services.storage_service.requests.post", return_value=fake_resp):
        signed = storage_service.create_signed_url("a.jpg", expires_in=600)
        assert signed == "https://demo.supabase.co/storage/v1/object/sign/snapshots/a.jpg?token=abc123"

        public_url = "https://demo.supabase.co/storage/v1/object/public/snapshots/a.jpg"
        resolved = storage_service.resolve_snapshot_url(public_url)
        assert resolved == signed


def test_auth_guard_revokes_locked_account_and_invalidates_cache(monkeypatch):
    state = {"active": True, "calls": 0}

    def _fake_check(user_id):
        state["calls"] += 1
        return state["active"]

    fake_mysql_mod = types.ModuleType("database.mysql_service")
    fake_mysql_mod.kiem_tra_tai_khoan_hoat_dong = _fake_check

    monkeypatch.setitem(sys.modules, "database.mysql_service", fake_mysql_mod)
    sys.modules.pop("backend.middleware.auth_guard", None)

    import backend.middleware.auth_guard as auth_guard

    auth_guard._ACCOUNT_STATUS_CACHE.clear()
    assert auth_guard._is_account_active(42) is True
    assert state["calls"] == 1

    # Cached hit -> no extra DB call
    assert auth_guard._is_account_active(42) is True
    assert state["calls"] == 1

    # Admin locks account and invalidates cache -> immediately returns False
    state["active"] = False
    auth_guard.invalidate_account_cache(42)
    assert auth_guard._is_account_active(42) is False
    assert state["calls"] == 2


def test_alert_state_machine_and_device_health_and_masking():
    # Alert state machine
    assert kiem_tra_chuyen_trang_thai_canh_bao("MOI", "DA_TIEP_NHAN") is True
    assert kiem_tra_chuyen_trang_thai_canh_bao("DA_TIEP_NHAN", "DA_DONG") is True
    assert kiem_tra_chuyen_trang_thai_canh_bao("DA_DONG", "DA_TIEP_NHAN") is False
    assert kiem_tra_chuyen_trang_thai_canh_bao("CANH_BAO_SAI", "DA_DONG") is False

    # 3-level Device Health
    assert phan_loai_suc_khoe_thiet_bi(10, camera_ok=True, fps=20.0, outbox_pending=0) == "ONLINE_HEALTHY"
    assert phan_loai_suc_khoe_thiet_bi(10, camera_ok=True, fps=5.0, outbox_pending=0) == "ONLINE_DEGRADED"
    assert phan_loai_suc_khoe_thiet_bi(10, camera_ok=True, fps=20.0, outbox_pending=3) == "ONLINE_DEGRADED"
    assert phan_loai_suc_khoe_thiet_bi(75, camera_ok=True, fps=20.0, outbox_pending=0) == "OFFLINE"

    # Sensitive CCCD/GPLX masking
    assert mask_sensitive_id("079203012345") == "079******345"
    assert mask_sensitive_id("1234") == "1234"


def test_eye_calibration_p75_and_scale_clamp():
    from detection.eye_calibration import EyeCalibration

    # AI-01: Blinks during calibration shouldn't drag down baseline (p75 ignores low outliers)
    cal = EyeCalibration(duration=0.0, reference_ear=0.30, min_samples=8)
    for ear in [0.10, 0.12, 0.28, 0.29, 0.30, 0.30, 0.31, 0.31]:
        cal.update(ear, ear)
    assert cal.ready is True
    assert cal.left_baseline >= 0.30

    # Extreme squinting during calibration cannot exceed max_scale=1.50
    squint_cal = EyeCalibration(duration=0.0, reference_ear=0.30, min_samples=5, max_scale=1.50)
    for _ in range(5):
        squint_cal.update(0.10, 0.10)
    assert squint_cal.ready is True
    # 0.10 * 1.50 = 0.15 (< 0.20 drowsy threshold, so drowsiness is still caught)
    assert squint_cal.normalize_ear(0.10, 0.10) == 0.15


def test_offline_outbox_max_rows_fifo_pruning(tmp_path):
    db_file = tmp_path / "capped_outbox.db"
    outbox = OfflineOutbox(db_path=str(db_file), max_rows=3)

    for i in range(5):
        outbox.enqueue("alert_event", {"i": i}, event_id=f"evt-cap-{i}")

    assert outbox.count_pending() == 3


def test_enhance_low_light_frame_brightens_dark_image():
    import numpy as np
    from detection.mediapipe_detector import enhance_low_light_frame

    # Dark synthetic cabin frame (non-uniform low-light pattern so CLAHE boosts contrast)
    dark = np.zeros((64, 64, 3), dtype=np.uint8)
    dark[:, :32] = 15
    dark[:, 32:] = 35
    enhanced = enhance_low_light_frame(dark, brightness_threshold=65.0)
    assert enhanced.shape == dark.shape
    assert float(enhanced.mean()) > float(dark.mean())

