-- ============================================================
-- DACN1 - SUPABASE (POSTGRESQL) SCHEMA
-- Dan va chay truc tiep trong Supabase SQL Editor
-- ============================================================

-- 1. TAI KHOAN
CREATE TABLE IF NOT EXISTS tai_khoan (
    id SERIAL PRIMARY KEY,
    ten_dang_nhap VARCHAR(100) UNIQUE NOT NULL,
    mat_khau VARCHAR(255) NOT NULL,
    vai_tro VARCHAR(20) NOT NULL CHECK (vai_tro IN ('quan_ly', 'tai_xe')),
    trang_thai VARCHAR(20) DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong', 'khoa')),
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TAI XE
CREATE TABLE IF NOT EXISTS tai_xe (
    id SERIAL PRIMARY KEY,
    tai_khoan_id INT REFERENCES tai_khoan(id) ON DELETE SET NULL,
    ho_ten VARCHAR(255) NOT NULL,
    so_dien_thoai VARCHAR(20),
    so_gplx VARCHAR(100) UNIQUE,
    dia_chi TEXT,
    avatar VARCHAR(255),
    trang_thai VARCHAR(20) DEFAULT 'nghi' CHECK (trang_thai IN ('dang_lam', 'nghi', 'tam_khoa')),
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. XE
CREATE TABLE IF NOT EXISTS xe (
    id SERIAL PRIMARY KEY,
    bien_so VARCHAR(50) UNIQUE NOT NULL,
    model VARCHAR(255),
    loai_xe VARCHAR(255),
    trang_thai VARCHAR(20) DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong', 'bao_tri', 'ngung')),
    ghi_chu TEXT,
    tai_xe_mac_dinh_id INT NULL REFERENCES tai_xe(id) ON DELETE SET NULL,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. LICH CHAY
CREATE TABLE IF NOT EXISTS lich_chay (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT REFERENCES tai_xe(id) ON DELETE SET NULL,
    xe_id INT REFERENCES xe(id) ON DELETE SET NULL,
    tuyen_duong VARCHAR(255),
    gio_bat_dau TIMESTAMP,
    gio_ket_thuc TIMESTAMP,
    trang_thai VARCHAR(20) DEFAULT 'sap_chay'
        CHECK (trang_thai IN ('sap_chay', 'dang_chay', 'tam_ngung', 'hoan_thanh', 'da_huy')),
    ghi_chu TEXT,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. PHIEN LAI XE
CREATE TABLE IF NOT EXISTS phien_lai_xe (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT REFERENCES tai_xe(id) ON DELETE SET NULL,
    xe_id INT REFERENCES xe(id) ON DELETE SET NULL,
    lich_chay_id INT NULL REFERENCES lich_chay(id) ON DELETE SET NULL,
    bat_dau TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ket_thuc TIMESTAMP NULL,
    thoi_diem_mat_dau TIMESTAMP NULL,
    tong_phut DOUBLE PRECISION DEFAULT 0,
    tong_lan_buon_ngu INT DEFAULT 0,
    trang_thai VARCHAR(20) DEFAULT 'DANG_LAI'
        CHECK (trang_thai IN ('DANG_LAI', 'TAM_MAT_DAU', 'DA_KET_THUC'))
);

-- 6. NHAT KY PHAT HIEN AI
CREATE TABLE IF NOT EXISTS nhat_ky_phat_hien (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT REFERENCES tai_xe(id) ON DELETE SET NULL,
    xe_id INT REFERENCES xe(id) ON DELETE SET NULL,
    lich_chay_id INT NULL REFERENCES lich_chay(id) ON DELETE SET NULL,
    ear DOUBLE PRECISION,
    mar DOUBLE PRECISION,
    risk_score INT,
    trang_thai VARCHAR(100),
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. ANH CANH BAO
CREATE TABLE IF NOT EXISTS anh_canh_bao (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT REFERENCES tai_xe(id) ON DELETE SET NULL,
    xe_id INT REFERENCES xe(id) ON DELETE SET NULL,
    lich_chay_id INT NULL REFERENCES lich_chay(id) ON DELETE SET NULL,
    duong_dan_anh VARCHAR(255),
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. NGUOI LA / TAI XE SAI XE
CREATE TABLE IF NOT EXISTS nguoi_la (
    id SERIAL PRIMARY KEY,
    xe_id INT REFERENCES xe(id) ON DELETE SET NULL,
    duong_dan_anh VARCHAR(255),
    ghi_chu TEXT,
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. GHI CHU / THONG BAO QUAN LY
CREATE TABLE IF NOT EXISTS ghi_chu (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT REFERENCES tai_xe(id) ON DELETE CASCADE,
    quan_ly_id INT REFERENCES tai_khoan(id) ON DELETE SET NULL,
    noi_dung TEXT,
    da_doc BOOLEAN DEFAULT FALSE,
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. BAO CAO SU CO
CREATE TABLE IF NOT EXISTS bao_cao_su_co (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT REFERENCES tai_xe(id) ON DELETE SET NULL,
    xe_id INT NULL REFERENCES xe(id) ON DELETE SET NULL,
    lich_chay_id INT NULL REFERENCES lich_chay(id) ON DELETE SET NULL,
    tieu_de VARCHAR(255) NOT NULL,
    loai_su_co VARCHAR(100) DEFAULT 'KHAC',
    noi_dung TEXT,
    hinh_anh VARCHAR(255) NULL,
    trang_thai VARCHAR(50) DEFAULT 'CHO_XU_LY',
    phan_hoi_quan_ly TEXT NULL,
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. AUDIT LOG
CREATE TABLE IF NOT EXISTS lich_su_thao_tac (
    id SERIAL PRIMARY KEY,
    nguoi_thuc_hien_id INT,
    vai_tro VARCHAR(100),
    hanh_dong VARCHAR(255),
    bang_du_lieu VARCHAR(255),
    doi_tuong_id INT NULL,
    ghi_chu TEXT,
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. DU LIEU VECTOR KHUON MAT (128D)
CREATE TABLE IF NOT EXISTS du_lieu_khuon_mat (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE CASCADE,
    vector_khuon_mat TEXT NOT NULL,
    do_tin_cay DOUBLE PRECISION DEFAULT 1.0,
    trang_thai VARCHAR(20) DEFAULT 'hoat_dong' CHECK (trang_thai IN ('hoat_dong', 'vo_hieu')),
    mo_ta VARCHAR(255) NULL,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. ANH KHUON MAT DANG KY
CREATE TABLE IF NOT EXISTS anh_khuon_mat (
    id SERIAL PRIMARY KEY,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE CASCADE,
    du_lieu_anh BYTEA NOT NULL,
    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. THIET BI NHAN THONG BAO DAY (EXPO PUSH NOTIFICATIONS)
CREATE TABLE IF NOT EXISTS thiet_bi_thong_bao (
    id SERIAL PRIMARY KEY,
    tai_khoan_id INT NOT NULL REFERENCES tai_khoan(id) ON DELETE CASCADE,
    vai_tro VARCHAR(20) NOT NULL,
    expo_push_token VARCHAR(255) UNIQUE NOT NULL,
    nen_tang VARCHAR(30) DEFAULT 'unknown',
    cap_nhat_cuoi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. SU KIEN CANH BAO (VONG DOI XU LY + CHONG TRUNG UUID)
CREATE TABLE IF NOT EXISTS su_kien_canh_bao (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    payload_version VARCHAR(16) DEFAULT '1.0',
    device_id VARCHAR(100) NULL,
    tai_xe_id INT NULL REFERENCES tai_xe(id) ON DELETE SET NULL,
    xe_id INT NULL REFERENCES xe(id) ON DELETE SET NULL,
    phien_id INT NULL REFERENCES phien_lai_xe(id) ON DELETE SET NULL,
    nguon VARCHAR(30) DEFAULT 'vehicle_camera',
    loai_canh_bao VARCHAR(50) NOT NULL,
    muc_do VARCHAR(20) DEFAULT 'CAO',
    noi_dung TEXT,
    duong_dan_anh VARCHAR(255) NULL,
    risk_score INT DEFAULT 0,
    trang_thai VARCHAR(30) DEFAULT 'MOI'
        CHECK (trang_thai IN ('MOI', 'DA_TIEP_NHAN', 'DANG_XU_LY', 'DA_DONG', 'CANH_BAO_SAI')),
    nguoi_xu_ly_id INT NULL REFERENCES tai_khoan(id) ON DELETE SET NULL,
    ghi_chu_xu_ly TEXT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NULL,
    thoi_gian_xay_ra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    thoi_gian_xu_ly TIMESTAMP NULL
);

-- 16. THIET BI CAMERA & HEARTBEAT (ONLINE_HEALTHY / ONLINE_DEGRADED / OFFLINE)
CREATE TABLE IF NOT EXISTS thiet_bi_camera (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE NOT NULL,
    xe_id INT NULL REFERENCES xe(id) ON DELETE SET NULL,
    ten_thiet_bi VARCHAR(150),
    nguon_camera VARCHAR(255),
    fps DOUBLE PRECISION DEFAULT 0,
    camera_ok BOOLEAN DEFAULT TRUE,
    trang_thai_hoat_dong VARCHAR(50) DEFAULT 'DANG_CHAY',
    active_driver_id INT NULL REFERENCES tai_xe(id) ON DELETE SET NULL,
    active_phien_id INT NULL REFERENCES phien_lai_xe(id) ON DELETE SET NULL,
    outbox_pending INT DEFAULT 0,
    dead_letter_count INT DEFAULT 0,
    lan_cuoi_ket_noi TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- P0+ REV-03/08: CHONG TRUNG PHIEN DANG MO O TANG DB & LY DO KET THUC PHIEN
ALTER TABLE phien_lai_xe ADD COLUMN IF NOT EXISTS ly_do_ket_thuc VARCHAR(100) NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_phien_lai_xe_tai_xe_dang_mo
    ON phien_lai_xe (tai_xe_id)
    WHERE trang_thai != 'DA_KET_THUC';
