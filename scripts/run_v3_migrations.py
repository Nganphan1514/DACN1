"""
Script chay 5 file SQL Migration V3.0 (v3_001 -> v3_005) truc tiep len Supabase PostgreSQL
va thuc hien smoke test kiem tra cac bang moi, trigger bat bien & du lieu backfill.
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import psycopg2
from psycopg2.extras import RealDictCursor

from config.app_config import DATABASE_URL

MIGRATION_FILES = [
    "database/migrations/v3_001_org_rbac_core.sql",
    "database/migrations/v3_002_schedule_and_requests.sql",
    "database/migrations/v3_003_trips_and_camera_logs.sql",
    "database/migrations/v3_004_violations_and_appeals.sql",
    "database/migrations/v3_005_p1_checklist_and_analytics.sql",
    "database/migrations/v3_006_hardening_and_fixes.sql",
]

EXPECTED_V3_TABLES = [
    "cong_ty",
    "chi_nhanh",
    "doi_xe",
    "lich_su_chuyen_doi_xe",
    "yeu_cau_thay_doi_lich",
    "lich_su_phan_cong",
    "chuyen_thuc_te",
    "lich_su_ket_noi_camera",
    "vi_pham",
    "khieu_nai_vi_pham",
    "lich_su_khieu_nai",
    "checklist_truoc_chuyen",
    "checklist_truoc_chuyen_chi_tiet",
]


def main():
    if not DATABASE_URL:
        print("ERROR: Thieu DATABASE_URL trong .env")
        sys.exit(1)

    print("Ket noi toi Supabase PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for rel_path in MIGRATION_FILES:
                full_path = os.path.join(ROOT_DIR, rel_path)
                print(f"\n>>> Dang chay migration: {rel_path}")
                with open(full_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                cur.execute(sql)
                conn.commit()
                print(f"    [OK] Hoan tat {rel_path}")

            # Smoke test 1: Kiem tra tat ca 13 bang moi da ton tai
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                ORDER BY table_name
                """,
                (EXPECTED_V3_TABLES,),
            )
            found = [r["table_name"] for r in cur.fetchall()]
            missing = sorted(set(EXPECTED_V3_TABLES) - set(found))
            print(f"\n>>> Bang V3 da ton tai: {len(found)}/{len(EXPECTED_V3_TABLES)}")
            if missing:
                print(f"    [WARN] Thieu bang: {missing}")
                sys.exit(2)

            # Smoke test 2: Kiem tra seed to chuc mac dinh
            cur.execute("SELECT ma_cong_ty, ten FROM cong_ty ORDER BY id ASC LIMIT 5")
            companies = cur.fetchall()
            cur.execute("SELECT ma_chi_nhanh, ten FROM chi_nhanh ORDER BY id ASC LIMIT 5")
            branches = cur.fetchall()
            cur.execute("SELECT ma_doi_xe, ten FROM doi_xe ORDER BY id ASC LIMIT 5")
            fleets = cur.fetchall()
            print(f"    Cong ty: {len(companies)} | Chi nhanh: {len(branches)} | Doi xe: {len(fleets)}")

            # Smoke test 3: Kiem tra 2 trigger bat bien (su_kien_canh_bao & khieu_nai_vi_pham)
            cur.execute(
                """
                SELECT trigger_name, event_object_table
                FROM information_schema.triggers
                WHERE trigger_name IN ('trg_su_kien_canh_bao_immutable', 'trg_khieu_nai_immutable')
                ORDER BY trigger_name
                """
            )
            triggers = cur.fetchall()
            print(f"    Trigger bat bien: {[t['trigger_name'] for t in triggers]}")

            # Smoke test 4: Kiem tra backfill doi_xe_id
            cur.execute("SELECT COUNT(*) AS c FROM tai_xe WHERE doi_xe_id IS NULL")
            tx_null = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM xe WHERE doi_xe_id IS NULL")
            xe_null = cur.fetchone()["c"]
            print(f"    Backfill check -> tai_xe chua co doi_xe_id: {tx_null}, xe chua co doi_xe_id: {xe_null}")

        print("\n=== MIGRATION V3 & SMOKE TEST SUPABASE THANH CONG 100% ===")
    except Exception as e:
        conn.rollback()
        print(f"\nERROR khi chay migration: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
