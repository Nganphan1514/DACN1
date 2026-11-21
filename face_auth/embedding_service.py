import base64
import json
import numpy as np
import cv2

try:
    import dlib
    import face_recognition_models

    _face_detector = dlib.get_frontal_face_detector()
    _shape_predictor = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )
    _face_encoder = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )
    EMBEDDING_AVAILABLE = True
except Exception as _e:
    _face_detector = None
    _shape_predictor = None
    _face_encoder = None
    EMBEDDING_AVAILABLE = False
    print("Face embedding engine chua san sang (se fallback LBPH):", _e)


DEFAULT_DISTANCE_THRESHOLD = 0.48
MIN_BRIGHTNESS = 35.0


def decode_base64_image(data_url):
    """
    Giai ma chuoi data:image/jpeg;base64,... thanh (frame_bgr, raw_bytes).
    """
    if not data_url or not isinstance(data_url, str):
        return None, None

    payload = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        raw_bytes = base64.b64decode(payload)
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame, raw_bytes
    except Exception:
        return None, None


def extract_face_embedding(frame_bgr, require_single_face=True):
    """
    Kiem tra chat luong anh va trich xuat vector khuon mat 128 chieu.
    Tra ve: (embedding_np | None, error_message | None)
    """
    if not EMBEDDING_AVAILABLE:
        return None, "Hệ thống chưa sẵn sàng thư viện nhận diện khuôn mặt (dlib)."

    if frame_bgr is None or frame_bgr.size == 0:
        return None, "Ảnh không hợp lệ."

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    if float(np.mean(gray)) < MIN_BRIGHTNESS:
        return None, "Ảnh quá tối. Vui lòng tăng ánh sáng và thử lại."

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    faces = _face_detector(rgb, 1)

    if len(faces) == 0:
        return None, "Không tìm thấy khuôn mặt trong khung hình."

    if require_single_face and len(faces) > 1:
        return None, "Phát hiện nhiều hơn 1 khuôn mặt. Vui lòng chỉ để 1 người trước camera."

    face_rect = faces[0]
    shape = _shape_predictor(rgb, face_rect)
    descriptor = _face_encoder.compute_face_descriptor(rgb, shape)
    embedding = np.array(descriptor, dtype=np.float64)

    if embedding.shape != (128,):
        return None, "Không thể trích xuất vector đặc trưng khuôn mặt."

    return embedding, None


def parse_embedding_json(raw_text):
    try:
        values = json.loads(raw_text)
        arr = np.array(values, dtype=np.float64)
        if arr.shape == (128,):
            return arr
    except Exception:
        pass
    return None


def match_embedding(target_vec, known_entries, threshold=DEFAULT_DISTANCE_THRESHOLD):
    """
    So khop vector 128 chieu voi danh sach [(tai_xe_id, embedding_np), ...].
    Tra ve: (tai_xe_id | None, similarity_percent)
    """
    if target_vec is None or not known_entries:
        return None, 0.0

    best_driver_id = None
    best_distance = float("inf")

    for tai_xe_id, known_vec in known_entries:
        distance = float(np.linalg.norm(target_vec - known_vec))
        if distance < best_distance:
            best_distance = distance
            best_driver_id = tai_xe_id

    similarity = max(0.0, min(100.0, round((1.0 - best_distance) * 100.0, 2)))

    if best_driver_id is not None and best_distance <= threshold:
        return int(best_driver_id), similarity

    return None, similarity
