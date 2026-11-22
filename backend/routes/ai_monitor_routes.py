from datetime import datetime, timezone
import os
import threading
import time
import uuid

from flask import Blueprint, jsonify, request

from alerts.snapshot import save_snapshot
from backend.middleware.auth_guard import require_role, resolve_driver_id
from backend.routes.realtime_routes import broadcast_event
from core.drowsiness_analyzer import DrowsinessAnalyzer
from database.mysql_service import (
    lay_tai_xe_theo_id,
    lay_xe_theo_tai_xe,
    luu_anh_canh_bao,
    save_detection_log,
    tao_su_kien_canh_bao,
)
from detection.head_pose import get_head_pose
from detection.mediapipe_detector import detect_face_features
from detection.predictor import predict_proba_dict
from face_auth.embedding_service import decode_base64_image
from services.expo_push_service import send_alert_push_to_managers_async
from services.storage_service import upload_snapshot_to_supabase

ai_monitor_bp = Blueprint("ai_monitor_bp", __name__)

_state_lock = threading.Lock()
_driver_sessions = {}

MOBILE_SAVE_INTERVAL = 10.0
MOBILE_SNAPSHOT_INTERVAL = 20.0


def _get_driver_session(tai_xe_id):
    with _state_lock:
        session = _driver_sessions.get(tai_xe_id)
        if session is None:
            # Tinh chinh nguong frame phu hop voi toc do ~1 FPS cua App Expo du phong
            analyzer = DrowsinessAnalyzer(
                drowsy_threshold=2,
                head_down_threshold=2,
                min_perclos_frames=8,
                drowsy_confirm_time=1.2,
                head_down_confirm_time=1.0,
                distraction_confirm_time=2.5,
                yawn_confirm_time=0.8,
            )
            session = {
                "analyzer": analyzer,
                "last_save_time": 0.0,
                "last_saved_status": None,
                "last_snapshot_time": 0.0,
            }
            _driver_sessions[tai_xe_id] = session
        return session


def _handle_mobile_drowsy_side_effects(frame, tai_xe_id, xe_id, driver_name, vehicle_name, risk_score, reasons):
    local_path = save_snapshot(frame)
    final_path = upload_snapshot_to_supabase(local_path) if local_path else None

    if final_path:
        luu_anh_canh_bao(
            tai_xe_id=tai_xe_id,
            xe_id=xe_id,
            duong_dan_anh=final_path,
        )

    snapshot_url = None
    if final_path:
        if str(final_path).startswith(("http://", "https://")):
            snapshot_url = str(final_path)
        else:
            snapshot_url = f"/api/snapshots/{os.path.basename(str(final_path))}"

    reason_text = ", ".join(reasons) if reasons else "BUON NGU"
    event_id = str(uuid.uuid4())
    message = f"[App Dự Phòng] Tài xế {driver_name} buồn ngủ ({reason_text})"
    occurred_at = datetime.now(timezone.utc).isoformat()

    # V3.0: Luu su_kien_canh_bao (PENDING_REVIEW) cho Quan ly xac minh, khong tu ket luan vi pham
    inserted_id = tao_su_kien_canh_bao(
        event_id=event_id,
        loai_canh_bao="BUON_NGU",
        noi_dung=message,
        tai_xe_id=tai_xe_id,
        xe_id=xe_id,
        nguon="mobile_backup",
        muc_do="CAO",
        duong_dan_anh=snapshot_url,
        risk_score=risk_score,
        device_id=f"mobile-driver-{tai_xe_id}",
        occurred_at=occurred_at,
        payload_version="1.0",
    )

    event = {
        "id": inserted_id,
        "event_id": event_id,
        "type": "BUON_NGU",
        "driver_name": driver_name,
        "vehicle_name": vehicle_name,
        "message": message,
        "risk_score": risk_score,
        "snapshot_url": snapshot_url,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    broadcast_event(event)
    send_alert_push_to_managers_async(event)


@ai_monitor_bp.route("/api/ai/reset-monitor", methods=["POST"])
@require_role("tai_xe", "quan_ly")
def api_reset_monitor():
    data = request.get_json(silent=True) or {}
    resolved_id, allowed = resolve_driver_id(data.get("tai_xe_id"))
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Không có quyền reset phiên giám sát này."
        }), 403

    with _state_lock:
        if resolved_id in _driver_sessions:
            _driver_sessions[resolved_id]["analyzer"].reset_counters()

    return jsonify({"success": True, "message": "Đã reset bộ phân tích dự phòng."})


@ai_monitor_bp.route("/api/ai/analyze-frame", methods=["POST"])
@require_role("tai_xe", "quan_ly")
def api_analyze_frame():
    data = request.get_json(silent=True) or {}
    resolved_id, allowed = resolve_driver_id(data.get("tai_xe_id"))
    if not allowed:
        return jsonify({
            "success": False,
            "message": "Không có quyền giám sát tài xế khác."
        }), 403

    frame, _ = decode_base64_image(data.get("image"))
    if frame is None:
        return jsonify({
            "success": False,
            "message": "Ảnh gửi lên không hợp lệ."
        }), 400

    session = _get_driver_session(resolved_id)
    analyzer = session["analyzer"]

    h, w, _ = frame.shape
    face_landmarks, ear, mar, _annotated = detect_face_features(frame)

    if face_landmarks is None:
        return jsonify({
            "success": True,
            "data": {
                "face_detected": False,
                "status": "KHONG TIM THAY MAT",
                "fatigue_score": round(analyzer.fatigue_score, 1),
                "risk_score": int(round(analyzer.fatigue_score / 10.0)),
                "ear": 0.0,
                "mar": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "reasons": [],
                "ai_probs": {"awake": 0.0, "fatigue": 0.0, "drowsy": 0.0},
            },
        })

    pitch, yaw = get_head_pose(face_landmarks, w, h)
    now = time.time()
    current_hour = datetime.now().hour
    is_dangerous_hour = (0 <= current_hour <= 5) or (13 <= current_hour <= 15)

    current_perclos = (
        sum(analyzer.eye_window) / len(analyzer.eye_window)
        if len(analyzer.eye_window) >= analyzer.min_perclos_frames
        else 0.0
    )

    ai_out = predict_proba_dict(
        ear=ear,
        mar=mar,
        pitch=pitch,
        yaw=yaw,
        perclos=current_perclos,
    )

    with _state_lock:
        result = analyzer.update(
            ear=ear,
            mar=mar,
            pitch=pitch,
            yaw=yaw,
            prediction=ai_out["prediction"],
            confidence=ai_out["confidence"],
            probs=ai_out["probs"],
            is_dangerous_hour=is_dangerous_hour,
            now=now,
        )

    status = result["status"]
    risk_score = result["risk_score"]

    # Luu log DB + ban canh bao neu phat hien bat thuong (co cooldown chong spam)
    should_save = status in ("MET MOI", "BUON NGU", "MAT TAP TRUNG") and (
        status != session["last_saved_status"]
        or (now - session["last_save_time"]) >= MOBILE_SAVE_INTERVAL
    )

    if should_save:
        xe_info = lay_xe_theo_tai_xe(resolved_id)
        xe_id = xe_info["id"] if xe_info else None
        save_detection_log(
            tai_xe_id=resolved_id,
            xe_id=xe_id,
            status=status,
            ear=ear,
            mar=mar,
            risk_score=risk_score,
        )
        session["last_saved_status"] = status
        session["last_save_time"] = now

    if status == "BUON NGU" and (now - session["last_snapshot_time"]) >= MOBILE_SNAPSHOT_INTERVAL:
        session["last_snapshot_time"] = now
        tx_info = lay_tai_xe_theo_id(resolved_id)
        xe_info = lay_xe_theo_tai_xe(resolved_id)
        driver_name = tx_info["ho_ten"] if tx_info else f"Tài xế #{resolved_id}"
        vehicle_name = xe_info["bien_so"] if xe_info else "Mobile Backup"
        xe_id = xe_info["id"] if xe_info else None

        threading.Thread(
            target=_handle_mobile_drowsy_side_effects,
            args=(frame.copy(), resolved_id, xe_id, driver_name, vehicle_name, risk_score, result["reasons"]),
            daemon=True,
        ).start()

    return jsonify({
        "success": True,
        "data": {
            "face_detected": True,
            "status": status,
            "fatigue_score": result["fatigue_score"],
            "risk_score": risk_score,
            "ear": round(float(ear), 3),
            "mar": round(float(mar), 3),
            "pitch": round(float(pitch), 1),
            "yaw": round(float(yaw), 1),
            "reasons": result["reasons"],
            "ai_probs": result["ai_probs"],
        },
    })
