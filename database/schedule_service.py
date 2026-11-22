"""
DACN1 V3.0 - Sprint 2: Dich vu Dieu phoi Lich chay (Transaction + Lock),
Xac nhan bat buoc, Tu choi co ly do, Yeu cau doi lich/doi xe & Bao tri xe.
"""

from datetime import datetime, timedelta
import json

from core.ops_rules import (
    CHANGE_REQUEST_TYPES,
    LICH_CHAY_ACTIVE_FOR_OVERLAP,
    LICH_CHAY_TERMINAL_STATUSES,
    can_xac_nhan_lai_lich,
)
from database.mysql_service import (
    chuyen_int_hoac_none,
    db,
    ghi_lich_su_thao_tac,
    them_ghi_chu,
)
from database.org_service import build_scope_filter_sql


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("T", " ").replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:len(fmt) + 2].strip(), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _lock_driver_and_vehicle(cur, tai_xe_id, xe_id):
    """
    Khoa muc transaction theo thu tu on dinh de chong deadlock va race condition
    khi 2 dieu phoi vien phan cong cung tai xe hoac cung xe dong thoi (SCH-02).
    """
    keys = []
    if tai_xe_id is not None:
        keys.append((1001, int(tai_xe_id)))
    if xe_id is not None:
        keys.append((1002, int(xe_id)))
    for ns, obj_id in sorted(keys):
        cur.execute("SELECT pg_advisory_xact_lock(%s, %s)", (ns, obj_id))


def _check_overlap_in_tx(cur, tai_xe_id, xe_id, gio_bat_dau, gio_ket_thuc, ignore_lich_id=None):
    """Kiem tra trung lich [start, end) trong cung transaction da co advisory lock."""
    active_tuple = tuple(LICH_CHAY_ACTIVE_FOR_OVERLAP)
    sql = """
    SELECT id, tai_xe_id, xe_id, gio_bat_dau, gio_ket_thuc, trang_thai
    FROM lich_chay
    WHERE trang_thai = ANY(%s)
      AND (tai_xe_id = %s OR xe_id = %s)
      AND gio_bat_dau < %s
      AND COALESCE(gio_ket_thuc, gio_bat_dau + INTERVAL '4 hours') > %s
    """
    params = [list(active_tuple), int(tai_xe_id), int(xe_id), gio_ket_thuc, gio_bat_dau]
    if ignore_lich_id is not None:
        sql += " AND id != %s"
        params.append(int(ignore_lich_id))
    sql += " LIMIT 1"
    cur.execute(sql, tuple(params))
    return cur.fetchone()


def _validate_driver_and_vehicle_in_tx(cur, tai_xe_id, xe_id):
    cur.execute(
        """
        SELECT tx.id, tx.ho_ten, tx.trang_thai, tx.doi_xe_id, tk.trang_thai AS tk_trang_thai
        FROM tai_xe tx
        LEFT JOIN tai_khoan tk ON tx.tai_khoan_id = tk.id
        WHERE tx.id = %s
        LIMIT 1
        """,
        (int(tai_xe_id),),
    )
    tx = cur.fetchone()
    if not tx:
        return None, None, "Không tìm thấy tài xế."
    if tx.get("trang_thai") != "dang_lam" or tx.get("tk_trang_thai") == "khoa":
        return None, None, "Tài xế không ở trạng thái đang làm việc hoặc tài khoản đã bị khóa."

    cur.execute(
        "SELECT id, bien_so, trang_thai, doi_xe_id FROM xe WHERE id = %s LIMIT 1",
        (int(xe_id),),
    )
    xe = cur.fetchone()
    if not xe:
        return None, None, "Không tìm thấy phương tiện."
    if xe.get("trang_thai") != "hoat_dong":
        return None, None, "Phương tiện đang bảo trì hoặc ngừng hoạt động."

    return dict(tx), dict(xe), None


# ============================================================
# 1. TAO / CAP NHAT / HUY LICH CHAY V3 (TRANSACTION + LOCK)
# ============================================================

def lay_danh_sach_lich_chay_v3(scope=None, trang_thai=None):
    try:
        where = ["1=1"]
        params = []
        scope_sql, scope_params = build_scope_filter_sql(scope, doi_xe_col="lc.doi_xe_id")
        if scope_sql != "1=1":
            where.append(scope_sql)
            params.extend(scope_params)
        if trang_thai:
            where.append("lc.trang_thai = %s")
            params.append(trang_thai)

        sql = f"""
        SELECT
            lc.*,
            tx.ho_ten,
            x.bien_so,
            dx.ten AS ten_doi_xe
        FROM lich_chay lc
        LEFT JOIN tai_xe tx ON lc.tai_xe_id = tx.id
        LEFT JOIN xe x ON lc.xe_id = x.id
        LEFT JOIN doi_xe dx ON lc.doi_xe_id = dx.id
        WHERE {' AND '.join(where)}
        ORDER BY lc.gio_bat_dau DESC
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach lich chay v3 error:", e)
        return []


def tao_lich_chay_v3(
    tai_xe_id,
    xe_id,
    tuyen_duong,
    gio_bat_dau,
    gio_ket_thuc=None,
    ghi_chu=None,
    trang_thai_ban_dau="CHO_XAC_NHAN",
    actor_id=None,
    actor_role="quan_ly",
    scope=None,
):
    """
    SCH-01, SCH-02, SCH-03:
    Tao lich chay trong 1 transaction co advisory lock chong trung ca dong thoi.
    Tra ve (lich_id, http_status, message).
    """
    tuyen = (tuyen_duong or "").strip()
    if not tai_xe_id or not xe_id or not tuyen or not gio_bat_dau:
        return None, 400, "Vui lòng nhập đầy đủ tài xế, xe, tuyến đường và giờ bắt đầu."

    dt_start = _parse_dt(gio_bat_dau)
    if dt_start is None:
        return None, 400, "Định dạng giờ bắt đầu không hợp lệ."

    dt_end = _parse_dt(gio_ket_thuc) if gio_ket_thuc else (dt_start + timedelta(hours=4))
    if dt_end is None or dt_end <= dt_start:
        return None, 400, "Giờ kết thúc phải lớn hơn giờ bắt đầu (SCH-01)."

    init_status = (trang_thai_ban_dau or "CHO_XAC_NHAN").strip().upper()
    if init_status not in ("NHAP", "CHO_XAC_NHAN"):
        init_status = "CHO_XAC_NHAN"

    try:
        with db.transaction() as cur:
            _lock_driver_and_vehicle(cur, tai_xe_id, xe_id)
            tx, xe, err = _validate_driver_and_vehicle_in_tx(cur, tai_xe_id, xe_id)
            if err:
                return None, 400, err

            conflict = _check_overlap_in_tx(cur, tai_xe_id, xe_id, dt_start, dt_end)
            if conflict:
                return None, 409, f"Trùng khung giờ với lịch chạy #{conflict['id']} của cùng tài xế hoặc phương tiện."

            doi_xe_id = xe.get("doi_xe_id") or tx.get("doi_xe_id") or (scope.get("doi_xe_id") if scope else None)
            cur.execute(
                """
                INSERT INTO lich_chay
                (tai_xe_id, xe_id, doi_xe_id, tuyen_duong, gio_bat_dau, gio_ket_thuc, trang_thai, ghi_chu, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    int(tai_xe_id),
                    int(xe_id),
                    chuyen_int_hoac_none(doi_xe_id),
                    tuyen,
                    dt_start,
                    dt_end,
                    init_status,
                    ghi_chu,
                    actor_id,
                    actor_id,
                ),
            )
            lich_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO lich_su_phan_cong
                (lich_chay_id, tai_xe_moi_id, xe_moi_id, gio_bat_dau_moi, gio_ket_thuc_moi, nguoi_thuc_hien_id, nguon_thay_doi, ly_do)
                VALUES (%s, %s, %s, %s, %s, %s, 'TAO_MOI', %s)
                """,
                (lich_id, int(tai_xe_id), int(xe_id), dt_start, dt_end, actor_id, ghi_chu or "Phân công lịch mới"),
            )

        if init_status == "CHO_XAC_NHAN":
            them_ghi_chu(
                tai_xe_id=int(tai_xe_id),
                quan_ly_id=actor_id,
                noi_dung=(
                    f"Bạn có lịch chạy mới tuyến {tuyen} ({dt_start.strftime('%Y-%m-%d %H:%M')} - "
                    f"{dt_end.strftime('%H:%M')}). Vui lòng xác nhận lịch trước khi khởi hành."
                ),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong="TAO_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=lich_id,
            du_lieu_sau={
                "tai_xe_id": int(tai_xe_id),
                "xe_id": int(xe_id),
                "tuyen_duong": tuyen,
                "gio_bat_dau": str(dt_start),
                "gio_ket_thuc": str(dt_end),
                "trang_thai": init_status,
            },
        )
        return lich_id, 201, "Đã tạo lịch chạy và gửi yêu cầu xác nhận cho tài xế."
    except Exception as e:
        print("Tao lich chay v3 error:", e)
        return None, 500, "Tạo lịch chạy thất bại."


def cap_nhat_lich_chay_v3(
    lich_id,
    tai_xe_id=None,
    xe_id=None,
    tuyen_duong=None,
    gio_bat_dau=None,
    gio_ket_thuc=None,
    trang_thai=None,
    ghi_chu=None,
    ly_do=None,
    actor_id=None,
    actor_role="quan_ly",
):
    """
    SCH-01, SCH-02, SCH-04:
    Cap nhat lich chay trong transaction. Neu thay doi tai xe / xe / gio sau khi
    tai xe da xac nhan -> tu dong quay ve CHO_XAC_NHAN va luu lich_su_phan_cong.
    """
    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s FOR UPDATE", (int(lich_id),))
            lich_cu = cur.fetchone()
            if not lich_cu:
                return False, 404, "Không tìm thấy lịch chạy."

            lich_cu = dict(lich_cu)
            if lich_cu["trang_thai"] in LICH_CHAY_TERMINAL_STATUSES:
                return False, 400, "Lịch đã hủy hoặc đã kết thúc, không thể chỉnh sửa."

            new_tx = int(tai_xe_id) if tai_xe_id is not None else lich_cu["tai_xe_id"]
            new_xe = int(xe_id) if xe_id is not None else lich_cu["xe_id"]
            new_tuyen = (tuyen_duong if tuyen_duong is not None else lich_cu["tuyen_duong"] or "").strip()
            dt_start = _parse_dt(gio_bat_dau) if gio_bat_dau is not None else lich_cu["gio_bat_dau"]
            dt_end = _parse_dt(gio_ket_thuc) if gio_ket_thuc is not None else lich_cu["gio_ket_thuc"]

            if not new_tuyen or not dt_start or not dt_end or dt_end <= dt_start:
                return False, 400, "Thông tin tuyến đường hoặc khung giờ không hợp lệ (giờ kết thúc phải lớn hơn giờ bắt đầu)."

            _lock_driver_and_vehicle(cur, new_tx, new_xe)
            _, _, err = _validate_driver_and_vehicle_in_tx(cur, new_tx, new_xe)
            if err:
                return False, 400, err

            conflict = _check_overlap_in_tx(cur, new_tx, new_xe, dt_start, dt_end, ignore_lich_id=lich_id)
            if conflict:
                return False, 409, f"Trùng khung giờ với lịch chạy #{conflict['id']}."

            need_reconfirm = can_xac_nhan_lai_lich(lich_cu, new_tx, new_xe, dt_start, dt_end)
            new_status = (trang_thai or lich_cu["trang_thai"]).strip()
            new_xac_nhan_at = lich_cu.get("xac_nhan_at")

            # Neu lich bi tu choi va dieu phoi gan lai tai xe/xe -> chuyen lai CHO_XAC_NHAN
            if lich_cu["trang_thai"] == "BI_TU_CHOI" and (new_tx != lich_cu["tai_xe_id"] or new_xe != lich_cu["xe_id"]):
                new_status = "CHO_XAC_NHAN"
                new_xac_nhan_at = None

            if need_reconfirm:
                new_status = "CHO_XAC_NHAN"
                new_xac_nhan_at = None

            cur.execute(
                """
                UPDATE lich_chay
                SET
                    tai_xe_id = %s,
                    xe_id = %s,
                    tuyen_duong = %s,
                    gio_bat_dau = %s,
                    gio_ket_thuc = %s,
                    trang_thai = %s,
                    xac_nhan_at = %s,
                    ghi_chu = COALESCE(%s, ghi_chu),
                    updated_by = %s
                WHERE id = %s
                """,
                (new_tx, new_xe, new_tuyen, dt_start, dt_end, new_status, new_xac_nhan_at, ghi_chu, actor_id, int(lich_id)),
            )

            cur.execute(
                """
                INSERT INTO lich_su_phan_cong
                (
                    lich_chay_id, tai_xe_cu_id, tai_xe_moi_id, xe_cu_id, xe_moi_id,
                    gio_bat_dau_cu, gio_bat_dau_moi, gio_ket_thuc_cu, gio_ket_thuc_moi,
                    nguoi_thuc_hien_id, nguon_thay_doi, ly_do
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'DIEU_CHINH_LICH', %s)
                """,
                (
                    int(lich_id),
                    lich_cu["tai_xe_id"],
                    new_tx,
                    lich_cu["xe_id"],
                    new_xe,
                    lich_cu["gio_bat_dau"],
                    dt_start,
                    lich_cu["gio_ket_thuc"],
                    dt_end,
                    actor_id,
                    ly_do or ("Yêu cầu xác nhận lại do thay đổi lịch" if need_reconfirm else "Cập nhật lịch"),
                ),
            )

        msg_note = (
            f"Lịch chạy #{lich_id} tuyến {new_tuyen} đã được thay đổi. Vui lòng xác nhận lại lịch trước khi khởi hành."
            if need_reconfirm
            else f"Lịch chạy #{lich_id} tuyến {new_tuyen} đã được cập nhật (trạng thái: {new_status})."
        )
        them_ghi_chu(tai_xe_id=new_tx, quan_ly_id=actor_id, noi_dung=msg_note)

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong="CAP_NHAT_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=int(lich_id),
            du_lieu_truoc=lich_cu,
            du_lieu_sau={"tai_xe_id": new_tx, "xe_id": new_xe, "trang_thai": new_status, "reconfirm_required": need_reconfirm},
            ly_do=ly_do,
        )
        return True, 200, (
            "Đã cập nhật lịch chạy và yêu cầu tài xế xác nhận lại."
            if need_reconfirm
            else "Đã cập nhật lịch chạy."
        )
    except Exception as e:
        print("Cap nhat lich chay v3 error:", e)
        return False, 500, "Cập nhật lịch chạy thất bại."


def huy_lich_chay_v3(lich_id, ly_do_huy, actor_id, actor_role):
    ly_do_clean = (ly_do_huy or "").strip()
    if not ly_do_clean:
        return False, 400, "Vui lòng nhập lý do hủy lịch chạy."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s FOR UPDATE", (int(lich_id),))
            lich = cur.fetchone()
            if not lich:
                return False, 404, "Không tìm thấy lịch chạy."
            lich = dict(lich)
            if lich["trang_thai"] in ("DA_HUY", "da_huy"):
                return True, 200, "Lịch chạy đã được hủy trước đó."
            if lich["trang_thai"] in ("DANG_THUC_HIEN", "dang_chay", "HOAN_THANH", "hoan_thanh"):
                return False, 400, "Không thể hủy lịch đang chạy hoặc đã hoàn thành."

            cur.execute(
                "UPDATE lich_chay SET trang_thai = 'DA_HUY', ly_do_huy = %s, updated_by = %s WHERE id = %s",
                (ly_do_clean, actor_id, int(lich_id)),
            )

        if lich.get("tai_xe_id"):
            them_ghi_chu(
                tai_xe_id=lich["tai_xe_id"],
                quan_ly_id=actor_id,
                noi_dung=f"Lịch chạy #{lich_id} tuyến {lich.get('tuyen_duong')} đã bị hủy. Lý do: {ly_do_clean}",
            )
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong="HUY_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=int(lich_id),
            du_lieu_truoc={"trang_thai": lich["trang_thai"]},
            du_lieu_sau={"trang_thai": "DA_HUY"},
            ly_do=ly_do_clean,
        )
        return True, 200, "Đã hủy lịch chạy."
    except Exception as e:
        print("Huy lich chay v3 error:", e)
        return False, 500, "Hủy lịch chạy thất bại."


# ============================================================
# 2. TAI XE XAC NHAN / TU CHOI LICH (SCH-03)
# ============================================================

def tai_xe_xac_nhan_lich(lich_id, tai_xe_id, actor_id):
    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s FOR UPDATE", (int(lich_id),))
            lich = cur.fetchone()
            if not lich:
                return False, 404, "Không tìm thấy lịch chạy."
            if int(lich["tai_xe_id"] or 0) != int(tai_xe_id):
                return False, 403, "Bạn không phải tài xế được phân công cho lịch này."
            if lich["trang_thai"] not in ("CHO_XAC_NHAN", "sap_chay"):
                return False, 409, f"Lịch chạy đang ở trạng thái {lich['trang_thai']}, không thể xác nhận."

            cur.execute(
                "UPDATE lich_chay SET trang_thai = 'DA_XAC_NHAN', xac_nhan_at = NOW(), ly_do_tu_choi = NULL WHERE id = %s",
                (int(lich_id),),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="XAC_NHAN_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=int(lich_id),
            du_lieu_truoc={"trang_thai": lich["trang_thai"]},
            du_lieu_sau={"trang_thai": "DA_XAC_NHAN"},
        )
        return True, 200, "Đã xác nhận lịch chạy thành công."
    except Exception as e:
        print("Tai xe xac nhan lich error:", e)
        return False, 500, "Xác nhận lịch chạy thất bại."


def tai_xe_tu_choi_lich(lich_id, tai_xe_id, ly_do, actor_id):
    ly_do_clean = (ly_do or "").strip()
    if not ly_do_clean:
        return False, 400, "Bắt buộc nhập lý do khi từ chối lịch chạy."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s FOR UPDATE", (int(lich_id),))
            lich = cur.fetchone()
            if not lich:
                return False, 404, "Không tìm thấy lịch chạy."
            if int(lich["tai_xe_id"] or 0) != int(tai_xe_id):
                return False, 403, "Bạn không phải tài xế được phân công cho lịch này."
            if lich["trang_thai"] not in ("CHO_XAC_NHAN", "sap_chay"):
                return False, 409, f"Lịch chạy đang ở trạng thái {lich['trang_thai']}, không thể từ chối."

            cur.execute(
                "UPDATE lich_chay SET trang_thai = 'BI_TU_CHOI', ly_do_tu_choi = %s WHERE id = %s",
                (ly_do_clean, int(lich_id)),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="TU_CHOI_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=int(lich_id),
            du_lieu_truoc={"trang_thai": lich["trang_thai"]},
            du_lieu_sau={"trang_thai": "BI_TU_CHOI"},
            ly_do=ly_do_clean,
        )
        return True, 200, "Đã từ chối lịch chạy và thông báo điều phối viên phân công lại."
    except Exception as e:
        print("Tai xe tu choi lich error:", e)
        return False, 500, "Từ chối lịch chạy thất bại."


# ============================================================
# 3. YEU CAU DOI LICH / DOI XE (REQ-01)
# ============================================================

def tai_xe_gui_yeu_cau_doi_lich(lich_id, tai_xe_id, loai_yeu_cau, du_lieu_de_xuat, ly_do, actor_id):
    loai = (loai_yeu_cau or "").strip().upper()
    ly_do_clean = (ly_do or "").strip()
    if loai not in CHANGE_REQUEST_TYPES:
        return None, 400, "Loại yêu cầu thay đổi lịch không hợp lệ."
    if not ly_do_clean:
        return None, 400, "Vui lòng nhập lý do gửi yêu cầu."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s LIMIT 1", (int(lich_id),))
            lich = cur.fetchone()
            if not lich:
                return None, 404, "Không tìm thấy lịch chạy."
            if int(lich["tai_xe_id"] or 0) != int(tai_xe_id):
                return None, 403, "Bạn chỉ có thể gửi yêu cầu cho lịch chạy của chính mình."
            if lich["trang_thai"] in ("DANG_THUC_HIEN", "dang_chay") or lich["trang_thai"] in LICH_CHAY_TERMINAL_STATUSES:
                return None, 400, "Chỉ được gửi yêu cầu đổi lịch/xe trước khi chuyến đi bắt đầu."

            # REQ-01: Khong thay doi lich goc, chi tao yeu cau CHO_DUYET
            cur.execute(
                """
                INSERT INTO yeu_cau_thay_doi_lich
                (lich_chay_id, tai_xe_id, doi_xe_id, loai_yeu_cau, du_lieu_de_xuat, ly_do, trang_thai)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, 'CHO_DUYET')
                RETURNING id
                """,
                (
                    int(lich_id),
                    int(tai_xe_id),
                    lich.get("doi_xe_id"),
                    loai,
                    json.dumps(du_lieu_de_xuat or {}, ensure_ascii=False),
                    ly_do_clean,
                ),
            )
            yc_id = cur.fetchone()["id"]

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="GUI_YEU_CAU_DOI_LICH",
            bang_du_lieu="yeu_cau_thay_doi_lich",
            doi_tuong_id=yc_id,
            du_lieu_sau={"lich_chay_id": int(lich_id), "loai_yeu_cau": loai, "du_lieu_de_xuat": du_lieu_de_xuat},
            ly_do=ly_do_clean,
        )
        return yc_id, 201, "Đã gửi yêu cầu thay đổi lịch chờ quản lý phê duyệt."
    except Exception as e:
        print("Gui yeu cau doi lich error:", e)
        return None, 500, "Gửi yêu cầu thất bại."


def tai_xe_rut_yeu_cau_doi_lich(yeu_cau_id, tai_xe_id, actor_id):
    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM yeu_cau_thay_doi_lich WHERE id = %s FOR UPDATE", (int(yeu_cau_id),))
            yc = cur.fetchone()
            if not yc:
                return False, 404, "Không tìm thấy yêu cầu."
            if int(yc["tai_xe_id"]) != int(tai_xe_id):
                return False, 403, "Không có quyền rút yêu cầu của tài xế khác."
            if yc["trang_thai"] not in ("CHO_DUYET", "CAN_BO_SUNG"):
                return False, 409, "Yêu cầu đã được xử lý, không thể rút."

            cur.execute(
                "UPDATE yeu_cau_thay_doi_lich SET trang_thai = 'DA_RUT_YEU_CAU', decided_at = NOW() WHERE id = %s",
                (int(yeu_cau_id),),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="RUT_YEU_CAU_DOI_LICH",
            bang_du_lieu="yeu_cau_thay_doi_lich",
            doi_tuong_id=int(yeu_cau_id),
        )
        return True, 200, "Đã rút yêu cầu thay đổi lịch."
    except Exception as e:
        print("Rut yeu cau doi lich error:", e)
        return False, 500, "Rút yêu cầu thất bại."


def lay_danh_sach_yeu_cau_doi_lich(scope=None, tai_xe_id=None, trang_thai=None):
    try:
        where = ["1=1"]
        params = []
        if tai_xe_id is not None:
            where.append("yc.tai_xe_id = %s")
            params.append(int(tai_xe_id))
        else:
            scope_sql, scope_params = build_scope_filter_sql(scope, doi_xe_col="yc.doi_xe_id")
            if scope_sql != "1=1":
                where.append(scope_sql)
                params.extend(scope_params)
        if trang_thai:
            where.append("yc.trang_thai = %s")
            params.append(trang_thai)

        sql = f"""
        SELECT
            yc.*,
            tx.ho_ten,
            lc.tuyen_duong,
            lc.gio_bat_dau,
            lc.gio_ket_thuc,
            lc.trang_thai AS lich_trang_thai,
            x.bien_so
        FROM yeu_cau_thay_doi_lich yc
        JOIN lich_chay lc ON yc.lich_chay_id = lc.id
        JOIN tai_xe tx ON yc.tai_xe_id = tx.id
        LEFT JOIN xe x ON lc.xe_id = x.id
        WHERE {' AND '.join(where)}
        ORDER BY yc.id DESC
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach yeu cau doi lich error:", e)
        return []


def quan_ly_xu_ly_yeu_cau_doi_lich(yeu_cau_id, quyet_dinh, ly_do_tu_choi=None, actor_id=None, actor_role="quan_ly"):
    """
    REQ-01: Quan ly phe duyet (DA_DUYET / TU_CHOI / CAN_BO_SUNG).
    Khi DA_DUYET: kiem tra lai trung lich & dieu kien xe/tai xe trong cung transaction.
    """
    decision = (quyet_dinh or "").strip().upper()
    if decision not in ("DA_DUYET", "TU_CHOI", "CAN_BO_SUNG"):
        return False, 400, "Quyết định không hợp lệ (DA_DUYET, TU_CHOI, CAN_BO_SUNG)."

    reason_clean = (ly_do_tu_choi or "").strip()
    if decision == "TU_CHOI" and not reason_clean:
        return False, 400, "Bắt buộc nhập lý do khi từ chối yêu cầu."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM yeu_cau_thay_doi_lich WHERE id = %s FOR UPDATE", (int(yeu_cau_id),))
            yc = cur.fetchone()
            if not yc:
                return False, 404, "Không tìm thấy yêu cầu."
            yc = dict(yc)
            if yc["trang_thai"] not in ("CHO_DUYET", "CAN_BO_SUNG"):
                return False, 409, f"Yêu cầu đang ở trạng thái {yc['trang_thai']}, không thể xử lý lại."

            if decision in ("TU_CHOI", "CAN_BO_SUNG"):
                cur.execute(
                    """
                    UPDATE yeu_cau_thay_doi_lich
                    SET trang_thai = %s, nguoi_duyet_id = %s, ly_do_tu_choi = %s, decided_at = NOW()
                    WHERE id = %s
                    """,
                    (decision, actor_id, reason_clean or None, int(yeu_cau_id)),
                )
                target_tx = yc["tai_xe_id"]
                lich_id = yc["lich_chay_id"]
            else:
                # DA_DUYET: khoa lich chay & kiem tra lai trung lich trong transaction
                cur.execute("SELECT * FROM lich_chay WHERE id = %s FOR UPDATE", (yc["lich_chay_id"],))
                lich = cur.fetchone()
                if not lich:
                    return False, 404, "Lịch chạy gốc không tồn tại."
                lich = dict(lich)
                if lich["trang_thai"] in LICH_CHAY_TERMINAL_STATUSES:
                    return False, 409, "Lịch chạy gốc đã kết thúc hoặc bị hủy."

                de_xuat = yc.get("du_lieu_de_xuat") or {}
                if isinstance(de_xuat, str):
                    de_xuat = json.loads(de_xuat)

                loai = yc["loai_yeu_cau"]
                if loai in ("HUY_LICH", "KHONG_THE_NHAN"):
                    cur.execute(
                        "UPDATE lich_chay SET trang_thai = 'DA_HUY', ly_do_huy = %s, updated_by = %s WHERE id = %s",
                        (f"Duyệt yêu cầu #{yeu_cau_id}: {yc['ly_do']}", actor_id, lich["id"]),
                    )
                else:
                    new_xe = int(de_xuat.get("xe_id") or lich["xe_id"])
                    new_tx = int(de_xuat.get("tai_xe_id") or lich["tai_xe_id"])
                    dt_start = _parse_dt(de_xuat.get("gio_bat_dau")) or lich["gio_bat_dau"]
                    dt_end = _parse_dt(de_xuat.get("gio_ket_thuc")) or lich["gio_ket_thuc"]
                    if not dt_start or not dt_end or dt_end <= dt_start:
                        return False, 400, "Khung giờ đề xuất không hợp lệ."

                    _lock_driver_and_vehicle(cur, new_tx, new_xe)
                    _, _, err = _validate_driver_and_vehicle_in_tx(cur, new_tx, new_xe)
                    if err:
                        return False, 400, err

                    conflict = _check_overlap_in_tx(cur, new_tx, new_xe, dt_start, dt_end, ignore_lich_id=lich["id"])
                    if conflict:
                        return False, 409, f"Không thể duyệt: trùng khung giờ với lịch #{conflict['id']}."

                    cur.execute(
                        """
                        UPDATE lich_chay
                        SET tai_xe_id = %s, xe_id = %s, gio_bat_dau = %s, gio_ket_thuc = %s,
                            trang_thai = 'CHO_XAC_NHAN', xac_nhan_at = NULL, updated_by = %s
                        WHERE id = %s
                        """,
                        (new_tx, new_xe, dt_start, dt_end, actor_id, lich["id"]),
                    )
                    cur.execute(
                        """
                        INSERT INTO lich_su_phan_cong
                        (
                            lich_chay_id, tai_xe_cu_id, tai_xe_moi_id, xe_cu_id, xe_moi_id,
                            gio_bat_dau_cu, gio_bat_dau_moi, gio_ket_thuc_cu, gio_ket_thuc_moi,
                            nguoi_thuc_hien_id, nguon_thay_doi, ly_do
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'DUYET_YEU_CAU_DOI_LICH', %s)
                        """,
                        (
                            lich["id"], lich["tai_xe_id"], new_tx, lich["xe_id"], new_xe,
                            lich["gio_bat_dau"], dt_start, lich["gio_ket_thuc"], dt_end,
                            actor_id, f"Duyệt yêu cầu #{yeu_cau_id}",
                        ),
                    )

                cur.execute(
                    """
                    UPDATE yeu_cau_thay_doi_lich
                    SET trang_thai = 'DA_DUYET', nguoi_duyet_id = %s, decided_at = NOW()
                    WHERE id = %s
                    """,
                    (actor_id, int(yeu_cau_id)),
                )
                target_tx = yc["tai_xe_id"]
                lich_id = yc["lich_chay_id"]

        them_ghi_chu(
            tai_xe_id=target_tx,
            quan_ly_id=actor_id,
            noi_dung=f"Yêu cầu thay đổi lịch #{yeu_cau_id} (lịch #{lich_id}) đã được cập nhật: {decision}."
            + (f" Ghi chú: {reason_clean}" if reason_clean else ""),
        )
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong=f"XU_LY_YEU_CAU_DOI_LICH_{decision}",
            bang_du_lieu="yeu_cau_thay_doi_lich",
            doi_tuong_id=int(yeu_cau_id),
            du_lieu_truoc={"trang_thai": yc["trang_thai"]},
            du_lieu_sau={"trang_thai": decision},
            ly_do=reason_clean or None,
        )
        return True, 200, f"Đã xử lý yêu cầu ({decision})."
    except Exception as e:
        print("Xu ly yeu cau doi lich error:", e)
        return False, 500, "Xử lý yêu cầu thất bại."


# ============================================================
# 4. BAO TRI XE -> LIET KE LICH TUONG LAI BI ANH HUONG (5.8)
# ============================================================

def lay_lich_bi_anh_huong_khi_bao_tri_xe(xe_id):
    try:
        active_tuple = list(LICH_CHAY_ACTIVE_FOR_OVERLAP)
        return db.fetch_all(
            """
            SELECT lc.id, lc.tai_xe_id, tx.ho_ten, lc.tuyen_duong, lc.gio_bat_dau, lc.gio_ket_thuc, lc.trang_thai
            FROM lich_chay lc
            LEFT JOIN tai_xe tx ON lc.tai_xe_id = tx.id
            WHERE lc.xe_id = %s
              AND lc.trang_thai = ANY(%s)
              AND COALESCE(lc.gio_ket_thuc, lc.gio_bat_dau) >= NOW()
            ORDER BY lc.gio_bat_dau ASC
            """,
            (int(xe_id), active_tuple),
        )
    except Exception as e:
        print("Lay lich bi anh huong error:", e)
        return []
