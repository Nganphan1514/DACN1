import cv2
import time
import csv
import os
import queue
import threading

from datetime import datetime
from collections import deque

from config.ai_config import (
    AUTH_CHECK_INTERVAL,
    AUTH_MIN_HITS,
    AUTH_SCAN_SECONDS,
    CAMERA_INDEX,
    DANGEROUS_TIME_WARNING_INTERVAL,
    DROWSY_CONFIRM_TIME,
    DROWSY_THRESHOLD,
    DROWSY_WARNING_INTERVAL,
    EAR_THRESHOLD,
    FACE_MISSING_REAUTH_TIME,
    FATIGUE_WARNING_INTERVAL,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    HEAD_DOWN_CONFIRM_TIME,
    HEAD_DOWN_THRESHOLD,
    LONG_DRIVE_WARNING_INTERVAL,
    LOST_TIMEOUT,
    MAR_THRESHOLD,
    MIN_PERCLOS_FRAMES,
    PERCLOS_THRESHOLD,
    PITCH_LIMIT,
    REST_WARNING_INTERVAL,
    SAVE_INTERVAL,
    SNAPSHOT_INTERVAL,
    UNKNOWN_LOG_INTERVAL,
    UNKNOWN_TIMEOUT,
    WARNING_BEFORE_CLOSE,
    WINDOW_TITLE,
)
from core.drowsiness_analyzer import DrowsinessAnalyzer
from core.hud_renderer import render_hud
from detection.mediapipe_detector import detect_face_features
from detection.predictor import predict_proba_dict
from detection.head_pose import get_head_pose
from detection.eye_calibration import eye_calibrator
from config.vehicle_config import VEHICLE_ID, VEHICLE_NAME
from services.location_service import (
    get_cached_rest_stop,
    prefetch_nearest_rest_stop_async,
)
from services.realtime_client import push_realtime_alert

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
    lay_tai_xe_theo_id,
    kiem_tra_tai_xe_duoc_phan_cong_xe,
)

from alerts.snapshot import save_snapshot
from face_auth.recognize_driver import recognize_driver

from alerts.smart_voice import (
    driver_found_voice,
    fatigue_warning,
    drowsy_with_rest_warning,
    long_drive_warning,
    dangerous_time_warning,
    nearby_rest_warning,
    session_close_warning,
    unknown_driver_warning,
    wrong_vehicle_driver_warning,
    distraction_warning,
)


# THƯ MỤC / LOG

os.makedirs("logs", exist_ok=True)
os.makedirs("snapshots", exist_ok=True)

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


def save_log_csv(ear, mar, blink, perclos, pitch, risk_score, status):
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



# HANG DOI GHI DB NEN (CHONG LAG CAMERA)

_db_queue = queue.Queue(maxsize=100)


def _db_worker():
    while True:
        task = _db_queue.get()
        try:
            fn, args, kwargs = task
            fn(*args, **kwargs)
        except Exception as e:
            print("Async DB task error:", e)
        finally:
            _db_queue.task_done()


_db_worker_thread = threading.Thread(target=_db_worker, daemon=True)
_db_worker_thread.start()


def enqueue_db_task(fn, *args, **kwargs):
    try:
        _db_queue.put_nowait((fn, args, kwargs))
    except queue.Full:
        print("DB queue full, bo qua task de giu FPS")


# GỢI Ý ĐIỂM DỪNG (KHONG BLOCK CAMERA)

prefetch_nearest_rest_stop_async()


def lay_text_diem_dung():
    try:
        rest_stop = get_cached_rest_stop()

        if rest_stop:
            place_name = rest_stop["name"].split(",")[0]
            distance_km = rest_stop["distance_km"]
            return f"{place_name}, cách khoảng {distance_km} ki lô mét"

        return None

    except Exception as e:
        print("Loi lay diem dung:", e)
        return None



# RESET BỘ ĐẾM BUỒN NGỦ

analyzer = DrowsinessAnalyzer()


def reset_bo_dem_buon_ngu():
    analyzer.reset_counters()


def reset_calibration_va_nhan_dien():
    """
    Reset khi xe chuyển từ TẠM DỪNG sang CHẠY lại.

    Sau khi reset:
    - Chưa có khuôn mặt thì chưa đếm 3 giây.
    - Khi bắt được khuôn mặt mới calibration mắt 3 giây.
    - Trong 3 giây calibration chưa nhận diện tài xế và chưa chạy AI buồn ngủ.
    """
    global tai_xe_hien_tai
    global ten_tai_xe
    global driver_locked
    global nguoi_lai_hop_le
    global unknown_start_time
    global face_missing_start_time
    global last_auth_check_time
    global auth_scan_start_time
    global auth_hits
    global auth_driver_names
    global auth_done
    global auth_failed_logged

    eye_calibrator.reset()

    tai_xe_hien_tai = None
    ten_tai_xe = "CHUA XAC DINH"
    driver_locked = False
    nguoi_lai_hop_le = False
    unknown_start_time = None
    face_missing_start_time = None
    last_auth_check_time = 0
    auth_scan_start_time = None
    auth_hits = {}
    auth_driver_names = {}
    auth_done = False
    auth_failed_logged = False



def khoa_tai_xe_hop_le(tai_xe_id, ten_nhan_dien):
    """
    Khóa tài xế sau khi đã nhận diện ổn định trong AUTH_SCAN_SECONDS.
    Sau khi khóa, hệ thống không nhận diện lại liên tục nữa.
    """
    global tai_xe_hien_tai
    global ten_tai_xe
    global driver_locked
    global nguoi_lai_hop_le
    global phien_hien_tai
    global close_warning_spoken
    global auth_done

    tai_xe_hien_tai = tai_xe_id
    ten_tai_xe = ten_nhan_dien
    nguoi_lai_hop_le = True
    driver_locked = True
    auth_done = True

    phien = lay_phien_dang_lai(tai_xe_hien_tai)

    if phien:
        phien_hien_tai = phien["id"]
        reset_mat_dau(phien_hien_tai)
        close_warning_spoken = False
    else:
        phien_hien_tai = tao_phien_lai_xe(
            tai_xe_hien_tai,
            VEHICLE_ID,
        )
        print("Da tao phien moi")

    print(f"Da khoa tai xe: {ten_tai_xe}")
    driver_found_voice(ten_tai_xe)


def khoa_nguoi_lai_khong_hop_le(frame=None, ghi_chu="Nguoi lai chua xac thuc hoac khong co trong he thong"):
    """
    Chốt phiên hiện tại là người lái không hợp lệ.

    Quan trọng:
    - Không reset auth_scan_start_time.
    - Không đặt auth_done = False.
    - Nhờ vậy hệ thống KHÔNG chạy lại vòng nhận diện 3 giây liên tục.
    - Chỉ khi bấm phím 1 tạm dừng rồi phím 2 chạy lại mới reset và nhận diện lại.
    """
    global tai_xe_hien_tai
    global ten_tai_xe
    global driver_locked
    global nguoi_lai_hop_le
    global auth_done
    global auth_failed_logged
    global last_unknown_log

    tai_xe_hien_tai = None
    ten_tai_xe = "NGUOI LA / CHUA XAC THUC"
    nguoi_lai_hop_le = False
    driver_locked = True
    auth_done = True

    current_time = time.time()

    # Chỉ cảnh báo/lưu người lạ 1 lần cho mỗi lần xe chạy lại, tránh spam voice và snapshot.
    if not auth_failed_logged:
        unknown_driver_warning()

        if frame is not None and current_time - last_unknown_log > UNKNOWN_LOG_INTERVAL:
            duong_dan_anh = save_snapshot(frame)

            enqueue_db_task(
                luu_nguoi_la,
                xe_id=VEHICLE_ID,
                duong_dan_anh=duong_dan_anh,
                ghi_chu=ghi_chu,
            )
            enqueue_db_task(
                push_realtime_alert,
                event_type="NGUOI_LA",
                driver_name=ten_tai_xe,
                vehicle_name=VEHICLE_NAME,
                message=ghi_chu,
                snapshot_path=duong_dan_anh,
                risk_score=10,
            )

            last_unknown_log = current_time

        auth_failed_logged = True


def khoa_tai_xe_sai_xe(tai_xe_id, ten_nhan_dien, frame=None):
    """
    Nhận diện được người trong hệ thống nhưng người đó không thuộc xe mặc định hiện tại.

    Hành vi:
    - Chốt kết quả cho phiên chạy này là SAI XE.
    - Không nhận diện lại liên tục.
    - Cảnh báo sai xe và lưu vào mục người lái không hợp lệ.
    - Chỉ khi bấm phím 1 rồi phím 2 mới reset và nhận diện lại.
    """
    global tai_xe_hien_tai
    global ten_tai_xe
    global driver_locked
    global nguoi_lai_hop_le
    global auth_done
    global auth_failed_logged
    global last_unknown_log

    tai_xe_hien_tai = None
    ten_tai_xe = f"SAI XE: {ten_nhan_dien}"
    nguoi_lai_hop_le = False
    driver_locked = True
    auth_done = True

    current_time = time.time()

    if not auth_failed_logged:
        print(f"Tai xe sai xe: {ten_nhan_dien} - ID: {tai_xe_id}")
        wrong_vehicle_driver_warning(ten_nhan_dien)

        if frame is not None and current_time - last_unknown_log > UNKNOWN_LOG_INTERVAL:
            duong_dan_anh = save_snapshot(frame)

            enqueue_db_task(
                luu_nguoi_la,
                xe_id=VEHICLE_ID,
                duong_dan_anh=duong_dan_anh,
                ghi_chu=(
                    f"Nhan dien duoc {ten_nhan_dien} "
                    f"nhung tai xe nay khong duoc phan cong xe {VEHICLE_NAME}"
                ),
            )
            enqueue_db_task(
                push_realtime_alert,
                event_type="SAI_XE",
                driver_name=ten_nhan_dien,
                vehicle_name=VEHICLE_NAME,
                message=f"Tài xế {ten_nhan_dien} không được phân công xe {VEHICLE_NAME}",
                snapshot_path=duong_dan_anh,
                risk_score=10,
            )

            last_unknown_log = current_time

        auth_failed_logged = True



# CAMERA

print("Dang mo camera...", flush=True)

if os.name == "nt":
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(CAMERA_INDEX)
else:
    cap = cv2.VideoCapture(CAMERA_INDEX)

if not cap.isOpened():
    print("Khong mo duoc camera! Hay kiem tra quyen webcam hoac dong ung dung khac dang dung camera.", flush=True)
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
print("Da mo camera thanh cong! Nhan 1 (Dung), 2 (Chay), Q (Thoat).", flush=True)


# NGƯỠNG CÁ NHÂN SAU CALIBRATION

# EAR được chuẩn hoá bởi eye_calibrator trong 3 giây đầu sau khi bắt được mặt.
# Sau khi chuẩn hoá, vẫn dùng ngưỡng 0.20 để xét mắt nhắm.
personal_ear_threshold = EAR_THRESHOLD
personal_mar_threshold = MAR_THRESHOLD
personal_pitch_limit = PITCH_LIMIT


# TIME

start_time = time.time()
drive_start_time = time.time()
prev_time = time.time()


# TRẠNG THÁI XE

xe_dang_chay = True


# DRIVER AUTH

tai_xe_hien_tai = None
ten_tai_xe = "CHUA XAC DINH"

driver_locked = False
nguoi_lai_hop_le = False

phien_hien_tai = None
close_warning_spoken = False

unknown_start_time = None
last_unknown_log = 0

last_auth_check_time = 0

auth_scan_start_time = None
auth_hits = {}
auth_driver_names = {}

# True nghĩa là đã chốt kết quả nhận diện cho phiên xe đang chạy.
# Nếu nhận diện thất bại thì vẫn chốt là người lạ/không hợp lệ,
# không chạy lại vòng 3 giây liên tục. Chỉ bấm 1 rồi bấm 2 mới nhận diện lại.
auth_done = False
auth_failed_logged = False

face_missing_start_time = None


# COUNTER

blink_count = 0
drowsy_count = 0

last_drowsy_count_time = 0
drowsy_frames = 0
head_down_frames = 0
yawn_frames = 0

last_snapshot_time = 0

eye_closed = False
drowsy_start_time = None
head_down_start_time = None

last_saved_status = None
last_save_time = 0


# COOLDOWN CẢNH BÁO

last_fatigue_warning_time = 0
last_drowsy_warning_time = 0
last_rest_warning_time = 0
last_dangerous_time_warning_time = 0
last_long_drive_warning_time = 0


# PERCLOS

eye_window = deque(maxlen=300)



# MAIN LOOP

while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    # Frame sạch dùng riêng cho nhận diện tài xế.
    # Không dùng frame đã vẽ landmark để tránh làm giảm độ chính xác.
    frame_auth = frame.copy()

    h, w, _ = frame.shape

    status = "KHONG TIM THAY MAT"
    color = (255, 255, 255)

    risk_score = 0
    fatigue_score = analyzer.fatigue_score
    reasons = []
    ai_probs = {"awake": 100.0, "fatigue": 0.0, "drowsy": 0.0}
    blink_rate_per_min = 0
    yawn_count_3m = 0
    ear = 0
    mar = 0
    pitch = 0
    yaw = 0
    perclos = 0
    confidence = 0
    prediction = None
    is_real_drowsy = False
    left_ear = 0
    right_ear = 0
    face_landmarks = None

    
    # XE TẠM DỪNG
    
    # Khi xe tạm dừng thì KHÔNG detect face, KHÔNG nhận diện tài xế,
    # KHÔNG calibration và KHÔNG chạy AI buồn ngủ.
    if not xe_dang_chay:
        status = "XE DUNG"
        color = (0, 255, 255)

        reset_bo_dem_buon_ngu()

        cv2.putText(
            frame,
            "XE DANG TAM DUNG - KHONG NHAN DIEN KHUON MAT",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )

    else:

        
        # DETECT FACE
        
        face_landmarks, ear, mar, frame, left_ear, right_ear = detect_face_features(
            frame,
            return_eye_detail=True
        )
    
    # CALIBRATION 3 GIÂY ĐẦU
    
    if face_landmarks is not None and not eye_calibrator.ready:
        eye_calibrator.update(left_ear, right_ear)

        info = eye_calibrator.get_info()

        cv2.putText(
            frame,
            f"CALIBRATING EYES: {info['progress']}%",
            (30, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            "Nhin thang va mo mat binh thuong",
            (30, 175),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
        )

        cv2.imshow(WINDOW_TITLE, frame)

        key_calibration = cv2.waitKey(1) & 0xFF

        if key_calibration == ord("q"):
            break

        elif key_calibration == ord("1"):
            xe_dang_chay = False
            reset_bo_dem_buon_ngu()
            reset_calibration_va_nhan_dien()
            ten_tai_xe = "XE TAM DUNG"
            print("Da chuyen sang che do XE DUNG - tam dung calibration va nhan dien")

        continue
    
    # KHÔNG TÌM THẤY MẶT
    
    if xe_dang_chay and not face_landmarks:

        status = "KHONG TIM THAY MAT"
        color = (255, 255, 255)

        if face_missing_start_time is None:
            face_missing_start_time = time.time()

        # Khi đã khóa tài xế thì KHÔNG nhận diện lại chỉ vì mất mặt vài giây.
        # Tài xế chỉ được nhận diện lại khi bấm phím 1 tạm dừng rồi phím 2 chạy lại.

        # Nếu xe đang dừng thì không xử lý mất dấu phiên
        if xe_dang_chay and phien_hien_tai:

            phien = db.fetch_one(
                """
                SELECT *
                FROM phien_lai_xe
                WHERE id=%s
                """,
                (phien_hien_tai,),
            )

            if phien:

                if phien["thoi_diem_mat_dau"] is None:

                    cap_nhat_mat_dau(phien_hien_tai)

                else:

                    lost_seconds = (
                        datetime.now() - phien["thoi_diem_mat_dau"]
                    ).total_seconds()

                    remaining = LOST_TIMEOUT - lost_seconds

                    if remaining <= WARNING_BEFORE_CLOSE and not close_warning_spoken:
                        session_close_warning()
                        close_warning_spoken = True

                    if lost_seconds > LOST_TIMEOUT:

                        dong_phien_lai_xe(phien_hien_tai)

                        print("Da dong phien")

                        phien_hien_tai = None
                        driver_locked = False
                        nguoi_lai_hop_le = False
                        tai_xe_hien_tai = None
                        ten_tai_xe = "CHUA XAC DINH"
                        auth_done = False
                        close_warning_spoken = False

    
    # CÓ KHUÔN MẶT
    
    if face_landmarks:

        # Sau khi calibration xong mới chuẩn hoá EAR rồi mới nhận diện tài xế / chạy AI.
        if eye_calibrator.ready:
            ear = eye_calibrator.normalize_ear(left_ear, right_ear)

        face_missing_start_time = None

        # Tài xế quay lại thì reset mất dấu phiên
        if xe_dang_chay and phien_hien_tai:
            reset_mat_dau(phien_hien_tai)
            close_warning_spoken = False

        
        # NHẬN DIỆN TÀI XẾ TRONG VÀI GIÂY RỒI KHÓA
        
        current_auth_time = time.time()

        if not auth_done:

            # Bắt đầu scan đúng 1 lần sau khi calibration xong.
            # Không reset biến này khi nhận diện thất bại, nếu reset sẽ bị lặp 3 giây hoài.
            if auth_scan_start_time is None:
                auth_scan_start_time = current_auth_time
                auth_hits = {}
                auth_driver_names = {}
                last_auth_check_time = 0
                ten_tai_xe = "DANG NHAN DIEN TAI XE..."
                print(f"Bat dau nhan dien tai xe trong {AUTH_SCAN_SECONDS} giay")

            elapsed_auth = current_auth_time - auth_scan_start_time
            remaining_auth = max(0, AUTH_SCAN_SECONDS - elapsed_auth)

            # Trong thời gian scan, cứ mỗi AUTH_CHECK_INTERVAL giây nhận diện 1 lần.
            if elapsed_auth < AUTH_SCAN_SECONDS:

                if current_auth_time - last_auth_check_time >= AUTH_CHECK_INTERVAL:
                    last_auth_check_time = current_auth_time

                    # Nhận diện bằng frame sạch, không dùng frame đã vẽ landmark.
                    tai_xe_id_nhan_dien, similarity = recognize_driver(frame_auth)

                    print("MAIN FACE RESULT:", tai_xe_id_nhan_dien, similarity)

                    if tai_xe_id_nhan_dien:

                        thong_tin_tai_xe = lay_tai_xe_theo_id(tai_xe_id_nhan_dien)

                        if thong_tin_tai_xe:

                            ten_nhan_dien = thong_tin_tai_xe["ho_ten"]

                            # Đếm tất cả tài xế nhận diện được.
                            # Hết thời gian scan mới kiểm tra người đó có thuộc xe mặc định hay không.
                            auth_hits[tai_xe_id_nhan_dien] = auth_hits.get(tai_xe_id_nhan_dien, 0) + 1
                            auth_driver_names[tai_xe_id_nhan_dien] = ten_nhan_dien
                            ten_tai_xe = f"DANG NHAN DIEN: {ten_nhan_dien}"

                        else:
                            ten_tai_xe = "DANG NHAN DIEN / ID KHONG CO DB"

                    else:
                        ten_tai_xe = "DANG NHAN DIEN / CHUA XAC THUC"

            # Hết thời gian scan thì chốt đúng 1 lần.
            if elapsed_auth >= AUTH_SCAN_SECONDS:

                if auth_hits:
                    best_driver_id = max(auth_hits, key=auth_hits.get)
                    best_hits = auth_hits[best_driver_id]
                    best_name = auth_driver_names.get(best_driver_id, "TAI XE")

                    if best_hits >= AUTH_MIN_HITS:
                        la_tai_xe_dung_xe = kiem_tra_tai_xe_duoc_phan_cong_xe(
                            tai_xe_id=best_driver_id,
                            xe_id=VEHICLE_ID,
                        )

                        if la_tai_xe_dung_xe:
                            khoa_tai_xe_hop_le(best_driver_id, best_name)
                        else:
                            khoa_tai_xe_sai_xe(
                                tai_xe_id=best_driver_id,
                                ten_nhan_dien=best_name,
                                frame=frame_auth,
                            )
                    else:
                        khoa_nguoi_lai_khong_hop_le(
                            frame=frame_auth,
                            ghi_chu=(
                                f"Nhan dien khong on dinh trong {AUTH_SCAN_SECONDS} giay. "
                                f"Ung vien: {best_name}, so lan khop: {best_hits}"
                            ),
                        )

                else:
                    khoa_nguoi_lai_khong_hop_le(
                        frame=frame_auth,
                        ghi_chu=f"Khong xac thuc duoc nguoi lai sau {AUTH_SCAN_SECONDS} giay",
                    )

            # Trong lúc chưa chốt kết quả nhận diện thì chưa chạy AI buồn ngủ.
            if not auth_done:
                status = "DANG NHAN DIEN TAI XE"
                color = (0, 255, 255)

                cv2.putText(
                    frame,
                    f"DANG NHAN DIEN TAI XE: {max(0, int(remaining_auth + 1))}s",
                    (30, 140),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )

                cv2.putText(
                    frame,
                    "Nhan dien xong se khoa cho den khi xe tam dung/chay lai",
                    (30, 175),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )

                cv2.imshow(WINDOW_TITLE, frame)

                key_auth = cv2.waitKey(1) & 0xFF

                if key_auth == ord("q"):
                    break

                elif key_auth == ord("1"):
                    xe_dang_chay = False
                    status = "XE DUNG"
                    color = (0, 255, 255)

                    reset_bo_dem_buon_ngu()
                    reset_calibration_va_nhan_dien()
                    ten_tai_xe = "XE TAM DUNG"

                    print("Da chuyen sang che do XE DUNG - tam dung nhan dien khuon mat")

                continue

        # Nếu đã chốt là người lạ/không hợp lệ thì KHÔNG nhận diện lại nữa.
        # Hệ thống chỉ nhận diện lại khi bấm 1 tạm dừng rồi bấm 2 chạy lại.
        
        # HEAD POSE

        pitch, yaw = get_head_pose(face_landmarks, w, h)

        # TIME FACTOR

        now = time.time()
        current_hour = datetime.now().hour
        is_dangerous_hour = (0 <= current_hour <= 5) or (13 <= current_hour <= 15)
        drive_hours = (now - drive_start_time) / 3600.0
        is_long_drive = drive_hours > 2.0

        if is_dangerous_hour and (
            now - last_dangerous_time_warning_time >= DANGEROUS_TIME_WARNING_INTERVAL
        ):
            dangerous_time_warning()
            last_dangerous_time_warning_time = now

        if is_long_drive and (
            now - last_long_drive_warning_time >= LONG_DRIVE_WARNING_INTERVAL
        ):
            long_drive_warning()
            last_long_drive_warning_time = now

        # AI PREDICT (3-CLASS PROBABILITIES, TU DONG HO TRO 2 HOAC 5 DAC TRUNG)

        current_perclos = (
            sum(analyzer.eye_window) / len(analyzer.eye_window)
            if len(analyzer.eye_window) >= MIN_PERCLOS_FRAMES
            else 0.0
        )
        ai_out = predict_proba_dict(
            ear=ear,
            mar=mar,
            pitch=pitch,
            yaw=yaw,
            perclos=current_perclos,
        )
        prediction = ai_out["prediction"]
        confidence = ai_out["confidence"]

        # MULTI-FACTOR DRIVER STATE ENGINE

        analysis = analyzer.update(
            ear=ear,
            mar=mar,
            pitch=pitch,
            yaw=yaw,
            prediction=prediction,
            confidence=confidence,
            probs=ai_out["probs"],
            is_dangerous_hour=is_dangerous_hour,
            is_long_drive=is_long_drive,
            now=now,
        )

        status = analysis["status"]
        color = analysis["status_color"]
        fatigue_score = analysis["fatigue_score"]
        risk_score = analysis["risk_score"]
        is_real_drowsy = analysis["is_real_drowsy"]
        reasons = analysis["reasons"]
        perclos = analysis["perclos"]
        ai_probs = analysis["ai_probs"]
        blink_count = analysis["blink_count"]
        blink_rate_per_min = analysis["blink_rate_per_min"]
        yawn_count_3m = analysis["yawn_count_3m"]
        drowsy_count = analysis["drowsy_count"]

        # FINAL DECISION & ALERTS

        if status == "BUON NGU":

            if now - last_drowsy_warning_time >= DROWSY_WARNING_INTERVAL:

                rest_text = lay_text_diem_dung()
                drowsy_with_rest_warning(rest_text)

                reason_str = ", ".join(reasons) if reasons else "BUON NGU"
                enqueue_db_task(
                    push_realtime_alert,
                    event_type="BUON_NGU",
                    driver_name=ten_tai_xe,
                    vehicle_name=VEHICLE_NAME,
                    message=f"Tài xế {ten_tai_xe} buồn ngủ ({reason_str} | Fatigue {fatigue_score:.0f}%)",
                    snapshot_path=None,
                    risk_score=risk_score,
                )

                last_drowsy_warning_time = now
                last_rest_warning_time = now

            current_snapshot_time = time.time()
            duong_dan_anh = None

            if current_snapshot_time - last_snapshot_time > SNAPSHOT_INTERVAL:
                duong_dan_anh = save_snapshot(frame)
                last_snapshot_time = current_snapshot_time

            if duong_dan_anh:
                if nguoi_lai_hop_le and tai_xe_hien_tai:
                    enqueue_db_task(
                        luu_anh_canh_bao,
                        tai_xe_id=tai_xe_hien_tai,
                        xe_id=VEHICLE_ID,
                        duong_dan_anh=duong_dan_anh,
                    )
                else:
                    enqueue_db_task(
                        luu_nguoi_la,
                        xe_id=VEHICLE_ID,
                        duong_dan_anh=duong_dan_anh,
                        ghi_chu=(
                            f"Nguoi lai khong hop le co dau hieu buon ngu. "
                            f"Ten hien thi: {ten_tai_xe}"
                        ),
                    )

        elif status == "MAT TAP TRUNG":
            distraction_warning()

        elif status == "MET MOI":

            if now - last_fatigue_warning_time >= FATIGUE_WARNING_INTERVAL:
                fatigue_warning()
                last_fatigue_warning_time = now

            if now - last_rest_warning_time >= REST_WARNING_INTERVAL:
                rest_text = lay_text_diem_dung()
                if rest_text:
                    nearby_rest_warning(rest_text)
                else:
                    nearby_rest_warning(
                        "Không tìm thấy địa điểm cụ thể. Hãy tấp vào vị trí an toàn gần nhất."
                    )
                last_rest_warning_time = now

        # SAVE DATABASE THÔNG MINH

        current_time = time.time()
        should_save = False

        if status in ["MET MOI", "BUON NGU", "MAT TAP TRUNG"]:
            if status != last_saved_status:
                should_save = True
            elif current_time - last_save_time > SAVE_INTERVAL:
                should_save = True

        if should_save and tai_xe_hien_tai and nguoi_lai_hop_le:
            enqueue_db_task(
                save_detection_log,
                tai_xe_id=tai_xe_hien_tai,
                xe_id=VEHICLE_ID,
                status=status,
                ear=ear,
                mar=mar,
                risk_score=risk_score,
            )

            last_saved_status = status
            last_save_time = current_time

    # FPS

    current = time.time()
    fps = int(1 / max(current - prev_time, 0.0001))
    prev_time = current
    runtime = int(time.time() - start_time)

    # DISPLAY HUD

    render_hud(
        frame=frame,
        ten_tai_xe=ten_tai_xe,
        auth_done=auth_done,
        nguoi_lai_hop_le=nguoi_lai_hop_le,
        vehicle_name=VEHICLE_NAME,
        xe_dang_chay=xe_dang_chay,
        ear=ear,
        mar=mar,
        blink_count=blink_count,
        perclos=perclos,
        pitch=pitch,
        yaw=yaw,
        confidence=confidence,
        risk_score=risk_score,
        fatigue_score=fatigue_score,
        status=status,
        status_color=color,
        reasons=reasons,
        ai_probs=ai_probs,
        blink_rate_per_min=blink_rate_per_min,
        yawn_count_3m=yawn_count_3m,
        drowsy_count=drowsy_count,
        fps=fps,
        runtime=runtime,
    )

    cv2.imshow(WINDOW_TITLE, frame)

    
    # PHÍM ĐIỀU KHIỂN
    
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break

    elif key == ord("1"):

        xe_dang_chay = False
        status = "XE DUNG"
        color = (0, 255, 255)

        reset_bo_dem_buon_ngu()

        # Khi tạm dừng: không nhận diện khuôn mặt/tài xế ở các vòng lặp tiếp theo.
        reset_calibration_va_nhan_dien()
        ten_tai_xe = "XE TAM DUNG"

        print("Da chuyen sang che do XE DUNG - tam dung nhan dien khuon mat")

    elif key == ord("2"):

        xe_dang_chay = True
        drive_start_time = time.time()

        reset_bo_dem_buon_ngu()
        reset_calibration_va_nhan_dien()

        print("Da chuyen sang che do XE DANG CHAY - bat dau calibration lai khi thay khuon mat")


cap.release()
cv2.destroyAllWindows()
