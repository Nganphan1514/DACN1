import threading

import requests

from config.logger import get_logger
from database.mysql_service import db, lay_danh_sach_push_token

logger = get_logger("expo_push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

ALERT_TITLES = {
    "BUON_NGU": "Cảnh báo BUỒN NGỦ",
    "NGUOI_LA": "Cảnh báo NGƯỜI LẠ lái xe",
    "SAI_XE": "Cảnh báo TÀI XẾ SAI XE",
    "MET_MOI": "Cảnh báo Mệt mỏi",
    "CAMERA_OFFLINE": "Cảnh báo CAMERA MẤT KẾT NỐI",
    "VI_PHAM_XAC_NHAN": "Thông báo Vi phạm đã xác minh",
    "KET_QUA_KHIEU_NAI": "Kết quả xử lý Khiếu nại",
}


def is_valid_expo_token(token):
    if not token or not isinstance(token, str):
        return False
    return token.startswith(("ExponentPushToken[", "ExpoPushToken["))


def send_expo_push_messages(tokens, title, body, data=None):
    valid_tokens = [t for t in (tokens or []) if is_valid_expo_token(t)]
    if not valid_tokens:
        return False

    messages = [
        {
            "to": token,
            "sound": "default",
            "priority": "high",
            "channelId": "alerts",
            "title": title,
            "body": body,
            "data": data or {},
        }
        for token in valid_tokens
    ]

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("Da gui %s Expo Push Notifications", len(valid_tokens))
            return True

        logger.warning("Expo Push HTTP %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception as e:
        logger.warning("Expo Push error: %s", e)
        return False


def send_alert_push_to_managers(event):
    event_type = event.get("type", "ALERT")
    driver_name = event.get("driver_name") or "Chưa xác định"
    vehicle_name = event.get("vehicle_name") or "N/A"
    message = event.get("message") or "Phát hiện cảnh báo mới"

    title = f"{ALERT_TITLES.get(event_type, 'Cảnh báo hệ thống')} • {vehicle_name}"
    body = f"{driver_name}: {message}"

    tokens = lay_danh_sach_push_token(vai_tro="quan_ly")
    if not tokens:
        return False

    return send_expo_push_messages(
        tokens=tokens,
        title=title,
        body=body,
        data={
            "type": event_type,
            "driver_name": driver_name,
            "vehicle_name": vehicle_name,
            "snapshot_url": event.get("snapshot_url"),
            "risk_score": event.get("risk_score", 0),
            "timestamp": event.get("timestamp"),
        },
    )


def send_alert_push_to_managers_async(event):
    thread = threading.Thread(
        target=send_alert_push_to_managers,
        args=(event,),
        daemon=True,
    )
    thread.start()


def send_push_to_account(tai_khoan_id, title, body, data=None):
    """V3.0: Gui Expo Push nham dich truc tiep toi 1 tai khoan (vi du: tai xe)."""
    if not tai_khoan_id:
        return False
    try:
        rows = db.fetch_all(
            "SELECT expo_push_token FROM thiet_bi_thong_bao WHERE tai_khoan_id = %s",
            (int(tai_khoan_id),),
        )
        tokens = [r["expo_push_token"] for r in rows if r.get("expo_push_token")]
        if not tokens:
            return False
        return send_expo_push_messages(tokens=tokens, title=title, body=body, data=data or {})
    except Exception as e:
        logger.warning("Push to account %s error: %s", tai_khoan_id, e)
        return False


def send_push_to_account_async(tai_khoan_id, title, body, data=None):
    thread = threading.Thread(
        target=send_push_to_account,
        args=(tai_khoan_id, title, body, data),
        daemon=True,
    )
    thread.start()
