from datetime import datetime, timezone
import os
import uuid

import requests

from config.app_config import FLASK_HOST, FLASK_PORT, INTERNAL_API_KEY

_target_host = "127.0.0.1" if FLASK_HOST in ("0.0.0.0", "") else FLASK_HOST
_base_url = os.getenv("BACKEND_BASE_URL", f"http://{_target_host}:{FLASK_PORT}").rstrip("/")
BACKEND_ALERT_URL = os.getenv(
    "BACKEND_ALERT_URL",
    f"{_base_url}/api/internal/alert-event",
)
BACKEND_HEARTBEAT_URL = os.getenv(
    "BACKEND_HEARTBEAT_URL",
    f"{_base_url}/api/internal/device-heartbeat",
)


def push_realtime_alert_status(
    event_type,
    driver_name,
    vehicle_name,
    message,
    snapshot_path=None,
    snapshot_url=None,
    risk_score=0,
    event_id=None,
    tai_xe_id=None,
    xe_id=None,
    phien_id=None,
    source="vehicle_camera",
    device_id=None,
    occurred_at=None,
    payload_version="1.0",
):
    """
    Gui su kien canh bao realtime ve Flask backend theo Event Contract chuan (P0+ REV-04/05).
    Tra ve:
    - "OK": server da nhan (HTTP 2xx)
    - "DEAD_LETTER": loi du lieu vinh vien (HTTP 400/422) -> khong retry vo han
    - "RETRY": mat mang hoac loi tam thoi (401/403/408/429/5xx) -> luu Outbox retry
    """
    try:
        resolved_url = snapshot_url
        snapshot_filename = None

        if not resolved_url and snapshot_path:
            if str(snapshot_path).startswith(("http://", "https://")):
                resolved_url = str(snapshot_path)
            else:
                snapshot_filename = os.path.basename(snapshot_path)

        payload = {
            "event_id": event_id or str(uuid.uuid4()),
            "payload_version": payload_version,
            "device_id": device_id,
            "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "driver_name": driver_name,
            "vehicle_name": vehicle_name,
            "message": message,
            "snapshot_filename": snapshot_filename,
            "snapshot_url": resolved_url,
            "risk_score": risk_score,
            "tai_xe_id": tai_xe_id,
            "xe_id": xe_id,
            "phien_id": phien_id,
            "source": source,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        resp = requests.post(
            BACKEND_ALERT_URL,
            json=payload,
            headers={"X-Internal-Key": INTERNAL_API_KEY},
            timeout=3,
        )
        if 200 <= resp.status_code < 300:
            return "OK"
        if resp.status_code in (400, 422):
            return "DEAD_LETTER"
        return "RETRY"
    except Exception:
        return "RETRY"


def push_realtime_alert(
    event_type,
    driver_name,
    vehicle_name,
    message,
    snapshot_path=None,
    snapshot_url=None,
    risk_score=0,
    event_id=None,
    tai_xe_id=None,
    xe_id=None,
    phien_id=None,
    source="vehicle_camera",
    device_id=None,
    occurred_at=None,
    payload_version="1.0",
):
    """Wrapper tuong thich nguoc tra ve bool."""
    status = push_realtime_alert_status(
        event_type=event_type,
        driver_name=driver_name,
        vehicle_name=vehicle_name,
        message=message,
        snapshot_path=snapshot_path,
        snapshot_url=snapshot_url,
        risk_score=risk_score,
        event_id=event_id,
        tai_xe_id=tai_xe_id,
        xe_id=xe_id,
        phien_id=phien_id,
        source=source,
        device_id=device_id,
        occurred_at=occurred_at,
        payload_version=payload_version,
    )
    return status == "OK"


def push_device_heartbeat(
    device_id,
    xe_id=None,
    ten_thiet_bi=None,
    nguon_camera=None,
    camera_source=None,
    fps=0.0,
    camera_ok=True,
    trang_thai_hoat_dong=None,
    status=None,
    active_driver_id=None,
    active_phien_id=None,
    outbox_pending=0,
    dead_letter_count=0,
    firmware_version="edge-2.0",
):
    """
    Gui nhip tim Heartbeat dinh ky tu Camera AI ve Backend (P0-3 + P0+ REV-13).
    """
    try:
        resolved_source = camera_source if camera_source is not None else (nguon_camera or "0")
        resolved_status = status or trang_thai_hoat_dong or "DANG_CHAY"
        resp = requests.post(
            BACKEND_HEARTBEAT_URL,
            json={
                "device_id": device_id,
                "xe_id": xe_id,
                "ten_thiet_bi": ten_thiet_bi or device_id,
                "nguon_camera": str(resolved_source),
                "fps": round(float(fps or 0.0), 1),
                "camera_ok": bool(camera_ok),
                "trang_thai_hoat_dong": resolved_status,
                "active_driver_id": active_driver_id,
                "active_phien_id": active_phien_id,
                "outbox_pending": int(outbox_pending or 0),
                "dead_letter_count": int(dead_letter_count or 0),
                "firmware_version": firmware_version,
            },
            headers={"X-Internal-Key": INTERNAL_API_KEY},
            timeout=2,
        )
        return resp.status_code == 200
    except Exception:
        return False
