-- ============================================================
-- DACN1 V3.0 - MIGRATION P1
-- Checklist kiem tra xe truoc chuyen (muc 5.3 & 8.3)
-- Chay truc tiep trong Supabase SQL Editor (idempotent)
-- ============================================================

CREATE TABLE IF NOT EXISTS checklist_truoc_chuyen (
    id SERIAL PRIMARY KEY,
    lich_chay_id INT NOT NULL REFERENCES lich_chay(id) ON DELETE RESTRICT,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    xe_id INT NOT NULL REFERENCES xe(id) ON DELETE RESTRICT,
    doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    ket_qua_tong VARCHAR(20) NOT NULL CHECK (ket_qua_tong IN ('DAT', 'KHONG_DAT')),
    bao_cao_su_co_id INT NULL REFERENCES bao_cao_su_co(id) ON DELETE RESTRICT,
    ghi_chu TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checklist_truoc_chuyen_chi_tiet (
    id SERIAL PRIMARY KEY,
    checklist_id INT NOT NULL REFERENCES checklist_truoc_chuyen(id) ON DELETE CASCADE,
    ma_hang_muc VARCHAR(50) NOT NULL,
    ten_hang_muc VARCHAR(150) NOT NULL,
    bat_buoc BOOLEAN NOT NULL DEFAULT TRUE,
    ket_qua VARCHAR(20) NOT NULL CHECK (ket_qua IN ('DAT', 'KHONG_DAT')),
    ghi_chu TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_checklist_lich_chay
    ON checklist_truoc_chuyen (lich_chay_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_checklist_doi_xe
    ON checklist_truoc_chuyen (doi_xe_id, created_at DESC);
