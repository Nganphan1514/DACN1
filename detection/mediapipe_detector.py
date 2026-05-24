import cv2
import mediapipe as mp

from detection.feature_extractor import (
    LEFT_EYE,
    RIGHT_EYE,
    MOUTH,
    calculate_ear,
    calculate_mar,
)

# ==========================
# INIT MEDIAPIPE
# ==========================
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)


# ==========================
# DETECT
# ==========================
def detect_face_features(frame):

    try:

        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = face_mesh.process(rgb)

        # ==========================
        # Không tìm thấy mặt
        # ==========================
        if not results.multi_face_landmarks:

            return (None, 0, 0, frame)

        for face_landmarks in results.multi_face_landmarks:

            left_eye = []
            right_eye = []
            mouth = []

            # ==========================
            # Mắt trái
            # ==========================
            for idx in LEFT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)

                y = int(point.y * h)

                left_eye.append((x, y))

                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # ==========================
            # Mắt phải
            # ==========================
            for idx in RIGHT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)

                y = int(point.y * h)

                right_eye.append((x, y))

                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # ==========================
            # Miệng
            # ==========================
            for idx in MOUTH:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)

                y = int(point.y * h)

                mouth.append((x, y))

                cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)

            # ==========================
            # EAR
            # ==========================
            left_ear = calculate_ear(left_eye)

            right_ear = calculate_ear(right_eye)

            ear = round((left_ear + right_ear) / 2, 4)

            # ==========================
            # MAR
            # ==========================
            mar = calculate_mar(mouth)

            return (face_landmarks, ear, mar, frame)

    except Exception as e:

        print("MediaPipe error:", e)

        return (None, 0, 0, frame)
