import mysql.connector
from mysql.connector import Error


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
                host="localhost", user="root", password="", database="he_thong_tai_xe"
            )

            print("MySQL Connected")

        except Error as e:

            print("Database Error:", e)

    # ==========================
    # GET CURSOR
    # ==========================
    def get_cursor(self):

        if self.connection is None or not self.connection.is_connected():

            self.connect()

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
    # AUDIT LOG
    # ==========================
    def ghi_lich_su_thao_tac(
        self,
        nguoi_thuc_hien_id,
        vai_tro,
        hanh_dong,
        bang_du_lieu,
        doi_tuong_id=None,
        ghi_chu=None,
    ):

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

        values = (
            nguoi_thuc_hien_id,
            vai_tro,
            hanh_dong,
            bang_du_lieu,
            doi_tuong_id,
            ghi_chu,
        )

        self.execute(query, values)

    # ==========================
    # THEM GHI CHU
    # ==========================
    def them_ghi_chu(self, tai_xe_id, quan_ly_id, noi_dung):

        query = """
        INSERT INTO
        ghi_chu
        (
            tai_xe_id,
            quan_ly_id,
            noi_dung
        )
        VALUES
        (%s,%s,%s)
        """

        values = (tai_xe_id, quan_ly_id, noi_dung)

        self.execute(query, values)

    # ==========================
    # GET GHI CHU
    # ==========================
    def lay_ghi_chu(self, tai_xe_id):

        query = """
        SELECT *
        FROM ghi_chu
        WHERE tai_xe_id=%s
        ORDER BY id DESC
        """

        return self.fetch_all(query, (tai_xe_id,))


# ==========================
# INIT DB
# ==========================
db = MySQLService()


# ==========================
# SAVE DETECTION LOG
# ==========================
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
        INSERT INTO
        nhat_ky_phat_hien
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
            status
        )
        db.execute(query, values)

        print("Da luu nhat ky AI")

    except Exception as e:

        print("Save detection log error:", e)


# ==========================
# LẤY THÔNG TIN TÀI XẾ
# ==========================
def lay_tai_xe_theo_id(tai_xe_id):

    try:

        query = """
        SELECT *
        FROM tai_xe
        WHERE id=%s
        """

        return db.fetch_one(query, (tai_xe_id,))

    except Exception as e:

        print("Loi lay tai xe:", e)

        return None


# ==========================
# LUU ANH CANH BAO
# ==========================
def luu_anh_canh_bao(
    tai_xe_id,
    xe_id,
    duong_dan_anh,
    lich_chay_id=None,
):

    try:

        query = """
        INSERT INTO
        anh_canh_bao
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

    except Exception as e:


        print("Loi luu anh:", e)
# ==========================
# TAO PHIEN LAI XE
# ==========================
def tao_phien_lai_xe(
    tai_xe_id,
    xe_id,
):

    try:

        query = """
        INSERT INTO
        phien_lai_xe
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

        query = """
        SELECT *
        FROM phien_lai_xe
        WHERE tai_xe_id=%s
        AND trang_thai!='DA_KET_THUC'
        ORDER BY id DESC
        LIMIT 1
        """

        return db.fetch_one(query, (tai_xe_id,))

    except Exception as e:

        print("Loi lay phien:", e)

        return None


# ==========================
# CAP NHAT MAT DAU
# ==========================
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

        print("Loi mat dau:", e)


# ==========================
# RESET MAT DAU
# ==========================
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

        print("Loi reset mat dau:", e)


# ==========================
# DONG PHIEN
# ==========================
def dong_phien_lai_xe(phien_id):

    try:

        query = """
        UPDATE phien_lai_xe
        SET
            ket_thuc=
            thoi_diem_mat_dau,

            tong_phut=
            TIMESTAMPDIFF(
                MINUTE,
                bat_dau,
                thoi_diem_mat_dau
            ),

            trang_thai=
            'DA_KET_THUC'
        WHERE id=%s
        """

        db.execute(query, (phien_id,))

    except Exception as e:

        print("Loi dong phien:", e)


def luu_nguoi_la(xe_id, duong_dan_anh=None, ghi_chu=None):

    sql = """
    INSERT INTO nguoi_la
    (
        xe_id,
        duong_dan_anh,
        ghi_chu
    )
    VALUES (%s, %s, %s)
    """

    db.execute(sql, (xe_id, duong_dan_anh, ghi_chu))


def lay_xe_theo_tai_xe(tai_xe_id):

    sql = """
    SELECT *
    FROM xe
    WHERE tai_xe_mac_dinh_id = %s
    LIMIT 1
    """

    return db.fetch_one(sql, (tai_xe_id,))
