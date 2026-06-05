import time
from collections import deque


class EyeCalibration:
    """
    Calibration chỉ số mắt theo từng tài xế.

    Luồng xử lý:
    - Khi chưa bắt được khuôn mặt: không đếm thời gian calibration.
    - Khi bắt được khuôn mặt: bắt đầu lấy EAR mắt trái/phải trong 3 giây.
    - Sau 3 giây: tạo baseline mắt riêng của tài xế.
    - Khi chạy realtime: chuẩn hoá EAR theo baseline để giảm lỗi mắt híp/mắt nhỏ.
    """

    def __init__(self, duration=3.0, reference_ear=0.30, min_samples=20):
        self.duration = duration
        self.reference_ear = reference_ear
        self.min_samples = min_samples
        self.reset()

    def reset(self):
        self.start_time = None
        self.left_samples = deque()
        self.right_samples = deque()
        self.left_baseline = None
        self.right_baseline = None
        self.ready = False

    def update(self, left_ear, right_ear):
        """
        Chỉ gọi hàm này khi đã bắt được khuôn mặt.
        Vì vậy 3 giây calibration chỉ bắt đầu sau khi có face_landmarks.
        """
        if self.ready:
            return True

        if self.start_time is None:
            self.start_time = time.time()

        if left_ear and right_ear and left_ear > 0 and right_ear > 0:
            self.left_samples.append(float(left_ear))
            self.right_samples.append(float(right_ear))

        elapsed = time.time() - self.start_time

        if elapsed >= self.duration and len(self.left_samples) >= self.min_samples:
            self.left_baseline = sum(self.left_samples) / len(self.left_samples)
            self.right_baseline = sum(self.right_samples) / len(self.right_samples)
            self.ready = True

            print("Eye calibration done")
            print("Left EAR baseline:", round(self.left_baseline, 4))
            print("Right EAR baseline:", round(self.right_baseline, 4))

        return self.ready

    def progress_percent(self):
        if self.ready:
            return 100

        if self.start_time is None:
            return 0

        elapsed = time.time() - self.start_time
        return min(99, int((elapsed / self.duration) * 100))

    def normalize_eye(self, ear, baseline):
        if not self.ready or not baseline or baseline <= 0:
            return ear

        return ear / baseline * self.reference_ear

    def normalize_ear(self, left_ear, right_ear):
        if not self.ready:
            return round((left_ear + right_ear) / 2, 4)

        left_norm = self.normalize_eye(left_ear, self.left_baseline)
        right_norm = self.normalize_eye(right_ear, self.right_baseline)

        return round((left_norm + right_norm) / 2, 4)

    def get_info(self):
        return {
            "ready": self.ready,
            "progress": self.progress_percent(),
            "left_baseline": (
                round(self.left_baseline, 4) if self.left_baseline else None
            ),
            "right_baseline": (
                round(self.right_baseline, 4) if self.right_baseline else None
            ),
        }


eye_calibrator = EyeCalibration(duration=3.0, reference_ear=0.30, min_samples=20)
