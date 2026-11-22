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


# ============================================================
# V3.0 - RBAC 6 VAI TRO & DATA SCOPE RULES (PURE FUNCTIONS)
# ============================================================

ROLE_ADMIN_HE_THONG = "admin_he_thong"
ROLE_QUAN_TRI_CONG_TY = "quan_tri_cong_ty"
ROLE_QUAN_LY = "quan_ly"
ROLE_DIEU_PHOI_VIEN = "dieu_phoi_vien"
ROLE_GIAM_SAT = "giam_sat"
ROLE_TAI_XE = "tai_xe"

VALID_ROLES = {
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
    ROLE_DIEU_PHOI_VIEN,
    ROLE_GIAM_SAT,
    ROLE_TAI_XE,
}

ROLE_LABELS = {
    ROLE_ADMIN_HE_THONG: "Quản trị hệ thống",
    ROLE_QUAN_TRI_CONG_TY: "Quản trị công ty",
    ROLE_QUAN_LY: "Quản lý chi nhánh / đội xe",
    ROLE_DIEU_PHOI_VIEN: "Điều phối viên",
    ROLE_GIAM_SAT: "Nhân viên giám sát",
    ROLE_TAI_XE: "Tài xế",
}

# Nhom vai tro duoc vao Web Quan tri
ADMIN_PANEL_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
    ROLE_DIEU_PHOI_VIEN,
    ROLE_GIAM_SAT,
)

# Quan ly to chuc cap Cong ty / Chi nhanh
ORG_ADMIN_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
)

# Quan ly doi xe, tai xe, xe
FLEET_MANAGE_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
)

# Xem danh sach tai xe / xe / doi xe
FLEET_VIEW_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
    ROLE_DIEU_PHOI_VIEN,
    ROLE_GIAM_SAT,
)

# Dieu phoi lich trinh (phan cong tai xe & phuong tien)
DISPATCH_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
    ROLE_DIEU_PHOI_VIEN,
)

# Theo doi chuyen di realtime, camera & su kien AI
MONITOR_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
    ROLE_GIAM_SAT,
)

# Xac minh su kien AI -> vi pham, xu ly khieu nai, ket thuc chuyen ngoai le
MANAGER_CONTROL_ROLES = (
    ROLE_QUAN_LY,
    ROLE_QUAN_TRI_CONG_TY,
)

# Xem nhat ky kiem toan (Audit Log)
AUDIT_VIEW_ROLES = (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    ROLE_QUAN_LY,
)


def la_vai_tro_hop_le(vai_tro):
    return str(vai_tro or "").strip() in VALID_ROLES


def xac_dinh_cap_pham_vi(vai_tro):
    """
    Tra ve cap pham vi du lieu cua tung vai tro:
    - 'SYSTEM': admin_he_thong (toan he thong)
    - 'COMPANY': quan_tri_cong_ty (toan cong ty)
    - 'UNIT': quan_ly, dieu_phoi_vien, giam_sat (chi nhanh hoac doi xe phu trach)
    - 'SELF': tai_xe (chi du lieu ca nhan)
    """
    role = str(vai_tro or "").strip()
    if role == ROLE_ADMIN_HE_THONG:
        return "SYSTEM"
    if role == ROLE_QUAN_TRI_CONG_TY:
        return "COMPANY"
    if role in (ROLE_QUAN_LY, ROLE_DIEU_PHOI_VIEN, ROLE_GIAM_SAT):
        return "UNIT"
    return "SELF"


def co_quyen_trong_pham_vi(user_scope, target_scope):
    """
    Kiem tra nguoi dung (user_scope) co quyen truy cap ban ghi (target_scope)
    theo nguyen tac Data Scope V3.0 hay khong.
    user_scope / target_scope gom: vai_tro, cong_ty_id, chi_nhanh_id, doi_xe_id, tai_xe_id.
    """
    if not isinstance(user_scope, dict):
        return False
    role = user_scope.get("vai_tro")
    if not la_vai_tro_hop_le(role):
        return False

    level = xac_dinh_cap_pham_vi(role)
    if level == "SYSTEM":
        return True

    if not isinstance(target_scope, dict):
        return False

    if level == "SELF":
        u_tx = user_scope.get("tai_xe_id")
        t_tx = target_scope.get("tai_xe_id")
        return u_tx is not None and t_tx is not None and int(u_tx) == int(t_tx)

    u_cty = user_scope.get("cong_ty_id")
    t_cty = target_scope.get("cong_ty_id")
    if u_cty is not None and t_cty is not None and int(u_cty) != int(t_cty):
        return False

    if level == "COMPANY":
        return u_cty is None or t_cty is None or int(u_cty) == int(t_cty)

    # level == 'UNIT' (quan_ly, dieu_phoi_vien, giam_sat)
    u_dx = user_scope.get("doi_xe_id")
    t_dx = target_scope.get("doi_xe_id")
    if u_dx is not None:
        return t_dx is not None and int(u_dx) == int(t_dx)

    u_cn = user_scope.get("chi_nhanh_id")
    t_cn = target_scope.get("chi_nhanh_id")
    if u_cn is not None:
        return t_cn is not None and int(u_cn) == int(t_cn)

    # Truong hop tai khoan quan_ly cu chua gan chi_nhanh_id/doi_xe_id thi fallback theo cong_ty_id
    return u_cty is None or t_cty is None or int(u_cty) == int(t_cty)


def lay_menu_theo_vai_tro(vai_tro):
    """
    Tra ve danh sach ma phan he Web Quan tri duoc phep hien thi theo vai tro.
    """
    role = str(vai_tro or "").strip()
    if role == ROLE_ADMIN_HE_THONG:
        return ["dashboard", "organization", "accounts", "drivers", "vehicles", "scheduler", "reports", "analytics", "audit"]
    if role == ROLE_QUAN_TRI_CONG_TY:
        return ["dashboard", "organization", "accounts", "drivers", "vehicles", "scheduler", "reports", "analytics", "audit"]
    if role == ROLE_QUAN_LY:
        return ["dashboard", "organization", "drivers", "vehicles", "scheduler", "reports", "analytics", "audit"]
    if role == ROLE_DIEU_PHOI_VIEN:
        return ["dashboard", "drivers", "vehicles", "scheduler", "reports"]
    if role == ROLE_GIAM_SAT:
        return ["dashboard", "drivers", "vehicles", "reports"]
    return []


# ============================================================
# V3.0 - SPRINT 2: LICH CHAY & YEU CAU DOI LICH (PURE RULES)
# ============================================================

LICH_CHAY_V3_STATUSES = {
    "NHAP",
    "CHO_XAC_NHAN",
    "DA_XAC_NHAN",
    "SAP_CHAY",
    "DANG_THUC_HIEN",
    "HOAN_THANH",
    "BI_TU_CHOI",
    "DA_HUY",
    "KHONG_KHOI_HANH",
    "CAN_KIEM_TRA",
    "KET_THUC_NGOAI_LE",
}

# Trang thai chiem lich tai xe / phuong tien khi kiem tra trung lich (SCH-02)
LICH_CHAY_ACTIVE_FOR_OVERLAP = {
    "CHO_XAC_NHAN",
    "DA_XAC_NHAN",
    "SAP_CHAY",
    "DANG_THUC_HIEN",
    "sap_chay",
    "dang_chay",
    "tam_ngung",
}

# Trang thai cho phep bat dau chuyen di (SCH-03: bat buoc da xac nhan)
LICH_CHAY_READY_FOR_START = {"DA_XAC_NHAN", "SAP_CHAY"}

# Trang thai lich da ket thuc hoac huy -> khong sua / khong gui yeu cau doi lich
LICH_CHAY_TERMINAL_STATUSES = {
    "HOAN_THANH",
    "DA_HUY",
    "KHONG_KHOI_HANH",
    "KET_THUC_NGOAI_LE",
    "hoan_thanh",
    "da_huy",
}

CHANGE_REQUEST_TYPES = {
    "DOI_THOI_GIAN",
    "DOI_XE",
    "HUY_LICH",
    "KHONG_THE_NHAN",
}

CHANGE_REQUEST_STATUSES = {
    "CHO_DUYET",
    "DA_DUYET",
    "TU_CHOI",
    "CAN_BO_SUNG",
    "DA_RUT_YEU_CAU",
    "HET_HAN",
}


def kiem_tra_khoang_thoi_gian_giao_nhau(start1, end1, start2, end2):
    """
    SCH-02: Kiem tra giao nhau theo khoang nua mo [start, end).
    Hai lich noi tiep [08:00, 10:00) va [10:00, 12:00) -> False (khong trung).
    """
    if start1 is None or end1 is None or start2 is None or end2 is None:
        return False
    return start1 < end2 and end1 > start2


def can_xac_nhan_lai_lich(lich_cu, tai_xe_moi, xe_moi, gio_bd_moi, gio_kt_moi):
    """
    SCH-04: Neu lich da o trang thai DA_XAC_NHAN / SAP_CHAY va co thay doi
    tai xe, phuong tien hoac khung gio -> bat buoc quay ve CHO_XAC_NHAN.
    """
    if not isinstance(lich_cu, dict):
        return False
    if lich_cu.get("trang_thai") not in ("DA_XAC_NHAN", "SAP_CHAY"):
        return False

    def _norm(v):
        return str(v).strip()[:19] if v is not None else None

    if tai_xe_moi is not None and lich_cu.get("tai_xe_id") is not None and int(tai_xe_moi) != int(lich_cu["tai_xe_id"]):
        return True
    if xe_moi is not None and lich_cu.get("xe_id") is not None and int(xe_moi) != int(lich_cu["xe_id"]):
        return True
    if gio_bd_moi is not None and _norm(gio_bd_moi) != _norm(lich_cu.get("gio_bat_dau")):
        return True
    if gio_kt_moi is not None and _norm(gio_kt_moi) != _norm(lich_cu.get("gio_ket_thuc")):
        return True
    return False
