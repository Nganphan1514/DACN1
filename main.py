import cv2
import mediapipe as mp
import time
import csv
import os
from datetime import datetime
from collections import deque

from detection.feature_extractor import (
    LEFT_EYE,
    RIGHT_EYE,
    MOUTH,
    calculate_ear,
    calculate_mar,
)

from detection.predictor import predict_state

from detection.head_pose import get_head_pose

from database.mysql_service import save_detection_log

from alerts.voice_alert import speak_warning

from alerts.snapshot import save_snapshot

from alerts.smart_voice import (
    fatigue_warning,
    drowsy_warning,
    long_drive_warning,
    dangerous_time_warning,
    nearby_rest_warning,
)

# ==========================
# CREATE FOLDERS
# ==========================
os.makedirs("logs", exist_ok=True)

os.makedirs("snapshots", exist_ok=True)

# ==========================
# LOG FILE
# ==========================
log_file = "logs/detection_log.csv"

if not os.path.exists(log_file):

    with open(log_file, mode="w", newline="") as file:

        writer = csv.writer(file)

        writer.writerow(
            ["Time", "EAR", "MAR", "Blink", "PERCLOS", "Pitch", "RiskScore", "Status"]
        )


def save_log(ear, mar, blink, perclos, pitch, risk_score, status):

    with open(log_file, mode="a", newline="") as file:

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
# MEDIAPIPE
# ==========================
mp_face_mesh = mp.solutions.face_mesh

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)

# ==========================
# CAMERA
# ==========================
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)

cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

# ==========================
# THRESHOLD
# ==========================
EAR_THRESHOLD = 0.20
MAR_THRESHOLD = 0.65

DROWSY_THRESHOLD = 20
HEAD_DOWN_THRESHOLD = 15
HEAD_PITCH_LIMIT = 15

PERCLOS_THRESHOLD = 0.40

# ==========================
# STATS
# ==========================

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

personal_pitch_limit = HEAD_PITCH_LIMIT

start_time = time.time()
drive_start_time = time.time()
prev_time = time.time()

drowsy_count = 0
blink_count = 0

# ==========================
# TEMPORAL LOGIC
# ==========================
drowsy_frames = 0
head_down_frames = 0
yawn_frames = 0

eye_closed = False

# ==========================
# PERCLOS WINDOW
# ==========================
eye_window = deque(maxlen=300)

# ~10 giây nếu 30 FPS
# đổi 1800 nếu muốn ~60s

while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_mesh.process(rgb)

    status = "KHONG TIM THAY MAT"

    color = (255, 255, 255)

    ear = 0
    mar = 0
    pitch = 0
    yaw = 0
    risk_score = 0
    perclos = 0

    if results.multi_face_landmarks:

        face_landmarks = results.multi_face_landmarks[0]

        left_eye = []
        right_eye = []
        mouth = []

        # ======================
        # EYES
        # ======================
        for idx in LEFT_EYE:

            point = face_landmarks.landmark[idx]

            x = int(point.x * w)
            y = int(point.y * h)

            left_eye.append((x, y))

            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

        for idx in RIGHT_EYE:

            point = face_landmarks.landmark[idx]

            x = int(point.x * w)
            y = int(point.y * h)

            right_eye.append((x, y))

            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

        # ======================
        # MOUTH
        # ======================
        for idx in MOUTH:

            point = face_landmarks.landmark[idx]

            x = int(point.x * w)
            y = int(point.y * h)

            mouth.append((x, y))

            cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)

        # ======================
        # FEATURE EXTRACTION
        # ======================
        left_ear = calculate_ear(left_eye)

        right_ear = calculate_ear(right_eye)

        ear = (left_ear + right_ear) / 2

        mar = calculate_mar(mouth)

        # ======================
        # HEAD POSE
        # ======================
        pitch, yaw = get_head_pose(face_landmarks, w, h)

        # ======================
        # PERSONAL CALIBRATION
        # ======================
        if not calibrated:

            ear_samples.append(ear)

            mar_samples.append(mar)

            pitch_samples.append(pitch)

            elapsed = time.time() - calibration_start

            cv2.putText(
                frame,
                "CALIBRATING...",
                (300, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                3,
            )

            if elapsed > CALIBRATION_TIME:

                avg_ear = sum(ear_samples) / len(ear_samples)

                avg_mar = sum(mar_samples) / len(mar_samples)

                avg_pitch = sum(pitch_samples) / len(pitch_samples)

                personal_ear_threshold = avg_ear * 0.7

                personal_mar_threshold = avg_mar * 1.5

                personal_pitch_limit = avg_pitch + 10

                calibrated = True

                print("Calibration Done")

                print(personal_ear_threshold)

        if pitch > personal_pitch_limit:
            head_down_frames += 1
        else:
            head_down_frames = 0

        # ======================
        # BLINK
        # ======================
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

        # ======================
        # PERCLOS
        # ======================
        if len(eye_window) > 0:

            perclos = sum(eye_window) / len(eye_window)

        # ======================
        # YAWN
        # ======================
        if mar > personal_mar_threshold:
            yawn_frames += 1
        else:
            yawn_frames = 0

        # ======================
        # AI MODEL
        # ======================
        prediction = predict_state(ear, mar)

        # ======================
        # SMART RISK SCORE
        # ======================
        if drowsy_frames > DROWSY_THRESHOLD:
            risk_score += 2

        if perclos > PERCLOS_THRESHOLD:
            risk_score += 2

        if head_down_frames > HEAD_DOWN_THRESHOLD:
            risk_score += 2

        if yawn_frames > 15:
            risk_score += 1

        # AI bonus
        if prediction == 2:
            risk_score += 1

        # ======================
        # TIME FACTOR
        # ======================
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

        # ======================
        # FINAL DECISION
        # ======================
        if risk_score <= 2:

            status = (
                "TINH TAO"
            )

            color = (
                0,
                255,
                0
            )

        elif risk_score <= 4:

            status = (
                "MET MOI"
            )

            color = (
                0,
                165,
                255
            )

            fatigue_warning()

        else:

            status = (
                "BUON NGU"
            )

            color = (
                0,
                0,
                255
            )

            drowsy_warning()

            nearby_rest_warning()
            
            save_snapshot(
                frame
            )

            drowsy_count += 1

        save_log(ear, mar, blink_count, perclos, pitch, risk_score, status)

        save_detection_log(ear, mar, blink_count, perclos, pitch, risk_score, status)

    # ======================
    # FPS
    # ======================
    current = time.time()

    fps = int(1 / (current - prev_time))

    prev_time = current

    runtime = int(time.time() - start_time)

    # ======================
    # DISPLAY
    # ======================
    texts = [
        f"EAR: {ear:.2f}",
        f"MAR: {mar:.2f}",
        f"Blink: {blink_count}",
        f"PERCLOS: {perclos:.2f}",
        f"Pitch: {pitch:.1f}",
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

        y += 40

    cv2.imshow("AI Drowsiness Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
