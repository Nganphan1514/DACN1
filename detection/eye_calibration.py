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

    def __init__(
        self,
        duration=3.0,
        reference_ear=0.30,
        min_samples=20,
        min_scale=0.75,
        max_scale=1.50,
    ):
        self.duration = duration
        self.reference_ear = reference_ear
        self.min_samples = min_samples
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.reset()

    @staticmethod
    def _percentile(samples, pct=75.0):
        ordered = sorted(samples)
        if not ordered:
            return 0.0
        idx = int(round((pct / 100.0) * (len(ordered) - 1)))
        idx = max(0, min(len(ordered) - 1, idx))
        return ordered[idx]

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
            # AI-01: Dung phan vi 75% de loai bo frame chop mat / nheo mat trong 3s dau
            self.left_baseline = self._percentile(self.left_samples, 75.0)
            self.right_baseline = self._percentile(self.right_samples, 75.0)
            self.ready = True

            print("Eye calibration done (p75)")
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

        # AI-01: Kep he so scale trong [min_scale, max_scale] tranh nheo mat pha hong nguong
        scale = self.reference_ear / baseline
        scale = max(self.min_scale, min(self.max_scale, scale))
        return ear * scale

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
