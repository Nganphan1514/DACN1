from collections import deque
import time

from config.ai_config import (
    DROWSY_CONFIRM_TIME,
    DROWSY_THRESHOLD,
    EAR_THRESHOLD,
    HEAD_DOWN_CONFIRM_TIME,
    HEAD_DOWN_THRESHOLD,
    MAR_THRESHOLD,
    MIN_PERCLOS_FRAMES,
    PERCLOS_THRESHOLD,
    PITCH_LIMIT,
)


class DrowsinessAnalyzer:
    """
    Bo phan tich trang thai tai xe da yeu to (4 cap do + Fatigue Score 0..100):
    - Ket hop xac suat 3 lop tu AI SVM (lam muot theo cua so truot 15 frame)
    - Theo doi nham mat keo dai, PERCLOS, tan suat chop mat/phut
    - Theo doi tan suat ngap that (>= 0.8s) trong 3 phut gan nhat
    - Theo doi guc dau (pitch) va mat tap trung / nhin lech duong (yaw)
    - Tinh diem met moi tich luy 0..100 co hoi phuc dan (hysteresis)
    """

    def __init__(
        self,
        ear_threshold=EAR_THRESHOLD,
        mar_threshold=MAR_THRESHOLD,
        pitch_limit=PITCH_LIMIT,
        yaw_limit=25.0,
        drowsy_threshold=DROWSY_THRESHOLD,
        head_down_threshold=HEAD_DOWN_THRESHOLD,
        perclos_threshold=PERCLOS_THRESHOLD,
        min_perclos_frames=MIN_PERCLOS_FRAMES,
        drowsy_confirm_time=DROWSY_CONFIRM_TIME,
        head_down_confirm_time=HEAD_DOWN_CONFIRM_TIME,
        distraction_confirm_time=2.5,
        yawn_confirm_time=0.8,
    ):
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        self.pitch_limit = pitch_limit
        self.yaw_limit = yaw_limit
        self.drowsy_threshold = drowsy_threshold
        self.head_down_threshold = head_down_threshold
        self.perclos_threshold = perclos_threshold
        self.min_perclos_frames = min_perclos_frames
        self.drowsy_confirm_time = drowsy_confirm_time
        self.head_down_confirm_time = head_down_confirm_time
        self.distraction_confirm_time = distraction_confirm_time
        self.yawn_confirm_time = yawn_confirm_time

        self.eye_window = deque(maxlen=300)
        self.prob_window = deque(maxlen=15)
        self.blink_timestamps = deque()
        self.yawn_timestamps = deque()

        self.blink_count = 0
        self.drowsy_count = 0
        self.last_drowsy_count_time = 0.0
        self.fatigue_score = 0.0
        self.reset_counters()

    def reset_counters(self):
        self.drowsy_frames = 0
        self.head_down_frames = 0
        self.yawn_frames = 0
        self.drowsy_start_time = None
        self.head_down_start_time = None
        self.yawn_start_time = None
        self.yawn_counted_current = False
        self.distraction_start_time = None
        self.eye_closed = False
        self.eye_window.clear()
        self.prob_window.clear()
        self.fatigue_score = 0.0

    def _prune_old_timestamps(self, now):
        while self.blink_timestamps and (now - self.blink_timestamps[0]) > 60.0:
            self.blink_timestamps.popleft()
        while self.yawn_timestamps and (now - self.yawn_timestamps[0]) > 180.0:
            self.yawn_timestamps.popleft()

    def update(
        self,
        ear,
        mar,
        pitch,
        yaw=0.0,
        prediction=None,
        confidence=0.0,
        probs=None,
        is_dangerous_hour=False,
        is_long_drive=False,
        now=None,
    ):
        now = time.time() if now is None else now
        self._prune_old_timestamps(now)

        # 1. Head down (Pitch)
        if pitch > self.pitch_limit:
            self.head_down_frames += 1
            if self.head_down_start_time is None:
                self.head_down_start_time = now
        else:
            self.head_down_frames = 0
            self.head_down_start_time = None

        # 2. Distraction / Looking away (Yaw)
        if abs(yaw) > self.yaw_limit:
            if self.distraction_start_time is None:
                self.distraction_start_time = now
        else:
            self.distraction_start_time = None

        distraction_duration = (
            (now - self.distraction_start_time)
            if self.distraction_start_time is not None
            else 0.0
        )
        is_distracted = distraction_duration >= self.distraction_confirm_time

        # 3. Blink & Eye closed duration
        if ear < self.ear_threshold:
            self.eye_window.append(1)
            if not self.eye_closed:
                self.eye_closed = True
                self.blink_count += 1
                self.blink_timestamps.append(now)
            self.drowsy_frames += 1
            if self.drowsy_start_time is None:
                self.drowsy_start_time = now
        else:
            self.eye_window.append(0)
            self.eye_closed = False
            self.drowsy_frames = 0
            self.drowsy_start_time = None

        eye_closed_duration = (
            (now - self.drowsy_start_time) if self.drowsy_start_time is not None else 0.0
        )

        # 4. PERCLOS
        if len(self.eye_window) >= self.min_perclos_frames:
            perclos = sum(self.eye_window) / len(self.eye_window)
        else:
            perclos = 0.0

        # 5. Yawn duration & frequency (trong 3 phut gan nhat)
        if mar > self.mar_threshold:
            self.yawn_frames += 1
            if self.yawn_start_time is None:
                self.yawn_start_time = now
                self.yawn_counted_current = False
            elif (
                not self.yawn_counted_current
                and (now - self.yawn_start_time) >= self.yawn_confirm_time
            ):
                self.yawn_timestamps.append(now)
                self.yawn_counted_current = True
        else:
            self.yawn_frames = 0
            self.yawn_start_time = None
            self.yawn_counted_current = False

        blink_rate_per_min = len(self.blink_timestamps)
        yawn_count_3m = len(self.yawn_timestamps)

        # 6. Lam muot xac suat 3 lop tu AI SVM
        if isinstance(probs, dict):
            p0 = float(probs.get(0, 0.0))
            p1 = float(probs.get(1, 0.0))
            p2 = float(probs.get(2, 0.0))
        elif prediction == 2:
            p2 = confidence / 100.0
            p0, p1 = max(0.0, 1.0 - p2), 0.0
        elif prediction == 1:
            p1 = confidence / 100.0
            p0, p2 = max(0.0, 1.0 - p1), 0.0
        else:
            p0, p1, p2 = 1.0, 0.0, 0.0

        self.prob_window.append((p0, p1, p2))
        n_probs = len(self.prob_window)
        avg_p_awake = sum(x[0] for x in self.prob_window) / n_probs
        avg_p_fatigue = sum(x[1] for x in self.prob_window) / n_probs
        avg_p_drowsy = sum(x[2] for x in self.prob_window) / n_probs

        # 7. Xac dinh cac dieu kien nguy hiem & ly do cu the
        reasons = []

        eye_closed_long_enough = (
            self.drowsy_start_time is not None
            and eye_closed_duration >= self.drowsy_confirm_time
            and self.drowsy_frames >= self.drowsy_threshold
        )
        head_down_long_enough = (
            self.head_down_start_time is not None
            and (now - self.head_down_start_time) >= self.head_down_confirm_time
            and self.head_down_frames >= self.head_down_threshold
        )
        perclos_danger = (
            len(self.eye_window) >= self.min_perclos_frames
            and perclos >= self.perclos_threshold
            and self.drowsy_frames >= 10
        )
        ai_drowsy_confirmed = (
            avg_p_drowsy >= 0.65 and self.drowsy_frames >= 10
        )

        if eye_closed_long_enough:
            reasons.append("NHAM MAT LAU")
        if head_down_long_enough:
            reasons.append("GUC DAU")
        if perclos_danger:
            reasons.append("PERCLOS CAO")
        if ai_drowsy_confirmed:
            reasons.append("AI BUON NGU")
        if yawn_count_3m >= 2 or self.yawn_frames > 12:
            reasons.append("NGAP LIEN TUC")
        if blink_rate_per_min >= 26:
            reasons.append("CHOP MAT DAY")
        if avg_p_fatigue >= 0.55 and "NGAP LIEN TUC" not in reasons:
            reasons.append("AI MET MOI")
        if is_distracted:
            reasons.append("MAT TAP TRUNG")

        is_real_drowsy = (
            eye_closed_long_enough
            or head_down_long_enough
            or perclos_danger
            or ai_drowsy_confirmed
        )

        # 8. Cap nhat Fatigue Score 0..100 (co tich luy va hoi phuc dan)
        delta = 0.0
        if is_real_drowsy:
            delta += 12.0
        elif eye_closed_duration >= 0.45:
            delta += 3.0

        if avg_p_drowsy >= 0.50:
            delta += avg_p_drowsy * 4.5
        if avg_p_fatigue >= 0.45:
            delta += avg_p_fatigue * 2.5
        if len(self.eye_window) >= self.min_perclos_frames and perclos > 0.30:
            delta += perclos * 4.0
        if self.yawn_frames > 10 or yawn_count_3m >= 2:
            delta += 1.8
        if blink_rate_per_min >= 26:
            delta += 1.0
        if is_dangerous_hour:
            delta += 0.3
        if is_long_drive:
            delta += 0.4

        if delta > 0:
            self.fatigue_score = min(100.0, self.fatigue_score + delta)
        else:
            # Hoi phuc tu tu khi tai xe tinh tao tro lai (tranh nhay ve 0 ngay lap tuc)
            self.fatigue_score = max(0.0, self.fatigue_score - 1.2)

        if is_real_drowsy and self.fatigue_score < 70.0:
            self.fatigue_score = 70.0

        # 9. Phan loai 4 trang thai + risk_score tuong thich DB (0..10)
        risk_score = int(round(self.fatigue_score / 10.0))

        if is_real_drowsy or self.fatigue_score >= 65.0:
            status = "BUON NGU"
            status_color = (0, 0, 255)
            is_real_drowsy = True
        elif is_distracted:
            status = "MAT TAP TRUNG"
            status_color = (0, 215, 255)
        elif (
            self.fatigue_score >= 30.0
            or yawn_count_3m >= 2
            or avg_p_fatigue >= 0.55
            or self.yawn_frames > 10
        ):
            status = "MET MOI"
            status_color = (0, 165, 255)
        else:
            status = "TINH TAO"
            status_color = (0, 255, 0)

        if is_real_drowsy and (now - self.last_drowsy_count_time) > 5.0:
            self.drowsy_count += 1
            self.last_drowsy_count_time = now

        return {
            "status": status,
            "status_color": status_color,
            "fatigue_score": round(self.fatigue_score, 1),
            "risk_score": risk_score,
            "is_real_drowsy": is_real_drowsy,
            "is_distracted": is_distracted,
            "reasons": reasons,
            "perclos": perclos,
            "drowsy_frames": self.drowsy_frames,
            "head_down_frames": self.head_down_frames,
            "yawn_frames": self.yawn_frames,
            "blink_count": self.blink_count,
            "blink_rate_per_min": blink_rate_per_min,
            "yawn_count_3m": yawn_count_3m,
            "drowsy_count": self.drowsy_count,
            "ai_probs": {
                "awake": round(avg_p_awake * 100.0, 1),
                "fatigue": round(avg_p_fatigue * 100.0, 1),
                "drowsy": round(avg_p_drowsy * 100.0, 1),
            },
        }
