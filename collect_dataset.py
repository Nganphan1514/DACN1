import cv2
import mediapipe as mp
import numpy as np
import csv
import os

# ======================
# Khởi tạo MediaPipe
# ======================
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True
)

# ======================
# Landmark mắt và miệng
# ======================
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [61, 13, 291, 14]


# ======================
# Hàm tính khoảng cách
# ======================
def distance(p1, p2):
    return np.linalg.norm(
        np.array(p1) - np.array(p2)
    )


# ======================
# Hàm tính EAR
# ======================
def calculate_ear(points):

    A = distance(points[1], points[5])
    B = distance(points[2], points[4])
    C = distance(points[0], points[3])

    ear = (A + B) / (2 * C)

    return ear


# ======================
# Hàm tính MAR
# ======================
def calculate_mar(points):

    vertical = distance(
        points[1],
        points[3]
    )

    horizontal = distance(
        points[0],
        points[2]
    )

    mar = vertical / horizontal

    return mar


# ======================
# Tạo folder dataset
# ======================
os.makedirs("dataset", exist_ok=True)

file_name = "dataset/drowsiness_dataset.csv"

# Nếu chưa có file thì tạo mới
if not os.path.exists(file_name):

    with open(
        file_name,
        mode="w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "EAR",
            "MAR",
            "Label"
        ])


# ======================
# Mở camera
# ======================
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

    ear = 0
    mar = 0

    if results.multi_face_landmarks:

        for face_landmarks in results.multi_face_landmarks:

            left_eye = []
            right_eye = []
            mouth = []

            # ===== Mắt trái =====
            for idx in LEFT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                left_eye.append((x, y))

                cv2.circle(
                    frame,
                    (x, y),
                    2,
                    (0, 255, 0),
                    -1
                )

            # ===== Mắt phải =====
            for idx in RIGHT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                right_eye.append((x, y))

                cv2.circle(
                    frame,
                    (x, y),
                    2,
                    (0, 255, 0),
                    -1
                )

            # ===== Miệng =====
            for idx in MOUTH:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                mouth.append((x, y))

                cv2.circle(
                    frame,
                    (x, y),
                    3,
                    (0, 0, 255),
                    -1
                )

            # ===== Tính EAR =====
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

            # ===== Tính MAR =====
            mar = calculate_mar(
                mouth
            )

            # ===== Hiển thị =====
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

    # ======================
    # Hướng dẫn
    # ======================
    cv2.putText(
        frame,
        "Nhan A = Tinh tao",
        (30, 170),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "Nhan Y = Ngap / Met",
        (30, 210),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 165, 255),
        2
    )

    cv2.putText(
        frame,
        "Nhan D = Buon ngu",
        (30, 250),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )

    cv2.putText(
        frame,
        "Nhan Q = Thoat",
        (30, 290),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "Thu thap du lieu",
        frame
    )

    key = cv2.waitKey(1)

    # ======================
    # Tỉnh táo = 0
    # ======================
    if key == ord("a"):

        with open(
            file_name,
            mode="a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                ear,
                mar,
                0
            ])

        print("Da luu: Tinh tao")

    # ======================
    # Ngáp / mệt = 1
    # ======================
    elif key == ord("y"):

        with open(
            file_name,
            mode="a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                ear,
                mar,
                1
            ])

        print("Da luu: Ngap / Met")

    # ======================
    # Buồn ngủ = 2
    # ======================
    elif key == ord("d"):

        with open(
            file_name,
            mode="a",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                ear,
                mar,
                2
            ])

        print("Da luu: Buon ngu")

    # ======================
    # Thoát
    # ======================
    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()