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
    driver_id=None,
    vehicle_id=None,
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

        values = (driver_id, vehicle_id, lich_chay_id, ear, mar, risk_score, status)

        db.execute(query, values)

        print("Da luu nhat ky AI")

    except Exception as e:

        print("Save detection log error:", e)
