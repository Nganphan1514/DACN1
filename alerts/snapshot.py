import cv2
import time
import os

from datetime import datetime


# COOLDOWN

last_snapshot_time = 0
snapshot_delay = 8



# SAVE SNAPSHOT

def save_snapshot(frame):

    global last_snapshot_time

    try:

        
        # Kiểm tra frame
        
        if frame is None:

            print("Frame rong, khong the chup anh")

            return None

        current_time = time.time()

        
        # Cooldown
        
        if current_time - last_snapshot_time < snapshot_delay:

            return None

        
        # Tạo folder snapshots
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        snapshot_folder = os.path.join(base_dir, "snapshots")

        os.makedirs(snapshot_folder, exist_ok=True)

        
        # Tạo tên file
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_name = os.path.join(snapshot_folder, f"drowsy_{timestamp}.jpg")

        
        # Lưu ảnh
        
        success = cv2.imwrite(file_name, frame)

        if not success:

            print("Khong luu duoc snapshot")

            return None

        last_snapshot_time = current_time

        print(f"Da luu snapshot: {file_name}")

        return file_name

    except Exception as e:

        print("Loi snapshot:", e)

        return None
