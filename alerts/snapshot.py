import cv2
import time
from datetime import datetime

last_snapshot_time = 0
snapshot_delay = 8


def save_snapshot(frame):

    global last_snapshot_time

    current_time = time.time()

    # cooldown chống chụp liên tục
    if (
        current_time
        - last_snapshot_time
        < snapshot_delay
    ):
        return

    file_name = (
        "snapshots/"
        f"drowsy_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    )

    cv2.imwrite(
        file_name,
        frame
    )

    last_snapshot_time = (
        current_time
    )