import os
import threading
import time

import cv2
import mediapipe as mp

from database.mysql_service import lay_du_lieu_khuon_mat
from face_auth.embedding_service import (
    DEFAULT_DISTANCE_THRESHOLD,
    EMBEDDING_AVAILABLE,
    extract_face_embedding,
    match_embedding,
    parse_embedding_json,
)

# PATH LBPH FALLBACK
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "face_model.yml")
LABEL_PATH = os.path.join(BASE_DIR, "model", "face_labels.txt")

# CACHE VECTOR EMBEDDING TU MYSQL (TU DONG LAM MOI MOI 60s)
EMBEDDING_CACHE_TTL = 60.0
_embedding_lock = threading.Lock()
_known_embeddings = []
_embeddings_loaded_at = 0.0


def reload_face_embeddings():
    global _known_embeddings, _embeddings_loaded_at

    rows = lay_du_lieu_khuon_mat()
    parsed = []

    for row in rows:
        vec = parse_embedding_json(row.get("vector_khuon_mat"))
        if vec is not None and row.get("tai_xe_id") is not None:
            parsed.append((int(row["tai_xe_id"]), vec))

    with _embedding_lock:
        _known_embeddings = parsed
        _embeddings_loaded_at = time.time()

    return len(parsed)


def _get_known_embeddings():
    with _embedding_lock:
        expired = (time.time() - _embeddings_loaded_at) >= EMBEDDING_CACHE_TTL
        entries = list(_known_embeddings)

    if expired or not entries:
        reload_face_embeddings()
        with _embedding_lock:
            entries = list(_known_embeddings)

    return entries


# LOAD LBPH FALLBACK (CHI DUNG KHI CHUA CO DU LIEU EMBEDDING 128D)
recognizer = None
label_map = {}

try:
    if os.path.exists(MODEL_PATH):
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_PATH)

    if os.path.exists(LABEL_PATH):
        with open(LABEL_PATH, "r", encoding="utf-8") as file:
            for line in file:
                if ":" in line:
                    key, value = line.strip().split(":", 1)
                    label_map[int(key)] = value
except Exception as e:
    print("LBPH fallback load warning:", e)
    recognizer = None

mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(min_detection_confidence=0.5)


def _recognize_with_lbph(frame):
    if recognizer is None:
        return (None, 0.0)

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detector.process(rgb)

    if not results.detections:
        return (None, 0.0)

    detection = results.detections[0]
    bbox = detection.location_data.relative_bounding_box

    x = int(bbox.xmin * w)
    y = int(bbox.ymin * h)
    bw = int(bbox.width * w)
    bh = int(bbox.height * h)

    padding = 20
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(w, x + bw + padding)
    y2 = min(h, y + bh + padding)

    face_crop = frame[y1:y2, x1:x2]
    if face_crop.size == 0:
        return (None, 0.0)

    gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    gray_face = cv2.resize(gray_face, (200, 200))

    label, confidence = recognizer.predict(gray_face)
    similarity = max(0.0, 100.0 - confidence)

    if similarity < 45:
        return (None, similarity)

    folder_name = label_map.get(label)
    if not folder_name:
        return (None, similarity)

    tai_xe_id = int(folder_name.replace("tai_xe_", ""))
    return (tai_xe_id, similarity)


def recognize_driver(frame):
    """
    Uu tien nhan dien bang Face Embedding 128D (luu trong MySQL).
    Tu dong fallback sang LBPH neu DB chua co du lieu vector 128D hoac thieu dlib.
    """
    try:
        if EMBEDDING_AVAILABLE:
            known_entries = _get_known_embeddings()
            if known_entries:
                target_vec, err = extract_face_embedding(frame, require_single_face=False)
                if target_vec is None:
                    return (None, 0.0)
                return match_embedding(
                    target_vec,
                    known_entries,
                    threshold=DEFAULT_DISTANCE_THRESHOLD,
                )

        return _recognize_with_lbph(frame)

    except Exception as e:
        print("Face recognize error:", e)
        return (None, 0.0)


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        tai_xe_id, do_tuong_dong = recognize_driver(frame)

        text = "Khong xac dinh"
        color = (0, 0, 255)

        if tai_xe_id:
            text = f"Tai xe: {tai_xe_id}"
            color = (0, 255, 0)

        cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(
            frame,
            f"Similarity: {do_tuong_dong:.1f}%",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        cv2.imshow("Nhan dien tai xe", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
