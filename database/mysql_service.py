import mysql.connector
from mysql.connector import Error


# ==========================
# MYSQL SERVICE
# ==========================
class MySQLService:

    def __init__(self):

        self.connection = None

        self.connect()

    # ==========================
    # CONNECT
    # ==========================
    def connect(self):

        try:

            self.connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="he_thong_tai_xe",
                charset="utf8mb4",
            )

            print("MySQL Connected")

        except Error as e:

            print("Database Error:", e)

    # ==========================
    # CHECK CONNECTION
    # ==========================
    def reconnect_if_needed(self):

        try:

            if self.connection is None or not self.connection.is_connected():

                self.connect()

        except Exception:

            self.connect()

    # ==========================
    # GET CURSOR
    # ==========================
    def get_cursor(self):

        self.reconnect_if_needed()

        return self.connection.cursor(dictionary=True)

    # ==========================
    # EXECUTE
    # ==========================
    def execute(self, query, values=None):

        cursor = self.get_cursor()

        cursor.execute(query, values)

        self.connection.commit()

        return cursor

    # ==========================
    # FETCH ONE
    # ==========================
    def fetch_one(self, query, values=None):

        cursor = self.get_cursor()

        cursor.execute(query, values)

        return cursor.fetchone()

    # ==========================
    # FETCH ALL
    # ==========================
    def fetch_all(self, query, values=None):

        cursor = self.get_cursor()

        cursor.execute(query, values)

        return cursor.fetchall()


# ==========================
# INIT DB
# ==========================
db = MySQLService()


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

            WHEN lc.trang_thai =
            'dang_chay'
            THEN 1

            WHEN lc.trang_thai =
            'sap_chay'
            THEN 2

            WHEN lc.trang_thai =
            'hoan_thanh'
            THEN 3

            ELSE 4

        END,

        lc.gio_bat_dau DESC

        LIMIT 1
        """

        return db.fetch_one(sql, (tai_xe_id,))

    except Exception as e:

        print("Dashboard error:", e)

        return None
