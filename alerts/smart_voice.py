from alerts.voice_alert import speak_warning

import time

# ==========================
# COOLDOWN
# ==========================
last_drive_warning = 0
last_time_warning = 0
last_rest_warning = 0

DRIVE_COOLDOWN = 1800
TIME_COOLDOWN = 1800
REST_COOLDOWN = 600


# ==========================
# FATIGUE
# ==========================
def fatigue_warning():

    speak_warning("Bạn có dấu hiệu mệt mỏi. Hãy chú ý lái xe.")


# ==========================
# DROWSY
# ==========================
def drowsy_warning():

    speak_warning("Cảnh báo. Tài xế đang buồn ngủ. Hãy dừng nghỉ ngơi.")


# ==========================
# LONG DRIVE
# ==========================
def long_drive_warning():

    global last_drive_warning

    current = time.time()

    if current - last_drive_warning < DRIVE_COOLDOWN:
        return

    speak_warning("Bạn đã lái xe liên tục trong thời gian dài. Hãy nghỉ ngơi.")

    last_drive_warning = current


# ==========================
# DANGEROUS TIME
# ==========================
def dangerous_time_warning():

    global last_time_warning

    current = time.time()

    if current - last_time_warning < TIME_COOLDOWN:
        return

    speak_warning("Sắp tới khung giờ dễ buồn ngủ. Hãy chú ý.")

    last_time_warning = current


# ==========================
# REST STOP WARNING
# ==========================
def nearby_rest_warning():

    global last_rest_warning

    current = time.time()

    if current - last_rest_warning < REST_COOLDOWN:
        return

    speak_warning("Có trạm dừng nghỉ phía trước. Hãy nghỉ ngơi để đảm bảo an toàn.")

    last_rest_warning = current
