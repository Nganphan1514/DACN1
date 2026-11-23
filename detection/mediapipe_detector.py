import cv2
import mediapipe as mp

from detection.feature_extractor import (
    LEFT_EYE,
    RIGHT_EYE,
    MOUTH,
    calculate_ear,
    calculate_mar,
)


# INIT MEDIAPIPE

mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)



_CLAHE = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))


def enhance_low_light_frame(frame, brightness_threshold=65.0):
    """
    AI-03: Tang sang thich nghi (CLAHE tren kenh L cua khong gian LAB)
    khi cabin toi (ban dem 0h-5h) de MediaPipe bat landmark mat/mieng on dinh hon.
    """
    if frame is None or frame.size == 0:
        return frame
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    if float(l_channel.mean()) >= brightness_threshold:
        return frame
    l_enhanced = _CLAHE.apply(l_channel)
    merged = cv2.merge((l_enhanced, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


# DETECT FACE FEATURES

def detect_face_features(frame, return_eye_detail=False):
    """
    Mặc định giữ luồng cũ:
        return (face_landmarks, ear, mar, frame)

    Khi cần calibration mắt riêng:
        return (face_landmarks, ear, mar, frame, left_ear, right_ear)
    """

    try:
        h, w, _ = frame.shape

        processed = enhance_low_light_frame(frame)
        rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)

        results = face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            if return_eye_detail:
                return (None, 0, 0, frame, 0, 0)

            return (None, 0, 0, frame)

        for face_landmarks in results.multi_face_landmarks:
            left_eye = []
            right_eye = []
            mouth = []

            # Mắt trái
            for idx in LEFT_EYE:
                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                left_eye.append((x, y))

                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # Mắt phải
            for idx in RIGHT_EYE:
                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                right_eye.append((x, y))

                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # Miệng
            for idx in MOUTH:
                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                mouth.append((x, y))

                cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)

            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)

            ear = round((left_ear + right_ear) / 2, 4)

            mar = calculate_mar(mouth)

            if return_eye_detail:
                return (face_landmarks, ear, mar, frame, left_ear, right_ear)

            return (face_landmarks, ear, mar, frame)

        if return_eye_detail:
            return (None, 0, 0, frame, 0, 0)

        return (None, 0, 0, frame)

    except Exception as e:
        print("MediaPipe error:", e)

        if return_eye_detail:
            return (None, 0, 0, frame, 0, 0)

        return (None, 0, 0, frame)
