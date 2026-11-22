import csv
import os
import sys
import time
from collections import deque

import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.ai_config import CAMERA_SOURCE, EAR_THRESHOLD, FRAME_HEIGHT, FRAME_WIDTH
from detection.eye_calibration import EyeCalibration
from detection.head_pose import get_head_pose
from detection.mediapipe_detector import detect_face_features


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

V2_CSV_PATH = os.path.join(DATASET_DIR, "drowsiness_dataset_v2.csv")
LEGACY_CSV_PATH = os.path.join(DATASET_DIR, "drowsiness_dataset.csv")

LABEL_INFO = {
    0: ("TINH TAO", (0, 255, 0)),
    1: ("MET MOI / NGAP", (0, 165, 255)),
    2: ("BUON NGU", (0, 0, 255)),
}

AUTO_SAVE_INTERVAL = 0.15  # ~6-7 mau sach moi giay khi bat che do thu thap tu dong


def ensure_csv_files():
    if not os.path.exists(V2_CSV_PATH):
        with open(V2_CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["EAR", "MAR", "Pitch", "Yaw", "PERCLOS", "Label", "SessionId"])

    if not os.path.exists(LEGACY_CSV_PATH):
        with open(LEGACY_CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["EAR", "MAR", "Label"])


def count_existing_labels(csv_path):
    counts = {0: 0, 1: 0, 2: 0}
    if not os.path.exists(csv_path):
        return counts
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lbl = int(row["Label"])
                if lbl in counts:
                    counts[lbl] += 1
    except Exception:
        pass
    return counts


def save_sample(ear, mar, pitch, yaw, perclos, label, session_id="sess-default"):
    with open(V2_CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            round(ear, 4),
            round(mar, 4),
            round(pitch, 2),
            round(yaw, 2),
            round(perclos, 4),
            int(label),
            session_id,
        ])

    with open(LEGACY_CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([round(ear, 4), round(mar, 4), int(label)])


def open_camera():
    if isinstance(CAMERA_SOURCE, int):
        if os.name == "nt":
            cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(CAMERA_SOURCE)
        else:
            cap = cv2.VideoCapture(CAMERA_SOURCE)
    else:
        cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(CAMERA_SOURCE)

    if not cap.isOpened():
        print(f"Khong mo duoc camera ({CAMERA_SOURCE})!", flush=True)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def main():
    ensure_csv_files()
    counts = count_existing_labels(V2_CSV_PATH)
    calibrator = EyeCalibration(duration=3.0, reference_ear=0.30, min_samples=20)
    eye_window = deque(maxlen=150)

    cap = open_camera()
    window_name = "DACN1 - Thu thap Du lieu AI (v2)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    active_label = None  # None = dang tam dung ghi
    last_save_time = 0.0
    session_saved = 0
    current_session_id = f"sess-{int(time.time())}"

    print("Da mo cong cu thu thap du lieu v2!", flush=True)
    print("Phim 0/A: Ghi TINH TAO | 1/Y: Ghi MET MOI | 2/D: Ghi BUON NGU | SPACE: Dung | R: Calib lai | Q: Thoat", flush=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        face_landmarks, raw_ear, mar, frame, left_ear, right_ear = detect_face_features(
            frame, return_eye_detail=True
        )

        ear = raw_ear
        pitch = 0.0
        yaw = 0.0
        perclos = 0.0

        if face_landmarks is not None:
            if not calibrator.ready:
                calibrator.update(left_ear, right_ear)
            else:
                ear = calibrator.normalize_ear(left_ear, right_ear)

            pitch, yaw = get_head_pose(face_landmarks, w, h)
            eye_window.append(1 if ear < EAR_THRESHOLD else 0)
            perclos = sum(eye_window) / len(eye_window) if eye_window else 0.0

            # Tu dong luu mau khi dang bat che do ghi va da calibrate xong
            now = time.time()
            if (
                calibrator.ready
                and active_label is not None
                and ear > 0
                and (now - last_save_time) >= AUTO_SAVE_INTERVAL
            ):
                save_sample(ear, mar, pitch, yaw, perclos, active_label, session_id=current_session_id)
                counts[active_label] += 1
                session_saved += 1
                last_save_time = now

        # VE GIAO DIEN HUONG DAN
        if not calibrator.ready:
            prog = calibrator.progress_percent()
            cv2.putText(
                frame,
                f"CALIBRATING EYES: {prog}% (Nhin thang, mo mat binh thuong)",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
        else:
            if active_label is not None:
                lbl_name, lbl_color = LABEL_INFO[active_label]
                cv2.putText(
                    frame,
                    f"DANG TU DONG GHI: [{active_label}] {lbl_name}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    lbl_color,
                    2,
                )
            else:
                cv2.putText(
                    frame,
                    "TRANG THAI: TAM DUNG (Bam 0/1/2 de bat ghi tu dong)",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (200, 200, 200),
                    2,
                )

        hud_lines = [
            f"EAR(norm): {ear:.3f} | MAR: {mar:.3f} | PERCLOS: {perclos:.2f}",
            f"Pitch: {pitch:.1f} | Yaw: {yaw:.1f}",
            f"Tong v2 -> [0] Tinh tao: {counts[0]} | [1] Met/Ngap: {counts[1]} | [2] Buon ngu: {counts[2]}",
            f"Da thu phien nay: +{session_saved} mau",
            "0/A: Tinh tao | 1/Y: Met/Ngap | 2/D: Buon ngu | SPACE: Dung | R: Calib lai | Q: Thoat",
        ]

        y = 75
        for line in hud_lines:
            cv2.putText(frame, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
            y += 28

        if face_landmarks is None:
            cv2.putText(
                frame,
                "KHONG TIM THAY KHUON MAT - KHONG LUU MAU RAC",
                (20, y + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key in (ord("0"), ord("a")):
            active_label = None if active_label == 0 else 0
        elif key in (ord("1"), ord("y")):
            active_label = None if active_label == 1 else 1
        elif key in (ord("2"), ord("d")):
            active_label = None if active_label == 2 else 2
        elif key == ord(" "):
            active_label = None
        elif key == ord("r"):
            active_label = None
            calibrator.reset()
            eye_window.clear()
            current_session_id = f"sess-{int(time.time())}"
            print(f"Da reset Eye Calibration cho nguoi/phien moi ({current_session_id})!", flush=True)

    cap.release()
    cv2.destroyAllWindows()
    print(f"Hoan tat! Phien nay thu them {session_saved} mau. Tong v2: {counts}", flush=True)


if __name__ == "__main__":
    main()
