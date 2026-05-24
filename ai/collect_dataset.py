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
    refine_landmarks=True,
    max_num_faces=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# ======================
# Landmark mắt và miệng
# ======================
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH = [61, 13, 291, 14]

# ======================
# Path dataset
# ======================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

dataset_folder = os.path.join(BASE_DIR, "dataset")

os.makedirs(dataset_folder, exist_ok=True)

file_name = os.path.join(dataset_folder, "drowsiness_dataset.csv")

# ======================
# Tạo file CSV nếu chưa có
# ======================
if not os.path.exists(file_name):

    with open(file_name, mode="w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(["EAR", "MAR", "Label"])


# ======================
# Hàm tính khoảng cách
# ======================
def distance(p1, p2):

    return np.linalg.norm(np.array(p1) - np.array(p2))


# ======================
# Hàm tính EAR
# ======================
def calculate_ear(points):

    A = distance(points[1], points[5])
    B = distance(points[2], points[4])
    C = distance(points[0], points[3])

    if C == 0:
        return 0

    ear = (A + B) / (2 * C)

    return ear


# ======================
# Hàm tính MAR
# ======================
def calculate_mar(points):

    vertical = distance(points[1], points[3])

    horizontal = distance(points[0], points[2])

    if horizontal == 0:
        return 0

    mar = vertical / horizontal

    return mar


# ======================
# Hàm lưu dữ liệu
# ======================
def save_data(ear, mar, label):

    with open(file_name, mode="a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow([round(ear, 4), round(mar, 4), label])


# ======================
# Mở camera
# ======================
cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("Khong mo duoc camera!")

    exit()

sample_count = 0

while True:

    success, frame = cap.read()

    if not success:
        print("Khong doc duoc frame!")
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_mesh.process(rgb)

    ear = 0
    mar = 0
    face_detected = False

    # ======================
    # Detect khuôn mặt
    # ======================
    if results.multi_face_landmarks:

        face_detected = True

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

                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # ===== Mắt phải =====
            for idx in RIGHT_EYE:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                right_eye.append((x, y))

                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # ===== Miệng =====
            for idx in MOUTH:

                point = face_landmarks.landmark[idx]

                x = int(point.x * w)
                y = int(point.y * h)

                mouth.append((x, y))

                cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)

            # ======================
            # Tính EAR
            # ======================
            left_ear = calculate_ear(left_eye)

            right_ear = calculate_ear(right_eye)

            ear = (left_ear + right_ear) / 2

            # ======================
            # Tính MAR
            # ======================
            mar = calculate_mar(mouth)

    # ======================
    # Hiển thị thông số
    # ======================
    cv2.putText(
        frame,
        f"EAR: {ear:.2f}",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
    )

    cv2.putText(
        frame,
        f"MAR: {mar:.2f}",
        (30, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
    )

    cv2.putText(
        frame,
        f"Samples: {sample_count}",
        (30, 130),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2,
    )

    # ======================
    # Hướng dẫn
    # ======================
    cv2.putText(
        frame, "A = Tinh tao", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
    )

    cv2.putText(
        frame,
        "Y = Ngap / Met",
        (30, 230),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 165, 255),
        2,
    )

    cv2.putText(
        frame, "D = Buon ngu", (30, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2
    )

    cv2.putText(
        frame, "Q = Thoat", (30, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
    )

    # ======================
    # Không thấy mặt
    # ======================
    if not face_detected:

        cv2.putText(
            frame,
            "Khong tim thay khuon mat",
            (30, 350),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

    cv2.imshow("Thu thap du lieu", frame)

    key = cv2.waitKey(1) & 0xFF

    # ======================
    # Không lưu dữ liệu rác
    # ======================
    if not face_detected:
        if key == ord("q"):
            break
        continue

    # ======================
    # Tỉnh táo
    # ======================
    if key == ord("a"):

        save_data(ear, mar, 0)

        sample_count += 1

        print("Da luu: Tinh tao")

    # ======================
    # Ngáp / mệt
    # ======================
    elif key == ord("y"):

        save_data(ear, mar, 1)

        sample_count += 1

        print("Da luu: Ngap / Met")

    # ======================
    # Buồn ngủ
    # ======================
    elif key == ord("d"):

        save_data(ear, mar, 2)

        sample_count += 1

        print("Da luu: Buon ngu")

    # ======================
    # Thoát
    # ======================
    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
