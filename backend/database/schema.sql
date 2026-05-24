CREATE DATABASE IF NOT EXISTS he_thong_tai_xe;

USE he_thong_tai_xe;

-- ==========================
-- TAI KHOAN
-- ==========================
CREATE TABLE tai_khoan (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    ten_dang_nhap
    VARCHAR(100)
    UNIQUE
    NOT NULL,

    mat_khau
    VARCHAR(255)
    NOT NULL,

    vai_tro
    ENUM(
        'quan_ly',
        'tai_xe'
    )
    NOT NULL,

    trang_thai
    ENUM(
        'hoat_dong',
        'khoa'
    )
    DEFAULT 'hoat_dong',

    ngay_tao
    DATETIME
    DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- TAI XE
-- ==========================
CREATE TABLE tai_xe (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    tai_khoan_id INT,

    ho_ten
    VARCHAR(255)
    NOT NULL,

    so_dien_thoai
    VARCHAR(20),

    so_gplx
    VARCHAR(100),

    dia_chi
    TEXT,

    avatar
    VARCHAR(255),

    trang_thai
    ENUM(
        'dang_lam',
        'nghi',
        'tam_khoa'
    )
    DEFAULT 'nghi',

    ngay_tao
    DATETIME
    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (
        tai_khoan_id
    )
    REFERENCES tai_khoan(id)
);

-- ==========================
-- XE
-- ==========================
CREATE TABLE xe (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    bien_so
    VARCHAR(50)
    NOT NULL,

    model
    VARCHAR(255),

    loai_xe
    VARCHAR(255),

    trang_thai
    ENUM(
        'hoat_dong',
        'bao_tri',
        'ngung'
    )
    DEFAULT 'hoat_dong',

    ghi_chu
    TEXT,

    ngay_tao
    DATETIME
    DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- LICH CHAY
-- ==========================
CREATE TABLE lich_chay (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    tai_xe_id INT,

    xe_id INT,

    tuyen_duong
    VARCHAR(255),

    gio_bat_dau
    DATETIME,

    gio_ket_thuc
    DATETIME,

    trang_thai
    ENUM(
        'sap_chay',
        'dang_chay',
        'hoan_thanh',
        'huy'
    )
    DEFAULT 'sap_chay',

    ghi_chu
    TEXT,

    ngay_tao
    DATETIME
    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (
        tai_xe_id
    )
    REFERENCES tai_xe(id),

    FOREIGN KEY (
        xe_id
    )
    REFERENCES xe(id)
);

-- ==========================
-- NHAT KY PHAT HIEN AI
-- ==========================
CREATE TABLE nhat_ky_phat_hien (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    tai_xe_id INT,

    xe_id INT,

    lich_chay_id INT,

    ear FLOAT,

    mar FLOAT,

    risk_score INT,

    trang_thai
    VARCHAR(100),

    thoi_gian
    DATETIME
    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (
        tai_xe_id
    )
    REFERENCES tai_xe(id),

    FOREIGN KEY (
        xe_id
    )
    REFERENCES xe(id),

    FOREIGN KEY (
        lich_chay_id
    )
    REFERENCES lich_chay(id)
);

-- ==========================
-- ANH CANH BAO
-- ==========================
CREATE TABLE anh_canh_bao (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    tai_xe_id INT,

    xe_id INT,

    lich_chay_id INT,

    duong_dan_anh
    VARCHAR(255),

    thoi_gian
    DATETIME
    DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- GHI CHU QUAN LY
-- ==========================
CREATE TABLE ghi_chu (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    tai_xe_id INT,

    quan_ly_id INT,

    noi_dung
    TEXT,

    da_doc
    BOOLEAN
    DEFAULT FALSE,

    thoi_gian
    DATETIME
    DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- AUDIT LOG
-- ==========================
CREATE TABLE lich_su_thao_tac (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    nguoi_thuc_hien_id INT,

    vai_tro
    VARCHAR(100),

    hanh_dong
    VARCHAR(255),

    bang_du_lieu
    VARCHAR(255),

    doi_tuong_id INT,

    ghi_chu
    TEXT,

    thoi_gian
    DATETIME
    DEFAULT CURRENT_TIMESTAMP
);

-- ==========================
-- PHIEN DANG NHAP HIEN TAI
-- ==========================
CREATE TABLE phien_dang_nhap (

    id INT AUTO_INCREMENT
    PRIMARY KEY,

    tai_xe_id INT,

    xe_id INT,

    thoi_gian_dang_nhap DATETIME
    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (
        tai_xe_id
    )
    REFERENCES tai_xe(id),

    FOREIGN KEY (
        xe_id
    )
    REFERENCES xe(id)
);