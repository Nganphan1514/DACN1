import cv2
import mediapipe as mp
import numpy as np
import time

# ===== MediaPipe =====
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True
)

# ===== Landmarks =====
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [61, 13, 291, 14]


# ===== Distance =====
def distance(p1, p2):
    return np.linalg.norm(
        np.array(p1) - np.array(p2)
    )


# ===== EAR =====
def calculate_ear(points):

    A = distance(points[1], points[5])
    B = distance(points[2], points[4])
    C = distance(points[0], points[3])

    return (A + B) / (2 * C)


# ===== MAR =====
def calculate_mar(points):

    vertical = distance(
        points[1],
        points[3]
    )

    horizontal = distance(
        points[0],
        points[2]
    )

    return vertical / horizontal


cap = cv2.VideoCapture(0)

# ===== Threshold =====
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.45

closed_eye_frames = 0

while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = face_mesh.process(rgb)

    status = "Awake"

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            left_eye = []
            right_eye = []
            mouth = []

            # Eye points
            for idx in LEFT_EYE:
                p = face_landmarks.landmark[idx]

                x = int(p.x * w)
                y = int(p.y * h)

                left_eye.append((x, y))

            for idx in RIGHT_EYE:
                p = face_landmarks.landmark[idx]

                x = int(p.x * w)
                y = int(p.y * h)

                right_eye.append((x, y))

            for idx in MOUTH:
                p = face_landmarks.landmark[idx]

                x = int(p.x * w)
                y = int(p.y * h)

                mouth.append((x, y))

            # ===== EAR =====
            left_ear = calculate_ear(
                left_eye
            )

            right_ear = calculate_ear(
                right_eye
            )

            ear = (
                left_ear +
                right_ear
            ) / 2

            # ===== MAR =====
            mar = calculate_mar(
                mouth
            )

            # ===== Detect Sleep =====
            if ear < EAR_THRESHOLD:
                closed_eye_frames += 1
            else:
                closed_eye_frames = 0

            # Nhắm mắt lâu
            if closed_eye_frames > 20:
                status = "Buồn ngủ"

            # Ngáp
            if mar > MAR_THRESHOLD:
                status = "Ngáp"

            # ===== Display =====
            cv2.putText(
                frame,
                f"EAR: {ear:.2f}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2
            )

            cv2.putText(
                frame,
                f"MAR: {mar:.2f}",
                (30,100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,0,255),
                2
            )

            color = (0,255,0)

            if status == "Buồn ngủ":
                color = (0,0,255)

            elif status == "Ngáp":
                color = (0,165,255)

            cv2.putText(
                frame,
                status,
                (30,160),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                color,
                3
            )

    cv2.imshow(
        "Drowsy Detection",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()