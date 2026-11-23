"""
DACN1 V3.0 - Sprint 4: Dich vu Xac minh Su kien AI -> Vi pham (vi_pham)
va Phan he Khieu nai vi pham bat buoc (khieu_nai_vi_pham, lich_su_khieu_nai).
"""

from datetime import datetime, timedelta
import json

from database.mysql_service import (
    db,
    ghi_lich_su_thao_tac,
    them_ghi_chu,
)
from database.org_service import build_scope_filter_sql
from services.expo_push_service import send_push_to_account_async
from services.storage_service import resolve_snapshot_url


# ============================================================
# 1. XAC MINH SU KIEN AI -> VI PHAM (VIO-01, VIO-02, VIO-03)
# ============================================================

def lay_danh_sach_su_kien_ai_v3(scope=None, tai_xe_id=None, trang_thai=None, limit=50):
    try:
        where = ["1=1"]
        params = []
        if tai_xe_id is not None:
            where.append("sk.tai_xe_id = %s")
            params.append(int(tai_xe_id))
        else:
            scope_sql, scope_params = build_scope_filter_sql(scope, doi_xe_col="sk.doi_xe_id")
            if scope_sql != "1=1":
                where.append(scope_sql)
                params.extend(scope_params)
        if trang_thai:
            where.append("sk.trang_thai = %s")
            params.append(trang_thai)

        params.append(int(limit))
        sql = f"""
        SELECT
            sk.*,
            tx.ho_ten,
            x.bien_so,
            tk.ten_dang_nhap AS nguoi_xu_ly,
            vp.id AS vi_pham_id,
            vp.trang_thai AS vi_pham_trang_thai
        FROM su_kien_canh_bao sk
        LEFT JOIN tai_xe tx ON sk.tai_xe_id = tx.id
        LEFT JOIN xe x ON sk.xe_id = x.id
        LEFT JOIN tai_khoan tk ON sk.nguoi_xu_ly_id = tk.id
        LEFT JOIN vi_pham vp ON vp.su_kien_canh_bao_id = sk.id
        WHERE {' AND '.join(where)}
        ORDER BY sk.id DESC
        LIMIT %s
        """
        rows = db.fetch_all(sql, tuple(params))
        for row in rows:
            row["image_url"] = resolve_snapshot_url(row.get("duong_dan_anh"))
        return rows
    except Exception as e:
        print("Lay danh sach su kien ai v3 error:", e)
        return []


def quan_ly_xac_minh_vi_pham(su_kien_id, ly_do_xac_minh, actor_id, actor_role):
    """
    VIO-01, VIO-02, VIO-03:
    Quan ly kiem tra bang chung va xac minh 1 su_kien_canh_bao thanh 1 ban ghi vi_pham doc lap.
    Moi su kien AI tao toi da 1 vi pham (chan trung tra 409).
    """
    ly_do_clean = (ly_do_xac_minh or "").strip()
    if len(ly_do_clean) < 5:
        return None, 400, "Bắt buộc nhập lý do xác minh vi phạm chi tiết (tối thiểu 5 ký tự)."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM su_kien_canh_bao WHERE id = %s FOR UPDATE", (int(su_kien_id),))
            sk = cur.fetchone()
            if not sk:
                return None, 404, "Không tìm thấy sự kiện cảnh báo AI."
            sk = dict(sk)

            if sk.get("trang_thai") in ("CONFIRMED", "REJECTED", "CANH_BAO_SAI"):
                return None, 409, f"Sự kiện AI #{su_kien_id} đã được xử lý ({sk.get('trang_thai')})."

            if not sk.get("tai_xe_id"):
                return None, 400, "Sự kiện AI chưa xác định tài xế, không thể lập biên bản vi phạm cá nhân."

            # VIO-03: Khong xac nhan vi pham khi khong co anh bang chung
            if not sk.get("duong_dan_anh"):
                return None, 400, "Không đủ bằng chứng hình ảnh để xác minh vi phạm (VIO-03)."

            cur.execute("SELECT id FROM vi_pham WHERE su_kien_canh_bao_id = %s LIMIT 1", (int(su_kien_id),))
            if cur.fetchone():
                return None, 409, "Sự kiện AI này đã được xác minh thành vi phạm trước đó."

            doi_xe_id = sk.get("doi_xe_id")
            if doi_xe_id is None:
                cur.execute("SELECT doi_xe_id FROM tai_xe WHERE id = %s LIMIT 1", (sk["tai_xe_id"],))
                r_tx = cur.fetchone()
                if r_tx:
                    doi_xe_id = r_tx.get("doi_xe_id")

            cur.execute(
                """
                INSERT INTO vi_pham
                (
                    su_kien_canh_bao_id, chuyen_thuc_te_id, doi_xe_id,
                    tai_xe_id, xe_id, loai_vi_pham, duong_dan_anh,
                    trang_thai, nguoi_xac_minh_id, ly_do_xac_minh
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'HIEU_LUC', %s, %s)
                RETURNING id
                """,
                (
                    int(su_kien_id),
                    sk.get("chuyen_thuc_te_id"),
                    doi_xe_id,
                    sk["tai_xe_id"],
                    sk.get("xe_id"),
                    sk["loai_canh_bao"],
                    sk.get("duong_dan_anh"),
                    actor_id,
                    ly_do_clean,
                ),
            )
            vp_id = cur.fetchone()["id"]

            # Chi cap nhat cac cot xu ly cua con nguoi, KHONG sua du lieu AI goc
            cur.execute(
                """
                UPDATE su_kien_canh_bao
                SET
                    trang_thai = 'CONFIRMED',
                    nguoi_xu_ly_id = %s,
                    ghi_chu_xu_ly = %s,
                    thoi_gian_xu_ly = NOW()
                WHERE id = %s
                """,
                (actor_id, ly_do_clean, int(su_kien_id)),
            )

            cur.execute("SELECT tai_khoan_id FROM tai_xe WHERE id = %s LIMIT 1", (sk["tai_xe_id"],))
            tx_acc = cur.fetchone()
            tk_tx_id = tx_acc["tai_khoan_id"] if tx_acc else None

        msg = (
            f"Quản lý đã xác minh vi phạm #{vp_id} ({sk['loai_canh_bao']}). "
            f"Lý do: {ly_do_clean}. Bạn có quyền xem bằng chứng và gửi khiếu nại trong thời hạn quy định."
        )
        them_ghi_chu(tai_xe_id=sk["tai_xe_id"], quan_ly_id=actor_id, noi_dung=msg)
        if tk_tx_id:
            send_push_to_account_async(
                tai_khoan_id=tk_tx_id,
                title=f"Vi phạm đã xác minh • #{vp_id}",
                body=msg,
                data={"type": "VI_PHAM_XAC_NHAN", "vi_pham_id": vp_id},
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong="XAC_MINH_VI_PHAM",
            bang_du_lieu="vi_pham",
            doi_tuong_id=vp_id,
            du_lieu_truoc={"su_kien_trang_thai": sk["trang_thai"]},
            du_lieu_sau={"vi_pham_id": vp_id, "su_kien_trang_thai": "CONFIRMED", "tai_xe_id": sk["tai_xe_id"]},
            ly_do=ly_do_clean,
        )
        return vp_id, 201, "Đã xác minh sự kiện AI thành vi phạm và thông báo cho tài xế."
    except Exception as e:
        print("Xac minh vi pham error:", e)
        return None, 500, "Xác minh vi phạm thất bại."


def quan_ly_bac_bo_su_kien_ai(su_kien_id, ly_do, actor_id, actor_role, trang_thai="REJECTED"):
    tt = (trang_thai or "REJECTED").strip().upper()
    if tt not in ("REJECTED", "NEED_MORE_INFO", "UNDER_REVIEW"):
        return False, 400, "Trạng thái xử lý không hợp lệ."

    ly_do_clean = (ly_do or "").strip()
    if tt == "REJECTED" and len(ly_do_clean) < 3:
        return False, 400, "Bắt buộc nhập lý do khi bác bỏ sự kiện AI."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT id, trang_thai FROM su_kien_canh_bao WHERE id = %s FOR UPDATE", (int(su_kien_id),))
            sk = cur.fetchone()
            if not sk:
                return False, 404, "Không tìm thấy sự kiện AI."
            if sk["trang_thai"] in ("CONFIRMED", "REJECTED", "CANH_BAO_SAI"):
                return False, 409, f"Sự kiện AI đã ở trạng thái kết thúc ({sk['trang_thai']})."

            cur.execute(
                """
                UPDATE su_kien_canh_bao
                SET trang_thai = %s, nguoi_xu_ly_id = %s, ghi_chu_xu_ly = %s, thoi_gian_xu_ly = NOW()
                WHERE id = %s
                """,
                (tt, actor_id, ly_do_clean or None, int(su_kien_id)),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong=f"XU_LY_SU_KIEN_AI_{tt}",
            bang_du_lieu="su_kien_canh_bao",
            doi_tuong_id=int(su_kien_id),
            du_lieu_truoc={"trang_thai": sk["trang_thai"]},
            du_lieu_sau={"trang_thai": tt},
            ly_do=ly_do_clean or None,
        )
        return True, 200, f"Đã cập nhật sự kiện AI sang {tt}."
    except Exception as e:
        print("Bac bo su kien AI error:", e)
        return False, 500, "Cập nhật sự kiện AI thất bại."


def danh_gia_quyen_khieu_nai(
    vi_pham_row,
    so_khieu_nai_da_gui=0,
    co_khieu_nai_dang_mo=False,
    max_appeals=1,
    deadline_hours=72,
    now=None,
):
    """
    FIX-04: Ham thuan danh gia tai xe co duoc gui khieu nai cho vi pham hay khong.
    Tra ve (can_appeal: bool, block_reason: str | None, http_status: int).
    """
    if not isinstance(vi_pham_row, dict):
        return False, "Không tìm thấy vi phạm.", 404

    if vi_pham_row.get("trang_thai") == "DA_HUY_DO_KHIEU_NAI":
        return False, "Vi phạm này đã được hủy do khiếu nại trước đó.", 409

    if co_khieu_nai_dang_mo:
        return False, "Vi phạm này đang có khiếu nại chờ xử lý.", 409

    if int(so_khieu_nai_da_gui or 0) >= int(max_appeals or 1):
        return False, f"Vi phạm này đã đạt giới hạn tối đa ({max_appeals} lần khiếu nại).", 409

    xac_minh_at = vi_pham_row.get("xac_minh_at")
    if isinstance(xac_minh_at, datetime):
        ref_now = now or datetime.now()
        if ref_now.replace(tzinfo=None) - xac_minh_at.replace(tzinfo=None) > timedelta(hours=int(deadline_hours or 72)):
            return False, f"Đã quá thời hạn khiếu nại cho phép ({deadline_hours} giờ kể từ lúc xác minh).", 400

    return True, None, 200


def lay_danh_sach_vi_pham(scope=None, tai_xe_id=None, trang_thai=None, limit=100):
    try:
        where = ["1=1"]
        params = []
        if tai_xe_id is not None:
            where.append("vp.tai_xe_id = %s")
            params.append(int(tai_xe_id))
        else:
            scope_sql, scope_params = build_scope_filter_sql(scope, doi_xe_col="vp.doi_xe_id")
            if scope_sql != "1=1":
                where.append(scope_sql)
                params.extend(scope_params)
        if trang_thai:
            where.append("vp.trang_thai = %s")
            params.append(trang_thai)

        params.append(int(limit))
        sql = f"""
        SELECT
            vp.*,
            tx.ho_ten,
            x.bien_so,
            tk.ten_dang_nhap AS nguoi_xac_minh,
            sk.risk_score,
            sk.occurred_at,
            (SELECT COUNT(*) FROM khieu_nai_vi_pham kn WHERE kn.vi_pham_id = vp.id) AS so_khieu_nai,
            (
                SELECT COUNT(*) > 0 FROM khieu_nai_vi_pham kn
                WHERE kn.vi_pham_id = vp.id
                  AND kn.trang_thai IN ('SUBMITTED', 'RECEIVED', 'UNDER_REVIEW', 'NEED_MORE_INFO')
            ) AS co_khieu_nai_dang_mo
        FROM vi_pham vp
        LEFT JOIN tai_xe tx ON vp.tai_xe_id = tx.id
        LEFT JOIN xe x ON vp.xe_id = x.id
        LEFT JOIN tai_khoan tk ON vp.nguoi_xac_minh_id = tk.id
        LEFT JOIN su_kien_canh_bao sk ON vp.su_kien_canh_bao_id = sk.id
        WHERE {' AND '.join(where)}
        ORDER BY vp.id DESC
        LIMIT %s
        """
        rows = db.fetch_all(sql, tuple(params))
        for row in rows:
            row["image_url"] = resolve_snapshot_url(row.get("duong_dan_anh"))
            can_ap, block_reason, _ = danh_gia_quyen_khieu_nai(
                row,
                so_khieu_nai_da_gui=row.get("so_khieu_nai", 0),
                co_khieu_nai_dang_mo=bool(row.get("co_khieu_nai_dang_mo")),
            )
            row["can_appeal"] = can_ap
            row["appeal_block_reason"] = block_reason
        return rows
    except Exception as e:
        print("Lay danh sach vi pham error:", e)
        return []


# ============================================================
# 2. KHIEU NAI VI PHAM (APP-01, APP-02, FIX-04)
# ============================================================

def tai_xe_gui_khieu_nai(
    vi_pham_id,
    tai_xe_id,
    noi_dung_giai_trinh,
    minh_chung_urls=None,
    actor_id=None,
    han_khieu_nai_gio=72,
    max_appeals=1,
):
    noi_dung = (noi_dung_giai_trinh or "").strip()
    if len(noi_dung) < 5:
        return None, 400, "Vui lòng nhập nội dung giải trình khiếu nại chi tiết (tối thiểu 5 ký tự)."

    urls = minh_chung_urls if isinstance(minh_chung_urls, list) else []

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM vi_pham WHERE id = %s FOR UPDATE", (int(vi_pham_id),))
            vp = cur.fetchone()
            if not vp:
                return None, 404, "Không tìm thấy vi phạm."
            vp = dict(vp)

            if int(vp["tai_xe_id"]) != int(tai_xe_id):
                return None, 403, "Bạn chỉ được khiếu nại vi phạm của chính mình."

            cur.execute(
                """
                SELECT
                    COUNT(*) AS tong,
                    COUNT(*) FILTER (WHERE trang_thai IN ('SUBMITTED', 'RECEIVED', 'UNDER_REVIEW', 'NEED_MORE_INFO')) AS dang_mo
                FROM khieu_nai_vi_pham
                WHERE vi_pham_id = %s
                """,
                (int(vi_pham_id),),
            )
            cnt = cur.fetchone() or {}
            so_da_gui = int(cnt.get("tong") or 0)
            dang_mo = int(cnt.get("dang_mo") or 0) > 0

            can_ap, block_reason, err_code = danh_gia_quyen_khieu_nai(
                vp,
                so_khieu_nai_da_gui=so_da_gui,
                co_khieu_nai_dang_mo=dang_mo,
                max_appeals=max_appeals,
                deadline_hours=han_khieu_nai_gio,
            )
            if not can_ap:
                return None, err_code, block_reason

            lan_khieu_nai = so_da_gui + 1
            cur.execute(
                """
                INSERT INTO khieu_nai_vi_pham
                (vi_pham_id, doi_xe_id, tai_xe_id, noi_dung_giai_trinh, minh_chung_urls, trang_thai, lan_khieu_nai)
                VALUES (%s, %s, %s, %s, %s::jsonb, 'SUBMITTED', %s)
                RETURNING id
                """,
                (
                    int(vi_pham_id),
                    vp.get("doi_xe_id"),
                    int(tai_xe_id),
                    noi_dung,
                    json.dumps(urls, ensure_ascii=False),
                    lan_khieu_nai,
                ),
            )
            kn_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO lich_su_khieu_nai (khieu_nai_id, old_status, new_status, actor_id, ghi_chu)
                VALUES (%s, NULL, 'SUBMITTED', %s, 'Tài xế gửi khiếu nại và giải trình')
                """,
                (kn_id, actor_id),
            )

            cur.execute(
                "UPDATE vi_pham SET trang_thai = 'DANG_KHIEU_NAI' WHERE id = %s",
                (int(vi_pham_id),),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro="tai_xe",
            hanh_dong="GUI_KHIEU_NAI_VI_PHAM",
            bang_du_lieu="khieu_nai_vi_pham",
            doi_tuong_id=kn_id,
            du_lieu_sau={"vi_pham_id": int(vi_pham_id), "trang_thai": "SUBMITTED"},
        )
        return kn_id, 201, "Đã gửi khiếu nại thành công. Quản lý sẽ xem xét và phản hồi."
    except Exception as e:
        print("Gui khieu nai error:", e)
        return None, 500, "Gửi khiếu nại thất bại."


def tai_xe_bo_sung_khieu_nai(khieu_nai_id, tai_xe_id, ghi_chu_bo_sung, minh_chung_urls=None, actor_id=None):
    """APP-01: Bo sung minh chung khi NEED_MORE_INFO, KHONG sua noi_dung_giai_trinh goc."""
    ghi_chu = (ghi_chu_bo_sung or "").strip()
    new_urls = minh_chung_urls if isinstance(minh_chung_urls, list) else []
    if not ghi_chu and not new_urls:
        return False, 400, "Vui lòng nhập nội dung bổ sung hoặc đính kèm minh chứng."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM khieu_nai_vi_pham WHERE id = %s FOR UPDATE", (int(khieu_nai_id),))
            kn = cur.fetchone()
            if not kn:
                return False, 404, "Không tìm thấy khiếu nại."
            kn = dict(kn)

            if int(kn["tai_xe_id"]) != int(tai_xe_id):
                return False, 403, "Không có quyền bổ sung khiếu nại của tài xế khác."
            if kn["trang_thai"] != "NEED_MORE_INFO":
                return False, 409, "Chỉ được bổ sung khi quản lý yêu cầu (NEED_MORE_INFO)."

            existing_urls = kn.get("minh_chung_urls") or []
            if isinstance(existing_urls, str):
                existing_urls = json.loads(existing_urls)
            merged_urls = list(existing_urls) + new_urls

            cur.execute(
                "UPDATE khieu_nai_vi_pham SET minh_chung_urls = %s::jsonb, trang_thai = 'UNDER_REVIEW' WHERE id = %s",
                (json.dumps(merged_urls, ensure_ascii=False), int(khieu_nai_id)),
            )
            cur.execute(
                """
                INSERT INTO lich_su_khieu_nai (khieu_nai_id, old_status, new_status, actor_id, ghi_chu)
                VALUES (%s, 'NEED_MORE_INFO', 'UNDER_REVIEW', %s, %s)
                """,
                (int(khieu_nai_id), actor_id, ghi_chu or "Tài xế đã bổ sung minh chứng"),
            )
        return True, 200, "Đã bổ sung thông tin khiếu nại."
    except Exception as e:
        print("Bo sung khieu nai error:", e)
        return False, 500, "Bổ sung khiếu nại thất bại."


def quan_ly_xu_ly_khieu_nai(khieu_nai_id, quyet_dinh, ly_do_ket_luan=None, actor_id=None, actor_role="quan_ly"):
    """
    APP-02:
    - ACCEPTED / REJECTED: bat buoc nhap ly do ket luan.
    - ACCEPTED: tu dong cap nhat vi_pham.trang_thai = 'DA_HUY_DO_KHIEU_NAI' (su kien AI goc van bat bien).
    - REJECTED: cap nhat vi_pham.trang_thai = 'GIU_NGUYEN'.
    """
    decision = (quyet_dinh or "").strip().upper()
    if decision not in ("RECEIVED", "UNDER_REVIEW", "NEED_MORE_INFO", "ACCEPTED", "REJECTED", "CLOSED"):
        return False, 400, "Trạng thái quyết định khiếu nại không hợp lệ."

    ly_do_clean = (ly_do_ket_luan or "").strip()
    if decision in ("ACCEPTED", "REJECTED") and len(ly_do_clean) < 5:
        return False, 400, "Bắt buộc nhập lý do kết luận chi tiết (tối thiểu 5 ký tự) khi chấp nhận hoặc bác bỏ khiếu nại."

    try:
        with db.transaction() as cur:
            cur.execute("SELECT * FROM khieu_nai_vi_pham WHERE id = %s FOR UPDATE", (int(khieu_nai_id),))
            kn = cur.fetchone()
            if not kn:
                return False, 404, "Không tìm thấy khiếu nại."
            kn = dict(kn)
            old_status = kn["trang_thai"]

            if old_status == "CLOSED":
                return False, 409, "Khiếu nại đã đóng (CLOSED), không thể cập nhật lại."

            if decision in ("ACCEPTED", "REJECTED"):
                cur.execute(
                    """
                    UPDATE khieu_nai_vi_pham
                    SET
                        trang_thai = %s,
                        nguoi_xu_ly_id = %s,
                        ket_luan = %s,
                        ly_do_ket_luan = %s,
                        decided_at = NOW()
                    WHERE id = %s
                    """,
                    (decision, actor_id, decision, ly_do_clean, int(khieu_nai_id)),
                )
                new_vp_status = "DA_HUY_DO_KHIEU_NAI" if decision == "ACCEPTED" else "GIU_NGUYEN"
                cur.execute(
                    "UPDATE vi_pham SET trang_thai = %s WHERE id = %s",
                    (new_vp_status, kn["vi_pham_id"]),
                )
            else:
                cur.execute(
                    """
                    UPDATE khieu_nai_vi_pham
                    SET trang_thai = %s, nguoi_xu_ly_id = %s, ly_do_ket_luan = COALESCE(%s, ly_do_ket_luan)
                    WHERE id = %s
                    """,
                    (decision, actor_id, ly_do_clean or None, int(khieu_nai_id)),
                )

            cur.execute(
                """
                INSERT INTO lich_su_khieu_nai (khieu_nai_id, old_status, new_status, actor_id, ghi_chu)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (int(khieu_nai_id), old_status, decision, actor_id, ly_do_clean or f"Chuyển trạng thái sang {decision}"),
            )

            cur.execute("SELECT tai_khoan_id FROM tai_xe WHERE id = %s LIMIT 1", (kn["tai_xe_id"],))
            tx_acc = cur.fetchone()
            tk_tx_id = tx_acc["tai_khoan_id"] if tx_acc else None

        if decision in ("ACCEPTED", "REJECTED", "NEED_MORE_INFO"):
            label_map = {
                "ACCEPTED": "CHẤP NHẬN (Vi phạm đã được hủy)",
                "REJECTED": "BÁC BỎ (Giữ nguyên hiệu lực vi phạm)",
                "NEED_MORE_INFO": "YÊU CẦU BỔ SUNG THÔNG TIN",
            }
            msg = f"Khiếu nại #{khieu_nai_id} cho vi phạm #{kn['vi_pham_id']}: {label_map[decision]}. Lý do: {ly_do_clean}"
            them_ghi_chu(tai_xe_id=kn["tai_xe_id"], quan_ly_id=actor_id, noi_dung=msg)
            if tk_tx_id:
                send_push_to_account_async(
                    tai_khoan_id=tk_tx_id,
                    title=f"Kết quả khiếu nại #{khieu_nai_id}",
                    body=msg,
                    data={"type": "KET_QUA_KHIEU_NAI", "khieu_nai_id": int(khieu_nai_id), "decision": decision},
                )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong=f"XU_LY_KHIEU_NAI_{decision}",
            bang_du_lieu="khieu_nai_vi_pham",
            doi_tuong_id=int(khieu_nai_id),
            du_lieu_truoc={"trang_thai": old_status},
            du_lieu_sau={"trang_thai": decision, "vi_pham_id": kn["vi_pham_id"]},
            ly_do=ly_do_clean or None,
        )
        return True, 200, f"Đã xử lý khiếu nại ({decision})."
    except Exception as e:
        print("Xu ly khieu nai error:", e)
        return False, 500, "Xử lý khiếu nại thất bại."


def lay_danh_sach_khieu_nai(scope=None, tai_xe_id=None, trang_thai=None, limit=100):
    try:
        where = ["1=1"]
        params = []
        if tai_xe_id is not None:
            where.append("kn.tai_xe_id = %s")
            params.append(int(tai_xe_id))
        else:
            scope_sql, scope_params = build_scope_filter_sql(scope, doi_xe_col="kn.doi_xe_id")
            if scope_sql != "1=1":
                where.append(scope_sql)
                params.extend(scope_params)
        if trang_thai:
            where.append("kn.trang_thai = %s")
            params.append(trang_thai)

        params.append(int(limit))
        sql = f"""
        SELECT
            kn.*,
            tx.ho_ten,
            vp.loai_vi_pham,
            vp.trang_thai AS vi_pham_trang_thai,
            vp.ly_do_xac_minh,
            vp.duong_dan_anh AS vi_pham_anh,
            tk.ten_dang_nhap AS nguoi_xu_ly
        FROM khieu_nai_vi_pham kn
        JOIN vi_pham vp ON kn.vi_pham_id = vp.id
        LEFT JOIN tai_xe tx ON kn.tai_xe_id = tx.id
        LEFT JOIN tai_khoan tk ON kn.nguoi_xu_ly_id = tk.id
        WHERE {' AND '.join(where)}
        ORDER BY kn.id DESC
        LIMIT %s
        """
        rows = db.fetch_all(sql, tuple(params))
        for row in rows:
            row["vi_pham_image_url"] = resolve_snapshot_url(row.get("vi_pham_anh"))
        return rows
    except Exception as e:
        print("Lay danh sach khieu nai error:", e)
        return []


def lay_lich_su_khieu_nai(khieu_nai_id):
    try:
        return db.fetch_all(
            """
            SELECT ls.*, tk.ten_dang_nhap AS actor_name
            FROM lich_su_khieu_nai ls
            LEFT JOIN tai_khoan tk ON ls.actor_id = tk.id
            WHERE ls.khieu_nai_id = %s
            ORDER BY ls.id ASC
            """,
            (int(khieu_nai_id),),
        )
    except Exception as e:
        print("Lay lich su khieu nai error:", e)
        return []
