"""
DACN1 V3.0 - Dich vu To chuc da chi nhanh (Cong ty -> Chi nhanh -> Doi xe),
Quan ly Tai khoan/RBAC 6 vai tro, Dieu chuyen doi xe & Audit Log.
"""

import json

from core.ops_rules import (
    ROLE_ADMIN_HE_THONG,
    ROLE_QUAN_TRI_CONG_TY,
    la_vai_tro_hop_le,
    xac_dinh_cap_pham_vi,
)
from database.mysql_service import (
    chuyen_int_hoac_none,
    db,
    ghi_lich_su_thao_tac,
    hash_password,
    verify_password,
)


def build_scope_filter_sql(scope, doi_xe_col="doi_xe_id", chi_nhanh_col=None, cong_ty_col=None):
    """
    Xay dung menh de WHERE & params loc Data Scope tu dong cho PostgreSQL.
    Tra ve (where_clause_str, params_list). Neu khong can loc -> ("1=1", []).
    """
    if not isinstance(scope, dict):
        return "1=1", []

    role = scope.get("vai_tro")
    level = xac_dinh_cap_pham_vi(role)
    if level == "SYSTEM":
        return "1=1", []

    if level == "COMPANY":
        cty_id = scope.get("cong_ty_id")
        if cty_id is None:
            return "1=1", []
        if cong_ty_col:
            return f"{cong_ty_col} = %s", [int(cty_id)]
        return (
            f"{doi_xe_col} IN ("
            "SELECT dx.id FROM doi_xe dx "
            "JOIN chi_nhanh cn ON dx.chi_nhanh_id = cn.id "
            "WHERE cn.cong_ty_id = %s"
            ")",
            [int(cty_id)],
        )

    if level == "UNIT":
        dx_id = scope.get("doi_xe_id")
        if dx_id is not None:
            return f"{doi_xe_col} = %s", [int(dx_id)]

        cn_id = scope.get("chi_nhanh_id")
        if cn_id is not None:
            if chi_nhanh_col:
                return f"{chi_nhanh_col} = %s", [int(cn_id)]
            return (
                f"{doi_xe_col} IN (SELECT id FROM doi_xe WHERE chi_nhanh_id = %s)",
                [int(cn_id)],
            )

        cty_id = scope.get("cong_ty_id")
        if cty_id is not None:
            if cong_ty_col:
                return f"{cong_ty_col} = %s", [int(cty_id)]
            return (
                f"{doi_xe_col} IN ("
                "SELECT dx.id FROM doi_xe dx "
                "JOIN chi_nhanh cn ON dx.chi_nhanh_id = cn.id "
                "WHERE cn.cong_ty_id = %s"
                ")",
                [int(cty_id)],
            )

    return "1=1", []


def lay_pham_vi_tai_khoan(tai_khoan_id):
    """
    Lay thong tin vai tro + pham vi don vi cua tai khoan truc tiep tu DB.
    Ho tro fallback an toan neu DB chua chay migration V3.
    """
    try:
        row = db.fetch_one(
            """
            SELECT
                tk.id,
                tk.ten_dang_nhap,
                tk.vai_tro,
                tk.trang_thai,
                tk.cong_ty_id,
                tk.chi_nhanh_id,
                tk.doi_xe_id,
                tx.id AS tai_xe_id,
                COALESCE(tk.doi_xe_id, tx.doi_xe_id) AS resolved_doi_xe_id
            FROM tai_khoan tk
            LEFT JOIN tai_xe tx ON tx.tai_khoan_id = tk.id
            WHERE tk.id = %s
            LIMIT 1
            """,
            (tai_khoan_id,),
        )
        if not row:
            return None
        row["doi_xe_id"] = row.get("resolved_doi_xe_id")
        row.pop("resolved_doi_xe_id", None)
        return row
    except Exception:
        # Fallback tuong thich nguoc khi DB chua co cot cong_ty_id/chi_nhanh_id/doi_xe_id
        try:
            row = db.fetch_one(
                """
                SELECT
                    tk.id,
                    tk.ten_dang_nhap,
                    tk.vai_tro,
                    tk.trang_thai,
                    tx.id AS tai_xe_id
                FROM tai_khoan tk
                LEFT JOIN tai_xe tx ON tx.tai_khoan_id = tk.id
                WHERE tk.id = %s
                LIMIT 1
                """,
                (tai_khoan_id,),
            )
            if not row:
                return None
            row["cong_ty_id"] = None
            row["chi_nhanh_id"] = None
            row["doi_xe_id"] = None
            return row
        except Exception:
            return None


# ============================================================
# CONG TY / CHI NHANH / DOI XE
# ============================================================

def lay_danh_sach_cong_ty(scope=None):
    try:
        sql = "SELECT * FROM cong_ty"
        params = []
        if scope and scope.get("vai_tro") != ROLE_ADMIN_HE_THONG and scope.get("cong_ty_id"):
            sql += " WHERE id = %s"
            params.append(int(scope["cong_ty_id"]))
        sql += " ORDER BY id ASC"
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach cong ty error:", e)
        return []


def cap_nhat_cau_hinh_cong_ty(cong_ty_id, cau_hinh_dict, actor_id, actor_role):
    try:
        cu = db.fetch_one("SELECT * FROM cong_ty WHERE id = %s LIMIT 1", (cong_ty_id,))
        if not cu:
            return False

        hien_tai = cu.get("cau_hinh_jsonb") or {}
        if isinstance(hien_tai, str):
            hien_tai = json.loads(hien_tai)
        moi = dict(hien_tai)
        moi.update(cau_hinh_dict or {})

        db.execute(
            "UPDATE cong_ty SET cau_hinh_jsonb = %s::jsonb WHERE id = %s",
            (json.dumps(moi, ensure_ascii=False), cong_ty_id),
        )
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong="CAP_NHAT_CAU_HINH_CONG_TY",
            bang_du_lieu="cong_ty",
            doi_tuong_id=cong_ty_id,
            du_lieu_truoc={"cau_hinh_jsonb": hien_tai},
            du_lieu_sau={"cau_hinh_jsonb": moi},
        )
        return True
    except Exception as e:
        print("Cap nhat cau hinh cong ty error:", e)
        return False


def lay_danh_sach_chi_nhanh(scope=None, cong_ty_id=None):
    try:
        where = ["1=1"]
        params = []
        if cong_ty_id:
            where.append("cn.cong_ty_id = %s")
            params.append(int(cong_ty_id))
        if scope:
            role = scope.get("vai_tro")
            if role != ROLE_ADMIN_HE_THONG:
                if scope.get("cong_ty_id"):
                    where.append("cn.cong_ty_id = %s")
                    params.append(int(scope["cong_ty_id"]))
                if role != ROLE_QUAN_TRI_CONG_TY and scope.get("chi_nhanh_id"):
                    where.append("cn.id = %s")
                    params.append(int(scope["chi_nhanh_id"]))

        sql = f"""
        SELECT
            cn.*,
            ct.ten AS ten_cong_ty,
            (SELECT COUNT(*) FROM doi_xe dx WHERE dx.chi_nhanh_id = cn.id) AS so_doi_xe
        FROM chi_nhanh cn
        JOIN cong_ty ct ON cn.cong_ty_id = ct.id
        WHERE {' AND '.join(where)}
        ORDER BY cn.id ASC
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach chi nhanh error:", e)
        return []


def tao_chi_nhanh(cong_ty_id, ma_chi_nhanh, ten, dia_chi=None, so_dien_thoai=None, actor_id=None, actor_role=None):
    try:
        ma = (ma_chi_nhanh or "").strip().upper()
        ten = (ten or "").strip()
        if not cong_ty_id or not ma or not ten:
            return None

        res = db.execute(
            """
            INSERT INTO chi_nhanh (cong_ty_id, ma_chi_nhanh, ten, dia_chi, so_dien_thoai)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (int(cong_ty_id), ma, ten, dia_chi, so_dien_thoai),
        )
        new_id = res.lastrowid
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role or "quan_tri_cong_ty",
            hanh_dong="TAO_CHI_NHANH",
            bang_du_lieu="chi_nhanh",
            doi_tuong_id=new_id,
            du_lieu_sau={"cong_ty_id": int(cong_ty_id), "ma_chi_nhanh": ma, "ten": ten},
        )
        return new_id
    except Exception as e:
        print("Tao chi nhanh error:", e)
        return None


def cap_nhat_chi_nhanh(chi_nhanh_id, ten=None, dia_chi=None, so_dien_thoai=None, trang_thai=None, actor_id=None, actor_role=None):
    try:
        cu = db.fetch_one("SELECT * FROM chi_nhanh WHERE id = %s LIMIT 1", (chi_nhanh_id,))
        if not cu:
            return False

        ten_moi = (ten or cu["ten"]).strip()
        tt_moi = (trang_thai or cu["trang_thai"]).strip().upper()
        if tt_moi not in ("HOAT_DONG", "TAM_NGUNG"):
            return False

        db.execute(
            """
            UPDATE chi_nhanh
            SET ten = %s, dia_chi = %s, so_dien_thoai = %s, trang_thai = %s
            WHERE id = %s
            """,
            (
                ten_moi,
                dia_chi if dia_chi is not None else cu.get("dia_chi"),
                so_dien_thoai if so_dien_thoai is not None else cu.get("so_dien_thoai"),
                tt_moi,
                chi_nhanh_id,
            ),
        )
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role or "quan_tri_cong_ty",
            hanh_dong="CAP_NHAT_CHI_NHANH",
            bang_du_lieu="chi_nhanh",
            doi_tuong_id=chi_nhanh_id,
            du_lieu_truoc=cu,
            du_lieu_sau={"ten": ten_moi, "trang_thai": tt_moi},
        )
        return True
    except Exception as e:
        print("Cap nhat chi nhanh error:", e)
        return False


def lay_danh_sach_doi_xe(scope=None, chi_nhanh_id=None):
    try:
        where = ["1=1"]
        params = []
        if chi_nhanh_id:
            where.append("dx.chi_nhanh_id = %s")
            params.append(int(chi_nhanh_id))

        scope_sql, scope_params = build_scope_filter_sql(
            scope,
            doi_xe_col="dx.id",
            chi_nhanh_col="dx.chi_nhanh_id",
            cong_ty_col="cn.cong_ty_id",
        )
        if scope_sql != "1=1":
            where.append(scope_sql)
            params.extend(scope_params)

        sql = f"""
        SELECT
            dx.*,
            cn.ten AS ten_chi_nhanh,
            cn.cong_ty_id,
            (SELECT COUNT(*) FROM tai_xe tx WHERE tx.doi_xe_id = dx.id) AS so_tai_xe,
            (SELECT COUNT(*) FROM xe x WHERE x.doi_xe_id = dx.id) AS so_xe
        FROM doi_xe dx
        JOIN chi_nhanh cn ON dx.chi_nhanh_id = cn.id
        WHERE {' AND '.join(where)}
        ORDER BY dx.id ASC
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach doi xe error:", e)
        return []


def tao_doi_xe(chi_nhanh_id, ma_doi_xe, ten, mo_ta=None, actor_id=None, actor_role=None):
    try:
        ma = (ma_doi_xe or "").strip().upper()
        ten = (ten or "").strip()
        if not chi_nhanh_id or not ma or not ten:
            return None

        res = db.execute(
            """
            INSERT INTO doi_xe (chi_nhanh_id, ma_doi_xe, ten, mo_ta)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (int(chi_nhanh_id), ma, ten, mo_ta),
        )
        new_id = res.lastrowid
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role or "quan_ly",
            hanh_dong="TAO_DOI_XE",
            bang_du_lieu="doi_xe",
            doi_tuong_id=new_id,
            du_lieu_sau={"chi_nhanh_id": int(chi_nhanh_id), "ma_doi_xe": ma, "ten": ten},
        )
        return new_id
    except Exception as e:
        print("Tao doi xe error:", e)
        return None


def cap_nhat_doi_xe(doi_xe_id, ten=None, mo_ta=None, trang_thai=None, actor_id=None, actor_role=None):
    try:
        cu = db.fetch_one("SELECT * FROM doi_xe WHERE id = %s LIMIT 1", (doi_xe_id,))
        if not cu:
            return False

        ten_moi = (ten or cu["ten"]).strip()
        tt_moi = (trang_thai or cu["trang_thai"]).strip().upper()
        if tt_moi not in ("HOAT_DONG", "TAM_NGUNG"):
            return False

        db.execute(
            "UPDATE doi_xe SET ten = %s, mo_ta = %s, trang_thai = %s WHERE id = %s",
            (ten_moi, mo_ta if mo_ta is not None else cu.get("mo_ta"), tt_moi, doi_xe_id),
        )
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role or "quan_ly",
            hanh_dong="CAP_NHAT_DOI_XE",
            bang_du_lieu="doi_xe",
            doi_tuong_id=doi_xe_id,
            du_lieu_truoc=cu,
            du_lieu_sau={"ten": ten_moi, "trang_thai": tt_moi},
        )
        return True
    except Exception as e:
        print("Cap nhat doi xe error:", e)
        return False


def chuyen_doi_xe_thuc_the(entity_type, entity_id, doi_xe_moi_id, ly_do, actor_id, actor_role):
    """
    ORG-02: Chuyen tai xe hoac phuong tien sang doi xe moi trong 1 transaction,
    bat buoc nhap ly do va luu lich_su_chuyen_doi_xe + audit log.
    """
    etype = str(entity_type or "").strip().upper()
    ly_do_clean = str(ly_do or "").strip()
    if etype not in ("TAI_XE", "XE") or not ly_do_clean or not doi_xe_moi_id:
        return False, "Thiếu loại thực thể hợp lệ, đội xe mới hoặc lý do điều chuyển."

    table = "tai_xe" if etype == "TAI_XE" else "xe"
    try:
        with db.transaction() as cur:
            cur.execute(f"SELECT id, doi_xe_id FROM {table} WHERE id = %s FOR UPDATE", (int(entity_id),))
            row = cur.fetchone()
            if not row:
                return False, "Không tìm thấy đối tượng cần điều chuyển."

            doi_xe_cu_id = row.get("doi_xe_id")
            if doi_xe_cu_id is not None and int(doi_xe_cu_id) == int(doi_xe_moi_id):
                return False, "Đối tượng đã thuộc đội xe này."

            cur.execute("SELECT id, chi_nhanh_id FROM doi_xe WHERE id = %s LIMIT 1", (int(doi_xe_moi_id),))
            dx_moi = cur.fetchone()
            if not dx_moi:
                return False, "Đội xe đích không tồn tại."

            cur.execute(f"UPDATE {table} SET doi_xe_id = %s WHERE id = %s", (int(doi_xe_moi_id), int(entity_id)))

            # Neu la tai xe co tai khoan -> dong bo luon doi_xe_id & chi_nhanh_id tren tai_khoan
            if etype == "TAI_XE":
                cur.execute(
                    """
                    UPDATE tai_khoan
                    SET doi_xe_id = %s, chi_nhanh_id = %s
                    WHERE id = (SELECT tai_khoan_id FROM tai_xe WHERE id = %s)
                    """,
                    (int(doi_xe_moi_id), int(dx_moi["chi_nhanh_id"]), int(entity_id)),
                )

            cur.execute(
                """
                INSERT INTO lich_su_chuyen_doi_xe
                (entity_type, entity_id, doi_xe_cu_id, doi_xe_moi_id, ly_do, nguoi_thuc_hien_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (etype, int(entity_id), doi_xe_cu_id, int(doi_xe_moi_id), ly_do_clean, actor_id),
            )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role,
            hanh_dong=f"CHUYEN_DOI_XE_{etype}",
            bang_du_lieu=table,
            doi_tuong_id=int(entity_id),
            ghi_chu=f"Điều chuyển {etype} #{entity_id} từ đội xe {doi_xe_cu_id} -> {doi_xe_moi_id}",
            du_lieu_truoc={"doi_xe_id": doi_xe_cu_id},
            du_lieu_sau={"doi_xe_id": int(doi_xe_moi_id)},
            ly_do=ly_do_clean,
        )
        return True, "Đã điều chuyển đội xe thành công."
    except Exception as e:
        print("Chuyen doi xe error:", e)
        return False, "Điều chuyển đội xe thất bại."


# ============================================================
# QUAN LY TAI KHOAN, PHAN QUYEN & DOI MAT KHAU
# ============================================================

def lay_danh_sach_tai_khoan(scope=None):
    try:
        where = ["1=1"]
        params = []
        if scope and scope.get("vai_tro") != ROLE_ADMIN_HE_THONG:
            if scope.get("cong_ty_id"):
                where.append("tk.cong_ty_id = %s")
                params.append(int(scope["cong_ty_id"]))
            if scope.get("vai_tro") != ROLE_QUAN_TRI_CONG_TY:
                if scope.get("doi_xe_id"):
                    where.append("tk.doi_xe_id = %s")
                    params.append(int(scope["doi_xe_id"]))
                elif scope.get("chi_nhanh_id"):
                    where.append("tk.chi_nhanh_id = %s")
                    params.append(int(scope["chi_nhanh_id"]))

        sql = f"""
        SELECT
            tk.id,
            tk.ten_dang_nhap,
            tk.vai_tro,
            tk.trang_thai,
            tk.cong_ty_id,
            tk.chi_nhanh_id,
            tk.doi_xe_id,
            tk.ngay_tao,
            ct.ten AS ten_cong_ty,
            cn.ten AS ten_chi_nhanh,
            dx.ten AS ten_doi_xe,
            tx.id AS tai_xe_id,
            tx.ho_ten AS ho_ten_tai_xe
        FROM tai_khoan tk
        LEFT JOIN cong_ty ct ON tk.cong_ty_id = ct.id
        LEFT JOIN chi_nhanh cn ON tk.chi_nhanh_id = cn.id
        LEFT JOIN doi_xe dx ON tk.doi_xe_id = dx.id
        LEFT JOIN tai_xe tx ON tx.tai_khoan_id = tk.id
        WHERE {' AND '.join(where)}
        ORDER BY tk.id DESC
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay danh sach tai khoan error:", e)
        return []


def tao_tai_khoan_he_thong(
    ten_dang_nhap,
    mat_khau,
    vai_tro,
    cong_ty_id=None,
    chi_nhanh_id=None,
    doi_xe_id=None,
    actor_id=None,
    actor_role=None,
):
    ten_dn = (ten_dang_nhap or "").strip()
    mk = (mat_khau or "").strip()
    role = (vai_tro or "").strip()

    if not ten_dn or len(mk) < 4 or not la_vai_tro_hop_le(role):
        return None, "Tên đăng nhập, mật khẩu (tối thiểu 4 ký tự) hoặc vai trò không hợp lệ."

    try:
        hashed = hash_password(mk)
        res = db.execute(
            """
            INSERT INTO tai_khoan
            (ten_dang_nhap, mat_khau, vai_tro, trang_thai, cong_ty_id, chi_nhanh_id, doi_xe_id)
            VALUES (%s, %s, %s, 'hoat_dong', %s, %s, %s)
            RETURNING id
            """,
            (
                ten_dn,
                hashed,
                role,
                chuyen_int_hoac_none(cong_ty_id),
                chuyen_int_hoac_none(chi_nhanh_id),
                chuyen_int_hoac_none(doi_xe_id),
            ),
        )
        new_id = res.lastrowid
        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role or "admin_he_thong",
            hanh_dong="TAO_TAI_KHOAN",
            bang_du_lieu="tai_khoan",
            doi_tuong_id=new_id,
            du_lieu_sau={
                "ten_dang_nhap": ten_dn,
                "vai_tro": role,
                "cong_ty_id": chuyen_int_hoac_none(cong_ty_id),
                "chi_nhanh_id": chuyen_int_hoac_none(chi_nhanh_id),
                "doi_xe_id": chuyen_int_hoac_none(doi_xe_id),
            },
        )
        return new_id, "Đã tạo tài khoản thành công."
    except Exception as e:
        print("Tao tai khoan he thong error:", e)
        return None, "Không thể tạo tài khoản (tên đăng nhập có thể đã tồn tại)."


def cap_nhat_tai_khoan_va_quyen(
    tai_khoan_id,
    vai_tro=None,
    trang_thai=None,
    cong_ty_id=None,
    chi_nhanh_id=None,
    doi_xe_id=None,
    ly_do=None,
    actor_id=None,
    actor_role=None,
):
    try:
        cu = db.fetch_one(
            "SELECT id, ten_dang_nhap, vai_tro, trang_thai, cong_ty_id, chi_nhanh_id, doi_xe_id FROM tai_khoan WHERE id = %s LIMIT 1",
            (tai_khoan_id,),
        )
        if not cu:
            return False, "Không tìm thấy tài khoản."

        role_moi = (vai_tro or cu["vai_tro"]).strip()
        if not la_vai_tro_hop_le(role_moi):
            return False, "Vai trò không hợp lệ."

        tt_moi = (trang_thai or cu["trang_thai"]).strip()
        if tt_moi not in ("hoat_dong", "khoa"):
            return False, "Trạng thái tài khoản không hợp lệ."

        cty_moi = chuyen_int_hoac_none(cong_ty_id) if cong_ty_id is not None else cu.get("cong_ty_id")
        cn_moi = chuyen_int_hoac_none(chi_nhanh_id) if chi_nhanh_id is not None else cu.get("chi_nhanh_id")
        dx_moi = chuyen_int_hoac_none(doi_xe_id) if doi_xe_id is not None else cu.get("doi_xe_id")

        db.execute(
            """
            UPDATE tai_khoan
            SET vai_tro = %s, trang_thai = %s, cong_ty_id = %s, chi_nhanh_id = %s, doi_xe_id = %s
            WHERE id = %s
            """,
            (role_moi, tt_moi, cty_moi, cn_moi, dx_moi, tai_khoan_id),
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=actor_id,
            vai_tro=actor_role or "admin_he_thong",
            hanh_dong="CAP_NHAT_TAI_KHOAN",
            bang_du_lieu="tai_khoan",
            doi_tuong_id=tai_khoan_id,
            du_lieu_truoc=cu,
            du_lieu_sau={
                "vai_tro": role_moi,
                "trang_thai": tt_moi,
                "cong_ty_id": cty_moi,
                "chi_nhanh_id": cn_moi,
                "doi_xe_id": dx_moi,
            },
            ly_do=ly_do,
        )
        return True, "Đã cập nhật tài khoản."
    except Exception as e:
        print("Cap nhat tai khoan error:", e)
        return False, "Cập nhật tài khoản thất bại."


def doi_mat_khau_tai_khoan(tai_khoan_id, mat_khau_cu, mat_khau_moi):
    try:
        if not mat_khau_moi or len(str(mat_khau_moi).strip()) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự."

        row = db.fetch_one("SELECT id, vai_tro, mat_khau FROM tai_khoan WHERE id = %s LIMIT 1", (tai_khoan_id,))
        if not row:
            return False, "Không tìm thấy tài khoản."

        matched, _ = verify_password(mat_khau_cu or "", row["mat_khau"])
        if not matched:
            return False, "Mật khẩu hiện tại không đúng."

        new_hash = hash_password(str(mat_khau_moi).strip())
        db.execute("UPDATE tai_khoan SET mat_khau = %s WHERE id = %s", (new_hash, tai_khoan_id))

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=tai_khoan_id,
            vai_tro=row.get("vai_tro") or "tai_xe",
            hanh_dong="DOI_MAT_KHAU",
            bang_du_lieu="tai_khoan",
            doi_tuong_id=tai_khoan_id,
            ghi_chu="Người dùng tự đổi mật khẩu",
        )
        return True, "Đổi mật khẩu thành công."
    except Exception as e:
        print("Doi mat khau error:", e)
        return False, "Đổi mật khẩu thất bại."


def lay_lich_su_thao_tac(scope=None, limit=100, bang_du_lieu=None):
    try:
        where = ["1=1"]
        params = []
        if bang_du_lieu:
            where.append("ls.bang_du_lieu = %s")
            params.append(bang_du_lieu)
        if scope and scope.get("vai_tro") != ROLE_ADMIN_HE_THONG:
            if scope.get("cong_ty_id"):
                where.append("(tk.cong_ty_id = %s OR ls.nguoi_thuc_hien_id = %s)")
                params.extend([int(scope["cong_ty_id"]), int(scope.get("id") or 0)])
            if scope.get("vai_tro") != ROLE_QUAN_TRI_CONG_TY and scope.get("doi_xe_id"):
                where.append("(tk.doi_xe_id = %s OR ls.nguoi_thuc_hien_id = %s)")
                params.extend([int(scope["doi_xe_id"]), int(scope.get("id") or 0)])

        params.append(int(limit))
        sql = f"""
        SELECT
            ls.*,
            tk.ten_dang_nhap AS nguoi_thuc_hien
        FROM lich_su_thao_tac ls
        LEFT JOIN tai_khoan tk ON ls.nguoi_thuc_hien_id = tk.id
        WHERE {' AND '.join(where)}
        ORDER BY ls.id DESC
        LIMIT %s
        """
        return db.fetch_all(sql, tuple(params))
    except Exception as e:
        print("Lay lich su thao tac error:", e)
        return []
