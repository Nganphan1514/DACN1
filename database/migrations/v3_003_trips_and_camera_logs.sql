-- ============================================================
-- DACN1 V3.0 - MIGRATION SPRINT 3
-- Chuyen thuc te (tach khoi Phien lai xe) & Lich su ket noi Camera
-- Chay truc tiep trong Supabase SQL Editor (idempotent)
-- ============================================================

-- 1. BANG CHUYEN THUC TE (TRIP-01, TRIP-02, TRIP-03, TRIP-04)
CREATE TABLE IF NOT EXISTS chuyen_thuc_te (
    id SERIAL PRIMARY KEY,
    lich_chay_id INT NOT NULL UNIQUE REFERENCES lich_chay(id) ON DELETE RESTRICT,
    doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    xe_id INT NOT NULL REFERENCES xe(id) ON DELETE RESTRICT,
    trang_thai VARCHAR(30) NOT NULL DEFAULT 'DANG_CHAY'
        CHECK (trang_thai IN (
            'CHUA_KHOI_HANH',
            'DANG_CHAY',
            'TAM_DUNG',
            'GAP_SU_CO',
            'CAN_KIEM_TRA',
            'HOAN_THANH',
            'KET_THUC_NGOAI_LE'
        )),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    ket_thuc_boi_id INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    loai_ket_thuc VARCHAR(30) NULL
        CHECK (loai_ket_thuc IN ('TAI_XE_KET_THUC', 'QUAN_LY_NGOAI_LE')),
    ly_do_ngoai_le TEXT NULL,
    ghi_chu TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partial unique index: 1 tai xe / 1 xe chi co toi da 1 chuyen DANG_CHAY cung luc (TRIP-01)
CREATE UNIQUE INDEX IF NOT EXISTS uq_chuyen_thuc_te_tai_xe_dang_chay
    ON chuyen_thuc_te (tai_xe_id)
    WHERE trang_thai = 'DANG_CHAY';

CREATE UNIQUE INDEX IF NOT EXISTS uq_chuyen_thuc_te_xe_dang_chay
    ON chuyen_thuc_te (xe_id)
    WHERE trang_thai = 'DANG_CHAY';

CREATE INDEX IF NOT EXISTS idx_chuyen_thuc_te_doi_xe_created
    ON chuyen_thuc_te (doi_xe_id, created_at DESC);

-- 2. LIEN KET PHIEN_LAI_XE -> CHUYEN_THUC_TE
ALTER TABLE phien_lai_xe
    ADD COLUMN IF NOT EXISTS chuyen_thuc_te_id INT NULL REFERENCES chuyen_thuc_te(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_phien_lai_xe_chuyen
    ON phien_lai_xe (chuyen_thuc_te_id);

-- 3. BANG LICH SU KET NOI CAMERA (CAM-01, CAM-02, CAM-03)
CREATE TABLE IF NOT EXISTS lich_su_ket_noi_camera (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    xe_id INT NULL REFERENCES xe(id) ON DELETE RESTRICT,
    chuyen_thuc_te_id INT NULL REFERENCES chuyen_thuc_te(id) ON DELETE RESTRICT,
    trang_thai VARCHAR(30) NOT NULL
        CHECK (trang_thai IN ('ONLINE', 'UNSTABLE', 'OFFLINE', 'RECOVERING')),
    bat_dau_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ket_thuc_at TIMESTAMP NULL,
    thoi_luong_giay INT NULL,
    ghi_chu TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_cam_conn_device_time
    ON lich_su_ket_noi_camera (device_id, bat_dau_at DESC);

CREATE INDEX IF NOT EXISTS idx_cam_conn_chuyen
    ON lich_su_ket_noi_camera (chuyen_thuc_te_id, bat_dau_at DESC);
