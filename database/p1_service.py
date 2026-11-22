"""
DACN1 V3.0 - P1: Dich vu Checklist kiem tra xe truoc chuyen
va Thong ke da cap + Canh bao uu tien cho Dashboard Quan tri.
"""

from database.mysql_service import db, ghi_lich_su_thao_tac
from database.org_service import build_scope_filter_sql

DEFAULT_CHECKLIST_ITEMS = [
    {"ma_hang_muc": "LOP_XE", "ten_hang_muc": "Lốp xe và áp suất lốp", "bat_buoc": True},
    {"ma_hang_muc": "PHANH", "ten_hang_muc": "Hệ thống phanh an toàn", "bat_buoc": True},
    {"ma_hang_muc": "DEN_COI", "ten_hang_muc": "Đèn chiếu sáng, xi-nhan và còi", "bat_buoc": True},
    {"ma_hang_muc": "GUONG_CHIEU_HAU", "ten_hang_muc": "Gương chiếu hậu và kính chắn gió", "bat_buoc": True},
    {"ma_hang_muc": "GIAY_TO_XE", "ten_hang_muc": "Giấy tờ xe và GPLX hợp lệ", "bat_buoc": True},
    {"ma_hang_muc": "CAMERA_AI", "ten_hang_muc": "Camera AI và nguồn điện cabin", "bat_buoc": True},
]


def danh_gia_checklist(items):
    """
    Pure function: Danh gia danh sach hang muc checklist.
    Neu co it nhat 1 hang muc bat_buoc=True ma ket_qua='KHONG_DAT' -> ('KHONG_DAT', failed_list).
    """
    if not isinstance(items, list) or not items:
        return None, ["Danh sách hạng mục kiểm tra không được để trống."]

    normalized = []
    failed_required = []
    default_map = {x["ma_hang_muc"]: x for x in DEFAULT_CHECKLIST_ITEMS}

    for raw in items:
        ma = str(raw.get("ma_hang_muc") or "").strip().upper()
        kq = str(raw.get("ket_qua") or "").strip().upper()
        if not ma or kq not in ("DAT", "KHONG_DAT"):
            return None, [f"Hạng mục '{ma}' có kết quả không hợp lệ (chỉ nhận DAT / KHONG_DAT)."]
        meta = default_map.get(ma, {})
        ten = str(raw.get("ten_hang_muc") or meta.get("ten_hang_muc") or ma).strip()
        bat_buoc = bool(raw.get("bat_buoc") if "bat_buoc" in raw else meta.get("bat_buoc", True))
        ghi_chu = (raw.get("ghi_chu") or "").strip() or None
        normalized.append({
            "ma_hang_muc": ma,
            "ten_hang_muc": ten,
            "bat_buoc": bat_buoc,
            "ket_qua": kq,
            "ghi_chu": ghi_chu,
        })
        if bat_buoc and kq == "KHONG_DAT":
            failed_required.append(ten)

    ket_qua_tong = "KHONG_DAT" if failed_required else "DAT"
    return (ket_qua_tong, normalized), failed_required


def tai_xe_gui_checklist_truoc_chuyen(lich_chay_id, tai_xe_id, items, ghi_chu=None, actor_id=None):
    """
    Muc 5.3: Neu co hang muc bat buoc KHONG_DAT -> tu dong tao bao_cao_su_co
    va chan bat dau chuyen cho den khi khac phuc (dat lai checklist DAT).
    """
    parsed, failed_required = danh_gia_checklist(items)
    if parsed is None:
        return None, 400, failed_required[0]

    ket_qua_tong, normalized_items = parsed

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s LIMIT 1", (int(lich_chay_id),))
            lich = cur.fetchone()
            if not lich:
                return None, 404, "Không tìm thấy lịch chạy."
            lich = dict(lich)

            if int(lich.get("tai_xe_id") or 0) != int(tai_xe_id):
                return None, 403, "Bạn không phải tài xế được phân công cho lịch chạy này."

            bao_cao_id = None
            if ket_qua_tong == "KHONG_DAT":
                noi_dung_sc = (
                    f"Checklist trước chuyến cho lịch #{lich_chay_id} KHÔNG ĐẠT ở các hạng mục bắt buộc: "
                    + ", ".join(failed_required)
                )
                if ghi_chu:
                    noi_dung_sc += f". Ghi chú tài xế: {ghi_chu}"
                cur.execute(
                    """
                    INSERT INTO bao_cao_su_co
                    (tai_xe_id, xe_id, lich_chay_id, tieu_de, loai_su_co, noi_dung, trang_thai)
                    VALUES (%s, %s, %s, %s, 'CHECKLIST_KHONG_DAT', %s, 'CHO_XU_LY')
                    RETURNING id
                    """,
                    (
                        int(tai_xe_id),
                        lich.get("xe_id"),
                        int(lich_chay_id),
                        f"[Checklist KHÔNG ĐẠT] Lịch #{lich_chay_id}",
                        noi_dung_sc,
                    ),
                )
                bao_cao_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO checklist_truoc_chuyen
                (lich_chay_id, tai_xe_id, xe_id, doi_xe_id, ket_qua_tong, bao_cao_su_co_id, ghi_chu)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    int(lich_chay_id),
                    int(tai_xe_id),
                    lich.get("xe_id"),
                    lich.get("doi_xe_id"),
                    ket_qua_tong,
                    bao_cao_id,
                    ghi_chu,
                ),
            )
            checklist_id = cur.fetchone()["id"]

            for item in normalized_items:
                cur.execute(
                    """
                    INSERT INTO checklist_truoc_chuyen_chi_tiet
                    (checklist_id, ma_hang_muc, ten_hang_muc, bat_buoc, ket_qua, ghi_chu)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        checklist_id,
                        item["ma_hang_muc"],
                        item["ten_hang_muc"],
                        item["bat_buoc"],
                        item["ket_qua"],
                        item["ghi_chu"],
                    ),
                )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="GUI_CHECKLIST_TRUOC_CHUYEN",
            bang_du_lieu="checklist_truoc_chuyen",
            doi_tuong_id=checklist_id,
            du_lieu_sau={
                "lich_chay_id": int(lich_chay_id),
                "ket_qua_tong": ket_qua_tong,
                "bao_cao_su_co_id": bao_cao_id,
            },
        )
        msg = (
            f"Checklist KHÔNG ĐẠT ({', '.join(failed_required)}). "
            f"Hệ thống đã tự động tạo báo cáo sự cố #{bao_cao_id} và tạm chặn bắt đầu chuyến."
            if ket_qua_tong == "KHONG_DAT"
            else "Checklist kiểm tra xe trước chuyến ĐẠT yêu cầu an toàn."
        )
        return {"id": checklist_id, "ket_qua_tong": ket_qua_tong, "bao_cao_su_co_id": bao_cao_id}, 201, msg
    except Exception as e:
        print("Gui checklist truoc chuyen error:", e)
        return None, 500, "Lưu checklist kiểm tra trước chuyến thất bại."


def lay_checklist_theo_lich(lich_chay_id):
    try:
        rows = db.fetch_all(
            "SELECT * FROM checklist_truoc_chuyen WHERE lich_chay_id = %s ORDER BY id DESC LIMIT 10",
            (int(lich_chay_id),),
        )
        for row in rows:
            row["chi_tiet"] = db.fetch_all(
                "SELECT * FROM checklist_truoc_chuyen_chi_tiet WHERE checklist_id = %s ORDER BY id ASC",
                (row["id"],),
            )
        return rows
    except Exception:
        return []


def kiem_tra_checklist_bi_chan(lich_chay_id):
    """Tra ve True neu checklist moi nhat cua lich chay la KHONG_DAT."""
    try:
        row = db.fetch_one(
            "SELECT ket_qua_tong FROM checklist_truoc_chuyen WHERE lich_chay_id = %s ORDER BY id DESC LIMIT 1",
            (int(lich_chay_id),),
        )
        return bool(row and row.get("ket_qua_tong") == "KHONG_DAT")
    except Exception:
        return False


# ============================================================
# DASHBOARD CANH BAO UU TIEN (5 NHOM) & THONG KE DA CAP V3
# ============================================================

def lay_canh_bao_uu_tien(scope=None):
    """
    Muc 10.2: 5 nhom canh bao uu tien tren Dashboard Quan ly:
    1. Camera dang OFFLINE (> 60s)
    2. Su kien AI cho xac minh
    3. Lich chua xac nhan sap den gio chay (trong 24h toi)
    4. Yeu cau doi lich/xe dang CHO_DUYET
    5. Khieu nai vi pham dang cho xu ly
    """
    result = {
        "camera_offline": 0,
        "su_kien_ai_cho_xac_minh": 0,
        "lich_chua_xac_nhan_sap_chay": 0,
        "yeu_cau_doi_lich_cho_duyet": 0,
        "khieu_nai_cho_xu_ly": 0,
    }
    try:
        cam_sql, cam_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r1 = db.fetch_one(
            f"SELECT COUNT(*) AS c FROM thiet_bi_camera WHERE {cam_sql} AND EXTRACT(EPOCH FROM (NOW() - lan_cuoi_ket_noi)) > 60",
            tuple(cam_p),
        )
        result["camera_offline"] = int((r1 or {}).get("c") or 0)

        sk_sql, sk_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r2 = db.fetch_one(
            f"SELECT COUNT(*) AS c FROM su_kien_canh_bao WHERE {sk_sql} AND trang_thai IN ('MOI', 'PENDING_REVIEW', 'UNDER_REVIEW', 'DA_TIEP_NHAN')",
            tuple(sk_p),
        )
        result["su_kien_ai_cho_xac_minh"] = int((r2 or {}).get("c") or 0)

        lc_sql, lc_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r3 = db.fetch_one(
            f"SELECT COUNT(*) AS c FROM lich_chay WHERE {lc_sql} AND trang_thai = 'CHO_XAC_NHAN' AND gio_bat_dau <= NOW() + INTERVAL '24 hours'",
            tuple(lc_p),
        )
        result["lich_chua_xac_nhan_sap_chay"] = int((r3 or {}).get("c") or 0)

        yc_sql, yc_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r4 = db.fetch_one(
            f"SELECT COUNT(*) AS c FROM yeu_cau_thay_doi_lich WHERE {yc_sql} AND trang_thai = 'CHO_DUYET'",
            tuple(yc_p),
        )
        result["yeu_cau_doi_lich_cho_duyet"] = int((r4 or {}).get("c") or 0)

        kn_sql, kn_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r5 = db.fetch_one(
            f"SELECT COUNT(*) AS c FROM khieu_nai_vi_pham WHERE {kn_sql} AND trang_thai IN ('SUBMITTED', 'RECEIVED', 'UNDER_REVIEW')",
            tuple(kn_p),
        )
        result["khieu_nai_cho_xu_ly"] = int((r5 or {}).get("c") or 0)
    except Exception as e:
        print("Lay canh bao uu tien error:", e)
    return result


def lay_thong_ke_da_cap_v3(scope=None):
    """
    Muc 10.2 & P1: Thong ke da cap theo pham vi (Doi xe / Chi nhanh / Cong ty):
    - Tong vi pham, tong khieu nai, ty le khieu nai duoc chap nhan (%)
    - Tong thoi gian camera gian doan (giay)
    - Thong ke theo tung doi xe
    """
    out = {
        "priority_alerts": lay_canh_bao_uu_tien(scope=scope),
        "tong_vi_pham": 0,
        "vi_pham_da_huy_do_khieu_nai": 0,
        "tong_khieu_nai": 0,
        "khieu_nai_chap_nhan": 0,
        "ty_le_khieu_nai_chap_nhan_pct": 0.0,
        "tong_giay_camera_offline": 0,
        "theo_doi_xe": [],
    }
    try:
        vp_sql, vp_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r_vp = db.fetch_one(
            f"""
            SELECT
                COUNT(*) AS tong,
                COUNT(*) FILTER (WHERE trang_thai = 'DA_HUY_DO_KHIEU_NAI') AS da_huy
            FROM vi_pham
            WHERE {vp_sql}
            """,
            tuple(vp_p),
        ) or {}
        out["tong_vi_pham"] = int(r_vp.get("tong") or 0)
        out["vi_pham_da_huy_do_khieu_nai"] = int(r_vp.get("da_huy") or 0)

        kn_sql, kn_p = build_scope_filter_sql(scope, doi_xe_col="doi_xe_id")
        r_kn = db.fetch_one(
            f"""
            SELECT
                COUNT(*) AS tong,
                COUNT(*) FILTER (WHERE ket_luan = 'ACCEPTED' OR trang_thai = 'ACCEPTED') AS chap_nhan
            FROM khieu_nai_vi_pham
            WHERE {kn_sql}
            """,
            tuple(kn_p),
        ) or {}
        tong_kn = int(r_kn.get("tong") or 0)
        chap_nhan = int(r_kn.get("chap_nhan") or 0)
        out["tong_khieu_nai"] = tong_kn
        out["khieu_nai_chap_nhan"] = chap_nhan
        out["ty_le_khieu_nai_chap_nhan_pct"] = round((chap_nhan / tong_kn) * 100.0, 2) if tong_kn > 0 else 0.0

        r_cam = db.fetch_one(
            "SELECT COALESCE(SUM(thoi_luong_giay), 0) AS tong_giay FROM lich_su_ket_noi_camera WHERE trang_thai = 'OFFLINE'"
        ) or {}
        out["tong_giay_camera_offline"] = int(r_cam.get("tong_giay") or 0)

        dx_sql, dx_p = build_scope_filter_sql(scope, doi_xe_col="dx.id", chi_nhanh_col="dx.chi_nhanh_id", cong_ty_col="cn.cong_ty_id")
        out["theo_doi_xe"] = db.fetch_all(
            f"""
            SELECT
                dx.id,
                dx.ten AS ten_doi_xe,
                cn.ten AS ten_chi_nhanh,
                (SELECT COUNT(*) FROM chuyen_thuc_te ct WHERE ct.doi_xe_id = dx.id) AS so_chuyen,
                (SELECT COUNT(*) FROM vi_pham vp WHERE vp.doi_xe_id = dx.id AND vp.trang_thai != 'DA_HUY_DO_KHIEU_NAI') AS so_vi_pham_hieu_luc,
                (SELECT COUNT(*) FROM khieu_nai_vi_pham kn WHERE kn.doi_xe_id = dx.id) AS so_khieu_nai
            FROM doi_xe dx
            JOIN chi_nhanh cn ON dx.chi_nhanh_id = cn.id
            WHERE {dx_sql}
            ORDER BY dx.id ASC
            """,
            tuple(dx_p),
        )
    except Exception as e:
        print("Lay thong ke da cap v3 error:", e)
    return out
