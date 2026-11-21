import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts.voice_alert import speak_warning

speak_warning("Cảnh báo. Tài xế đang buồn ngủ. Hãy dừng nghỉ ngơi.")

input("Press Enter to exit...")
