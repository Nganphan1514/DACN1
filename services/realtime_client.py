from datetime import datetime
import os

import requests

from config.app_config import FLASK_HOST, FLASK_PORT, INTERNAL_API_KEY

_target_host = "127.0.0.1" if FLASK_HOST in ("0.0.0.0", "") else FLASK_HOST
BACKEND_ALERT_URL = os.getenv(
    "BACKEND_ALERT_URL",
    f"http://{_target_host}:{FLASK_PORT}/api/internal/alert-event",
)


def push_realtime_alert(
    event_type,
    driver_name,
    vehicle_name,
    message,
    snapshot_path=None,
    risk_score=0,
):
    """
    Gui su kien canh bao realtime ve Flask backend.
    Thiet ke de chay trong background queue (khong bao gio chan camera).
    """
    try:
        snapshot_filename = os.path.basename(snapshot_path) if snapshot_path else None
        payload = {
            "type": event_type,
            "driver_name": driver_name,
            "vehicle_name": vehicle_name,
            "message": message,
            "snapshot_filename": snapshot_filename,
            "risk_score": risk_score,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        requests.post(
            BACKEND_ALERT_URL,
            json=payload,
            headers={"X-Internal-Key": INTERNAL_API_KEY},
            timeout=2,
        )
    except Exception:
        # Web server co the chua bat khi chay main.py doc lap -> bo qua em ai
        pass
