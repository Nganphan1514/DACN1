"""
Script di chuyen toan bo du lieu tu MySQL (XAMPP) sang Supabase (PostgreSQL).

Cach chay:
1. Chay database/schema_postgres.sql trong Supabase SQL Editor truoc.
2. Dien DATABASE_URL (Supabase) va MYSQL_* (XAMPP) trong file .env.
3. Chay: python scripts/migrate_mysql_to_supabase.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
import psycopg2
from psycopg2.extras import execute_values

from config.app_config import (
    DATABASE_URL,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


# Thu tu bang dam bao dung khoa ngoai (parent -> child)
TABLES_IN_ORDER = [
    ("tai_khoan", ["id", "ten_dang_nhap", "mat_khau", "vai_tro", "trang_thai", "ngay_tao"]),
    ("tai_xe", ["id", "tai_khoan_id", "ho_ten", "so_dien_thoai", "so_gplx", "dia_chi", "avatar", "trang_thai", "ngay_tao"]),
    ("xe", ["id", "bien_so", "model", "loai_xe", "trang_thai", "ghi_chu", "tai_xe_mac_dinh_id", "ngay_tao"]),
    ("lich_chay", ["id", "tai_xe_id", "xe_id", "tuyen_duong", "gio_bat_dau", "gio_ket_thuc", "trang_thai", "ghi_chu", "ngay_tao"]),
    ("phien_lai_xe", ["id", "tai_xe_id", "xe_id", "lich_chay_id", "bat_dau", "ket_thuc", "thoi_diem_mat_dau", "tong_phut", "tong_lan_buon_ngu", "trang_thai"]),
    ("nhat_ky_phat_hien", ["id", "tai_xe_id", "xe_id", "lich_chay_id", "ear", "mar", "risk_score", "trang_thai", "thoi_gian"]),
    ("anh_canh_bao", ["id", "tai_xe_id", "xe_id", "lich_chay_id", "duong_dan_anh", "thoi_gian"]),
    ("nguoi_la", ["id", "xe_id", "duong_dan_anh", "ghi_chu", "thoi_gian"]),
    ("ghi_chu", ["id", "tai_xe_id", "quan_ly_id", "noi_dung", "da_doc", "thoi_gian"]),
    ("bao_cao_su_co", ["id", "tai_xe_id", "xe_id", "lich_chay_id", "tieu_de", "loai_su_co", "noi_dung", "hinh_anh", "trang_thai", "phan_hoi_quan_ly", "thoi_gian"]),
    ("lich_su_thao_tac", ["id", "nguoi_thuc_hien_id", "vai_tro", "hanh_dong", "bang_du_lieu", "doi_tuong_id", "ghi_chu", "thoi_gian"]),
    ("du_lieu_khuon_mat", ["id", "tai_xe_id", "vector_khuon_mat", "do_tin_cay", "trang_thai", "mo_ta", "ngay_tao"]),
    ("anh_khuon_mat", ["id", "tai_xe_id", "du_lieu_anh", "ngay_tao"]),
]

BOOLEAN_COLUMNS = {"da_doc"}
BYTES_COLUMNS = {"du_lieu_anh"}


def get_mysql_table_columns(mysql_cursor, table_name):
    try:
        mysql_cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        return {row["Field"] for row in mysql_cursor.fetchall()}
    except Exception:
        return set()


def normalize_value(table_name, col_name, value):
    if value is None:
        return None
    if table_name == "lich_chay" and col_name == "trang_thai" and value == "huy":
        return "da_huy"
    if col_name in BOOLEAN_COLUMNS:
        return bool(value)
    if col_name in BYTES_COLUMNS and isinstance(value, (bytes, bytearray)):
        return psycopg2.Binary(bytes(value))
    return value


def migrate():
    if not DATABASE_URL:
        print("LOI: Chua cau hinh DATABASE_URL (Supabase) trong file .env!")
        sys.exit(1)

    print(f"Dang ket noi MySQL XAMPP ({MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE})...")
    mysql_conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
    )
    mysql_cur = mysql_conn.cursor(dictionary=True)

    print("Dang ket noi Supabase PostgreSQL...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    try:
        # Xoa du lieu cu tren Supabase (theo thu tu nguoc) de tranh trung ID
        table_names = ", ".join(t[0] for t in reversed(TABLES_IN_ORDER))
        pg_cur.execute(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;")

        for table_name, target_cols in TABLES_IN_ORDER:
            mysql_cols = get_mysql_table_columns(mysql_cur, table_name)
            if not mysql_cols:
                print(f"[BO QUA] Bang '{table_name}' khong ton tai tren MySQL XAMPP.")
                continue

            common_cols = [c for c in target_cols if c in mysql_cols]
            if not common_cols:
                continue

            select_cols = ", ".join(f"`{c}`" for c in common_cols)
            mysql_cur.execute(f"SELECT {select_cols} FROM `{table_name}`")
            rows = mysql_cur.fetchall()

            if not rows:
                print(f"[0 dong] {table_name}")
                continue

            values = [
                tuple(normalize_value(table_name, col, row.get(col)) for col in common_cols)
                for row in rows
            ]

            pg_cols = ", ".join(common_cols)
            insert_sql = f"INSERT INTO {table_name} ({pg_cols}) VALUES %s ON CONFLICT DO NOTHING"
            execute_values(pg_cur, insert_sql, values, page_size=200)

            # Dong bo lai SEQUENCE cho cot id SERIAL
            if "id" in common_cols:
                pg_cur.execute(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                        true
                    );
                    """
                )

            pg_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            pg_count = pg_cur.fetchone()[0]
            status_tag = "KHOP 100%" if pg_count == len(rows) else f"LECH (MySQL={len(rows)}, Supabase={pg_count})"
            print(f"[{status_tag}] {table_name}: {pg_count}/{len(rows)} dong")

        # Kiem tra xem tren MySQL con bang nao khac chua nam trong danh sach migrate khong
        mysql_cur.execute("SHOW TABLES")
        all_mysql_tables = {list(r.values())[0] for r in mysql_cur.fetchall()}
        migrated_names = {t[0] for t in TABLES_IN_ORDER}
        extra_tables = sorted(all_mysql_tables - migrated_names)
        if extra_tables:
            print(f"\n[LUU Y] Cac bang co tren MySQL nhung chua migrate: {extra_tables}")

        pg_conn.commit()
        print("\nDI CHUYEN DU LIEU TU MYSQL XAMPP SANG SUPABASE THANH CONG!")

    except Exception as e:
        pg_conn.rollback()
        print("\nLOI KHI MIGRATE (da rollback):", e)
        raise
    finally:
        mysql_cur.close()
        mysql_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate()
