import cv2
import mediapipe as mp
import numpy as np

# ===== MediaPipe =====
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)

# ===== Eye Landmarks =====
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# ===== Mouth Landmarks =====
MOUTH = [61, 13, 291, 14]


# ===== Distance =====
def euclidean_distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


# ===== EAR =====
def calculate_ear(eye_points):

    A = euclidean_distance(
        eye_points[1],
        eye_points[5]
    )

    B = euclidean_distance(
        eye_points[2],
        eye_points[4]
    )

    C = euclidean_distance(
        eye_points[0],
        eye_points[3]
    )

    ear = (A + B) / (2.0 * C)

    return ear


# ===== MAR =====
def calculate_mar(mouth_points):

    vertical = euclidean_distance(
        mouth_points[1],
        mouth_points[3]
    )

    horizontal = euclidean_distance(
        mouth_points[0],
        mouth_points[2]
    )

    mar = vertical / horizontal

    return mar


cap = cv2.VideoCapture(0)

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

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            left_eye_points = []
            right_eye_points = []
            mouth_points = []

            # ===== LEFT EYE =====
            for idx in LEFT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                left_eye_points.append((x, y))

                cv2.circle(
                    frame,
                    (x, y),
                    2,
                    (0, 255, 0),
                    -1
                )

            # ===== RIGHT EYE =====
            for idx in RIGHT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                right_eye_points.append((x, y))

                cv2.circle(
                    frame,
                    (x, y),
                    2,
                    (0, 255, 0),
                    -1
                )

            # ===== MOUTH =====
            for idx in MOUTH:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                mouth_points.append((x, y))

                cv2.circle(
                    frame,
                    (x, y),
                    3,
                    (0, 0, 255),
                    -1
                )

            # ===== Calculate EAR =====
            left_ear = calculate_ear(
                left_eye_points
            )

            right_ear = calculate_ear(
                right_eye_points
            )

            ear = (
                left_ear +
                right_ear
            ) / 2

            # ===== Calculate MAR =====
            mar = calculate_mar(
                mouth_points
            )

            # ===== Display =====
            cv2.putText(
                frame,
                f"EAR: {ear:.2f}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"MAR: {mar:.2f}",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

    cv2.imshow(
        "EAR & MAR Detection",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()