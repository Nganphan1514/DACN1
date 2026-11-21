-- ============================================================
-- DACN1 - SUPABASE (POSTGRESQL) SEED DATA
-- Chay sau khi da chay database/schema_postgres.sql
-- ============================================================

TRUNCATE TABLE
    anh_khuon_mat,
    du_lieu_khuon_mat,
    bao_cao_su_co,
    nguoi_la,
    lich_su_thao_tac,
    ghi_chu,
    anh_canh_bao,
    nhat_ky_phat_hien,
    phien_lai_xe,
    lich_chay,
    xe,
    tai_xe,
    tai_khoan
RESTART IDENTITY CASCADE;

-- TAI KHOAN
INSERT INTO tai_khoan (ten_dang_nhap, mat_khau, vai_tro, trang_thai)
VALUES
('admin', '123456', 'quan_ly', 'hoat_dong'),
('manager01', '123456', 'quan_ly', 'hoat_dong'),
('taixe01', '123456', 'tai_xe', 'hoat_dong'),
('taixe02', '123456', 'tai_xe', 'hoat_dong'),
('taixe03', '123456', 'tai_xe', 'hoat_dong'),
('taixe04', '123456', 'tai_xe', 'hoat_dong'),
('taixe05', '123456', 'tai_xe', 'hoat_dong');

-- TAI XE
INSERT INTO tai_xe (tai_khoan_id, ho_ten, so_dien_thoai, so_gplx, dia_chi, avatar, trang_thai)
VALUES
(3, 'Nguyễn Văn An', '0905111111', 'GPLX001', 'Đà Nẵng', 'avatars/an.jpg', 'dang_lam'),
(4, 'Trần Văn Bình', '0905222222', 'GPLX002', 'Quảng Nam', 'avatars/binh.jpg', 'dang_lam'),
(5, 'Lê Quốc Huy', '0905333333', 'GPLX003', 'Huế', 'avatars/huy.jpg', 'nghi'),
(6, 'Phạm Minh Khang', '0905444444', 'GPLX004', 'Đà Nẵng', 'avatars/khang.jpg', 'dang_lam'),
(7, 'Hoàng Gia Bảo', '0905555555', 'GPLX005', 'Quảng Ngãi', 'avatars/bao.jpg', 'nghi');

-- XE
INSERT INTO xe (bien_so, model, loai_xe, trang_thai, ghi_chu, tai_xe_mac_dinh_id)
VALUES
('43A-12345', 'Hyundai Universe', 'Xe khách', 'hoat_dong', 'Xe tuyến Bắc Nam', 1),
('43B-56789', 'Ford Transit', 'Xe trung chuyển', 'hoat_dong', 'Xe nội thành', 2),
('92A-88888', 'Thaco Town', 'Xe buýt', 'bao_tri', 'Đang thay lốp', 3),
('92B-99999', 'Mercedes Sprinter', 'Xe khách', 'hoat_dong', 'Xe VIP', 4),
('75A-45678', 'Toyota Hiace', 'Xe dịch vụ', 'ngung', 'Tạm ngừng hoạt động', 5);

-- LICH CHAY
INSERT INTO lich_chay (tai_xe_id, xe_id, tuyen_duong, gio_bat_dau, gio_ket_thuc, trang_thai, ghi_chu)
VALUES
(1, 1, 'Đà Nẵng → Huế', NOW() - INTERVAL '2 hours', NOW() + INTERVAL '2 hours', 'dang_chay', 'Chuyến sáng'),
(2, 2, 'Đà Nẵng → Hội An', NOW() + INTERVAL '1 hour', NOW() + INTERVAL '3 hours', 'sap_chay', 'Ca chiều'),
(3, 3, 'Huế → Đà Nẵng', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '1 hour', 'hoan_thanh', 'Đã hoàn tất'),
(4, 4, 'Đà Nẵng → Quảng Ngãi', NOW() - INTERVAL '3 hours', NOW() + INTERVAL '4 hours', 'dang_chay', 'Chuyến dài'),
(5, 5, 'Tam Kỳ → Đà Nẵng', NOW() + INTERVAL '4 hours', NOW() + INTERVAL '8 hours', 'sap_chay', 'Ca tối');

-- PHIEN LAI XE
INSERT INTO phien_lai_xe (tai_xe_id, xe_id, lich_chay_id, bat_dau, ket_thuc, tong_phut, tong_lan_buon_ngu, trang_thai)
VALUES
(1, 1, 1, NOW() - INTERVAL '2 hours', NULL, 125.5, 2, 'DANG_LAI'),
(2, 2, 2, NOW() - INTERVAL '1 hour', NULL, 65, 1, 'DANG_LAI'),
(3, 3, 3, NOW() - INTERVAL '6 hours', NOW() - INTERVAL '1 hour', 300, 0, 'DA_KET_THUC');

-- NHAT KY PHAT HIEN
INSERT INTO nhat_ky_phat_hien (tai_xe_id, xe_id, lich_chay_id, ear, mar, risk_score, trang_thai, thoi_gian)
VALUES
(1, 1, 1, 0.24, 0.11, 1, 'TINH TAO', NOW()),
(1, 1, 1, 0.21, 0.15, 3, 'MET MOI', NOW() - INTERVAL '30 minutes'),
(1, 1, 1, 0.18, 0.32, 5, 'BUON NGU', NOW() - INTERVAL '10 minutes'),
(2, 2, 2, 0.23, 0.10, 2, 'TINH TAO', NOW()),
(2, 2, 2, 0.20, 0.18, 4, 'MET MOI', NOW() - INTERVAL '25 minutes'),
(4, 4, 4, 0.19, 0.31, 6, 'BUON NGU', NOW() - INTERVAL '5 minutes');

-- ANH CANH BAO
INSERT INTO anh_canh_bao (tai_xe_id, xe_id, lich_chay_id, duong_dan_anh, thoi_gian)
VALUES
(1, 1, 1, 'snapshots/vi_pham_001.jpg', NOW()),
(1, 1, 1, 'snapshots/vi_pham_002.jpg', NOW() - INTERVAL '10 minutes'),
(4, 4, 4, 'snapshots/vi_pham_003.jpg', NOW() - INTERVAL '5 minutes');

-- GHI CHU
INSERT INTO ghi_chu (tai_xe_id, quan_ly_id, noi_dung, da_doc)
VALUES
(1, 1, 'Kiểm tra sức khỏe trước chuyến đi.', TRUE),
(2, 1, 'Không chạy quá tốc độ quy định.', FALSE),
(3, 2, 'Nộp báo cáo cuối ngày.', TRUE),
(4, 1, 'Cần nghỉ ngơi đầy đủ.', FALSE),
(5, 2, 'Đã hoàn thành KPI tuần.', TRUE);

-- AUDIT LOG
INSERT INTO lich_su_thao_tac (nguoi_thuc_hien_id, vai_tro, hanh_dong, bang_du_lieu, doi_tuong_id, ghi_chu)
VALUES
(1, 'quan_ly', 'THEM', 'tai_xe', 1, 'Thêm tài xế Nguyễn Văn An'),
(1, 'quan_ly', 'SUA', 'xe', 2, 'Cập nhật xe Ford Transit'),
(2, 'quan_ly', 'XOA', 'lich_chay', 3, 'Hủy lịch chạy lỗi'),
(1, 'quan_ly', 'CAP_NHAT', 'ghi_chu', 4, 'Cập nhật ghi chú tài xế');
