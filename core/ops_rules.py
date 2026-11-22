"""
Pure business/operational rules (zero DB/native dependencies) for P0+ upgrades:
- Alert lifecycle state machine transitions (REV-08)
- 3-level camera device health classification (REV-13)
- Sensitive ID masking for CCCD/GPLX display (REV-06)
"""

TRANG_THAI_CANH_BAO_HOP_LE = {
    "MOI",
    "DA_TIEP_NHAN",
    "DANG_XU_LY",
    "DA_DONG",
    "CANH_BAO_SAI",
}

ALERT_ALLOWED_TRANSITIONS = {
    "MOI": {"DA_TIEP_NHAN", "DANG_XU_LY", "DA_DONG", "CANH_BAO_SAI"},
    "DA_TIEP_NHAN": {"DANG_XU_LY", "DA_DONG", "CANH_BAO_SAI"},
    "DANG_XU_LY": {"DA_DONG", "CANH_BAO_SAI"},
    "DA_DONG": set(),
    "CANH_BAO_SAI": set(),
}


def kiem_tra_chuyen_trang_thai_canh_bao(current_status, new_status):
    if new_status not in TRANG_THAI_CANH_BAO_HOP_LE:
        return False
    allowed = ALERT_ALLOWED_TRANSITIONS.get(current_status, set())
    return new_status in allowed


def phan_loai_suc_khoe_thiet_bi(
    seconds_since_seen,
    camera_ok=True,
    fps=0.0,
    outbox_pending=0,
    dead_letter_count=0,
    online_timeout_seconds=60,
):
    secs = float(seconds_since_seen if seconds_since_seen is not None else 9999)
    if secs > online_timeout_seconds:
        return "OFFLINE"
    if (
        not bool(camera_ok)
        or float(fps or 0.0) < 8.0
        or int(outbox_pending or 0) > 0
        or int(dead_letter_count or 0) > 0
    ):
        return "ONLINE_DEGRADED"
    return "ONLINE_HEALTHY"


def mask_sensitive_id(value):
    text = str(value or "").strip()
    if len(text) <= 4:
        return text
    if len(text) <= 7:
        return text[:2] + ("*" * (len(text) - 4)) + text[-2:]
    return text[:3] + ("*" * (len(text) - 6)) + text[-3:]
