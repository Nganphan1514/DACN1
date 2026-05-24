import cv2
import time
import csv
import os

from datetime import datetime
from collections import deque

from detection.mediapipe_detector import detect_face_features

from detection.predictor import predict_state

from detection.head_pose import get_head_pose

from config.vehicle_config import (
    VEHICLE_ID,
    VEHICLE_NAME,
)

from services.location_service import (find_nearest_rest_stop)

from database.mysql_service import (
    db,
    save_detection_log,
    luu_anh_canh_bao,
    tao_phien_lai_xe,
    lay_phien_dang_lai,
    cap_nhat_mat_dau,
    reset_mat_dau,
    dong_phien_lai_xe,
    luu_nguoi_la,
)

from alerts.snapshot import save_snapshot

from face_auth.recognize_driver import recognize_driver

from database.mysql_service import lay_tai_xe_theo_id

from alerts.smart_voice import (
    driver_found_voice,
    fatigue_warning,
    drowsy_warning,
    long_drive_warning,
    dangerous_time_warning,
    nearby_rest_warning,
    session_close_warning,
    unknown_driver_warning,
)

# ==========================
# TẠO THƯ MỤC
# ==========================
os.makedirs("logs", exist_ok=True)

os.makedirs("snapshots", exist_ok=True)

# ==========================
# FILE LOG
# ==========================
log_file = "logs/detection_log.csv"

if not os.path.exists(log_file):

    with open(log_file, mode="w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "ThoiGian",
                "EAR",
                "MAR",
                "SoLanNhayMat",
                "PERCLOS",
                "Pitch",
                "RiskScore",
                "TrangThai",
            ]
        )


# ==========================
# SAVE LOG
# ==========================
def save_log(ear, mar, blink, perclos, pitch, risk_score, status):

    with open(log_file, mode="a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round(ear, 3),
                round(mar, 3),
                blink,
                round(perclos, 3),
                round(pitch, 2),
                risk_score,
                status,
            ]
        )


# ==========================
# CAMERA
# ==========================
cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("Khong mo duoc camera")

    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)

cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)


# ==========================
# THRESHOLD
# ==========================
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.65

DROWSY_THRESHOLD = 20
HEAD_DOWN_THRESHOLD = 15

PERCLOS_THRESHOLD = 0.40


# ==========================
# CALIBRATION
# ==========================
calibration_start = time.time()

CALIBRATION_TIME = 3

ear_samples = []
mar_samples = []
pitch_samples = []

calibrated = False

personal_ear_threshold = EAR_THRESHOLD

personal_mar_threshold = MAR_THRESHOLD

personal_pitch_limit = 15


# ==========================
# TIME
# ==========================
start_time = time.time()

drive_start_time = time.time()

prev_time = time.time()

# ==========================
# DRIVER AUTH
# ==========================
tai_xe_hien_tai = None

ten_tai_xe = "CHUA XAC DINH"

driver_locked = False

phien_hien_tai = None

close_warning_spoken = False

unknown_start_time = None

last_unknown_log = 0

LOST_TIMEOUT = 1800

WARNING_BEFORE_CLOSE = 60

unknown_start_time = None

last_unknown_log = 0

UNKNOWN_TIMEOUT = 5

UNKNOWN_LOG_INTERVAL = 60

recognize_start_time = time.time()

# ==========================
# COUNTER
# ==========================
blink_count = 0
drowsy_count = 0
last_drowsy_count_time = 0
drowsy_frames = 0
head_down_frames = 0
yawn_frames = 0
last_snapshot_time = 0

SNAPSHOT_INTERVAL = 20
eye_closed = False

last_saved_status = None

last_save_time = 0

SAVE_INTERVAL = 10

# ==========================
# PERCLOS
# ==========================
eye_window = deque(maxlen=300)


# ==========================
# MAIN LOOP
# ==========================
while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    status = "KHONG TIM THAY MAT"

    color = (255, 255, 255)

    risk_score = 0
    ear = 0
    mar = 0
    pitch = 0
    yaw = 0
    perclos = 0
    confidence = 0

    # ==========================
    # DETECT FACE
    # ==========================
    face_landmarks, ear, mar, frame = detect_face_features(frame)

    if not face_landmarks:

        if phien_hien_tai:

            phien = db.fetch_one(
                """
                SELECT *
                FROM phien_lai_xe
                WHERE id=%s
                """,
                (
                    phien_hien_tai,
                )
            )

            if phien:

                # ==========================
                # CHUA DANH DAU MAT DAU
                # ==========================
                if (
                    phien[
                        "thoi_diem_mat_dau"
                    ]
                    is None
                ):

                    cap_nhat_mat_dau(
                        phien_hien_tai
                    )

                else:

                    lost_seconds = (
                        datetime.now()
                        -
                        phien[
                            "thoi_diem_mat_dau"
                        ]
                    ).total_seconds()

                    # ==========================
                    # CANH BAO
                    # CON 1 PHUT DONG PHIEN
                    # ==========================
                    remaining = (
                        LOST_TIMEOUT
                        -
                        lost_seconds
                    )

                    if (
                        remaining
                        <= WARNING_BEFORE_CLOSE
                        and not close_warning_spoken
                    ):

                        session_close_warning()

                        close_warning_spoken = True

                    # ==========================
                    # DONG PHIEN
                    # ==========================
                    if (
                        lost_seconds
                        >
                        LOST_TIMEOUT
                    ):

                        dong_phien_lai_xe(
                            phien_hien_tai
                        )

                        print(
                            "Da dong phien"
                        )

                        phien_hien_tai = None

                        driver_locked = False

                        tai_xe_hien_tai = None

                        ten_tai_xe = (
                            "CHUA XAC DINH"
                        )

                        close_warning_spoken = False
    if face_landmarks:

        # ==========================
        # TAI XE QUAY LAI
        # ==========================
        if phien_hien_tai:

            reset_mat_dau(
                phien_hien_tai
            )

            close_warning_spoken = False
        # ==========================
        # NHẬN DIỆN TÀI XẾ
        # ==========================
        if not driver_locked:

            tai_xe_id, similarity = recognize_driver(frame)

            # ==========================
            # NHAN DIEN THANH CONG
            # ==========================
            if tai_xe_id:

                unknown_start_time = None

                last_unknown_log = 0

                thong_tin_tai_xe = lay_tai_xe_theo_id(tai_xe_id)

                if thong_tin_tai_xe:

                    tai_xe_hien_tai = tai_xe_id

                    ten_tai_xe = thong_tin_tai_xe["ho_ten"]

                    driver_locked = True

                    phien = lay_phien_dang_lai(
                        tai_xe_hien_tai
                    )

                    if phien:

                        phien_hien_tai = (
                            phien["id"]
                        )

                        reset_mat_dau(
                            phien_hien_tai
                        )

                        close_warning_spoken = False

                    else:

                        phien_hien_tai = tao_phien_lai_xe(
                            tai_xe_hien_tai, VEHICLE_ID 
                        )

                        print(
                            "Da tao phien moi"
                        )

                    print(f"Tai xe: " f"{ten_tai_xe}")

                    driver_found_voice(ten_tai_xe)

            # ==========================
            # KHONG NHAN DIEN DUOC
            # ==========================
            else:

                if unknown_start_time is None:

                    unknown_start_time = time.time()

                elapsed = time.time() - unknown_start_time

                # ==========================
                # > 5s
                # ==========================
                if elapsed >= UNKNOWN_TIMEOUT:

                    unknown_driver_warning()

                    current_time = time.time()

                    if current_time - last_unknown_log > UNKNOWN_LOG_INTERVAL:

                        duong_dan_anh = save_snapshot(frame)

                        luu_nguoi_la(
                            xe_id=VEHICLE_ID, duong_dan_anh=duong_dan_anh, ghi_chu="Tai xe chua xac thuc"
                        )

                        last_unknown_log = current_time

        # ==========================
        # HEAD POSE
        # ==========================
        pitch, yaw = get_head_pose(face_landmarks, w, h)

        # ==========================
        # CALIBRATION
        # ==========================
        if not calibrated:

            ear_samples.append(ear)

            mar_samples.append(mar)

            pitch_samples.append(pitch)

            elapsed = time.time() - calibration_start

            cv2.putText(
                frame,
                "CALIBRATING...",
                (250, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                3,
            )

            if elapsed > CALIBRATION_TIME:

                personal_ear_threshold = (sum(ear_samples) / len(ear_samples)) * 0.7

                personal_mar_threshold = (sum(mar_samples) / len(mar_samples)) * 1.5

                personal_pitch_limit = (sum(pitch_samples) / len(pitch_samples)) + 10

                calibrated = True

                print("Calibration Done")

        # ==========================
        # HEAD DOWN
        # ==========================
        if pitch > personal_pitch_limit:

            head_down_frames += 1

        else:

            head_down_frames = 0

        # ==========================
        # BLINK
        # ==========================
        if ear < personal_ear_threshold:

            eye_window.append(1)

            if not eye_closed:

                eye_closed = True

                blink_count += 1

            drowsy_frames += 1

        else:

            eye_window.append(0)

            eye_closed = False

            drowsy_frames = 0

        # ==========================
        # PERCLOS
        # ==========================
        if len(eye_window) > 0:

            perclos = sum(eye_window) / len(eye_window)

        # ==========================
        # YAWN
        # ==========================
        if mar > personal_mar_threshold:

            yawn_frames += 1

        else:

            yawn_frames = 0

        # ==========================
        # AI PREDICT
        # ==========================
        prediction, confidence = predict_state(ear, mar)

        # ==========================
        # RISK SCORE
        # ==========================
        if drowsy_frames > DROWSY_THRESHOLD:

            risk_score += 2

        if perclos > PERCLOS_THRESHOLD:

            risk_score += 2

        if head_down_frames > HEAD_DOWN_THRESHOLD:

            risk_score += 2

        if yawn_frames > 15:

            risk_score += 1

        if prediction == 2:

            risk_score += 1

        # ==========================
        # TIME FACTOR
        # ==========================
        current_hour = datetime.now().hour

        if 0 <= current_hour <= 5:

            risk_score += 1

            dangerous_time_warning()

        if 13 <= current_hour <= 15:

            risk_score += 1

            dangerous_time_warning()

        drive_hours = (time.time() - drive_start_time) / 3600

        if drive_hours > 2:

            risk_score += 1

            long_drive_warning()

        # ==========================
        # FINAL DECISION
        # ==========================
        if risk_score <= 2:

            status = "TINH TAO"

            color = (0, 255, 0)

        elif risk_score <= 4:

            status = "MET MOI"

            color = (0, 165, 255)

            fatigue_warning()

            if (
                drowsy_frames
                > 10
            ):

                rest_stop = (
                    find_nearest_rest_stop()
                )

                if rest_stop:

                    place_name = (
                        rest_stop["name"]
                        .split(",")[0]
                    )

                    nearby_rest_warning(
                        f"{place_name}, "
                        f"cách khoảng "
                        f"{rest_stop['distance_km']} "
                        f"ki lô mét"
                    )

                else:

                    nearby_rest_warning()

        else:

            status = "BUON NGU"

            color = (0, 0, 255)

            drowsy_warning()

            rest_stop = (
                find_nearest_rest_stop()
            )

            if rest_stop:

                place_name = (
                rest_stop["name"]
                .split(",")[0]
                )

                nearby_rest_warning(
                    f"{place_name}, "
                    f"cách khoảng "
                    f"{rest_stop['distance_km']} "
                    f"ki lô mét"
                )
            else:

                nearby_rest_warning()

            current_snapshot_time = time.time()

            duong_dan_anh = None

            time_since_snapshot = (
                current_snapshot_time
                - last_snapshot_time
            )

            if (
                time_since_snapshot
                >
                SNAPSHOT_INTERVAL
            ):

                duong_dan_anh = (
                    save_snapshot(frame)
                )

                last_snapshot_time = (
                    current_snapshot_time
                )

            if (
                duong_dan_anh
                and tai_xe_hien_tai
            ):

                luu_anh_canh_bao(
                    tai_xe_id=tai_xe_hien_tai,
                    xe_id=VEHICLE_ID,
                    duong_dan_anh=duong_dan_anh
                )

            current_drowsy_time = time.time()

            if (
                current_drowsy_time
                - last_drowsy_count_time
                > 5
            ):

                drowsy_count += 1

                last_drowsy_count_time = (
                    current_drowsy_time
                )
        # ==========================
        # SAVE DATABASE THÔNG MINH
        # ==========================
        current_time = time.time()

        should_save = False

        # chỉ lưu mệt hoặc buồn ngủ
        if status in ["MET MOI", "BUON NGU"]:

            # trạng thái đổi
            if status != last_saved_status:

                should_save = True

            # hoặc mỗi 10 giây
            elif current_time - last_save_time > SAVE_INTERVAL:

                should_save = True

        if should_save and tai_xe_hien_tai:

            save_detection_log(
                tai_xe_id=tai_xe_hien_tai,
                xe_id=VEHICLE_ID,
                status=status,
                ear=ear,
                mar=mar,
                risk_score=risk_score,
            )

            last_saved_status = status

            last_save_time = current_time
    # ==========================
    # FPS
    # ==========================
    current = time.time()

    fps = int(1 / max(current - prev_time, 0.0001))

    prev_time = current

    runtime = int(time.time() - start_time)

    # ==========================
    # DISPLAY
    # ==========================
    texts = [
        f"Tai xe: {ten_tai_xe}",
        f"Xe: {VEHICLE_NAME}",
        f"EAR: {ear:.2f}",
        f"MAR: {mar:.2f}",
        f"Blink: {blink_count}",
        f"PERCLOS: {perclos:.2f}",
        f"Pitch: {pitch:.1f}",
        f"Confidence: {confidence:.1f}%",
        f"Risk Score: {risk_score}",
        status,
        f"Drowsy Count: {drowsy_count}",
        f"FPS: {fps}",
        f"Runtime: {runtime}s",
    ]

    y = 40

    for text in texts:

        cv2.putText(
            frame,
            text,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color if text == status else (255, 255, 255),
            2,
        )

        y += 35

    cv2.imshow("AI Drowsiness Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


cap.release()

cv2.destroyAllWindows()
