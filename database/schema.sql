CREATE DATABASE IF NOT EXISTS he_thong_tai_xe
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE he_thong_tai_xe;

-- 1. TAI KHOAN
CREATE TABLE IF NOT EXISTS tai_khoan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ten_dang_nhap VARCHAR(100) UNIQUE NOT NULL,
    mat_khau VARCHAR(255) NOT NULL,
    vai_tro ENUM('quan_ly', 'tai_xe') NOT NULL,
    trang_thai ENUM('hoat_dong', 'khoa') DEFAULT 'hoat_dong',
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. TAI XE
CREATE TABLE IF NOT EXISTS tai_xe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_khoan_id INT,
    ho_ten VARCHAR(255) NOT NULL,
    so_dien_thoai VARCHAR(20),
    so_gplx VARCHAR(100) UNIQUE,
    dia_chi TEXT,
    avatar VARCHAR(255),
    trang_thai ENUM('dang_lam', 'nghi', 'tam_khoa') DEFAULT 'nghi',
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_khoan_id) REFERENCES tai_khoan(id)
);

-- 3. XE
CREATE TABLE IF NOT EXISTS xe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bien_so VARCHAR(50) UNIQUE NOT NULL,
    model VARCHAR(255),
    loai_xe VARCHAR(255),
    trang_thai ENUM('hoat_dong', 'bao_tri', 'ngung') DEFAULT 'hoat_dong',
    ghi_chu TEXT,
    tai_xe_mac_dinh_id INT NULL,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_mac_dinh_id) REFERENCES tai_xe(id)
);

-- 4. LICH CHAY
CREATE TABLE IF NOT EXISTS lich_chay (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT,
    xe_id INT,
    tuyen_duong VARCHAR(255),
    gio_bat_dau DATETIME,
    gio_ket_thuc DATETIME,
    trang_thai ENUM('sap_chay', 'dang_chay', 'tam_ngung', 'hoan_thanh', 'da_huy') DEFAULT 'sap_chay',
    ghi_chu TEXT,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id),
    FOREIGN KEY (xe_id) REFERENCES xe(id)
);

-- 5. PHIEN LAI XE
CREATE TABLE IF NOT EXISTS phien_lai_xe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT,
    xe_id INT,
    lich_chay_id INT NULL,
    bat_dau DATETIME DEFAULT CURRENT_TIMESTAMP,
    ket_thuc DATETIME NULL,
    thoi_diem_mat_dau DATETIME NULL,
    tong_phut FLOAT DEFAULT 0,
    tong_lan_buon_ngu INT DEFAULT 0,
    trang_thai ENUM('DANG_LAI', 'TAM_MAT_DAU', 'DA_KET_THUC') DEFAULT 'DANG_LAI',
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id),
    FOREIGN KEY (xe_id) REFERENCES xe(id),
    FOREIGN KEY (lich_chay_id) REFERENCES lich_chay(id)
);

-- 6. NHAT KY PHAT HIEN AI
CREATE TABLE IF NOT EXISTS nhat_ky_phat_hien (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT,
    xe_id INT,
    lich_chay_id INT NULL,
    ear FLOAT,
    mar FLOAT,
    risk_score INT,
    trang_thai VARCHAR(100),
    thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id),
    FOREIGN KEY (xe_id) REFERENCES xe(id),
    FOREIGN KEY (lich_chay_id) REFERENCES lich_chay(id)
);

-- 7. ANH CANH BAO
CREATE TABLE IF NOT EXISTS anh_canh_bao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT,
    xe_id INT,
    lich_chay_id INT NULL,
    duong_dan_anh VARCHAR(255),
    thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id),
    FOREIGN KEY (xe_id) REFERENCES xe(id)
);

-- 8. NGUOI LA / TAI XE SAI XE
CREATE TABLE IF NOT EXISTS nguoi_la (
    id INT AUTO_INCREMENT PRIMARY KEY,
    xe_id INT,
    duong_dan_anh VARCHAR(255),
    ghi_chu TEXT,
    thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (xe_id) REFERENCES xe(id)
);

-- 9. GHI CHU / THONG BAO QUAN LY
CREATE TABLE IF NOT EXISTS ghi_chu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT,
    quan_ly_id INT,
    noi_dung TEXT,
    da_doc BOOLEAN DEFAULT FALSE,
    thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id),
    FOREIGN KEY (quan_ly_id) REFERENCES tai_khoan(id)
);

-- 10. BAO CAO SU CO
CREATE TABLE IF NOT EXISTS bao_cao_su_co (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT,
    xe_id INT NULL,
    lich_chay_id INT NULL,
    tieu_de VARCHAR(255) NOT NULL,
    loai_su_co VARCHAR(100) DEFAULT 'KHAC',
    noi_dung TEXT,
    hinh_anh VARCHAR(255) NULL,
    trang_thai VARCHAR(50) DEFAULT 'CHO_XU_LY',
    phan_hoi_quan_ly TEXT NULL,
    thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id),
    FOREIGN KEY (xe_id) REFERENCES xe(id),
    FOREIGN KEY (lich_chay_id) REFERENCES lich_chay(id)
);

-- 11. AUDIT LOG
CREATE TABLE IF NOT EXISTS lich_su_thao_tac (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nguoi_thuc_hien_id INT,
    vai_tro VARCHAR(100),
    hanh_dong VARCHAR(255),
    bang_du_lieu VARCHAR(255),
    doi_tuong_id INT NULL,
    ghi_chu TEXT,
    thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 12. DU LIEU VECTOR KHUON MAT
CREATE TABLE IF NOT EXISTS du_lieu_khuon_mat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT NOT NULL,
    vector_khuon_mat LONGTEXT NOT NULL,
    do_tin_cay FLOAT DEFAULT 1.0,
    trang_thai ENUM('hoat_dong', 'vo_hieu') DEFAULT 'hoat_dong',
    mo_ta VARCHAR(255) NULL,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id)
);

-- 13. ANH KHUON MAT DANG KY
CREATE TABLE IF NOT EXISTS anh_khuon_mat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tai_xe_id INT NOT NULL,
    du_lieu_anh LONGBLOB NOT NULL,
    ngay_tao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tai_xe_id) REFERENCES tai_xe(id)
);
