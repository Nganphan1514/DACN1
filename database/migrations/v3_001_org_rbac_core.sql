-- ============================================================
-- DACN1 V3.0 - MIGRATION SPRINT 1
-- To chuc da chi nhanh (Cong ty -> Chi nhanh -> Doi xe)
-- RBAC 6 vai tro & Audit Log mo rong (du_lieu_truoc/sau, ly_do)
-- Chay truc tiep trong Supabase SQL Editor (idempotent)
-- ============================================================

-- 1. CONG TY
CREATE TABLE IF NOT EXISTS cong_ty (
    id SERIAL PRIMARY KEY,
    ma_cong_ty VARCHAR(50) UNIQUE NOT NULL,
    ten VARCHAR(255) NOT NULL,
    dia_chi TEXT NULL,
    so_dien_thoai VARCHAR(30) NULL,
    cau_hinh_jsonb JSONB NOT NULL DEFAULT '{
        "quan_he_lich_chuyen": "1-1",
        "tu_choi_lich_dieu_phoi_gan_lai_ngay": true,
        "uy_quyen_giam_sat_xac_minh_vi_pham": false,
        "thoi_han_khieu_nai_ngay": 7,
        "camera_offline_timeout_giay": 60
    }'::jsonb,
    trang_thai VARCHAR(30) DEFAULT 'HOAT_DONG'
        CHECK (trang_thai IN ('HOAT_DONG', 'TAM_NGUNG')),
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. CHI NHANH
CREATE TABLE IF NOT EXISTS chi_nhanh (
    id SERIAL PRIMARY KEY,
    cong_ty_id INT NOT NULL REFERENCES cong_ty(id) ON DELETE RESTRICT,
    ma_chi_nhanh VARCHAR(50) UNIQUE NOT NULL,
    ten VARCHAR(255) NOT NULL,
    dia_chi TEXT NULL,
    so_dien_thoai VARCHAR(30) NULL,
    trang_thai VARCHAR(30) DEFAULT 'HOAT_DONG'
        CHECK (trang_thai IN ('HOAT_DONG', 'TAM_NGUNG')),
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. DOI XE
CREATE TABLE IF NOT EXISTS doi_xe (
    id SERIAL PRIMARY KEY,
    chi_nhanh_id INT NOT NULL REFERENCES chi_nhanh(id) ON DELETE RESTRICT,
    ma_doi_xe VARCHAR(50) UNIQUE NOT NULL,
    ten VARCHAR(255) NOT NULL,
    mo_ta TEXT NULL,
    trang_thai VARCHAR(30) DEFAULT 'HOAT_DONG'
        CHECK (trang_thai IN ('HOAT_DONG', 'TAM_NGUNG')),
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. LICH SU CHUYEN DOI XE (TAI XE / XE)
CREATE TABLE IF NOT EXISTS lich_su_chuyen_doi_xe (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('TAI_XE', 'XE')),
    entity_id INT NOT NULL,
    doi_xe_cu_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    doi_xe_moi_id INT NOT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    ly_do TEXT NOT NULL,
    nguoi_thuc_hien_id INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. MO RONG TAI_KHOAN LEN 6 VAI TRO & PHAM VI DU LIEU
ALTER TABLE tai_khoan DROP CONSTRAINT IF EXISTS tai_khoan_vai_tro_check;
ALTER TABLE tai_khoan
    ALTER COLUMN vai_tro TYPE VARCHAR(40);
ALTER TABLE tai_khoan
    ADD CONSTRAINT tai_khoan_vai_tro_check
    CHECK (vai_tro IN (
        'admin_he_thong',
        'quan_tri_cong_ty',
        'quan_ly',
        'dieu_phoi_vien',
        'giam_sat',
        'tai_xe'
    ));

ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS cong_ty_id INT NULL REFERENCES cong_ty(id) ON DELETE RESTRICT;
ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS chi_nhanh_id INT NULL REFERENCES chi_nhanh(id) ON DELETE RESTRICT;
ALTER TABLE tai_khoan ADD COLUMN IF NOT EXISTS doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT;

-- 6. BO SUNG DOI_XE_ID CHO CAC BANG NGHIỆP VỤ HIEN CO
ALTER TABLE tai_xe ADD COLUMN IF NOT EXISTS doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT;
ALTER TABLE xe ADD COLUMN IF NOT EXISTS doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT;
ALTER TABLE thiet_bi_camera ADD COLUMN IF NOT EXISTS doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT;
ALTER TABLE lich_chay ADD COLUMN IF NOT EXISTS doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT;

-- 7. MO RONG AUDIT LOG (LICH_SU_THAO_TAC)
ALTER TABLE lich_su_thao_tac ADD COLUMN IF NOT EXISTS du_lieu_truoc JSONB NULL;
ALTER TABLE lich_su_thao_tac ADD COLUMN IF NOT EXISTS du_lieu_sau JSONB NULL;
ALTER TABLE lich_su_thao_tac ADD COLUMN IF NOT EXISTS ly_do TEXT NULL;

-- 8. SEED TO CHUC MAC DINH & BACKFILL DU LIEU CU (KHONG GAY GIAN DOAN)
INSERT INTO cong_ty (ma_cong_ty, ten, dia_chi)
VALUES ('CTY_MAC_DINH', 'Công ty Vận tải DACN1', 'TP. Hồ Chí Minh')
ON CONFLICT (ma_cong_ty) DO NOTHING;

INSERT INTO chi_nhanh (cong_ty_id, ma_chi_nhanh, ten, dia_chi)
SELECT c.id, 'CN_MAC_DINH', 'Chi nhánh Trung tâm', 'TP. Hồ Chí Minh'
FROM cong_ty c
WHERE c.ma_cong_ty = 'CTY_MAC_DINH'
ON CONFLICT (ma_chi_nhanh) DO NOTHING;

INSERT INTO doi_xe (chi_nhanh_id, ma_doi_xe, ten, mo_ta)
SELECT cn.id, 'DX_MAC_DINH', 'Đội xe số 1', 'Đội xe mặc định khi nâng cấp lên V3.0'
FROM chi_nhanh cn
WHERE cn.ma_chi_nhanh = 'CN_MAC_DINH'
ON CONFLICT (ma_doi_xe) DO NOTHING;

-- Backfill cong_ty_id / chi_nhanh_id / doi_xe_id cho cac ban ghi cu dang NULL
UPDATE tai_khoan
SET
    cong_ty_id = COALESCE(cong_ty_id, (SELECT id FROM cong_ty WHERE ma_cong_ty = 'CTY_MAC_DINH' LIMIT 1)),
    chi_nhanh_id = CASE
        WHEN vai_tro IN ('admin_he_thong', 'quan_tri_cong_ty') THEN chi_nhanh_id
        ELSE COALESCE(chi_nhanh_id, (SELECT id FROM chi_nhanh WHERE ma_chi_nhanh = 'CN_MAC_DINH' LIMIT 1))
    END,
    doi_xe_id = CASE
        WHEN vai_tro IN ('admin_he_thong', 'quan_tri_cong_ty') THEN doi_xe_id
        ELSE COALESCE(doi_xe_id, (SELECT id FROM doi_xe WHERE ma_doi_xe = 'DX_MAC_DINH' LIMIT 1))
    END
WHERE cong_ty_id IS NULL;

UPDATE tai_xe
SET doi_xe_id = (SELECT id FROM doi_xe WHERE ma_doi_xe = 'DX_MAC_DINH' LIMIT 1)
WHERE doi_xe_id IS NULL;

UPDATE xe
SET doi_xe_id = (SELECT id FROM doi_xe WHERE ma_doi_xe = 'DX_MAC_DINH' LIMIT 1)
WHERE doi_xe_id IS NULL;

UPDATE thiet_bi_camera tb
SET doi_xe_id = COALESCE(
    (SELECT x.doi_xe_id FROM xe x WHERE x.id = tb.xe_id),
    (SELECT id FROM doi_xe WHERE ma_doi_xe = 'DX_MAC_DINH' LIMIT 1)
)
WHERE tb.doi_xe_id IS NULL;

UPDATE lich_chay lc
SET doi_xe_id = COALESCE(
    (SELECT x.doi_xe_id FROM xe x WHERE x.id = lc.xe_id),
    (SELECT tx.doi_xe_id FROM tai_xe tx WHERE tx.id = lc.tai_xe_id),
    (SELECT id FROM doi_xe WHERE ma_doi_xe = 'DX_MAC_DINH' LIMIT 1)
)
WHERE lc.doi_xe_id IS NULL;

-- 9. INDEX PHAM VI TO CHUC
CREATE INDEX IF NOT EXISTS idx_chi_nhanh_cong_ty ON chi_nhanh (cong_ty_id);
CREATE INDEX IF NOT EXISTS idx_doi_xe_chi_nhanh ON doi_xe (chi_nhanh_id);
CREATE INDEX IF NOT EXISTS idx_tai_khoan_scope ON tai_khoan (vai_tro, cong_ty_id, chi_nhanh_id, doi_xe_id);
CREATE INDEX IF NOT EXISTS idx_tai_xe_doi_xe ON tai_xe (doi_xe_id);
CREATE INDEX IF NOT EXISTS idx_xe_doi_xe ON xe (doi_xe_id);
CREATE INDEX IF NOT EXISTS idx_lich_chay_doi_xe_ngay ON lich_chay (doi_xe_id, ngay_tao DESC);
CREATE INDEX IF NOT EXISTS idx_lich_su_chuyen_doi_xe ON lich_su_chuyen_doi_xe (entity_type, entity_id, created_at DESC);
