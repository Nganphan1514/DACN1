from alerts.voice_alert import speak_warning
import time


# COOLDOWN

last_driver_found = 0
last_fatigue_warning = 0
last_drowsy_warning = 0
last_drive_warning = 0
last_time_warning = 0
last_rest_warning = 0
last_close_warning = 0
last_unknown_warning = 0
UNKNOWN_COOLDOWN = 60


# COOLDOWN TIME

FOUND_COOLDOWN = 60

FATIGUE_COOLDOWN = 25

DROWSY_COOLDOWN = 12

DRIVE_COOLDOWN = 1800

TIME_COOLDOWN = 3600

REST_COOLDOWN = 300

CLOSE_WARNING_COOLDOWN = 60



# SAFE SPEAK

def safe_speak(message):

    try:

        speak_warning(message)

    except Exception as e:

        print("Voice error:", e)



# TIM THAY TAI XE

def driver_found_voice(driver_name):

    global last_driver_found

    current = time.time()

    if current - last_driver_found < FOUND_COOLDOWN:

        return

    safe_speak(f"Đã nhận diện tài xế " f"{driver_name}. " f"Chúc bạn lái xe an toàn.")

    last_driver_found = current



# FATIGUE

def fatigue_warning():

    global last_fatigue_warning

    current = time.time()

    if current - last_fatigue_warning < FATIGUE_COOLDOWN:

        return

    safe_speak("Bạn có dấu hiệu mệt mỏi. " "Hãy chú ý lái xe.")

    last_fatigue_warning = current



# REST STOP

def nearby_rest_warning(place_name=None):

    global last_rest_warning

    current = time.time()

    if current - last_rest_warning < REST_COOLDOWN:

        return

    
    # CO DIA DIEM CU THE
    
    if place_name:

        safe_speak(f"Khuyến nghị nghỉ ngơi. " f"Gần đây có " f"{place_name}")

    
    # KHONG TIM THAY
    
    else:

        safe_speak(
            "Khuyến nghị nghỉ ngơi. "
            "Có trạm nghỉ "
            "hoặc cây xăng "
            "gần nhất phía trước."
        )

    last_rest_warning = current



# DROWSY

def drowsy_warning():

    global last_drowsy_warning

    current = time.time()

    if current - last_drowsy_warning < DROWSY_COOLDOWN:

        return

    safe_speak("Cảnh báo. " "Tài xế đang buồn ngủ. " "Hãy dừng xe " "nghỉ ngơi ngay.")

    last_drowsy_warning = current



# LONG DRIVE

def long_drive_warning():

    global last_drive_warning

    current = time.time()

    if current - last_drive_warning < DRIVE_COOLDOWN:

        return

    safe_speak(
        "Bạn đã lái xe liên tục "
        "trong thời gian dài. "
        "Hãy nghỉ ngơi để "
        "đảm bảo an toàn."
    )

    last_drive_warning = current



# DANGEROUS TIME

def dangerous_time_warning():

    global last_time_warning

    current = time.time()

    if current - last_time_warning < TIME_COOLDOWN:

        return

    safe_speak("Đây là khung giờ " "dễ gây buồn ngủ. " "Hãy chú ý giữ tỉnh táo.")

    last_time_warning = current



# SESSION CLOSE WARNING

def session_close_warning():

    global last_close_warning

    current = time.time()

    if current - last_close_warning < CLOSE_WARNING_COOLDOWN:

        return

    safe_speak("Còn một phút nữa " "hệ thống sẽ tự động " "kết thúc phiên làm việc.")

    last_close_warning = current


def unknown_driver_warning():

    global last_unknown_warning

    current = time.time()

    if current - last_unknown_warning < UNKNOWN_COOLDOWN:

        return

    safe_speak("Cảnh báo. " "Tài xế chưa xác thực. " "Vui lòng đăng nhập hệ thống.")


    last_unknown_warning = current

# DROWSY + REST WARNING

def drowsy_with_rest_warning(place_name=None):
    """
    Cảnh báo buồn ngủ kèm gợi ý điểm dừng nghỉ.
    Hàm này được main.py import trực tiếp.
    """

    drowsy_warning()

    if place_name:
        nearby_rest_warning(place_name)
    else:
        nearby_rest_warning()



# WRONG VEHICLE DRIVER

last_wrong_vehicle_warning = 0
WRONG_VEHICLE_COOLDOWN = 60


def wrong_vehicle_driver_warning(driver_name=None):
    """
    Cảnh báo khi nhận diện được tài xế
    nhưng tài xế không được phân công cho xe hiện tại.
    """

    global last_wrong_vehicle_warning

    current = time.time()

    if current - last_wrong_vehicle_warning < WRONG_VEHICLE_COOLDOWN:
        return

    if driver_name:
        safe_speak(f"Cảnh báo. Tài xế {driver_name} không được phân công cho xe này.")
    else:
        safe_speak("Cảnh báo. Tài xế không được phân công cho xe này.")

    last_wrong_vehicle_warning = current


# DISTRACTION WARNING

last_distraction_warning = 0
DISTRACTION_COOLDOWN = 15


def distraction_warning():
    global last_distraction_warning

    current = time.time()
    if current - last_distraction_warning < DISTRACTION_COOLDOWN:
        return

    safe_speak("Cảnh báo. Bạn đang mất tập trung. Hãy chú ý quan sát phía trước.")
    last_distraction_warning = current
