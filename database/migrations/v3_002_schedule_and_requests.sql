-- ============================================================
-- DACN1 V3.0 - MIGRATION SPRINT 2
-- Lich chay xac nhan bat buoc, Yeu cau doi lich/doi xe & Lich su phan cong
-- Chay truc tiep trong Supabase SQL Editor (idempotent)
-- ============================================================

-- 1. MO RONG BANG LICH_CHAY
ALTER TABLE lich_chay DROP CONSTRAINT IF EXISTS lich_chay_trang_thai_check;
ALTER TABLE lich_chay
    ALTER COLUMN trang_thai TYPE VARCHAR(30);

ALTER TABLE lich_chay
    ADD CONSTRAINT lich_chay_trang_thai_check
    CHECK (trang_thai IN (
        -- Chuan V3.0 (CHU HOA)
        'NHAP',
        'CHO_XAC_NHAN',
        'DA_XAC_NHAN',
        'SAP_CHAY',
        'DANG_THUC_HIEN',
        'HOAN_THANH',
        'BI_TU_CHOI',
        'DA_HUY',
        'KHONG_KHOI_HANH',
        'CAN_KIEM_TRA',
        'KET_THUC_NGOAI_LE',
        -- Tuong thich nguoc du lieu cu (chu thuong)
        'sap_chay',
        'dang_chay',
        'tam_ngung',
        'hoan_thanh',
        'da_huy'
    ));

ALTER TABLE lich_chay ADD COLUMN IF NOT EXISTS xac_nhan_at TIMESTAMP NULL;
ALTER TABLE lich_chay ADD COLUMN IF NOT EXISTS ly_do_tu_choi TEXT NULL;
ALTER TABLE lich_chay ADD COLUMN IF NOT EXISTS ly_do_huy TEXT NULL;
ALTER TABLE lich_chay ADD COLUMN IF NOT EXISTS created_by INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT;
ALTER TABLE lich_chay ADD COLUMN IF NOT EXISTS updated_by INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT;

-- Backfill gio_ket_thuc cho cac ban ghi cu bi NULL truoc khi them CHECK (SCH-01)
UPDATE lich_chay
SET gio_ket_thuc = gio_bat_dau + INTERVAL '4 hours'
WHERE gio_bat_dau IS NOT NULL AND gio_ket_thuc IS NULL;

ALTER TABLE lich_chay DROP CONSTRAINT IF EXISTS chk_lich_chay_gio_hop_le;
ALTER TABLE lich_chay
    ADD CONSTRAINT chk_lich_chay_gio_hop_le
    CHECK (gio_ket_thuc IS NULL OR gio_bat_dau IS NULL OR gio_ket_thuc > gio_bat_dau);

-- 2. BANG YEU CAU THAY DOI LICH / DOI XE (REQ-01)
CREATE TABLE IF NOT EXISTS yeu_cau_thay_doi_lich (
    id SERIAL PRIMARY KEY,
    lich_chay_id INT NOT NULL REFERENCES lich_chay(id) ON DELETE RESTRICT,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    loai_yeu_cau VARCHAR(30) NOT NULL
        CHECK (loai_yeu_cau IN ('DOI_THOI_GIAN', 'DOI_XE', 'HUY_LICH', 'KHONG_THE_NHAN')),
    du_lieu_de_xuat JSONB NOT NULL DEFAULT '{}'::jsonb,
    ly_do TEXT NOT NULL,
    trang_thai VARCHAR(30) NOT NULL DEFAULT 'CHO_DUYET'
        CHECK (trang_thai IN (
            'CHO_DUYET',
            'DA_DUYET',
            'TU_CHOI',
            'CAN_BO_SUNG',
            'DA_RUT_YEU_CAU',
            'HET_HAN'
        )),
    nguoi_duyet_id INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    ly_do_tu_choi TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMP NULL
);

-- 3. BANG LICH SU PHAN CONG (SCH-04)
CREATE TABLE IF NOT EXISTS lich_su_phan_cong (
    id SERIAL PRIMARY KEY,
    lich_chay_id INT NOT NULL REFERENCES lich_chay(id) ON DELETE RESTRICT,
    tai_xe_cu_id INT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    tai_xe_moi_id INT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    xe_cu_id INT NULL REFERENCES xe(id) ON DELETE RESTRICT,
    xe_moi_id INT NULL REFERENCES xe(id) ON DELETE RESTRICT,
    gio_bat_dau_cu TIMESTAMP NULL,
    gio_bat_dau_moi TIMESTAMP NULL,
    gio_ket_thuc_cu TIMESTAMP NULL,
    gio_ket_thuc_moi TIMESTAMP NULL,
    nguoi_thuc_hien_id INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    nguon_thay_doi VARCHAR(40) NOT NULL,
    ly_do TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. INDEX CHONG TRUNG LICH & TRUY VAN NHANH
CREATE INDEX IF NOT EXISTS idx_lich_chay_tai_xe_time
    ON lich_chay (tai_xe_id, gio_bat_dau, gio_ket_thuc, trang_thai);
CREATE INDEX IF NOT EXISTS idx_lich_chay_xe_time
    ON lich_chay (xe_id, gio_bat_dau, gio_ket_thuc, trang_thai);
CREATE INDEX IF NOT EXISTS idx_yc_thay_doi_lich_status
    ON yeu_cau_thay_doi_lich (trang_thai, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_yc_thay_doi_lich_tai_xe
    ON yeu_cau_thay_doi_lich (tai_xe_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lich_su_phan_cong_lich
    ON lich_su_phan_cong (lich_chay_id, created_at DESC);
