# TÀI LIỆU TỔNG HỢP ĐẶC TẢ & TRIỂN KHAI DACN1 V3.0

> **Hệ thống quản lý đội xe đa chi nhánh, điều phối tài xế và giám sát an toàn bằng AI**
> **Phiên bản:** 3.0 (Hoàn thiện trọn bộ P0 + Web/Mobile V3 + P1 — Đã chạy migration & smoke test trực tiếp trên Supabase: **29 bảng**)
> **Kiểm thử tự động:** `pytest -v` — **38/38 tests passed**
> **Bộ tài liệu `docs/`:** [DACN1_HE_THONG_VA_LOGIC.md](DACN1_HE_THONG_VA_LOGIC.md) | [DACN1_UI_UX_WEB_V3.md](DACN1_UI_UX_WEB_V3.md) | [DACN1_UI_UX_MOBILE_APP_V3.md](DACN1_UI_UX_MOBILE_APP_V3.md)

---

## 1. Bảy quyết định nghiệp vụ cốt lõi V3.0 đã triển khai

1. **Tổ chức đa chi nhánh & Data Scope:** `cong_ty` → `chi_nhanh` → `doi_xe`, điều chuyển tài xế/xe lưu `lich_su_chuyen_doi_xe` trong transaction.
2. **RBAC 6 vai trò tách bạch:** `admin_he_thong`, `quan_tri_cong_ty`, `quan_ly`, `dieu_phoi_vien`, `giam_sat`, `tai_xe` (Điều phối viên phân công lịch được nhưng bị chặn `403` khi xác minh vi phạm, duyệt đổi lịch, xử lý khiếu nại, hủy lịch hoặc kết thúc chuyến ngoại lệ).
3. **Xác nhận lịch bắt buộc & Yêu cầu đổi lịch/xe:** Tạo/sửa lịch trong PostgreSQL transaction có `pg_advisory_xact_lock` chống trùng ca đồng thời (`409`); sửa lịch sau khi xác nhận tự reset về `CHO_XAC_NHAN` + lưu `lich_su_phan_cong`; luồng `yeu_cau_thay_doi_lich` không sửa lịch gốc khi đang `CHO_DUYET`.
4. **Chuyến thực tế & Kết thúc ngoại lệ:** Tách `chuyen_thuc_te` khỏi `phien_lai_xe` (2 partial unique index chặn mở 2 chuyến `DANG_CHAY` cùng lúc); `AUTO_MAT_DAU_30P` chỉ đóng phiên kỹ thuật; Quản lý kết thúc ngoại lệ bắt buộc nhập lý do + ghi Audit Log trước/sau.
5. **Tách Sự kiện AI bất biến ↔ Vi phạm đã xác minh:** Trigger PostgreSQL khóa bất biến dữ liệu AI gốc trên `su_kien_canh_bao`; Quản lý xác minh có bằng chứng & lý do mới tạo đúng 1 bản ghi `vi_pham` (`UNIQUE(su_kien_canh_bao_id)`). App dự phòng (`ai_monitor_routes.py`) cũng ghi `su_kien_canh_bao` thay vì bỏ qua.
6. **Phân hệ Khiếu nại vi phạm bắt buộc:** Bảng `khieu_nai_vi_pham` (trigger khóa bất biến `noi_dung_giai_trinh` gốc) & `lich_su_khieu_nai`; khi Quản lý `ACCEPTED` tự động chuyển `vi_pham` sang `DA_HUY_DO_KHIEU_NAI` trong cùng transaction.
7. **Camera mất kết nối giữa chuyến độc lập:** Bảng `lich_su_ket_noi_camera` + Camera Offline Watcher trên Backend (quá hạn Heartbeat > 60s) tự ghi mốc `OFFLINE`, gửi cảnh báo **2 phía** (Tài xế + Quản lý/Giám sát), **không tự động kết thúc chuyến**, và tự tính `thoi_luong_giay` khi kết nối lại.

---

## 2. Năm file SQL Migration V3 (Chạy theo thứ tự trên Supabase)

Có thể chạy trực tiếp bằng script `.\venv\Scripts\python.exe scripts\run_v3_migrations.py` hoặc dán lần lượt vào **Supabase SQL Editor**:

| Thứ tự | File Migration | Nội dung chính |
| :---: | :--- | :--- |
| 1 | `database/migrations/v3_001_org_rbac_core.sql` | `cong_ty`, `chi_nhanh`, `doi_xe`, `lich_su_chuyen_doi_xe`, 6 vai trò RBAC, `lich_su_thao_tac` JSONB + backfill dữ liệu cũ |
| 2 | `database/migrations/v3_002_schedule_and_requests.sql` | Mở rộng `lich_chay`, `yeu_cau_thay_doi_lich`, `lich_su_phan_cong`, ràng buộc `gio_ket_thuc > gio_bat_dau` |
| 3 | `database/migrations/v3_003_trips_and_camera_logs.sql` | `chuyen_thuc_te` (+ 2 partial unique index), `phien_lai_xe.chuyen_thuc_te_id`, `lich_su_ket_noi_camera` |
| 4 | `database/migrations/v3_004_violations_and_appeals.sql` | Trigger bất biến `su_kien_canh_bao`, `vi_pham`, `khieu_nai_vi_pham` (+ trigger bất biến), `lich_su_khieu_nai` |
| 5 | `database/migrations/v3_005_p1_checklist_and_analytics.sql` | `checklist_truoc_chuyen`, `checklist_truoc_chuyen_chi_tiet` (P1) |

---

## 3. Bảng truy vết triển khai V3.0 (Service ↔ API ↔ UI ↔ Unit Tests)

| Phân hệ | Service Layer | Backend Routes | Giao diện Web & Mobile | Unit Tests |
| :--- | :--- | :--- | :--- | :--- |
| **Tổ chức, RBAC & Audit** | `database/org_service.py`, `core/ops_rules.py` | `backend/routes/org_routes.py`, `auth_routes.py`, `auth_guard.py` | `admin/operations.html` (Tab 5), `admin/dashboard.html` | `tests/test_v3_sprint1_org_rbac.py` |
| **Lịch chạy & Đổi lịch/xe** | `database/schedule_service.py` | `backend/routes/scheduler_routes.py`, `admin_routes.py` | `admin/operations.html` (Tab 4), `driver/schedules.html`, `mobile/.../SchedulesScreen.js` | `tests/test_v3_sprint2_schedules.py` |
| **Chuyến thực tế & Camera Offline** | `database/trip_camera_service.py` | `backend/routes/trip_routes.py`, `realtime_routes.py`, `expo_push_service.py` | `admin/operations.html` (Tab 3), `driver/schedules.html`, `mobile/.../DashboardScreen.js` | `tests/test_v3_sprint3_trips_camera.py` |
| **Xác minh Vi phạm & Khiếu nại** | `database/violation_appeal_service.py` | `backend/routes/violation_routes.py`, `ai_monitor_routes.py` | `admin/operations.html` (Tab 1 & 2), `driver/violations.html`, `mobile/.../ViolationsScreen.js` | `tests/test_v3_sprint4_violations_appeals.py` |
| **P1: Checklist & Thống kê đa cấp** | `database/p1_service.py` | `backend/routes/p1_routes.py` | `driver/schedules.html` (Checklist xe), `/api/admin/priority-alerts`, `/api/admin/analytics/v3` | `tests/test_v3_p1_checklist_analytics.py` |

---

## 4. Hướng dẫn áp dụng & kiểm thử trực tiếp

```powershell
# 1. Chay 5 file migration V3 len Supabase PostgreSQL (tu dong kiem tra ket qua)
.\venv\Scripts\python.exe scripts\run_v3_migrations.py

# 2. Chay toan bo 38 unit tests
.\venv\Scripts\python.exe -m pytest -v

# 3. Khoi chay Backend Web & API (hoac nhap dup run_web.bat)
.\run_web.bat

# 4. Khoi chay Mobile App Expo SDK 58 (hoac nhap dup run_expo.bat)
.\run_expo.bat
```
