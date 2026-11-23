"""
DACN1 V3.1 - FIX-06: Silent Re-verification Guard chong doi nguoi lai giua chuyen.
Pure stateful logic (khong phu thuoc DB/OpenCV), de unit test va tich hop vao main.py.
"""


class ReauthGuard:
    """
    Kich hoat tai xac thuc nen (Silent Re-verification) khi:
    1. Mat khuon mat lien tuc >= missing_trigger_sec (mac dinh 60s) roi thay lai mat.
    2. Dinh ky moi reauth_interval_sec (mac dinh 900s = 15 phut).
    Chi kiem tra khi khuon mat nhin thang (|yaw| < 20, |pitch| < 15).
    Yeu cau consecutive_mismatch_limit (3) lan lien tiep khong khop moi phat canh bao
    DRIVER_CHANGED_MID_TRIP de chong bao sai.
    """

    def __init__(
        self,
        missing_trigger_sec=60.0,
        reauth_interval_sec=900.0,
        max_yaw=20.0,
        max_pitch=15.0,
        consecutive_mismatch_limit=3,
    ):
        self.missing_trigger_sec = float(missing_trigger_sec)
        self.reauth_interval_sec = float(reauth_interval_sec)
        self.max_yaw = float(max_yaw)
        self.max_pitch = float(max_pitch)
        self.consecutive_mismatch_limit = int(consecutive_mismatch_limit)

        self.last_reauth_time = 0.0
        self.face_missing_since = None
        self.pending_reauth = False
        self.consecutive_mismatches = 0
        self.alert_triggered = False

    def reset(self, now=0.0):
        self.last_reauth_time = float(now)
        self.face_missing_since = None
        self.pending_reauth = False
        self.consecutive_mismatches = 0
        self.alert_triggered = False

    def on_face_missing(self, now):
        if self.face_missing_since is None:
            self.face_missing_since = float(now)
        elif (float(now) - self.face_missing_since) >= self.missing_trigger_sec:
            self.pending_reauth = True

    def should_check_face(self, now, yaw=0.0, pitch=0.0):
        now = float(now)
        self.face_missing_since = None

        if (now - self.last_reauth_time) >= self.reauth_interval_sec:
            self.pending_reauth = True

        if not self.pending_reauth:
            return False

        # Chong bao sai: chi trich xuat 128D khi mat nhin thang
        if abs(float(yaw)) >= self.max_yaw or abs(float(pitch)) >= self.max_pitch:
            return False

        return True

    def record_verification_result(self, expected_driver_id, matched_driver_id, now):
        """
        Ghi nhan ket qua so khop 1 frame.
        Tra ve 'DRIVER_CHANGED_MID_TRIP' neu 3 lan lien tiep khong khop; nguoc lai tra None.
        """
        now = float(now)
        if matched_driver_id is not None and int(matched_driver_id) == int(expected_driver_id):
            self.consecutive_mismatches = 0
            self.pending_reauth = False
            self.alert_triggered = False
            self.last_reauth_time = now
            return None

        self.consecutive_mismatches += 1
        if self.consecutive_mismatches >= self.consecutive_mismatch_limit:
            self.alert_triggered = True
            self.pending_reauth = False
            self.last_reauth_time = now
            return "DRIVER_CHANGED_MID_TRIP"
        return None
