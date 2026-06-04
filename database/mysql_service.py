import mysql.connector
from mysql.connector import Error
import threading


class MySQLService:

    def __init__(self):
        self.connection = None
        self.lock = threading.RLock()
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="he_thong_tai_xe",
                charset="utf8mb4",
                autocommit=True,
                connection_timeout=60
            )

            print("MySQL Connected")

        except Error as e:
            print("Database Error:", e)
            self.connection = None

    def reconnect_if_needed(self):
        if self.connection is None or not self.connection.is_connected():
            self.connect()
        else:
            self.connection.ping(reconnect=True, attempts=3, delay=2)

    def get_cursor(self):
        self.reconnect_if_needed()
        return self.connection.cursor(dictionary=True, buffered=True)

    def execute(self, query, values=None):
        with self.lock:
            cursor = self.get_cursor()
            try:
                cursor.execute(query, values)
                last_id = cursor.lastrowid

                class Result:
                    pass

                result = Result()
                result.lastrowid = last_id
                return result

            finally:
                cursor.close()

    def fetch_one(self, query, values=None):
        with self.lock:
            cursor = self.get_cursor()
            try:
                cursor.execute(query, values)
                return cursor.fetchone()

            finally:
                cursor.close()

    def fetch_all(self, query, values=None):
        with self.lock:
            cursor = self.get_cursor()
            try:
                cursor.execute(query, values)
                return cursor.fetchall()

            finally:
                cursor.close()
# ==========================
# INIT DB
# ==========================
db = MySQLService()

# ==================================================
# CAC TRANG THAI HOP LE
# ==================================================
TRANG_THAI_TAI_XE_HOP_LE = {
    "dang_lam",
    "nghi",
    "tam_khoa",
}

TRANG_THAI_XE_HOP_LE = {
    "hoat_dong",
    "bao_tri",
    "ngung",
}

TRANG_THAI_LICH_CHAY_HOP_LE = {
    "sap_chay",
    "dang_chay",
    "tam_ngung",
    "hoan_thanh",
    "da_huy",
}


def chuyen_int_hoac_none(gia_tri):
    """
    Chuyển dữ liệu từ form HTML thành int hoặc None.
    Tránh lỗi khóa ngoại khi select gửi chuỗi rỗng "".
    """

    if gia_tri in (None, "", "null", "None"):
        return None

    return int(gia_tri)
# ==================================================
# AUTH / LOGIN
# ==================================================
def kiem_tra_dang_nhap(ten_dang_nhap, mat_khau):

    try:

        query = """
        SELECT *
        FROM tai_khoan
        WHERE ten_dang_nhap=%s
        LIMIT 1
        """

        user = db.fetch_one(query, (ten_dang_nhap,))

        if not user:

            return None

        if user["mat_khau"] != mat_khau:

            return None

        return user

    except Exception as e:

        print("Login error:", e)

        return None


def lay_tai_khoan_theo_id(tai_khoan_id):

    try:

        query = """
        SELECT *
        FROM tai_khoan
        WHERE id=%s
        """

        return db.fetch_one(query, (tai_khoan_id,))

    except Exception as e:

        print("Lay tai khoan error:", e)

        return None


# ==================================================
# TAI XE
# ==================================================
def tao_tai_xe_va_tai_khoan(
    ten_dang_nhap,
    mat_khau,
    ho_ten,
    so_dien_thoai=None,
    so_gplx=None,
    dia_chi=None,
    trang_thai="dang_lam",
    quan_ly_id=1,
):
    """
    Admin tạo tài khoản đăng nhập và hồ sơ tài xế.
    """

    try:
        ten_dang_nhap = (ten_dang_nhap or "").strip()
        mat_khau = (mat_khau or "").strip()
        ho_ten = (ho_ten or "").strip()
        trang_thai = (trang_thai or "dang_lam").strip()

        if not ten_dang_nhap:
            print("Ten dang nhap khong duoc de trong")
            return None

        if not mat_khau:
            print("Mat khau khong duoc de trong")
            return None

        if not ho_ten:
            print("Ho ten khong duoc de trong")
            return None

        if trang_thai not in TRANG_THAI_TAI_XE_HOP_LE:
            print("Trang thai tai xe khong hop le:", trang_thai)
            return None

        tai_khoan_da_ton_tai = db.fetch_one(
            """
            SELECT id
            FROM tai_khoan
            WHERE ten_dang_nhap=%s
            LIMIT 1
            """,
            (ten_dang_nhap,)
        )

        if tai_khoan_da_ton_tai:
            print("Ten dang nhap da ton tai")
            return None

        if so_gplx:
            gplx_da_ton_tai = db.fetch_one(
                """
                SELECT id
                FROM tai_xe
                WHERE so_gplx=%s
                LIMIT 1
                """,
                (so_gplx,)
            )

            if gplx_da_ton_tai:
                print("So GPLX da ton tai")
                return None

        tai_khoan = db.execute(
            """
            INSERT INTO tai_khoan
            (
                ten_dang_nhap,
                mat_khau,
                vai_tro,
                trang_thai
            )
            VALUES
            (%s,%s,'tai_xe','hoat_dong')
            """,
            (
                ten_dang_nhap,
                mat_khau,
            )
        )

        tai_xe = db.execute(
            """
            INSERT INTO tai_xe
            (
                tai_khoan_id,
                ho_ten,
                so_dien_thoai,
                so_gplx,
                dia_chi,
                trang_thai
            )
            VALUES
            (%s,%s,%s,%s,%s,%s)
            """,
            (
                tai_khoan.lastrowid,
                ho_ten,
                so_dien_thoai,
                so_gplx,
                dia_chi,
                trang_thai,
            )
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="THEM_TAI_XE",
            bang_du_lieu="tai_xe",
            doi_tuong_id=tai_xe.lastrowid,
            ghi_chu=f"Thêm tài xế {ho_ten}"
        )

        return tai_xe.lastrowid

    except Exception as e:
        print("Tao tai xe error:", e)
        return None
def lay_tai_xe_theo_id(tai_xe_id):

    try:

        query = """
        SELECT *
        FROM tai_xe
        WHERE id=%s
        """

        return db.fetch_one(query, (tai_xe_id,))

    except Exception as e:

        print("Lay tai xe error:", e)

        return None


def lay_danh_sach_tai_xe():

    try:

        query = """
        SELECT *
        FROM tai_xe
        ORDER BY id DESC
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Lay danh sach tai xe error:", e)

        return []


def cap_nhat_tai_xe(tai_xe_id, ho_ten, so_dien_thoai, so_gplx, dia_chi, trang_thai):

    try:

        query = """
        UPDATE tai_xe
        SET
            ho_ten=%s,
            so_dien_thoai=%s,
            so_gplx=%s,
            dia_chi=%s,
            trang_thai=%s
        WHERE id=%s
        """

        db.execute(
            query,
            (
                ho_ten,
                so_dien_thoai,
                so_gplx,
                dia_chi,
                trang_thai,
                tai_xe_id,
            ),
        )

        return True

    except Exception as e:

        print("Cap nhat tai xe error:", e)

        return False


# ==================================================
# XE
# ==================================================
def tao_xe(
    bien_so,
    model=None,
    loai_xe=None,
    trang_thai="hoat_dong",
    ghi_chu=None,
    tai_xe_mac_dinh_id=None,
    quan_ly_id=1,
):
    """
    Admin thêm xe mới và có thể phân công tài xế phụ trách ngay.
    """

    try:
        bien_so = (bien_so or "").strip()
        trang_thai = (trang_thai or "hoat_dong").strip()
        tai_xe_mac_dinh_id = chuyen_int_hoac_none(tai_xe_mac_dinh_id)

        if not bien_so:
            print("Bien so khong duoc de trong")
            return None

        if trang_thai not in TRANG_THAI_XE_HOP_LE:
            print("Trang thai xe khong hop le:", trang_thai)
            return None

        xe_da_ton_tai = db.fetch_one(
            """
            SELECT id
            FROM xe
            WHERE bien_so=%s
            LIMIT 1
            """,
            (bien_so,)
        )

        if xe_da_ton_tai:
            print("Bien so xe da ton tai")
            return None

        if tai_xe_mac_dinh_id is not None:
            tai_xe = db.fetch_one(
                """
                SELECT id
                FROM tai_xe
                WHERE id=%s
                LIMIT 1
                """,
                (tai_xe_mac_dinh_id,)
            )

            if not tai_xe:
                print("Tai xe phu trach khong ton tai")
                return None

        xe = db.execute(
            """
            INSERT INTO xe
            (
                bien_so,
                model,
                loai_xe,
                trang_thai,
                ghi_chu,
                tai_xe_mac_dinh_id
            )
            VALUES
            (%s,%s,%s,%s,%s,%s)
            """,
            (
                bien_so,
                model,
                loai_xe,
                trang_thai,
                ghi_chu,
                tai_xe_mac_dinh_id,
            )
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="THEM_XE",
            bang_du_lieu="xe",
            doi_tuong_id=xe.lastrowid,
            ghi_chu=f"Thêm xe {bien_so}"
        )

        if tai_xe_mac_dinh_id is not None:
            them_ghi_chu(
                tai_xe_id=tai_xe_mac_dinh_id,
                quan_ly_id=quan_ly_id,
                noi_dung=f"Bạn được phân công phụ trách xe {bien_so}."
            )

        return xe.lastrowid

    except Exception as e:
        print("Tao xe error:", e)
        return None
def lay_xe_theo_id(xe_id):

    try:

        query = """
        SELECT *
        FROM xe
        WHERE id=%s
        """

        return db.fetch_one(query, (xe_id,))

    except Exception as e:

        print("Lay xe error:", e)

        return None


def lay_xe_theo_tai_xe(tai_xe_id):

    try:

        query = """
        SELECT *
        FROM xe
        WHERE tai_xe_mac_dinh_id=%s
        LIMIT 1
        """

        return db.fetch_one(query, (tai_xe_id,))

    except Exception as e:

        print("Lay xe theo tai xe error:", e)

        return None


def lay_danh_sach_xe():

    try:

        query = """
        SELECT *
        FROM xe
        ORDER BY id DESC
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Lay danh sach xe error:", e)

        return []


# ==================================================
# PHIEN LAI XE
# ==================================================
def tao_phien_lai_xe(tai_xe_id, xe_id):

    try:

        query = """
        INSERT INTO phien_lai_xe
        (
            tai_xe_id,
            xe_id
        )
        VALUES
        (%s,%s)
        """

        cursor = db.execute(
            query,
            (
                tai_xe_id,
                xe_id,
            ),
        )

        return cursor.lastrowid

    except Exception as e:

        print("Loi tao phien:", e)

        return None


# ==========================
# LAY PHIEN DANG LAI
# ==========================
def lay_phien_dang_lai(tai_xe_id):

    try:

        sql = """
        SELECT
            p.id,
            p.tai_xe_id,
            p.xe_id,
            p.lich_chay_id,
            p.trang_thai,

            x.bien_so,

            l.tuyen_duong,
            l.gio_bat_dau

        FROM phien_lai_xe p

        LEFT JOIN xe x
        ON p.xe_id = x.id

        LEFT JOIN lich_chay l
        ON p.lich_chay_id = l.id

        WHERE
        p.tai_xe_id = %s
        AND p.trang_thai = 'DANG_LAI'

        ORDER BY p.id DESC
        LIMIT 1
        """

        return db.fetch_one(sql, (tai_xe_id,))

    except Exception as e:

        print("Loi lay phien:", e)

        return None


def cap_nhat_mat_dau(phien_id):

    try:

        query = """
        UPDATE phien_lai_xe
        SET
            thoi_diem_mat_dau=NOW(),
            trang_thai='TAM_MAT_DAU'
        WHERE id=%s
        AND thoi_diem_mat_dau IS NULL
        """

        db.execute(query, (phien_id,))

    except Exception as e:

        print("Cap nhat mat dau error:", e)


def reset_mat_dau(phien_id):

    try:

        query = """
        UPDATE phien_lai_xe
        SET
            thoi_diem_mat_dau=NULL,
            trang_thai='DANG_LAI'
        WHERE id=%s
        """

        db.execute(query, (phien_id,))

    except Exception as e:

        print("Reset mat dau error:", e)


def dong_phien_lai_xe(phien_id):

    try:

        query = """
        UPDATE phien_lai_xe
        SET
            ket_thuc=NOW(),

            tong_phut=
            TIMESTAMPDIFF(
                MINUTE,
                bat_dau,
                NOW()
            ),

            trang_thai=
            'DA_KET_THUC'
        WHERE id=%s
        """

        db.execute(query, (phien_id,))

    except Exception as e:

        print("Dong phien error:", e)


# ==================================================
# AI DETECTION LOG
# ==================================================
def save_detection_log(
    tai_xe_id=None,
    xe_id=None,
    status="TINH TAO",
    ear=0,
    mar=0,
    risk_score=0,
    lich_chay_id=None,
):

    try:

        query = """
        INSERT INTO nhat_ky_phat_hien
        (
            tai_xe_id,
            xe_id,
            lich_chay_id,
            ear,
            mar,
            risk_score,
            trang_thai
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            tai_xe_id,
            xe_id,
            lich_chay_id,
            ear,
            mar,
            risk_score,
            status,
        )

        db.execute(query, values)

        return True

    except Exception as e:

        print("Save detection error:", e)

        return False


def lay_detection_logs(limit=100):

    try:

        query = f"""
        SELECT *
        FROM nhat_ky_phat_hien
        ORDER BY id DESC
        LIMIT {limit}
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Lay detection logs error:", e)

        return []


# ==================================================
# ANH CANH BAO
# ==================================================
def luu_anh_canh_bao(
    tai_xe_id,
    xe_id,
    duong_dan_anh,
    lich_chay_id=None,
):

    try:

        query = """
        INSERT INTO anh_canh_bao
        (
            tai_xe_id,
            xe_id,
            lich_chay_id,
            duong_dan_anh
        )
        VALUES
        (%s,%s,%s,%s)
        """

        values = (
            tai_xe_id,
            xe_id,
            lich_chay_id,
            duong_dan_anh,
        )

        db.execute(query, values)

        print("Da luu anh canh bao")

        return True

    except Exception as e:

        print("Loi luu anh:", e)

        return False


def lay_anh_canh_bao(limit=50):

    try:

        query = f"""
        SELECT
            a.*,
            t.ho_ten,
            x.bien_so
        FROM anh_canh_bao a
        LEFT JOIN tai_xe t
        ON a.tai_xe_id=t.id
        LEFT JOIN xe x
        ON a.xe_id=x.id
        ORDER BY a.id DESC
        LIMIT {limit}
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Lay anh canh bao error:", e)

        return []


# ==================================================
# UNKNOWN DRIVER
# ==================================================
def luu_nguoi_la(xe_id, duong_dan_anh=None, ghi_chu=None):

    try:

        query = """
        INSERT INTO nguoi_la
        (
            xe_id,
            duong_dan_anh,
            ghi_chu
        )
        VALUES
        (%s,%s,%s)
        """

        db.execute(query, (xe_id, duong_dan_anh, ghi_chu))

        print("Da luu nguoi la")

        return True

    except Exception as e:

        print("Luu nguoi la error:", e)

        return False


def lay_nguoi_la(limit=100):

    try:

        query = f"""
        SELECT
            n.*,
            x.bien_so
        FROM nguoi_la n
        LEFT JOIN xe x
        ON n.xe_id=x.id
        ORDER BY n.id DESC
        LIMIT {limit}
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Lay nguoi la error:", e)

        return []


# ==================================================
# GHI CHU
# ==================================================
def them_ghi_chu(tai_xe_id, quan_ly_id, noi_dung):

    try:

        query = """
        INSERT INTO ghi_chu
        (
            tai_xe_id,
            quan_ly_id,
            noi_dung
        )
        VALUES
        (%s,%s,%s)
        """

        db.execute(
            query,
            (
                tai_xe_id,
                quan_ly_id,
                noi_dung,
            ),
        )

        return True

    except Exception as e:

        print("Them ghi chu error:", e)

        return False


def lay_ghi_chu(tai_xe_id):

    try:

        query = """
        SELECT *
        FROM ghi_chu
        WHERE tai_xe_id=%s
        ORDER BY id DESC
        """

        return db.fetch_all(query, (tai_xe_id,))

    except Exception as e:

        print("Lay ghi chu error:", e)

        return []


def danh_dau_da_doc(ghi_chu_id):

    try:

        query = """
        UPDATE ghi_chu
        SET da_doc=1
        WHERE id=%s
        """

        db.execute(query, (ghi_chu_id,))

        return True

    except Exception as e:

        print("Danh dau da doc error:", e)

        return False


# ==================================================
# AUDIT LOG
# ==================================================
def ghi_lich_su_thao_tac(
    nguoi_thuc_hien_id,
    vai_tro,
    hanh_dong,
    bang_du_lieu,
    doi_tuong_id=None,
    ghi_chu=None,
):

    try:

        query = """
        INSERT INTO
        lich_su_thao_tac
        (
            nguoi_thuc_hien_id,
            vai_tro,
            hanh_dong,
            bang_du_lieu,
            doi_tuong_id,
            ghi_chu
        )
        VALUES
        (%s,%s,%s,%s,%s,%s)
        """

        db.execute(
            query,
            (
                nguoi_thuc_hien_id,
                vai_tro,
                hanh_dong,
                bang_du_lieu,
                doi_tuong_id,
                ghi_chu,
            ),
        )

        return True

    except Exception as e:

        print("Audit log error:", e)

        return False


# ==================================================
# REALTIME MONITOR
# ==================================================
def lay_xe_dang_hoat_dong():

    try:

        query = """
        SELECT
            p.id AS phien_id,
            p.trang_thai,
            p.bat_dau,
            p.tong_phut,

            x.id AS xe_id,
            x.bien_so,

            t.id AS tai_xe_id,
            t.ho_ten,

            n.risk_score,
            n.trang_thai
            AS ai_status

        FROM phien_lai_xe p

        LEFT JOIN xe x
        ON p.xe_id=x.id

        LEFT JOIN tai_xe t
        ON p.tai_xe_id=t.id

        LEFT JOIN
        (
            SELECT *
            FROM nhat_ky_phat_hien nk
            WHERE nk.id IN (
                SELECT MAX(id)
                FROM nhat_ky_phat_hien
                GROUP BY tai_xe_id
            )
        ) n
        ON p.tai_xe_id=n.tai_xe_id

        WHERE
        p.trang_thai!='DA_KET_THUC'

        ORDER BY p.id DESC
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Realtime monitor error:", e)

        return []


# ==================================================
# ANALYTICS
# ==================================================
def thong_ke_buon_ngu():

    try:

        query = """
        SELECT
            DATE(thoi_gian)
            AS ngay,

            COUNT(*) AS tong

        FROM nhat_ky_phat_hien

        WHERE
        trang_thai='BUON NGU'

        GROUP BY
        DATE(thoi_gian)

        ORDER BY
        ngay DESC
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Thong ke buon ngu error:", e)

        return []


def top_tai_xe_nguy_co():

    try:

        query = """
        SELECT
            t.ho_ten,
            COUNT(*) AS tong_lan

        FROM nhat_ky_phat_hien n

        JOIN tai_xe t
        ON n.tai_xe_id=t.id

        WHERE
        n.trang_thai='BUON NGU'

        GROUP BY
        n.tai_xe_id

        ORDER BY
        tong_lan DESC

        LIMIT 10
        """

        return db.fetch_all(query)

    except Exception as e:

        print("Top tai xe nguy co error:", e)

        return []


# ==========================
# DRIVER DASHBOARD
# ==========================
def lay_dashboard_tai_xe(tai_xe_id):

    try:

        sql = """
        SELECT
            tx.id,
            tx.ho_ten,

            x.id AS xe_id,
            x.bien_so,

            lc.id AS lich_id,
            lc.tuyen_duong,
            lc.gio_bat_dau,
            lc.trang_thai

        FROM tai_xe tx

        LEFT JOIN lich_chay lc
        ON tx.id = lc.tai_xe_id

        LEFT JOIN xe x
        ON lc.xe_id = x.id

        WHERE tx.id = %s

ORDER BY
CASE

    WHEN lc.trang_thai = 'dang_chay'
    THEN 1

    WHEN lc.trang_thai = 'tam_ngung'
    THEN 2

    WHEN lc.trang_thai = 'sap_chay'
    THEN 3

    WHEN lc.trang_thai = 'hoan_thanh'
    THEN 4

    WHEN lc.trang_thai = 'da_huy'
    THEN 5

    ELSE 6

END,

lc.gio_bat_dau DESC

LIMIT 1

        """

        return db.fetch_one(sql, (tai_xe_id,))

    except Exception as e:

        print("Dashboard error:", e)


        return None
# ==========================
# LAY LICH CHAY TAI XE
# ==========================
def lay_lich_chay_tai_xe(tai_xe_id):

    try:

        sql = """
        SELECT
            lc.id,
            lc.tuyen_duong,
            lc.gio_bat_dau,
            lc.gio_ket_thuc,
            lc.trang_thai,

            x.bien_so

        FROM lich_chay lc

        LEFT JOIN xe x
        ON lc.xe_id = x.id

        WHERE lc.tai_xe_id=%s

        ORDER BY lc.gio_bat_dau DESC
        """

        return db.fetch_all(sql, (tai_xe_id,))

    except Exception as e:

        print("Loi lay lich:", e)


        return []
# ==========================
# LAY THONG BAO TAI XE
# ==========================
def lay_thong_bao_tai_xe(tai_xe_id):

    try:

        sql = """
        SELECT
            gc.id,
            gc.noi_dung,
            gc.da_doc,
            gc.created_at,

            tk.ten_dang_nhap
            AS quan_ly

        FROM ghi_chu gc

        LEFT JOIN tai_khoan tk
        ON gc.quan_ly_id = tk.id

        WHERE gc.tai_xe_id=%s

        ORDER BY gc.id DESC
        """

        return db.fetch_all(sql, (tai_xe_id,))

    except Exception as e:

        print("Loi thong bao:", e)

        return []


# ==========================
# LAY PROFILE TAI XE
# ==========================
def lay_profile_tai_xe(
    tai_xe_id
):

    try:

        sql = """
        SELECT
            tx.id,
            tx.ho_ten,
            tx.so_dien_thoai,
            tx.so_gplx,
            tx.dia_chi,
            tx.avatar,
            tx.trang_thai,

            x.bien_so,
            x.model

        FROM tai_xe tx

        LEFT JOIN xe x
        ON x.tai_xe_mac_dinh_id =
        tx.id

        WHERE tx.id=%s

        LIMIT 1
        """

        return db.fetch_one(
            sql,
            (
                tai_xe_id,
            )
        )

    except Exception as e:

        print(
            "Profile error:",
            e
        )

        return None


# ==========================
# CAP NHAT PROFILE
# ==========================
def cap_nhat_profile_tai_xe(tai_xe_id, so_dien_thoai, dia_chi):

    try:

        sql = """
        UPDATE tai_xe
        SET
            so_dien_thoai=%s,
            dia_chi=%s
        WHERE id=%s
        """

        db.execute(sql, (so_dien_thoai, dia_chi, tai_xe_id))

        return True

    except Exception as e:

        print("Update profile error:", e)

        return False
import json


# ==========================
# LUU VECTOR KHUON MAT
# ==========================
def luu_vector_khuon_mat(tai_xe_id, embedding, do_tin_cay=1.0):

    try:

        # xoa vector cu
        sql_delete = """
        DELETE FROM
        du_lieu_khuon_mat
        WHERE tai_xe_id=%s
        """

        db.execute(sql_delete, (tai_xe_id,))

        # save vector moi
        sql_insert = """
        INSERT INTO
        du_lieu_khuon_mat
        (
            tai_xe_id,
            vector_khuon_mat,
            do_tin_cay
        )
        VALUES
        (%s,%s,%s)
        """

        db.execute(sql_insert, (tai_xe_id, json.dumps(embedding.tolist()), do_tin_cay))

        print("Da luu vector khuon mat")

        return True

    except Exception as e:

        print("Loi luu vector:", e)

        return False


# ==========================
# LUU ANH KHUON MAT
# ==========================
def luu_anh_khuon_mat(tai_xe_id, image_bytes):

    try:

        sql = """
        INSERT INTO
        anh_khuon_mat
        (
            tai_xe_id,
            du_lieu_anh
        )
        VALUES
        (%s,%s)
        """

        db.execute(sql, (tai_xe_id, image_bytes))

        print("Da luu anh khuon mat")

        return True

    except Exception as e:

        print("Loi luu anh:", e)

        return False


# ==========================
# LOAD VECTOR KHUON MAT
# ==========================
def lay_du_lieu_khuon_mat():

    try:

        sql = """
        SELECT *
        FROM du_lieu_khuon_mat
        WHERE trang_thai=
        'hoat_dong'
        """

        return db.fetch_all(sql)

    except Exception as e:

        print("Loi load vector:", e)

        return []


# ==========================
# KIEM TRA DA DANG KY MAT
# ==========================
def da_dang_ky_khuon_mat(tai_xe_id):

    try:

        sql = """
        SELECT id
        FROM du_lieu_khuon_mat
        WHERE tai_xe_id=%s
        LIMIT 1
        """

        result = db.fetch_one(sql, (tai_xe_id,))

        return result is not None

    except Exception as e:

        print("Loi check face:", e)

        return False

        # ==================================================
# BAO CAO SU CO
# ==================================================
def tao_bao_cao_su_co(
    tai_xe_id,
    xe_id,
    lich_chay_id,
    tieu_de,
    loai_su_co,
    noi_dung,
    hinh_anh=None
):
    try:
        sql = """
        INSERT INTO bao_cao_su_co
        (
            tai_xe_id,
            xe_id,
            lich_chay_id,
            tieu_de,
            loai_su_co,
            noi_dung,
            hinh_anh
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        db.execute(sql, (
            tai_xe_id,
            xe_id,
            lich_chay_id,
            tieu_de,
            loai_su_co,
            noi_dung,
            hinh_anh
        ))

        return True

    except Exception as e:
        print("Tao bao cao su co error:", e)
        return False


def lay_bao_cao_su_co_tai_xe(tai_xe_id):
    try:
        sql = """
        SELECT
            bc.*,
            tx.ho_ten,
            x.bien_so,
            lc.tuyen_duong
        FROM bao_cao_su_co bc
        LEFT JOIN tai_xe tx ON bc.tai_xe_id = tx.id
        LEFT JOIN xe x ON bc.xe_id = x.id
        LEFT JOIN lich_chay lc ON bc.lich_chay_id = lc.id
        WHERE bc.tai_xe_id = %s
        ORDER BY bc.id DESC
        """

        return db.fetch_all(sql, (tai_xe_id,))

    except Exception as e:
        print("Lay bao cao tai xe error:", e)
        return []


def lay_tat_ca_bao_cao_su_co():
    try:
        sql = """
        SELECT
            bc.*,
            tx.ho_ten,
            x.bien_so,
            lc.tuyen_duong
        FROM bao_cao_su_co bc
        LEFT JOIN tai_xe tx ON bc.tai_xe_id = tx.id
        LEFT JOIN xe x ON bc.xe_id = x.id
        LEFT JOIN lich_chay lc ON bc.lich_chay_id = lc.id
        ORDER BY bc.id DESC
        """

        return db.fetch_all(sql)

    except Exception as e:
        print("Lay tat ca bao cao error:", e)
        return []


def cap_nhat_trang_thai_bao_cao(
    bao_cao_id,
    trang_thai,
    phan_hoi_quan_ly=None
):
    try:
        sql = """
        UPDATE bao_cao_su_co
        SET
            trang_thai = %s,
            phan_hoi_quan_ly = %s
        WHERE id = %s
        """

        db.execute(sql, (
            trang_thai,
            phan_hoi_quan_ly,
            bao_cao_id
        ))

        return True

    except Exception as e:
        print("Cap nhat bao cao error:", e)
        return False


# ==================================================
# DRIVER HISTORY / VIOLATIONS
# ==================================================
def lay_lich_su_vi_pham_tai_xe(tai_xe_id):
    try:
        sql = """
        SELECT
            nk.*,
            x.bien_so
        FROM nhat_ky_phat_hien nk
        LEFT JOIN xe x ON nk.xe_id = x.id
        WHERE nk.tai_xe_id = %s
        AND nk.trang_thai IN ('MET MOI', 'BUON NGU')
        ORDER BY nk.id DESC
        """

        return db.fetch_all(sql, (tai_xe_id,))

    except Exception as e:
        print("Lay lich su vi pham tai xe error:", e)
        return []


def lay_lich_su_chay_tai_xe(tai_xe_id):
    try:
        sql = """
        SELECT
            p.*,
            x.bien_so,
            lc.tuyen_duong
        FROM phien_lai_xe p
        LEFT JOIN xe x ON p.xe_id = x.id
        LEFT JOIN lich_chay lc ON p.lich_chay_id = lc.id
        WHERE p.tai_xe_id = %s
        ORDER BY p.id DESC
        """

        return db.fetch_all(sql, (tai_xe_id,))

    except Exception as e:
        print("Lay lich su chay tai xe error:", e)
        return []


# ==================================================
# ADMIN DASHBOARD
# ==================================================
def lay_admin_dashboard():
    try:
        tong_tai_xe = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM tai_xe
        """)

        tong_xe = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM xe
        """)

        xe_dang_hoat_dong = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM phien_lai_xe
            WHERE trang_thai != 'DA_KET_THUC'
        """)

        canh_bao_hom_nay = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM nhat_ky_phat_hien
            WHERE DATE(thoi_gian) = CURDATE()
            AND trang_thai IN ('MET MOI', 'BUON NGU')
        """)

        bao_cao_chua_xu_ly = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM bao_cao_su_co
            WHERE trang_thai = 'CHO_XU_LY'
        """)

        xe_live = db.fetch_all("""
            SELECT
                p.id AS phien_id,
                p.trang_thai AS trang_thai_phien,
                p.bat_dau,
                tx.ho_ten,
                x.bien_so,
                nk.trang_thai AS ai_status,
                nk.risk_score,
                nk.thoi_gian
            FROM phien_lai_xe p
            LEFT JOIN tai_xe tx ON p.tai_xe_id = tx.id
            LEFT JOIN xe x ON p.xe_id = x.id
            LEFT JOIN (
                SELECT n1.*
                FROM nhat_ky_phat_hien n1
                INNER JOIN (
                    SELECT tai_xe_id, MAX(id) AS max_id
                    FROM nhat_ky_phat_hien
                    GROUP BY tai_xe_id
                ) n2 ON n1.id = n2.max_id
            ) nk ON nk.tai_xe_id = p.tai_xe_id
            WHERE p.trang_thai != 'DA_KET_THUC'
            ORDER BY p.id DESC
            LIMIT 10
        """)

        canh_bao_moi = db.fetch_all("""
            SELECT
                nk.*,
                tx.ho_ten,
                x.bien_so
            FROM nhat_ky_phat_hien nk
            LEFT JOIN tai_xe tx ON nk.tai_xe_id = tx.id
            LEFT JOIN xe x ON nk.xe_id = x.id
            WHERE nk.trang_thai IN ('MET MOI', 'BUON NGU')
            ORDER BY nk.id DESC
            LIMIT 10
        """)

        bao_cao_moi = db.fetch_all("""
            SELECT
                bc.*,
                tx.ho_ten,
                x.bien_so
            FROM bao_cao_su_co bc
            LEFT JOIN tai_xe tx ON bc.tai_xe_id = tx.id
            LEFT JOIN xe x ON bc.xe_id = x.id
            ORDER BY bc.id DESC
            LIMIT 10
        """)

        return {
            "tong_tai_xe": tong_tai_xe["tong"] if tong_tai_xe else 0,
            "tong_xe": tong_xe["tong"] if tong_xe else 0,
            "xe_dang_hoat_dong": xe_dang_hoat_dong["tong"] if xe_dang_hoat_dong else 0,
            "canh_bao_hom_nay": canh_bao_hom_nay["tong"] if canh_bao_hom_nay else 0,
            "bao_cao_chua_xu_ly": bao_cao_chua_xu_ly["tong"] if bao_cao_chua_xu_ly else 0,
            "xe_live": xe_live,
            "canh_bao_moi": canh_bao_moi,
            "bao_cao_moi": bao_cao_moi,
        }

    except Exception as e:
        print("Lay admin dashboard error:", e)
        return {
            "tong_tai_xe": 0,
            "tong_xe": 0,
            "xe_dang_hoat_dong": 0,
            "canh_bao_hom_nay": 0,
            "bao_cao_chua_xu_ly": 0,
            "xe_live": [],
            "canh_bao_moi": [],
            "bao_cao_moi": [],
        }
    # ==================================================
# ADMIN - QUAN LY TAI XE
# ==================================================
def cap_nhat_tai_xe_va_thong_bao(
    tai_xe_id,
    ho_ten,
    so_dien_thoai,
    so_gplx,
    dia_chi,
    trang_thai,
    quan_ly_id=1
):
    try:
        ho_ten = (ho_ten or "").strip()
        trang_thai = (trang_thai or "").strip()

        if not ho_ten:
            print("Ho ten khong duoc de trong")
            return False

        if trang_thai not in TRANG_THAI_TAI_XE_HOP_LE:
            print("Trang thai tai xe khong hop le:", trang_thai)
            return False

        tai_xe = db.fetch_one(
            """
            SELECT id
            FROM tai_xe
            WHERE id=%s
            LIMIT 1
            """,
            (tai_xe_id,)
        )

        if not tai_xe:
            print("Khong tim thay tai xe")
            return False

        sql = """
        UPDATE tai_xe
        SET
            ho_ten=%s,
            so_dien_thoai=%s,
            so_gplx=%s,
            dia_chi=%s,
            trang_thai=%s
        WHERE id=%s
        """

        db.execute(sql, (
            ho_ten,
            so_dien_thoai,
            so_gplx,
            dia_chi,
            trang_thai,
            tai_xe_id
        ))

        them_ghi_chu(
            tai_xe_id=tai_xe_id,
            quan_ly_id=quan_ly_id,
            noi_dung="Thông tin cá nhân của bạn đã được quản lý cập nhật."
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="CAP_NHAT_TAI_XE",
            bang_du_lieu="tai_xe",
            doi_tuong_id=tai_xe_id,
            ghi_chu=f"Cập nhật thông tin tài xế ID {tai_xe_id}"
        )

        return True

    except Exception as e:
        print("Cap nhat tai xe va thong bao error:", e)
        return False
    # ==================================================
# ADMIN - QUAN LY XE
# ==================================================
def cap_nhat_xe(
    xe_id,
    bien_so,
    model=None,
    loai_xe=None,
    trang_thai="hoat_dong",
    ghi_chu=None,
    tai_xe_mac_dinh_id=None,
    quan_ly_id=1,
):
    """
    Admin sửa thông tin xe và thay đổi tài xế phụ trách xe.
    """

    try:
        bien_so = (bien_so or "").strip()
        trang_thai = (trang_thai or "").strip()
        tai_xe_mac_dinh_id = chuyen_int_hoac_none(tai_xe_mac_dinh_id)

        if not bien_so:
            print("Bien so khong duoc de trong")
            return False

        if trang_thai not in TRANG_THAI_XE_HOP_LE:
            print("Trang thai xe khong hop le:", trang_thai)
            return False

        xe_cu = db.fetch_one(
            """
            SELECT *
            FROM xe
            WHERE id=%s
            LIMIT 1
            """,
            (xe_id,)
        )

        if not xe_cu:
            print("Khong tim thay xe")
            return False

        xe_trung_bien_so = db.fetch_one(
            """
            SELECT id
            FROM xe
            WHERE bien_so=%s
            AND id<>%s
            LIMIT 1
            """,
            (
                bien_so,
                xe_id,
            )
        )

        if xe_trung_bien_so:
            print("Bien so xe da ton tai")
            return False

        if tai_xe_mac_dinh_id is not None:
            tai_xe = db.fetch_one(
                """
                SELECT id
                FROM tai_xe
                WHERE id=%s
                LIMIT 1
                """,
                (tai_xe_mac_dinh_id,)
            )

            if not tai_xe:
                print("Tai xe phu trach khong ton tai")
                return False

        db.execute(
            """
            UPDATE xe
            SET
                bien_so=%s,
                model=%s,
                loai_xe=%s,
                trang_thai=%s,
                ghi_chu=%s,
                tai_xe_mac_dinh_id=%s
            WHERE id=%s
            """,
            (
                bien_so,
                model,
                loai_xe,
                trang_thai,
                ghi_chu,
                tai_xe_mac_dinh_id,
                xe_id,
            )
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="CAP_NHAT_XE",
            bang_du_lieu="xe",
            doi_tuong_id=xe_id,
            ghi_chu=f"Cập nhật xe {bien_so}"
        )

        tai_xe_cu_id = xe_cu.get("tai_xe_mac_dinh_id")

        if tai_xe_cu_id != tai_xe_mac_dinh_id:
            if tai_xe_cu_id is not None:
                them_ghi_chu(
                    tai_xe_id=tai_xe_cu_id,
                    quan_ly_id=quan_ly_id,
                    noi_dung=f"Bạn không còn phụ trách xe {xe_cu['bien_so']}."
                )

            if tai_xe_mac_dinh_id is not None:
                them_ghi_chu(
                    tai_xe_id=tai_xe_mac_dinh_id,
                    quan_ly_id=quan_ly_id,
                    noi_dung=f"Bạn được phân công phụ trách xe {bien_so}."
                )

        return True

    except Exception as e:
        print("Cap nhat xe error:", e)
        return False

def lay_danh_sach_xe_admin():
    try:
        sql = """
        SELECT
            x.*,
            tx.ho_ten AS ten_tai_xe_mac_dinh
        FROM xe x
        LEFT JOIN tai_xe tx ON x.tai_xe_mac_dinh_id = tx.id
        ORDER BY x.id DESC
        """

        return db.fetch_all(sql)

    except Exception as e:
        print("Lay danh sach xe admin error:", e)
        return []
    # ==================================================
# ADMIN - QUAN LY LICH CHAY
# ==================================================
# ==================================================
# ADMIN - QUAN LY LICH CHAY
# ==================================================
def tao_lich_chay(
    tai_xe_id,
    xe_id,
    tuyen_duong,
    gio_bat_dau,
    gio_ket_thuc=None,
    quan_ly_id=1
):
    """
    Tạo lịch chạy mới.

    Chỉ cho phép:
    - tài xế đang làm việc
    - xe đang hoạt động
    """

    try:
        tuyen_duong = (tuyen_duong or "").strip()

        if not tai_xe_id:
            print("Chua chon tai xe")
            return None

        if not xe_id:
            print("Chua chon xe")
            return None

        if not tuyen_duong:
            print("Tuyen duong khong duoc de trong")
            return None

        if not gio_bat_dau:
            print("Gio bat dau khong duoc de trong")
            return None

        tai_xe = db.fetch_one(
            """
            SELECT id, ho_ten, trang_thai
            FROM tai_xe
            WHERE id=%s
            LIMIT 1
            """,
            (tai_xe_id,)
        )

        if not tai_xe:
            print("Khong tim thay tai xe")
            return None

        if tai_xe["trang_thai"] != "dang_lam":
            print("Tai xe khong o trang thai dang lam")
            return None

        xe = db.fetch_one(
            """
            SELECT id, bien_so, trang_thai
            FROM xe
            WHERE id=%s
            LIMIT 1
            """,
            (xe_id,)
        )

        if not xe:
            print("Khong tim thay xe")
            return None

        if xe["trang_thai"] != "hoat_dong":
            print("Xe khong o trang thai hoat dong")
            return None

        cursor = db.execute(
            """
            INSERT INTO lich_chay
            (
                tai_xe_id,
                xe_id,
                tuyen_duong,
                gio_bat_dau,
                gio_ket_thuc,
                trang_thai
            )
            VALUES
            (%s,%s,%s,%s,%s,'sap_chay')
            """,
            (
                tai_xe_id,
                xe_id,
                tuyen_duong,
                gio_bat_dau,
                gio_ket_thuc
            )
        )

        them_ghi_chu(
            tai_xe_id=tai_xe_id,
            quan_ly_id=quan_ly_id,
            noi_dung=(
                f"Bạn được phân công lịch chạy mới: "
                f"{tuyen_duong}, bắt đầu lúc {gio_bat_dau}."
            )
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="TAO_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=cursor.lastrowid,
            ghi_chu=(
                f"Tạo lịch chạy cho tài xế ID {tai_xe_id}, "
                f"xe ID {xe_id}"
            )
        )

        return cursor.lastrowid

    except Exception as e:
        print("Tao lich chay error:", e)
        return None


def lay_tat_ca_lich_chay():
    try:
        sql = """
        SELECT
            lc.*,
            tx.ho_ten,
            x.bien_so
        FROM lich_chay lc
        LEFT JOIN tai_xe tx
            ON lc.tai_xe_id = tx.id
        LEFT JOIN xe x
            ON lc.xe_id = x.id
        ORDER BY lc.gio_bat_dau DESC
        """

        return db.fetch_all(sql)

    except Exception as e:
        print("Lay tat ca lich chay error:", e)
        return []


def cap_nhat_lich_chay(
    lich_id,
    tai_xe_id,
    xe_id,
    tuyen_duong,
    gio_bat_dau,
    gio_ket_thuc,
    trang_thai,
    quan_ly_id=1
):
    """
    Cập nhật lịch chạy.

    Lịch đã hủy không được kích hoạt lại.
    Muốn hủy lịch phải dùng hàm xoa_lich_chay().
    """

    try:
        trang_thai = (trang_thai or "").strip()
        tuyen_duong = (tuyen_duong or "").strip()

        trang_thai_duoc_cap_nhat = {
            "sap_chay",
            "dang_chay",
            "tam_ngung",
            "hoan_thanh",
        }

        if trang_thai not in trang_thai_duoc_cap_nhat:
            print("Trang thai lich chay khong hop le:", trang_thai)
            return False

        if not tuyen_duong:
            print("Tuyen duong khong duoc de trong")
            return False

        lich_cu = db.fetch_one(
            """
            SELECT *
            FROM lich_chay
            WHERE id=%s
            LIMIT 1
            """,
            (lich_id,)
        )

        if not lich_cu:
            print("Khong tim thay lich chay")
            return False

        if lich_cu["trang_thai"] == "da_huy":
            print("Lich da huy, khong the cap nhat lai")
            return False

        # Nếu lịch chuẩn bị chạy hoặc đang chạy,
        # tài xế và xe bắt buộc phải còn hoạt động.
        if trang_thai in {"sap_chay", "dang_chay"}:
            tai_xe = db.fetch_one(
                """
                SELECT id
                FROM tai_xe
                WHERE id=%s
                AND trang_thai='dang_lam'
                LIMIT 1
                """,
                (tai_xe_id,)
            )

            if not tai_xe:
                print("Tai xe khong san sang lam viec")
                return False

            xe = db.fetch_one(
                """
                SELECT id
                FROM xe
                WHERE id=%s
                AND trang_thai='hoat_dong'
                LIMIT 1
                """,
                (xe_id,)
            )

            if not xe:
                print("Xe khong o trang thai hoat dong")
                return False

        db.execute(
            """
            UPDATE lich_chay
            SET
                tai_xe_id=%s,
                xe_id=%s,
                tuyen_duong=%s,
                gio_bat_dau=%s,
                gio_ket_thuc=%s,
                trang_thai=%s
            WHERE id=%s
            """,
            (
                tai_xe_id,
                xe_id,
                tuyen_duong,
                gio_bat_dau,
                gio_ket_thuc,
                trang_thai,
                lich_id
            )
        )

        them_ghi_chu(
            tai_xe_id=tai_xe_id,
            quan_ly_id=quan_ly_id,
            noi_dung=(
                f"Lịch chạy tuyến {tuyen_duong} đã được cập nhật. "
                f"Trạng thái mới: {trang_thai}."
            )
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="CAP_NHAT_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=lich_id,
            ghi_chu=(
                f"Cập nhật lịch chạy ID {lich_id}: "
                f"{trang_thai}"
            )
        )

        return True

    except Exception as e:
        print("Cap nhat lich chay error:", e)
        return False


def xoa_lich_chay(lich_id, quan_ly_id=1):
    """
    Hủy lịch nhưng không xóa dữ liệu.

    Trạng thái cuối cùng là da_huy.
    """

    try:
        lich = db.fetch_one(
            """
            SELECT *
            FROM lich_chay
            WHERE id=%s
            LIMIT 1
            """,
            (lich_id,)
        )

        if not lich:
            print("Khong tim thay lich chay")
            return False

        # Tránh ghi thông báo và lịch sử lặp lại
        # nếu admin bấm hủy nhiều lần.
        if lich["trang_thai"] == "da_huy":
            return True

        db.execute(
            """
            UPDATE lich_chay
            SET trang_thai='da_huy'
            WHERE id=%s
            """,
            (lich_id,)
        )

        them_ghi_chu(
            tai_xe_id=lich["tai_xe_id"],
            quan_ly_id=quan_ly_id,
            noi_dung=(
                f"Lịch chạy tuyến "
                f"{lich['tuyen_duong']} đã bị hủy."
            )
        )

        ghi_lich_su_thao_tac(
            nguoi_thuc_hien_id=quan_ly_id,
            vai_tro="quan_ly",
            hanh_dong="HUY_LICH_CHAY",
            bang_du_lieu="lich_chay",
            doi_tuong_id=lich_id,
            ghi_chu=f"Hủy lịch chạy ID {lich_id}"
        )

        return True

    except Exception as e:
        print("Xoa lich chay error:", e)
        return False
    # ==================================================
# ADMIN - ANALYTICS
# ==================================================
def lay_admin_analytics():
    try:
        tong_canh_bao = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM nhat_ky_phat_hien
            WHERE trang_thai IN ('MET MOI', 'BUON NGU')
        """)

        tong_buon_ngu = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM nhat_ky_phat_hien
            WHERE trang_thai = 'BUON NGU'
        """)

        tong_met_moi = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM nhat_ky_phat_hien
            WHERE trang_thai = 'MET MOI'
        """)

        tong_bao_cao_su_co = db.fetch_one("""
            SELECT COUNT(*) AS tong
            FROM bao_cao_su_co
        """)

        buon_ngu_theo_ngay = db.fetch_all("""
            SELECT
                DATE(thoi_gian) AS ngay,
                COUNT(*) AS tong
            FROM nhat_ky_phat_hien
            WHERE trang_thai = 'BUON NGU'
            GROUP BY DATE(thoi_gian)
            ORDER BY ngay ASC
        """)

        met_moi_theo_ngay = db.fetch_all("""
            SELECT
                DATE(thoi_gian) AS ngay,
                COUNT(*) AS tong
            FROM nhat_ky_phat_hien
            WHERE trang_thai = 'MET MOI'
            GROUP BY DATE(thoi_gian)
            ORDER BY ngay ASC
        """)

        top_tai_xe = db.fetch_all("""
            SELECT
                tx.id,
                tx.ho_ten,
                COUNT(*) AS tong_canh_bao,
                SUM(CASE WHEN nk.trang_thai = 'BUON NGU' THEN 1 ELSE 0 END) AS so_lan_buon_ngu,
                SUM(CASE WHEN nk.trang_thai = 'MET MOI' THEN 1 ELSE 0 END) AS so_lan_met_moi
            FROM nhat_ky_phat_hien nk
            LEFT JOIN tai_xe tx ON nk.tai_xe_id = tx.id
            WHERE nk.trang_thai IN ('MET MOI', 'BUON NGU')
            GROUP BY nk.tai_xe_id
            ORDER BY tong_canh_bao DESC
            LIMIT 10
        """)

        bao_cao_su_co_theo_loai = db.fetch_all("""
            SELECT
                loai_su_co,
                COUNT(*) AS tong
            FROM bao_cao_su_co
            GROUP BY loai_su_co
            ORDER BY tong DESC
        """)

        return {
            "tong_canh_bao": tong_canh_bao["tong"] if tong_canh_bao else 0,
            "tong_buon_ngu": tong_buon_ngu["tong"] if tong_buon_ngu else 0,
            "tong_met_moi": tong_met_moi["tong"] if tong_met_moi else 0,
            "tong_bao_cao_su_co": tong_bao_cao_su_co["tong"] if tong_bao_cao_su_co else 0,
            "buon_ngu_theo_ngay": buon_ngu_theo_ngay,
            "met_moi_theo_ngay": met_moi_theo_ngay,
            "top_tai_xe": top_tai_xe,
            "bao_cao_su_co_theo_loai": bao_cao_su_co_theo_loai,
        }

    except Exception as e:
        print("Lay admin analytics error:", e)
        return {
            "tong_canh_bao": 0,
            "tong_buon_ngu": 0,
            "tong_met_moi": 0,
            "tong_bao_cao_su_co": 0,
            "buon_ngu_theo_ngay": [],
            "met_moi_theo_ngay": [],
            "top_tai_xe": [],
            "bao_cao_su_co_theo_loai": [],
        }


# ==================================================
# KIEM TRA TAI XE CO DUOC PHAN CONG DUNG XE KHONG
# ==================================================
def kiem_tra_tai_xe_duoc_phan_cong_xe(tai_xe_id, xe_id):
    try:
        # Cách 1: Kiểm tra tài xế mặc định của xe
        sql_xe = """
        SELECT id
        FROM xe
        WHERE id = %s
        AND tai_xe_mac_dinh_id = %s
        LIMIT 1
        """

        result_xe = db.fetch_one(sql_xe, (xe_id, tai_xe_id))

        if result_xe:
            return True

        # Cách 2: Kiểm tra theo lịch chạy đang/sắp chạy
        sql_lich = """
        SELECT id
        FROM lich_chay
        WHERE xe_id = %s
        AND tai_xe_id = %s
        AND trang_thai IN ('dang_chay', 'sap_chay')
        LIMIT 1
        """

        result_lich = db.fetch_one(sql_lich, (xe_id, tai_xe_id))

        if result_lich:
            return True

        return False

    except Exception as e:
        print("Loi kiem tra tai xe duoc phan cong xe:", e)
        return False
