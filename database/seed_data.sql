USE he_thong_tai_xe;


-- RESET DATA + RESET AUTO_INCREMENT

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE anh_khuon_mat;
TRUNCATE TABLE du_lieu_khuon_mat;
TRUNCATE TABLE bao_cao_su_co;
TRUNCATE TABLE nguoi_la;
TRUNCATE TABLE lich_su_thao_tac;
TRUNCATE TABLE ghi_chu;
TRUNCATE TABLE anh_canh_bao;
TRUNCATE TABLE nhat_ky_phat_hien;
TRUNCATE TABLE phien_lai_xe;
TRUNCATE TABLE lich_chay;
TRUNCATE TABLE xe;
TRUNCATE TABLE tai_xe;
TRUNCATE TABLE tai_khoan;

SET FOREIGN_KEY_CHECKS = 1;



-- TAI KHOAN

INSERT INTO tai_khoan
(
    ten_dang_nhap,
    mat_khau,
    vai_tro,
    trang_thai
)
VALUES
('admin', '123456', 'quan_ly', 'hoat_dong'),
('manager01', '123456', 'quan_ly', 'hoat_dong'),

('taixe01', '123456', 'tai_xe', 'hoat_dong'),
('taixe02', '123456', 'tai_xe', 'hoat_dong'),
('taixe03', '123456', 'tai_xe', 'hoat_dong'),
('taixe04', '123456', 'tai_xe', 'hoat_dong'),
('taixe05', '123456', 'tai_xe', 'hoat_dong');



-- TAI XE

INSERT INTO tai_xe
(
    tai_khoan_id,
    ho_ten,
    so_dien_thoai,
    so_gplx,
    dia_chi,
    avatar,
    trang_thai
)
VALUES
(3, 'Nguyễn Văn An', '0905111111', 'GPLX001', 'Đà Nẵng', 'avatars/an.jpg', 'dang_lam'),

(4, 'Trần Văn Bình', '0905222222', 'GPLX002', 'Quảng Nam', 'avatars/binh.jpg', 'dang_lam'),

(5, 'Lê Quốc Huy', '0905333333', 'GPLX003', 'Huế', 'avatars/huy.jpg', 'nghi'),

(6, 'Phạm Minh Khang', '0905444444', 'GPLX004', 'Đà Nẵng', 'avatars/khang.jpg', 'dang_lam'),

(7, 'Hoàng Gia Bảo', '0905555555', 'GPLX005', 'Quảng Ngãi', 'avatars/bao.jpg', 'nghi');



-- XE

INSERT INTO xe
(
    bien_so,
    model,
    loai_xe,
    trang_thai,
    ghi_chu
)
VALUES
(
    '43A-12345',
    'Hyundai Universe',
    'Xe khách',
    'hoat_dong',
    'Xe tuyến Bắc Nam'
),
(
    '43B-56789',
    'Ford Transit',
    'Xe trung chuyển',
    'hoat_dong',
    'Xe nội thành'
),
(
    '92A-88888',
    'Thaco Town',
    'Xe buýt',
    'bao_tri',
    'Đang thay lốp'
),
(
    '92B-99999',
    'Mercedes Sprinter',
    'Xe khách',
    'hoat_dong',
    'Xe VIP'
),
(
    '75A-45678',
    'Toyota Hiace',
    'Xe dịch vụ',
    'ngung',
    'Tạm ngừng hoạt động'
);



-- LICH CHAY

INSERT INTO lich_chay
(
    tai_xe_id,
    xe_id,
    tuyen_duong,
    gio_bat_dau,
    gio_ket_thuc,
    trang_thai,
    ghi_chu
)
VALUES
(
    1,
    1,
    'Đà Nẵng → Huế',
    DATE_SUB(NOW(), INTERVAL 2 HOUR),
    DATE_ADD(NOW(), INTERVAL 2 HOUR),
    'dang_chay',
    'Chuyến sáng'
),

(
    2,
    2,
    'Đà Nẵng → Hội An',
    DATE_ADD(NOW(), INTERVAL 1 HOUR),
    DATE_ADD(NOW(), INTERVAL 3 HOUR),
    'sap_chay',
    'Ca chiều'
),

(
    3,
    3,
    'Huế → Đà Nẵng',
    DATE_SUB(NOW(), INTERVAL 5 HOUR),
    DATE_SUB(NOW(), INTERVAL 1 HOUR),
    'hoan_thanh',
    'Đã hoàn tất'
),

(
    4,
    4,
    'Đà Nẵng → Quảng Ngãi',
    DATE_SUB(NOW(), INTERVAL 3 HOUR),
    DATE_ADD(NOW(), INTERVAL 4 HOUR),
    'dang_chay',
    'Chuyến dài'
),

(
    5,
    5,
    'Tam Kỳ → Đà Nẵng',
    DATE_ADD(NOW(), INTERVAL 4 HOUR),
    DATE_ADD(NOW(), INTERVAL 8 HOUR),
    'sap_chay',
    'Ca tối'
);



-- PHIEN LAI XE

INSERT INTO phien_lai_xe
(
    tai_xe_id,
    xe_id,
    lich_chay_id,
    bat_dau,
    ket_thuc,
    tong_phut,
    tong_lan_buon_ngu,
    trang_thai
)
VALUES
(
    1,
    1,
    1,
    DATE_SUB(NOW(), INTERVAL 2 HOUR),
    NULL,
    125.5,
    2,
    'DANG_LAI'
),

(
    2,
    2,
    2,
    DATE_SUB(NOW(), INTERVAL 1 HOUR),
    NULL,
    65,
    1,
    'DANG_LAI'
),

(
    3,
    3,
    3,
    DATE_SUB(NOW(), INTERVAL 6 HOUR),
    DATE_SUB(NOW(), INTERVAL 1 HOUR),
    300,
    0,
    'DA_KET_THUC'
);



-- NHAT KY PHAT HIEN

INSERT INTO nhat_ky_phat_hien
(
    tai_xe_id,
    xe_id,
    lich_chay_id,
    ear,
    mar,
    risk_score,
    trang_thai,
    thoi_gian
)
VALUES
(1,1,1,0.24,0.11,1,'TINH TAO',NOW()),
(1,1,1,0.21,0.15,3,'MET MOI',DATE_SUB(NOW(),INTERVAL 30 MINUTE)),
(1,1,1,0.18,0.32,5,'BUON NGU',DATE_SUB(NOW(),INTERVAL 10 MINUTE)),

(2,2,2,0.23,0.10,2,'TINH TAO',NOW()),
(2,2,2,0.20,0.18,4,'MET MOI',DATE_SUB(NOW(),INTERVAL 25 MINUTE)),

(4,4,4,0.19,0.31,6,'BUON NGU',DATE_SUB(NOW(),INTERVAL 5 MINUTE));



-- ANH CANH BAO

INSERT INTO anh_canh_bao
(
    tai_xe_id,
    xe_id,
    lich_chay_id,
    duong_dan_anh,
    thoi_gian
)
VALUES
(1,1,1,'snapshots/vi_pham_001.jpg',NOW()),
(1,1,1,'snapshots/vi_pham_002.jpg',DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(4,4,4,'snapshots/vi_pham_003.jpg',DATE_SUB(NOW(), INTERVAL 5 MINUTE));



-- GHI CHU

INSERT INTO ghi_chu
(
    tai_xe_id,
    quan_ly_id,
    noi_dung,
    da_doc
)
VALUES
(1,1,'Kiểm tra sức khỏe trước chuyến đi.',TRUE),
(2,1,'Không chạy quá tốc độ quy định.',FALSE),
(3,2,'Nộp báo cáo cuối ngày.',TRUE),
(4,1,'Cần nghỉ ngơi đầy đủ.',FALSE),
(5,2,'Đã hoàn thành KPI tuần.',TRUE);



-- AUDIT LOG

INSERT INTO lich_su_thao_tac
(
    nguoi_thuc_hien_id,
    vai_tro,
    hanh_dong,
    bang_du_lieu,
    doi_tuong_id,
    ghi_chu
)
VALUES
(1,'quan_ly','THEM','tai_xe',1,'Thêm tài xế Nguyễn Văn An'),
(1,'quan_ly','SUA','xe',2,'Cập nhật xe Ford Transit'),
(2,'quan_ly','XOA','lich_chay',3,'Hủy lịch chạy lỗi'),
(1,'quan_ly','CAP_NHAT','ghi_chu',4,'Cập nhật ghi chú tài xế');



-- KHUON MAT

INSERT INTO du_lieu_khuon_mat
(
    tai_xe_id,
    vector_khuon_mat,
    mo_ta
)
VALUES
(1,'[0.12,0.55,0.88,0.44]','Ảnh chân dung 1'),
(2,'[0.22,0.35,0.18,0.74]','Ảnh cabin xe'),
(3,'[0.99,0.15,0.28,0.14]','Ảnh nhận diện'),
(4,'[0.77,0.63,0.48,0.20]','Ảnh profile'),
(5,'[0.61,0.32,0.78,0.54]','Ảnh khuôn mặt');