from collections import deque
from datetime import datetime
import json
import os
import queue
import threading

from flask import Blueprint, Response, g, jsonify, request, send_from_directory, stream_with_context

from backend.middleware.auth_guard import require_auth, require_role
from config.app_config import INTERNAL_API_KEY
from database.mysql_service import luu_expo_push_token, xoa_expo_push_token
from services.expo_push_service import is_valid_expo_token, send_alert_push_to_managers_async

realtime_bp = Blueprint("realtime_bp", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots")

_sub_lock = threading.Lock()
_subscribers = []
_recent_events = deque(maxlen=20)


def broadcast_event(event_data):
    _recent_events.append(event_data)
    with _sub_lock:
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(event_data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            if q in _subscribers:
                _subscribers.remove(q)


@realtime_bp.route("/api/internal/alert-event", methods=["POST"])
def api_internal_alert_event():
    api_key = request.headers.get("X-Internal-Key", "")
    if api_key != INTERNAL_API_KEY:
        return jsonify({
            "success": False,
            "message": "Unauthorized internal event key."
        }), 401

    data = request.get_json(silent=True) or {}
    snapshot_url = data.get("snapshot_url")
    if snapshot_url and not str(snapshot_url).startswith(("http://", "https://")):
        snapshot_url = None

    if not snapshot_url:
        snapshot_name = data.get("snapshot_filename")
        if snapshot_name:
            snapshot_url = f"/api/snapshots/{os.path.basename(str(snapshot_name))}"

    event = {
        "type": data.get("type", "ALERT"),
        "driver_name": data.get("driver_name") or "Chưa xác định",
        "vehicle_name": data.get("vehicle_name") or "N/A",
        "message": data.get("message") or "Phát hiện cảnh báo mới",
        "risk_score": data.get("risk_score", 0),
        "snapshot_url": snapshot_url,
        "timestamp": data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    broadcast_event(event)
    send_alert_push_to_managers_async(event)
    return jsonify({"success": True})


@realtime_bp.route("/api/push/register-token", methods=["POST"])
@require_auth
def api_register_push_token():
    data = request.get_json(silent=True) or {}
    token = (data.get("expo_push_token") or "").strip()
    platform = (data.get("platform") or "unknown").strip()

    if not is_valid_expo_token(token):
        return jsonify({
            "success": False,
            "message": "Expo Push Token không hợp lệ."
        }), 400

    ok = luu_expo_push_token(
        tai_khoan_id=g.current_user["id"],
        vai_tro=g.current_user["vai_tro"],
        expo_push_token=token,
        nen_tang=platform,
    )
    return jsonify({
        "success": ok,
        "message": "Đã đăng ký nhận thông báo đẩy." if ok else "Đăng ký token thất bại.",
    }), 200 if ok else 500


@realtime_bp.route("/api/push/unregister-token", methods=["POST"])
@require_auth
def api_unregister_push_token():
    data = request.get_json(silent=True) or {}
    token = (data.get("expo_push_token") or "").strip()
    ok = xoa_expo_push_token(token)
    return jsonify({"success": ok})


@realtime_bp.route("/api/admin/events", methods=["GET"])
@require_role("quan_ly")
def api_admin_events():
    client_queue = queue.Queue(maxsize=50)
    with _sub_lock:
        _subscribers.append(client_queue)

    def event_stream():
        try:
            yield f"event: connected\ndata: {json.dumps({'status': 'ok'})}\n\n"
            while True:
                try:
                    event = client_queue.get(timeout=15)
                    payload = json.dumps(event, ensure_ascii=False)
                    yield f"event: alert\ndata: {payload}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            with _sub_lock:
                if client_queue in _subscribers:
                    _subscribers.remove(client_queue)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@realtime_bp.route("/api/snapshots/<path:filename>", methods=["GET"])
@require_auth
def api_get_snapshot(filename):
    safe_name = os.path.basename(filename)
    full_path = os.path.join(SNAPSHOTS_DIR, safe_name)

    if not os.path.isfile(full_path):
        return jsonify({
            "success": False,
            "message": "Không tìm thấy ảnh cảnh báo."
        }), 404

    return send_from_directory(SNAPSHOTS_DIR, safe_name)
