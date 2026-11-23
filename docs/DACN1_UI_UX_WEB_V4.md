# ĐẶC TẢ THIẾT KẾ UI/UX — ỨNG DỤNG WEB (ADMIN & TÀI XẾ) — DACN1 V4.0 (REDESIGN)

> **Định hướng thiết kế:** Modern Fleet Command Center (Desktop Admin) & Cabin-Ready Web App (Mobile-first Driver)
> **Mã nguồn đã triển khai:**
> - Design System & Shared Primitives: `backend/static/css/design-system.css`, `backend/static/js/ui-kit.js`
> - Web Quản trị V4: `backend/templates/admin/operations.html`, `backend/templates/admin/dashboard.html`
> - Web Tài xế V4: `backend/templates/driver/schedules.html`, `backend/templates/driver/violations.html`
> **Phiên bản:** V4.0 — Đã hoàn thiện Redesign đồng bộ nghiệp vụ V3.0 + Hardening V3.1

---

## 1. Các cải tiến cốt lõi đã triển khai ở Web V4.0
1. **Zero Native Browser Dialogs:** Loại bỏ 100% `alert()`, `confirm()`, `prompt()` bằng bộ thư viện dùng chung `backend/static/js/ui-kit.js` (`UI.openDrawer`, `UI.confirmAction` có chip lý do gợi ý, `UI.openLightbox`, `UI.toast`, `UI.skeletonRows`, `UI.hasPerm`).
2. **Collapsible Sidebar + Top Command Bar (`/admin/operations`):** Nhóm menu 3 cụm (`Giám sát`, `Vận hành`, `Quản trị`) ẩn/hiện động theo `permissions`, hiển thị badge việc cần xử lý & trạng thái `● SSE Live`.
3. **Bố cục Master–Detail Triage Inbox:** Tab Thẩm định AI → Vi phạm chia đôi màn hình (40% Hàng đợi trái / 60% Khung thẩm định phải) có ảnh bằng chứng bấm mở Lightbox Zoom, thanh Risk, chip lý do mẫu.
4. **Audit Log Diff JSON Drawer:** Cho phép xem so sánh trực quan `du_lieu_truoc` vs `du_lieu_sau` ngay trong ngăn trượt bên phải.
5. **Đồng bộ Web Tài xế V4.0 với Mobile App V4.0:** Bottom Nav 4 mục (`Cabin`, `Lịch trình`, `An toàn`, `Cá nhân`), Mini Stepper 3 bước, Drawer Checklist 6 hạng mục, Lightbox Zoom bằng chứng & Timeline 3 mốc cho Khiếu nại.
