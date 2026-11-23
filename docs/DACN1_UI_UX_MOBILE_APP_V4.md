# ĐẶC TẢ THIẾT KẾ UI/UX — ỨNG DỤNG DI ĐỘNG (EXPO) — DACN1 V4.0 (REDESIGN)

> **Định hướng thiết kế:** Automotive Cabin HMI (Human-Machine Interface) & Safety-First Mobile UX
> **Nền tảng:** React Native / Expo SDK 58+ (Android & iOS)
> **Mã nguồn đã triển khai:** `mobile/App.js`, `mobile/src/theme/tokens.js`, `mobile/src/components/*` (`SlideToConfirm.js`, `BottomSheet.js`, `ToastBanner.js`, `SkeletonCard.js`), `mobile/src/screens/*`
> **Phiên bản:** V4.0 — Đã hoàn thiện Redesign đồng bộ nghiệp vụ V3.0 + Bản vá V3.1

---

## 1. Các thay đổi cốt lõi đã áp dụng ở V4.0
1. **Rút gọn Bottom Tab xuống 4 mục công thái học:**
   - **Tài xế:** `Cabin` | `Lịch trình` | `An toàn` | `Cá nhân` (Thông báo & Báo sự cố nhanh đặt ở Header Cabin, AI Cam Dự phòng mở full-screen trực tiếp từ thẻ Camera Cabin).
   - **Quản trị (5 vai trò RBAC):** `Điều hành` | `Đội ngũ` | `Lịch & Sự cố` | `Cá nhân`.
2. **Slide-to-Confirm & Draggable Bottom Sheet:**
   - Bắt đầu chuyến & Kết thúc chuyến dùng `SlideToConfirm` (cao `56dp`, chống bấm nhầm khi xe rung).
   - Từ chối lịch (có chip lý do nhanh), Đổi lịch/xe, Checklist 6 hạng mục, Gửi khiếu nại, Cấu hình Server URL + Ping, Xác nhận đăng xuất đều dùng `BottomSheet` và `ToastBanner`.
3. **Checklist 6 hạng mục trước chuyến (FIX-03) + Mini Stepper 3 bước:** `① Xác nhận → ② Checklist → ③ Khởi hành`.
4. **Phân quyền động theo `permissions` (FIX-01):** `AuthContext.hasPermission()` kiểm soát hiển thị nút Quét CCCD, Đăng ký Face 128D và Xử lý sự cố trên Mobile.
5. **Layered Dark Mode (`#090D16` → `#111827` → `#1A2234`) + `tabular-nums` + `SkeletonCard` + Lightbox Zoom ảnh bằng chứng.**
