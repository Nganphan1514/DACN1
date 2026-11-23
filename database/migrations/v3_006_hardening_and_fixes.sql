-- ============================================================================
-- MIGRATION V3.1 (v3_006): Hardening RBAC, Appeals, Camera Flapping & Enum
-- Chay truc tiep trong Supabase SQL Editor hoac scripts/run_v3_migrations.py
-- ============================================================================

-- 1. FIX-10: Thu hoi phien tuc thi da worker bang token_version
ALTER TABLE tai_khoan
    ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

-- 2. FIX-04: Chan vong lap khieu nai vo han
ALTER TABLE khieu_nai_vi_pham
    ADD COLUMN IF NOT EXISTS lan_khieu_nai SMALLINT NOT NULL DEFAULT 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_khieu_nai_dang_mo_theo_vi_pham
    ON khieu_nai_vi_pham (vi_pham_id)
    WHERE trang_thai IN ('SUBMITTED', 'RECEIVED', 'UNDER_REVIEW', 'NEED_MORE_INFO');

CREATE UNIQUE INDEX IF NOT EXISTS uq_khieu_nai_vi_pham_lan
    ON khieu_nai_vi_pham (vi_pham_id, lan_khieu_nai);

-- Bo sung cau hinh mac dinh vao cong_ty.cau_hinh_jsonb
UPDATE cong_ty
SET cau_hinh_jsonb = COALESCE(cau_hinh_jsonb, '{}'::jsonb)
    || jsonb_build_object(
        'max_appeals_per_violation', COALESCE((cau_hinh_jsonb->>'max_appeals_per_violation')::int, 1),
        'appeal_deadline_hours', COALESCE((cau_hinh_jsonb->>'appeal_deadline_hours')::int, 72),
        'require_pre_trip_checklist', COALESCE((cau_hinh_jsonb->>'require_pre_trip_checklist')::boolean, true)
    );

-- 3. FIX-07: Theo doi Flapping & PAUSED keo dai tren thiet_bi_camera
ALTER TABLE thiet_bi_camera
    ADD COLUMN IF NOT EXISTS paused_since TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS so_lan_mat_ket_noi_10p INTEGER NOT NULL DEFAULT 0;

-- 4. FIX-08: Danh dau canh bao tre gio tren chuyen_thuc_te
ALTER TABLE chuyen_thuc_te
    ADD COLUMN IF NOT EXISTS canh_bao_tre_gio BOOLEAN NOT NULL DEFAULT FALSE;

-- 5. FIX-09: Chuan hoa 100% du lieu cu & khoa CHECK constraint cho lich_chay.trang_thai
ALTER TABLE lich_chay DROP CONSTRAINT IF EXISTS lich_chay_trang_thai_check;
ALTER TABLE lich_chay DROP CONSTRAINT IF EXISTS chk_lich_chay_trang_thai_v3;

UPDATE lich_chay SET trang_thai = 'CHO_XAC_NHAN'   WHERE LOWER(trang_thai) IN ('sap_chay', 'cho_xac_nhan', 'nhap');
UPDATE lich_chay SET trang_thai = 'DA_XAC_NHAN'    WHERE LOWER(trang_thai) = 'da_xac_nhan';
UPDATE lich_chay SET trang_thai = 'BI_TU_CHOI'     WHERE LOWER(trang_thai) = 'bi_tu_choi';
UPDATE lich_chay SET trang_thai = 'DANG_THUC_HIEN' WHERE LOWER(trang_thai) IN ('dang_chay', 'dang_thuc_hien', 'tam_ngung');
UPDATE lich_chay SET trang_thai = 'HOAN_THANH'     WHERE LOWER(trang_thai) IN ('hoan_thanh', 'can_kiem_tra');
UPDATE lich_chay SET trang_thai = 'DA_HUY'         WHERE LOWER(trang_thai) IN ('huy', 'da_huy', 'khong_khoi_hanh');

ALTER TABLE lich_chay
    ALTER COLUMN trang_thai SET DEFAULT 'CHO_XAC_NHAN';

ALTER TABLE lich_chay
    ADD CONSTRAINT chk_lich_chay_trang_thai_v3
    CHECK (trang_thai IN (
        'CHO_XAC_NHAN', 'DA_XAC_NHAN', 'BI_TU_CHOI',
        'DANG_THUC_HIEN', 'HOAN_THANH', 'DA_HUY', 'KET_THUC_NGOAI_LE'
    ));
