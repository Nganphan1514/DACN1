-- ============================================================
-- DACN1 V3.0 - MIGRATION SPRINT 4
-- Tach Su kien AI (bat bien) <-> Vi pham da xac minh & Khieu nai vi pham
-- Chay truc tiep trong Supabase SQL Editor (idempotent)
-- ============================================================

-- 1. MO RONG SU_KIEN_CANH_BAO & KHOA BAT BIEN DU LIEU AI GOC (VIO-01)
ALTER TABLE su_kien_canh_bao ADD COLUMN IF NOT EXISTS chuyen_thuc_te_id INT NULL REFERENCES chuyen_thuc_te(id) ON DELETE RESTRICT;
ALTER TABLE su_kien_canh_bao ADD COLUMN IF NOT EXISTS doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT;
ALTER TABLE su_kien_canh_bao ADD COLUMN IF NOT EXISTS model_version VARCHAR(50) NULL;
ALTER TABLE su_kien_canh_bao ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION NULL;

ALTER TABLE su_kien_canh_bao DROP CONSTRAINT IF EXISTS su_kien_canh_bao_trang_thai_check;
ALTER TABLE su_kien_canh_bao
    ADD CONSTRAINT su_kien_canh_bao_trang_thai_check
    CHECK (trang_thai IN (
        -- Chuan V3.0
        'DETECTED',
        'PENDING_REVIEW',
        'UNDER_REVIEW',
        'CONFIRMED',
        'REJECTED',
        'NEED_MORE_INFO',
        -- Tuong thich nguoc P0-2
        'MOI',
        'DA_TIEP_NHAN',
        'DANG_XU_LY',
        'DA_DONG',
        'CANH_BAO_SAI'
    ));

-- Trigger chan xoa va chan sua du lieu AI goc cua su_kien_canh_bao
CREATE OR REPLACE FUNCTION fn_guard_su_kien_canh_bao_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'AUD-01: Khong duoc phep xoa vat ly su_kien_canh_bao';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF NEW.event_id IS DISTINCT FROM OLD.event_id
           OR NEW.loai_canh_bao IS DISTINCT FROM OLD.loai_canh_bao
           OR NEW.duong_dan_anh IS DISTINCT FROM OLD.duong_dan_anh
           OR NEW.risk_score IS DISTINCT FROM OLD.risk_score
           OR NEW.occurred_at IS DISTINCT FROM OLD.occurred_at THEN
            RAISE EXCEPTION 'VIO-01: Du lieu AI goc trong su_kien_canh_bao la bat bien';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_su_kien_canh_bao_immutable ON su_kien_canh_bao;
CREATE TRIGGER trg_su_kien_canh_bao_immutable
    BEFORE UPDATE OR DELETE ON su_kien_canh_bao
    FOR EACH ROW EXECUTE FUNCTION fn_guard_su_kien_canh_bao_immutable();

-- 2. BANG VI PHAM DA XAC MINH (VIO-02: 1 SU KIEN AI -> TOI DA 1 VI PHAM)
CREATE TABLE IF NOT EXISTS vi_pham (
    id SERIAL PRIMARY KEY,
    su_kien_canh_bao_id INT NOT NULL UNIQUE REFERENCES su_kien_canh_bao(id) ON DELETE RESTRICT,
    chuyen_thuc_te_id INT NULL REFERENCES chuyen_thuc_te(id) ON DELETE RESTRICT,
    doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    xe_id INT NULL REFERENCES xe(id) ON DELETE RESTRICT,
    loai_vi_pham VARCHAR(50) NOT NULL,
    duong_dan_anh VARCHAR(255) NULL,
    trang_thai VARCHAR(30) NOT NULL DEFAULT 'HIEU_LUC'
        CHECK (trang_thai IN ('HIEU_LUC', 'DANG_KHIEU_NAI', 'DA_HUY_DO_KHIEU_NAI', 'GIU_NGUYEN')),
    nguoi_xac_minh_id INT NOT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    xac_minh_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ly_do_xac_minh TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. BANG KHIEU NAI VI PHAM (APP-01, APP-02)
CREATE TABLE IF NOT EXISTS khieu_nai_vi_pham (
    id SERIAL PRIMARY KEY,
    vi_pham_id INT NOT NULL REFERENCES vi_pham(id) ON DELETE RESTRICT,
    doi_xe_id INT NULL REFERENCES doi_xe(id) ON DELETE RESTRICT,
    tai_xe_id INT NOT NULL REFERENCES tai_xe(id) ON DELETE RESTRICT,
    noi_dung_giai_trinh TEXT NOT NULL,
    minh_chung_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    trang_thai VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED'
        CHECK (trang_thai IN (
            'SUBMITTED',
            'RECEIVED',
            'UNDER_REVIEW',
            'NEED_MORE_INFO',
            'ACCEPTED',
            'REJECTED',
            'CLOSED'
        )),
    nguoi_xu_ly_id INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    ket_luan VARCHAR(30) NULL CHECK (ket_luan IN ('ACCEPTED', 'REJECTED')),
    ly_do_ket_luan TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMP NULL
);

-- Trigger chan xoa va chan sua noi_dung_giai_trinh goc cua tai xe (APP-01)
CREATE OR REPLACE FUNCTION fn_guard_khieu_nai_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'APP-01: Khong duoc phep xoa vat ly khieu_nai_vi_pham';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF NEW.noi_dung_giai_trinh IS DISTINCT FROM OLD.noi_dung_giai_trinh THEN
            RAISE EXCEPTION 'APP-01: Noi dung giai trinh goc cua tai xe la bat bien';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_khieu_nai_immutable ON khieu_nai_vi_pham;
CREATE TRIGGER trg_khieu_nai_immutable
    BEFORE UPDATE OR DELETE ON khieu_nai_vi_pham
    FOR EACH ROW EXECUTE FUNCTION fn_guard_khieu_nai_immutable();

-- 4. BANG LICH SU XU LY KHIEU NAI
CREATE TABLE IF NOT EXISTS lich_su_khieu_nai (
    id SERIAL PRIMARY KEY,
    khieu_nai_id INT NOT NULL REFERENCES khieu_nai_vi_pham(id) ON DELETE RESTRICT,
    old_status VARCHAR(30) NULL,
    new_status VARCHAR(30) NOT NULL,
    actor_id INT NULL REFERENCES tai_khoan(id) ON DELETE RESTRICT,
    ghi_chu TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. INDEX PHAM VI & TRUY VAN NHANH
CREATE INDEX IF NOT EXISTS idx_vi_pham_doi_xe_created ON vi_pham (doi_xe_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vi_pham_tai_xe ON vi_pham (tai_xe_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_khieu_nai_doi_xe_created ON khieu_nai_vi_pham (doi_xe_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_khieu_nai_vi_pham ON khieu_nai_vi_pham (vi_pham_id);
CREATE INDEX IF NOT EXISTS idx_lich_su_khieu_nai ON lich_su_khieu_nai (khieu_nai_id, created_at ASC);
