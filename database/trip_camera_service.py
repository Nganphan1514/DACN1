"""
DACN1 V3.0 - Sprint 3: Dich vu Chuyen thuc te (chuyen_thuc_te),
Ket thuc ngoai le co ly do & Giam sat ket noi Camera doc lap (lich_su_ket_noi_camera).
"""

from core.ops_rules import (
    LICH_CHAY_READY_FOR_START,
    phan_loai_suc_khoe_thiet_bi,
)
from database.mysql_service import (
    db,
    ghi_lich_su_thao_tac,
    them_ghi_chu,
)
from database.org_service import build_scope_filter_sql
from database.schedule_service import _lock_driver_and_vehicle


# ============================================================
# 1. CHUYEN THUC TE (TRIP-01, TRIP-02, TRIP-03, TRIP-04)
# ============================================================

def tai_xe_bat_dau_chuyen(lich_chay_id, tai_xe_id, actor_id, ghi_chu=None):
    """
    SCH-03, TRIP-01, TRIP-02:
    Chi dung tai xe duoc phan cong va lich da DA_XAC_NHAN moi duoc bat dau chuyen.
    Khong cho phep 1 tai xe hoac 1 xe co 2 chuyen DANG_CHAY cung luc.
    """
    if not lich_chay_id or not tai_xe_id:
        return None, 400, "Thiếu mã lịch chạy hoặc thông tin tài xế."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM lich_chay WHERE id = %s FOR UPDATE", (int(lich_chay_id),))
            lich = cur.fetchone()
            if not lich:
                return None, 404, "Không tìm thấy lịch chạy."
            lich = dict(lich)

            if int(lich.get("tai_xe_id") or 0) != int(tai_xe_id):
                return None, 403, "Bạn không phải tài xế được phân công cho lịch chạy này."

            if lich.get("trang_thai") not in LICH_CHAY_READY_FOR_START:
                return None, 409, (
                    f"Lịch chạy đang ở trạng thái {lich.get('trang_thai')}. "
                    "Tài xế bắt buộc xác nhận lịch (DA_XAC_NHAN) trước khi bắt đầu chuyến."
                )

            xe_id = lich.get("xe_id")
            _lock_driver_and_vehicle(cur, tai_xe_id, xe_id)

            # Kiem tra xe dang hoat dong
            cur.execute("SELECT id, bien_so, trang_thai FROM xe WHERE id = %s LIMIT 1", (int(xe_id),))
            xe = cur.fetchone()
            if not xe or xe.get("trang_thai") != "hoat_dong":
                return None, 400, "Phương tiện đang bảo trì hoặc ngừng hoạt động, không thể bắt đầu chuyến."

            # TRIP-01: Chan 2 chuyen DANG_CHAY cung luc cua tai xe hoac xe
            cur.execute(
                """
                SELECT id, tai_xe_id, xe_id
                FROM chuyen_thuc_te
                WHERE trang_thai = 'DANG_CHAY'
                  AND (tai_xe_id = %s OR xe_id = %s)
                LIMIT 1
                """,
                (int(tai_xe_id), int(xe_id)),
            )
            dang_chay = cur.fetchone()
            if dang_chay:
                return None, 409, f"Tài xế hoặc phương tiện đang có chuyến thực tế #{dang_chay['id']} đang chạy."

            # Kiem tra quan he 1-1 lich_chay -> chuyen_thuc_te
            cur.execute("SELECT id FROM chuyen_thuc_te WHERE lich_chay_id = %s LIMIT 1", (int(lich_chay_id),))
            existing = cur.fetchone()
            if existing:
                return None, 409, f"Lịch chạy này đã có chuyến thực tế #{existing['id']}."

            cur.execute(
                """
                INSERT INTO chuyen_thuc_te
                (lich_chay_id, doi_xe_id, tai_xe_id, xe_id, trang_thai, ghi_chu)
                VALUES (%s, %s, %s, %s, 'DANG_CHAY', %s)
                RETURNING id
                """,
                (int(lich_chay_id), lich.get("doi_xe_id"), int(tai_xe_id), int(xe_id), ghi_chu),
            )
            chuyen_id = cur.fetchone()["id"]

            cur.execute(
                "UPDATE lich_chay SET trang_thai = 'DANG_THUC_HIEN' WHERE id = %s",
                (int(lich_chay_id),),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="BAT_DAU_CHUYEN",
            bang_du_lieu="chuyen_thuc_te",
            doi_tuong_id=chuyen_id,
            du_lieu_sau={"lich_chay_id": int(lich_chay_id), "xe_id": int(xe_id), "trang_thai": "DANG_CHAY"},
        )
        return chuyen_id, 201, "Đã bắt đầu chuyến đi."
    except Exception as e:
        print("Tai xe bat dau chuyen error:", e)
        return None, 500, "Bắt đầu chuyến đi thất bại."


def tai_xe_ket_thuc_chuyen(chuyen_id, tai_xe_id, actor_id, ghi_chu=None):
    """
    TRIP-03: Chi tai xe duoc phan cong moi duoc tu ket thuc chuyen cua minh.
    """
    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM chuyen_thuc_te WHERE id = %s FOR UPDATE", (int(chuyen_id),))
            chuyen = cur.fetchone()
            if not chuyen:
                return False, 404, "Không tìm thấy chuyến thực tế."
            chuyen = dict(chuyen)

            if int(chuyen["tai_xe_id"]) != int(tai_xe_id):
                return False, 403, "Bạn không có quyền kết thúc chuyến của tài xế khác."

            if chuyen["trang_thai"] in ("HOAN_THANH", "KET_THUC_NGOAI_LE"):
                return False, 409, f"Chuyến đi đã kết thúc ({chuyen['trang_thai']})."

            cur.execute(
                """
                UPDATE chuyen_thuc_te
                SET
                    trang_thai = 'HOAN_THANH',
                    ended_at = NOW(),
                    ket_thuc_boi_id = %s,
                    loai_ket_thuc = 'TAI_XE_KET_THUC',
                    ghi_chu = COALESCE(%s, ghi_chu)
                WHERE id = %s
                """,
                (actor_id, ghi_chu, int(chuyen_id)),
            )

            # Dong cac phien lai ky thuat dang mo gan voi chuyen nay
            cur.execute(
                """
                UPDATE phien_lai_xe
                SET
                    ket_thuc = NOW(),
                    tong_phut = ROUND(EXTRACT(EPOCH FROM (NOW() - bat_dau)) / 60.0),
                    trang_thai = 'DA_KET_THUC',
                    ly_do_ket_thuc = 'TRIP_COMPLETED'
                WHERE (chuyen_thuc_te_id = %s OR (tai_xe_id = %s AND lich_chay_id = %s))
                  AND trang_thai != 'DA_KET_THUC'
                """,
                (int(chuyen_id), int(tai_xe_id), chuyen["lich_chay_id"]),
            )

            cur.execute(
                "UPDATE lich_chay SET trang_thai = 'HOAN_THANH' WHERE id = %s",
                (chuyen["lich_chay_id"],),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="KET_THUC_CHUYEN",
            bang_du_lieu="chuyen_thuc_te",
            doi_tuong_id=int(chuyen_id),
            du_lieu_truoc={"trang_thai": chuyen["trang_thai"]},
            du_lieu_sau={"trang_thai": "HOAN_THANH", "loai_ket_thuc": "TAI_XE_KET_THUC"},
        )
        return True, 200, "Đã kết thúc chuyến đi thành công."
    except Exception as e:
        print("Tai xe ket thuc chuyen error:", e)
        return False, 500, "Kết thúc chuyến đi thất bại."


def quan_ly_ket_thuc_chuyen_ngoai_le(chuyen_id, ly_do_ngoai_le, actor_id, actor_role):
    """
    TRIP-03: Quan ly ket thuc chuyen ngoai le — bat buoc nhap ly do chi tiet & ghi audit log.
    """
    ly_do_clean = (ly_do_ngoai_le or "").strip()
    if len(ly_do_clean) < 5:
        return False, 400, "Bắt buộc nhập lý do kết thúc ngoại lệ chi tiết (tối thiểu 5 ký tự)."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM chuyen_thuc_te WHERE id = %s FOR UPDATE", (int(chuyen_id),))
            chuyen = cur.fetchone()
            if not chuyen:
                return False, 404, "Không tìm thấy chuyến thực tế."
            chuyen = dict(chuyen)

            if chuyen["trang_thai"] in ("HOAN_THANH", "KET_THUC_NGOAI_LE"):
                return False, 409, f"Chuyến đi đã kết thúc ({chuyen['trang_thai']})."

            cur.execute(
                """
                UPDATE chuyen_thuc_te
                SET
                    trang_thai = 'KET_THUC_NGOAI_LE',
                    ended_at = NOW(),
                    ket_thuc_boi_id = %s,
                    loai_ket_thuc = 'QUAN_LY_NGOAI_LE',
                    ly_do_ngoai_le = %s
                WHERE id = %s
                """,
                (actor_id, ly_do_clean, int(chuyen_id)),
            )

            cur.execute(
                """
                UPDATE phien_lai_xe
                SET
                    ket_thuc = NOW(),
                    tong_phut = ROUND(EXTRACT(EPOCH FROM (NOW() - bat_dau)) / 60.0),
                    trang_thai = 'DA_KET_THUC',
                    ly_do_ket_thuc = 'ADMIN_EXCEPTION'
                WHERE (chuyen_thuc_te_id = %s OR (tai_xe_id = %s AND lich_chay_id = %s))
                  AND trang_thai != 'DA_KET_THUC'
                """,
                (int(chuyen_id), chuyen["tai_xe_id"], chuyen["lich_chay_id"]),
            )

            cur.execute(
                "UPDATE lich_chay SET trang_thai = 'KET_THUC_NGOAI_LE' WHERE id = %s",
                (chuyen["lich_chay_id"],),
            )

        them_ghi_chu(
            tai_xe_id=chuyen["tai_xe_id"],
            quan_ly_id=actor_id,
            noi_dung=f"Chuyến đi #{chuyen_id} đã được Quản lý kết thúc ngoại lệ. Lý do: {ly_do_clean}",
        )
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong="KET_THUC_CHUYEN_NGOAI_LE",
            bang_du_lieu="chuyen_thuc_te",
            doi_tuong_id=int(chuyen_id),
            du_lieu_truoc={"trang_thai": chuyen["trang_thai"]},
            du_lieu_sau={"trang_thai": "KET_THUC_NGOAI_LE", "loai_ket_thuc": "QUAN_LY_NGOAI_LE"},
            ly_do=ly_do_clean,
        )
        return True, 200, "Đã kết thúc chuyến đi ngoại lệ và ghi nhật ký kiểm toán."
    except Exception as e:
        print("Quan ly ket thuc chuyen ngoai le error:", e)
        return False, 500, "Kết thúc chuyến ngoại lệ thất bại."


def lay_danh_sach_chuyen_thuc_te(scope=None, trang_thai=None, tai_xe_id=None, limit=100):
    try:
        where = ["1=1"]
        params = []
        if tai_xe_id is not None:
            where.append("ct.tai_xe_id = %s")
            params.append(int(tai_xe_id))
        else:
            scope_sql, scope_params = build_scope_filter_sql(scope, doi_xe_col="ct.doi_xe_id")
            if scope_sql != "1=1":
                where.append(scope_sql)
                params.extend(scope_params)
        if trang_thai:
            where.append("ct.trang_thai = %s")
            params.append(trang_thai)

        params.append(int(limit))
        sql = f"""
        SELECT
            ct.*,
            tx.ho_ten,
            x.bien_so,
            lc.tuyen_duong,
            lc.gio_bat_dau,
            lc.gio_ket_thuc,
            (
                SELECT COALESCE(SUM(ls.thoi_luong_giay), 0)
                FROM lich_su_ket_noi_camera ls
                WHERE ls.chuyen_thuc_te_id = ct.id AND ls.trang_thai = 'OFFLINE'
            ) AS tong_giay_camera_offline
        FROM chuyen_thuc_te ct
        LEFT JOIN tai_xe tx ON ct.tai_xe_id = tx.id
        LEFT JOIN xe x ON ct.xe_id = x.id
        LEFT JOIN lich_chay lc ON ct.lich_chay_id = lc.id
        WHERE {' AND '.join(where)}
        ORDER BY ct.id DESC
        LIMIT %s
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach chuyen thuc te error:", e)
        return []


# ============================================================
# 2. CAMERA MAT KET NOI DOC LAP (CAM-01, CAM-02, CAM-03)
# ============================================================

def ghi_nhan_camera_heartbeat_va_lich_su(device_id, xe_id=None, camera_ok=True, fps=0.0, outbox_pending=0):
    """
    Khi nhan heartbeat tu thiet bi Edge:
    - Neu thiet bi dang co khoang OFFLINE/UNSTABLE mo trong lich_su_ket_noi_camera -> dong lai va tinh thoi_luong_giay.
    - Neu camera_ok=False hoac fps < 8 -> ghi nhan UNSTABLE neu chua co.
    """
    if not device_id:
        return False
    try:
        health = phan_loai_suc_khoe_thiet_bi(
            seconds_since_seen=0,
            camera_ok=camera_ok,
            fps=fps,
            outbox_pending=outbox_pending,
        )
        with db.transaction() as cur:
            # Tim chuyen dang chay cua xe (neu co)
            chuyen_id = None
            if xe_id:
                cur.execute(
                    "SELECT id FROM chuyen_thuc_te WHERE xe_id = %s AND trang_thai = 'DANG_CHAY' LIMIT 1",
                    (int(xe_id),),
                )
                row_ct = cur.fetchone()
                if row_ct:
                    chuyen_id = row_ct["id"]

            if health == "ONLINE_HEALTHY":
                cur.execute(
                    """
                    UPDATE lich_su_ket_noi_camera
                    SET
                        ket_thuc_at = NOW(),
                        thoi_luong_giay = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - bat_dau_at))::INT),
                        ghi_chu = COALESCE(ghi_chu, '') || ' [Đã khôi phục ONLINE]'
                    WHERE device_id = %s
                      AND trang_thai IN ('OFFLINE', 'UNSTABLE', 'RECOVERING')
                      AND ket_thuc_at IS NULL
                    """,
                    (device_id,),
                )
            elif health == "ONLINE_DEGRADED":
                cur.execute(
                    """
                    SELECT id FROM lich_su_ket_noi_camera
                    WHERE device_id = %s AND trang_thai = 'UNSTABLE' AND ket_thuc_at IS NULL
                    LIMIT 1
                    """,
                    (device_id,),
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO lich_su_ket_noi_camera
                        (device_id, xe_id, chuyen_thuc_te_id, trang_thai, ghi_chu)
                        VALUES (%s, %s, %s, 'UNSTABLE', %s)
                        """,
                        (device_id, xe_id, chuyen_id, f"Camera suy giảm (fps={fps}, camera_ok={camera_ok}, outbox={outbox_pending})"),
                    )
        return True
    except Exception:
        return False


def quet_camera_mat_ket_noi(timeout_seconds=60):
    """
    CAM-01, CAM-02:
    Quet cac thiet bi camera qua han Heartbeat (> timeout_seconds).
    - Mo ban ghi OFFLINE moi trong lich_su_ket_noi_camera (neu chua mo).
    - KHONG tu dong ket thuc chuyen_thuc_te (giu nguyen DANG_CHAY).
    - Tra ve danh sach su kien moi phat sinh de ban canh bao 2 phia (Tai xe + Quan ly/Giam sat).
    """
    newly_offline = []
    try:
        stale_devices = db.fetch_all(
            """
            SELECT
                tb.device_id,
                tb.xe_id,
                tb.ten_thiet_bi,
                tb.doi_xe_id,
                x.bien_so,
                ct.id AS chuyen_thuc_te_id,
                ct.tai_xe_id,
                tx.ho_ten AS ten_tai_xe,
                tx.tai_khoan_id AS tai_khoan_tai_xe_id,
                EXTRACT(EPOCH FROM (NOW() - tb.lan_cuoi_ket_noi))::INT AS seconds_since_seen
            FROM thiet_bi_camera tb
            LEFT JOIN xe x ON tb.xe_id = x.id
            LEFT JOIN chuyen_thuc_te ct ON ct.xe_id = tb.xe_id AND ct.trang_thai = 'DANG_CHAY'
            LEFT JOIN tai_xe tx ON ct.tai_xe_id = tx.id
            WHERE EXTRACT(EPOCH FROM (NOW() - tb.lan_cuoi_ket_noi)) > %s
            """,
            (int(timeout_seconds),),
        )

        for dev in stale_devices:
            with db.transaction() as cur:
                cur.execute(
                    """
                    SELECT id FROM lich_su_ket_noi_camera
                    WHERE device_id = %s AND trang_thai = 'OFFLINE' AND ket_thuc_at IS NULL
                    LIMIT 1
                    """,
                    (dev["device_id"],),
                )
                if cur.fetchone():
                    continue  # Da ghi nhan & canh bao khoang mat ket noi nay roi

                cur.execute(
                    """
                    INSERT INTO lich_su_ket_noi_camera
                    (device_id, xe_id, chuyen_thuc_te_id, trang_thai, ghi_chu)
                    VALUES (%s, %s, %s, 'OFFLINE', %s)
                    RETURNING id
                    """,
                    (
                        dev["device_id"],
                        dev.get("xe_id"),
                        dev.get("chuyen_thuc_te_id"),
                        f"Mất tín hiệu Heartbeat quá {timeout_seconds} giây (chuyến vẫn tiếp tục ghi nhận)",
                    ),
                )
                log_id = cur.fetchone()["id"]
                dev["connection_log_id"] = log_id
                newly_offline.append(dev)
    except Exception as e:
        print("Quet camera mat ket noi error:", e)
    return newly_offline


def lay_lich_su_ket_noi_camera(device_id=None, chuyen_thuc_te_id=None, limit=50):
    try:
        where = ["1=1"]
        params = []
        if device_id:
            where.append("ls.device_id = %s")
            params.append(device_id)
        if chuyen_thuc_te_id:
            where.append("ls.chuyen_thuc_te_id = %s")
            params.append(int(chuyen_thuc_te_id))
        params.append(int(limit))
        sql = f"""
        SELECT ls.*, x.bien_so
        FROM lich_su_ket_noi_camera ls
        LEFT JOIN xe x ON ls.xe_id = x.id
        WHERE {' AND '.join(where)}
        ORDER BY ls.id DESC
        LIMIT %s
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay lich su ket noi camera error:", e)
        return []


def lay_trang_thai_camera_cho_tai_xe(tai_xe_id, timeout_seconds=60):
    """Tra ve trang thai camera tren xe dang chay hoac xe mac dinh cua tai xe."""
    try:
        row = db.fetch_one(
            """
            SELECT
                tb.device_id,
                tb.xe_id,
                x.bien_so,
                tb.fps,
                tb.camera_ok,
                tb.outbox_pending,
                tb.dead_letter_count,
                tb.lan_cuoi_ket_noi,
                EXTRACT(EPOCH FROM (NOW() - tb.lan_cuoi_ket_noi)) AS seconds_since_seen,
                ct.id AS chuyen_thuc_te_id,
                ct.trang_thai AS chuyen_trang_thai
            FROM thiet_bi_camera tb
            JOIN xe x ON tb.xe_id = x.id
            LEFT JOIN chuyen_thuc_te ct ON ct.xe_id = x.id AND ct.tai_xe_id = %s AND ct.trang_thai = 'DANG_CHAY'
            WHERE ct.id IS NOT NULL OR x.tai_xe_mac_dinh_id = %s
            ORDER BY (ct.id IS NOT NULL) DESC, tb.lan_cuoi_ket_noi DESC
            LIMIT 1
            """,
            (int(tai_xe_id), int(tai_xe_id)),
        )
        if not row:
            return {"status": "UNKNOWN", "online": False, "message": "Chưa có thiết bị camera gắn trên xe phụ trách."}

        secs = float(row.get("seconds_since_seen") or 9999)
        health = phan_loai_suc_khoe_thiet_bi(
            seconds_since_seen=secs,
            camera_ok=row.get("camera_ok", True),
            fps=row.get("fps", 0.0),
            outbox_pending=row.get("outbox_pending", 0),
            dead_letter_count=row.get("dead_letter_count", 0),
            online_timeout_seconds=timeout_seconds,
        )
        row["health_status"] = health
        row["online"] = health != "OFFLINE"
        row["seconds_since_seen"] = int(max(0, secs))
        return row
    except Exception as e:
        print("Lay trang thai camera cho tai xe error:", e)
        return {"status": "UNKNOWN", "online": False}
