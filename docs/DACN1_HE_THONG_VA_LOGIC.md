# TÀI LIỆU RÀ SOÁT LOGIC HOẠT ĐỘNG & CHỨC NĂNG HỆ THỐNG DACN1

> **Hệ thống Quản lý Đội xe Đa chi nhánh, Điều phối Tài xế, Xác thực Khuôn mặt 128D & Giám sát An toàn bằng AI**
> Kiến trúc đa nền tảng: **Camera AI Edge (Windows/RTSP + SQLite Outbox) + Backend API & Web (Flask/Docker) + App Di động (Expo SDK 58) + Supabase (PostgreSQL 29 bảng & Storage)**.
> *Phiên bản V3.0 — Hoàn thiện trọn bộ P0 (5 hạng mục cốt lõi + 4 Sprint V3) & P1 (Checklist trước chuyến + Thống kê đa cấp).*
> *Tài liệu liên quan:* [DACN1_DAC_TA_VA_TRIEN_KHAI_V3.md](DACN1_DAC_TA_VA_TRIEN_KHAI_V3.md) | [DACN1_UI_UX_WEB_V3.md](DACN1_UI_UX_WEB_V3.md) | [DACN1_UI_UX_MOBILE_APP_V3.md](DACN1_UI_UX_MOBILE_APP_V3.md)

---

## 1. Kiến trúc tổng thể hệ thống

```mermaid
flowchart LR
    CAM["Camera AI trên xe\n(main.py - Windows/RTSP)"] -->|"1. Ghi log AI & phiên lái"| DB[("Supabase PostgreSQL\n29 bảng (16 gốc + 13 V3)")]
    CAM <-->|"Khi mất mạng / khởi động lại"| OB[("SQLite Offline Outbox\nlogs/offline_outbox.db")]
    CAM -->|"2. Upload ảnh vi phạm"| ST[("Supabase Storage\nBucket: snapshots\nPublic / Private Signed URL")]
    CAM -->|"3. Alert Event (UUID event_id)\n& Device Heartbeat 20s\n(X-Internal-Key)"| BE["Backend API & Web\n(Flask / Gunicorn / Docker)"]
    BE <-->|"ThreadedConnectionPool"| DB
    BE -->|"4. SSE Realtime\n(/api/admin/events)"| WEB["Web Admin & Tài xế\n(Browser)"]
    BE -->|"5. Expo Push API\n(Rung + Chuông)"| APP["App Điện thoại Expo\n(Quản lý & Tài xế)"]
    APP <-->|"JWT REST API\n(Quét CCCD, Face 128D, AI Cam)"| BE
```

### 4 thành phần cốt lõi
1. **Luồng Camera AI Edge (`main.py`)**: Chạy trên máy tính Windows hoặc thiết bị biên gắn cabin xe, hỗ trợ **Webcam USB (`0`, `1`)** và **Camera IP/RTSP (`rtsp://...`, `http://.../video`)** qua `CAMERA_SOURCE` trong `.env`. Tích hợp **SQLite Offline Outbox** chống mất dữ liệu khi rớt mạng và **Device Heartbeat** mỗi 20 giây.
2. **Backend API & Web Application (`backend/`)**: Viết bằng Flask, đóng gói sẵn Docker (`Dockerfile`, `docker-compose.yml`), chạy bằng Gunicorn (`1 worker, 8 threads`) để phục vụ song song Web, App Expo, SSE Realtime và vòng đời cảnh báo.
3. **Ứng dụng Di động (`mobile/`)**: Viết bằng Expo React Native (**SDK 58**), hỗ trợ Expo Go và build `.apk` / `.aab` qua `eas.json`.
4. **Cơ sở dữ liệu & Lưu trữ Cloud (Supabase)**:
   * **PostgreSQL**: **29 bảng** chuẩn hóa (16 bảng gốc + 13 bảng V3.0 qua `database/migrations/v3_001..v3_005.sql`) có khóa ngoại `ON DELETE RESTRICT`, ràng buộc `CHECK`/`UNIQUE`, partial unique index và 2 trigger khóa bất biến dữ liệu AI & giải trình khiếu nại.
   * **Supabase Storage**: Bucket `snapshots` hỗ trợ cả chế độ công khai lẫn **Private Bucket Signed URL** có thời hạn (`SUPABASE_BUCKET_PRIVATE=true`).

---

## 2. Logic hoạt động chi tiết của Luồng Camera AI (`main.py`)

```mermaid
flowchart TD
    S["Khởi động main.py\nMở Camera + Tải trước điểm dừng nghỉ"] --> K{"Xe đang chạy?\n(Phím 1: Dừng / 2: Chạy)"}
    K -->|"Tạm dừng"| P["Hiển thị XE DUNG\nReset bộ đếm & calibration\nVẫn gửi Heartbeat PAUSED"]
    K -->|"Đang chạy"| D["MediaPipe Face Mesh\nTính EAR trái/phải & MAR"]
    D --> F{"Có khuôn mặt?"}
    F -->|"Không"| L["Đếm thời gian mất dấu phiên\n(> 30 phút tự đóng phiên)"]
    F -->|"Có"| C{"Đã hiệu chuẩn mắt\n3 giây đầu?"}
    C -->|"Chưa"| C1["EyeCalibration.update()\nTạo baseline mắt cá nhân"]
    C -->|"Rồi"| A{"Đã chốt xác thực\ntài xế?"}
    A -->|"Chưa"| A1["Quét nhận diện 3 giây\n(Face 128D -> fallback LBPH)"]
    A1 --> A2{"Khớp >= 2 lần & đúng xe?"}
    A2 -->|"Đúng tài xế & đúng xe"| A3["Khóa tài xế hợp lệ\nMở/nối phiên lái + tự gắn lich_chay_id"]
    A2 -->|"Đúng người nhưng sai xe"| A4["Chốt SAI XE\nCảnh báo giọng nói + Ảnh + Alert UUID"]
    A2 -->|"Không khớp"| A5["Chốt NGUOI LA\nCảnh báo giọng nói + Ảnh + Alert UUID"]
    A -->|"Đã chốt"| AI["Tính Head Pose (Pitch/Yaw)\n+ SVM 3 xác suất + DrowsinessAnalyzer"]
    AI --> R["Phân loại 4 trạng thái & Fatigue 0-100%\nTINH TAO | MAT TAP TRUNG | MET MOI | BUON NGU"]
    R --> ACT["Giọng nói (Queue/Cache) + Điểm dừng nghỉ\nUpload Storage + Alert Event (Outbox fallback)\n+ Heartbeat 20s + Outbox Flush 15s"]
```

### 2.1. Hiệu chuẩn mắt cá nhân (`detection/eye_calibration.py`)
* Chỉ bắt đầu đếm **3 giây** sau khi camera nhận thấy khuôn mặt.
* Lấy trung bình `EAR` mắt trái và mắt phải làm baseline cá nhân, chuẩn hóa về mốc chuẩn `0.30` giúp **giảm báo sai cho người mắt nhỏ/híp**.
* Tự động reset khi bấm phím `1` (tạm dừng) rồi `2` (chạy lại).

### 2.2. Xác thực khuôn mặt tài xế (`face_auth/recognize_driver.py` & `embedding_service.py`)
* **Công nghệ chính**: **Face Embedding 128 chiều** (`dlib-bin` + `face_recognition_models`) so khớp bằng khoảng cách Euclidean (`threshold = 0.48`). Dữ liệu vector tải từ `du_lieu_khuon_mat` trên Supabase và tự làm mới cache mỗi **60 giây**.
* **Fallback tự động**: Nếu DB chưa có vector 128D, tự động chuyển sang bộ **LBPH** (`model/face_model.yml`).
* **Cơ chế chống chập chờn**: Quét trong `3 giây` (`AUTH_SCAN_SECONDS`), kiểm tra mỗi `0.7s`, yêu cầu khớp ít nhất `2 lần` (`AUTH_MIN_HITS`), sau đó đối chiếu phân công xe (`kiem_tra_tai_xe_duoc_phan_cong_xe`) và **khóa phiên**:
  * **Hợp lệ**: Mở/nối phiên `phien_lai_xe` (chống tạo phiên trùng & tự gắn `lich_chay_id` đang hoạt động), phát lời chào tên tài xế.
  * **Sai xe / Người lạ**: Chốt trạng thái, phát cảnh báo, chụp ảnh → upload Supabase Storage → lưu bảng `nguoi_la` → gửi sự kiện cảnh báo có UUID `event_id` (lưu `su_kien_canh_bao` + phát SSE + Expo Push).

### 2.3. Bộ đánh giá trạng thái đa yếu tố (`core/drowsiness_analyzer.py`)
Kết hợp **6 tín hiệu hành vi** + **3 xác suất từ model AI SVM** (làm mượt qua cửa sổ trượt 15 frame):

| Tín hiệu | Cơ chế xử lý | Tác dụng |
| :--- | :--- | :--- |
| **Nhắm mắt kéo dài** | `EAR < 0.20` liên tục ≥ `1.2s` và ≥ `25 frame` | Phân biệt rõ ngủ gật với chớp mắt thường (~0.1–0.3s) |
| **PERCLOS** | Tỷ lệ % mắt nhắm trong cửa sổ 120–300 frame (`> 45%`) | Phát hiện tình trạng mắt lờ đờ kéo dài |
| **Tần suất chớp mắt/phút** | Cửa sổ trượt 60 giây (`>= 26 lần/phút`) | Nhận biết mỏi mắt (`CHOP MAT DAY`) |
| **Tần suất ngáp** | `MAR > 0.65` liên tục ≥ `0.8s` (tránh nhầm khi nói chuyện), đếm trong 3 phút (`>= 2 lần`) | Nhận biết ngáp liên tục (`NGAP LIEN TUC`) |
| **Tư thế đầu (`Pitch` & `Yaw`)** | `Pitch > 15°` ≥ `1.0s` → Gục đầu; `\|Yaw\| > 25°` ≥ `2.5s` → Nhìn lệch đường | Phát hiện `GUC DAU` và `MAT TAP TRUNG` |
| **Bối cảnh & AI SVM** | Khung giờ nguy hiểm (0h–5h, 13h–15h), lái liên tục > 2h, xác suất 3 lớp SVM | Tích lũy vào **Fatigue Score (0–100%)** có hồi phục dần (hysteresis) |

* **4 trạng thái đầu ra kèm lý do cụ thể**:
  1. `TINH TAO` (0–29%, xanh lá)
  2. `MAT TAP TRUNG` (`|Yaw| > 25°` ≥ 2.5s, vàng)
  3. `MET MOI` (30–64% hoặc ngáp liên tục, cam)
  4. `BUON NGU` (65–100% hoặc nhắm mắt lâu / gục đầu / PERCLOS cao, đỏ)

### 2.4. Chống lag Camera, Offline Outbox bền vững & Giám sát Thiết bị (P0-3 & P0-4)
* **Hàng đợi ghi DB & Upload nền (`_db_queue`)**: Ghi log, upload ảnh, gửi cảnh báo và gửi heartbeat đều chạy ở luồng nền, không bao giờ làm tụt FPS camera.
* **SQLite Offline Outbox (`services/offline_outbox.py` → `logs/offline_outbox.db`)**:
  * Khi mất mạng hoặc Backend tạm gián đoạn, mọi `alert_event` và `detection_log` thất bại đều được lưu bền vững xuống SQLite trên đĩa theo **Event Contract chuẩn** (`event_id`, `payload_version`, `device_id`, `occurred_at` UTC ISO).
  * Phân biệt rõ **lỗi tạm thời (`RETRY` — 5xx/mạng)** với **lỗi dữ liệu vĩnh viễn (`DEAD_LETTER` — 400/422 hoặc vượt quá `max_retries=20`)**, tránh vòng lặp retry vô hạn.
  * Định kỳ mỗi **15 giây**, `main.py` tự động gọi `offline_outbox.flush()` để đồng bộ lại tối đa 25 sự kiện/đợt; chỉ xóa khỏi SQLite khi server xác nhận thành công.
  * Phía Backend sử dụng `ON CONFLICT (event_id) DO NOTHING` để đảm bảo **idempotency** (không ghi trùng và không bắn trùng Push/SSE khi gửi lại).
* **Device Heartbeat & 3 mức sức khỏe thiết bị (`POST /api/internal/device-heartbeat`)**:
  * Mỗi **20 giây**, `main.py` gửi nhịp tim thiết bị gồm `device_id`, `xe_id`, `nguon_camera`, `fps`, `trang_thai_hoat_dong`, `active_driver_id`, `active_phien_id`, `outbox_pending`, `dead_letter_count`.
  * Admin Dashboard tự động phân loại 3 mức: **🟢 `ONLINE_HEALTHY`** (< 60s, FPS ≥ 8, không tồn Outbox), **🟡 `ONLINE_DEGRADED`** (FPS < 8, lỗi camera hoặc còn Outbox/Dead-letter), và **🔴 `OFFLINE`** (> 60s mất tín hiệu).
* **Giọng nói thông minh (`alerts/voice_alert.py` & `smart_voice.py`)**: 1 worker thread đọc `queue.Queue`, cache `.mp3` trong `assets/audio/` (`pygame.mixer`), fallback offline `pyttsx3` khi mất mạng.
* **Tìm điểm dừng nghỉ bất đồng bộ (`services/location_service.py`)**: Gọi OpenStreetMap Nominatim nền và cache theo tọa độ (TTL 10 phút).

---

## 3. Logic Nghiệp vụ, Vòng đời Cảnh báo & Bảo mật (P0-1, P0-2, P0-5)

### 3.1. Chống trùng lịch chạy & trùng phiên lái xe (P0-1)
* **Chống trùng lịch (`kiem_tra_trung_lich_chay`)**: Được kiểm tra bắt buộc trong cả `tao_lich_chay()` và `cap_nhat_lich_chay()`. Chặn tuyệt đối việc phân công hai ca chạy giao thời gian (`gio_bat_dau < existing_end AND gio_ket_thuc > existing_start`) cho cùng một **tài xế** hoặc cùng một **xe** ở trạng thái `sap_chay` / `dang_chay`.
* **Chống trùng phiên lái, tự gắn lịch & ghi lý do đóng phiên (`tao_phien_lai_xe`, `dong_phien_lai_xe`)**:
  * Bảo vệ kép ở cả tầng ứng dụng lẫn tầng DB bằng partial unique index `uq_phien_lai_xe_tai_xe_dang_mo` (mỗi tài xế chỉ có tối đa 1 phiên đang mở).
  * Tự động tìm lịch chạy `dang_chay` / `sap_chay` phù hợp thời điểm hiện tại để gắn `lich_chay_id` vào phiên lái xe.
  * Khi đóng phiên tự động do mất mặt > 30 phút, ghi rõ `ly_do_ket_thuc = 'AUTO_MAT_DAU_30P'` phân biệt với kết thúc thủ công (`MANUAL_STOP`).

### 3.2. Vòng đời Cảnh báo — Alert Lifecycle & Optimistic Locking (P0-2 + P0+)
Mọi sự kiện cảnh báo (`BUON_NGU`, `NGUOI_LA`, `SAI_XE`, `MAT_TAP_TRUNG`, ...) từ `main.py` hoặc App dự phòng đều được lưu vào bảng `su_kien_canh_bao` với vòng đời khép kín và kiểm tra chuyển trạng thái hợp lệ (`core/ops_rules.py`):

```
MOI  ──►  DA_TIEP_NHAN  ──►  DANG_XU_LY  ──►  DA_DONG
                                          └──► CANH_BAO_SAI
```

* Không cho phép ghi đè cảnh báo đã đóng (`DA_DONG` / `CANH_BAO_SAI`); hỗ trợ `expected_status` (Optimistic Locking — trả `409 Conflict` nếu cảnh báo vừa được quản lý khác xử lý).
* Lưu đầy đủ `event_id` (UUID chống trùng), `payload_version`, `device_id`, `occurred_at` (UTC), `tai_xe_id`, `xe_id`, `phien_id`, `risk_score`, `duong_dan_anh`, `nguon`, `nguoi_xu_ly_id`, `ghi_chu_xu_ly`.
* Mỗi thao tác đổi trạng thái đều được ghi vào `lich_su_thao_tac` (audit log).

### 3.3. Bảo mật, Xác thực & Signed URL (P0-5)
* **Mã hóa mật khẩu (`bcrypt`)**: Mọi tài khoản mới lưu hash `$2b$...`; tài khoản cũ tự động nâng cấp sang `bcrypt` khi đăng nhập.
* **Thu hồi JWT / Session ngay khi khóa tài khoản (`backend/middleware/auth_guard.py`)**:
  * Mọi request xác thực qua JWT Bearer (hạn 12 giờ) hoặc Flask Session đều đi qua `_is_account_active(user_id)` kiểm tra `tai_khoan.trang_thai == 'hoat_dong'` (cache TTL 20 giây + hàm `invalidate_account_cache(user_id)` để thu hồi tức thì).
  * Nếu tài khoản bị chuyển sang `'khoa'`, hệ thống lập tức xóa session và trả về `401` / chuyển hướng `/login`.
* **Phân quyền vai trò chặt chẽ**:
  * `@require_role("quan_ly")`: Bảo vệ toàn bộ trang/API quản trị (`/admin/*`, `/api/admin/*`) **và khóa chặt quyền tạo tài khoản tài xế, quét CCCD, đăng ký / đăng ký lại khuôn mặt 128D**.
  * `@require_role("tai_xe", "quan_ly")` + `resolve_driver_id()`: **Chống IDOR** — tài xế chỉ truy cập được đúng `tai_xe_id` của mình.
  * `X-Internal-Key`: Bảo vệ các endpoint nội bộ `/api/internal/alert-event` và `/api/internal/device-heartbeat`.
* **Che dữ liệu nhạy cảm & kiểm soát quyền xem ảnh**:
  * Danh sách tài xế trả thêm `so_gplx_masked` (`079******345`) để che bớt CCCD/GPLX khi hiển thị.
  * Endpoint `/api/snapshots/<filename>` kiểm tra quyền sở hữu (`quan_ly` hoặc đúng `tai_xe_id` sở hữu ảnh, nếu không trả `403`).
* **Supabase Private Bucket Signed URL (`services/storage_service.py`)**:
  * Khi bật `SUPABASE_BUCKET_PRIVATE=true` trong `.env`, `resolve_snapshot_url()` tự động gọi `create_signed_url(filename, expires_in=3600)` để cấp đường dẫn có chữ ký tạm thời thay vì public URL cố định.

---

## 4. Logic Thu thập Dữ liệu & Huấn luyện AI (`ai/`)

* **Thu thập dữ liệu v2 (`ai/collect_dataset.py`)**:
  * Ghi **5 đặc trưng chuẩn hóa** + `SessionId`: `EAR (sau EyeCalibration)`, `MAR`, `Pitch`, `Yaw`, `PERCLOS`, `Label` (`0`, `1`, `2`), `SessionId` vào `dataset/drowsiness_dataset_v2.csv`.
  * Hỗ trợ ghi tự động liên tục (~6–7 mẫu/giây) bằng 1 phím (`0/A`, `1/Y`, `2/D`, `SPACE` tạm dừng, `R` hiệu chuẩn lại & tạo `SessionId` mới khi đổi người/phiên), tự lọc khung hình không có mặt.
* **Huấn luyện chống Data Leakage (`ai/train_model.py`) & Dự đoán (`detection/predictor.py`)**:
  * Tự lọc mẫu nhiễu (`Label 0` dính chớp mắt `EAR < 0.16`, `Label 2` mở mắt to `EAR > 0.28`).
  * Dùng **`GroupShuffleSplit` + `GroupKFold` theo `SessionId`** (khi có ≥ 2 phiên) kết hợp `Pipeline(StandardScaler, SVC(class_weight="balanced"))` để ngăn rò rỉ frame cùng phiên giữa train/test; in đầy đủ Precision/Recall/F1 từng lớp & Confusion Matrix.
  * Tự động chuyển từ 2 → 5 đặc trưng khi `drowsiness_dataset_v2.csv` đạt ≥ 150 mẫu (≥ 30 mẫu/nhãn) qua `model/model_meta.json`.

---

## 5. Tổng hợp đầy đủ Chức năng hiện có theo Nền tảng

### A. Trên Web Quản lý (`quan_ly`)
| Trang / API | Chức năng chi tiết |
| :--- | :--- |
| `/admin/dashboard` + `/api/admin/dashboard` | Thống kê 5 chỉ số đội xe, bảng xe đang hoạt động live, cảnh báo AI mới & báo cáo sự cố mới (auto-refresh 5s) |
| **Trạng thái Thiết bị Camera** (`/api/admin/devices`) | Hiển thị từng camera biên theo xe: 🟢 Online (`FPS`) / 🔴 Offline (số giây mất kết nối), tài xế đang khóa, số sự kiện tồn trong Outbox |
| **Quản lý Vòng đời Cảnh báo** (`/api/admin/alerts`, `PUT /api/admin/alerts/<id>`) | Lọc theo trạng thái (`MOI`, `DA_TIEP_NHAN`, `DANG_XU_LY`, `DA_DONG`, `CANH_BAO_SAI`), xem ảnh vi phạm và bấm 1 chạm `Tiếp nhận` / `Đã đóng` / `Báo sai` |
| **Realtime SSE** (`/api/admin/events`) | Bật thông báo toast góc dưới phải kèm ảnh chụp ngay khi có cảnh báo mới mà không cần tải lại trang |
| **Thư viện ảnh vi phạm** (`/api/admin/snapshots`) | Lưới xem lại ảnh vi phạm buồn ngủ & người lạ đồng bộ từ Supabase Storage (hỗ trợ cả Public & Signed URL) |
| `/admin/drivers` + `/api/admin/drivers` | Quản lý hồ sơ tài xế, tạo tài khoản (hash `bcrypt`), cập nhật trạng thái & gửi thông báo |
| `/admin/vehicles` + `/api/admin/vehicles` | Quản lý danh sách xe, thêm/sửa xe, phân công tài xế mặc định |
| `/admin/scheduler` + `/api/admin/schedules` | Tạo/cập nhật/hủy lịch chạy (**tự động chặn trùng ca tài xế và trùng ca xe**), gửi thông báo cho tài xế |
| `/admin/reports` + `/api/admin/reports` | Xem và xử lý báo cáo sự cố từ tài xế, gửi phản hồi |
| `/admin/analytics` + `/api/admin/export-pdf` | Biểu đồ thống kê theo ngày, top tài xế nguy cơ cao, **xuất báo cáo PDF tiếng Việt có dấu** |
| `/privacy` | Trang Chính sách Quyền riêng tư công khai |

### B. Trên Web Tài xế (`tai_xe`)
| Trang / API | Chức năng chi tiết |
| :--- | :--- |
| `/driver/dashboard` | Thông tin cabin, xe phụ trách và lịch chạy hiện tại |
| `/driver/schedules` | Danh sách lịch chạy được phân công |
| `/driver/violations` | Lịch sử vi phạm / cảnh báo AI |
| `/driver/history` | Lịch sử các phiên lái xe |
| `/driver/notifications` + `/driver/read-note/<id>` | Thông báo từ quản lý & đánh dấu đã đọc |
| `/driver/reports` | Gửi báo cáo sự cố & xem phản hồi |
| `/driver/profile` | Cập nhật SĐT, địa chỉ, xem trạng thái đã đăng ký khuôn mặt (chỉ quản lý được đăng ký/đổi khuôn mặt) |

### C. Trên App Điện thoại Expo (`mobile/` — SDK 58)
* **Màn hình Đăng nhập (`LoginScreen`)**: Đăng nhập chung Quản lý & Tài xế, có cấu hình **Server URL** linh hoạt.
* **Giao diện Quản lý (`quan_ly`) — 5 tab**:
  1. **Cabin**: 5 thẻ số liệu đội xe (kéo để làm mới).
  2. **Tài xế (`AdminDriversScreen`)**:
     * Danh sách tài xế + nút **Đăng ký / Đăng ký lại khuôn mặt 128D** (chụp 3 mẫu lưu Supabase, chỉ quản lý có quyền).
     * Nút **+ Thêm / Quét CCCD**: Mở camera **quét mã QR Căn cước công dân gắn chip Việt Nam**, tự điền Họ tên có dấu, Địa chỉ, Số CCCD, gợi ý tên đăng nhập → tạo tài khoản → chuyển thẳng sang bước đăng ký khuôn mặt.
  3. **Lịch**: Xem lịch chạy đội xe.
  4. **Sự cố**: Xem & bấm **Đánh dấu Đã xử lý** báo cáo sự cố.
  5. **Cá nhân**: Thông tin tài khoản, máy chủ kết nối, Đăng xuất.
  * **Expo Push Notifications**: Tự động rung + chuông khi có cảnh báo `BUON_NGU`, `NGUOI_LA`, `SAI_XE`.
* **Giao diện Tài xế (`tai_xe`) — 7 tab**:
  1. **Cabin**: Xe phụ trách, tuyến hiện tại, trạng thái khuôn mặt 128D.
  2. **AI Cam (`MonitorScreen` — Giám sát dự phòng)**: Gửi frame về `/api/ai/analyze-frame`, hiển thị Fatigue 0–100%, 4 trạng thái, **rung mạnh + phát giọng nói tiếng Việt (`expo-speech`)**, đồng bộ log/ảnh/Push về Quản lý.
  3. **Lịch**, **Vi phạm**, **T.Báo**, **Sự cố**, **Cá nhân**.

---

## 6. Cơ sở dữ liệu Supabase (29 bảng + Storage)

File định nghĩa gốc: `database/schema_postgres.sql` | 5 Migration V3: `database/migrations/v3_001..v3_005.sql` | Script chạy tự động: `scripts/run_v3_migrations.py`.

### 6.1. 16 bảng nền tảng gốc
1. `tai_khoan`: Tài khoản **6 vai trò RBAC** (`admin_he_thong`, `quan_tri_cong_ty`, `quan_ly`, `dieu_phoi_vien`, `giam_sat`, `tai_xe`), mật khẩu `bcrypt`, trạng thái `hoat_dong` / `khoa`, kèm phạm vi `cong_ty_id`, `chi_nhanh_id`, `doi_xe_id`.
2. `tai_xe`: Hồ sơ tài xế (họ tên, SĐT, GPLX unique, địa chỉ, trạng thái, `doi_xe_id`).
3. `xe`: Thông tin xe (biển số unique, model, loại xe, trạng thái, `tai_xe_mac_dinh_id`, `doi_xe_id`).
4. `lich_chay`: Lịch phân công chuyến đi (xác nhận bắt buộc `CHO_XAC_NHAN` → `DA_XAC_NHAN`, từ chối có lý do, chống trùng ca trong transaction có `pg_advisory_xact_lock`).
5. `phien_lai_xe`: Phiên lái kỹ thuật (chống trùng phiên mở, gắn `lich_chay_id` và `chuyen_thuc_te_id`, `AUTO_MAT_DAU_30P` không đóng chuyến thực tế).
6. `nhat_ky_phat_hien`: Log AI (`ear`, `mar`, `risk_score`, `trang_thai`, `thoi_gian`).
7. `anh_canh_bao`: URL Supabase Storage ảnh chụp cảnh báo buồn ngủ.
8. `nguoi_la`: Ảnh chụp & ghi chú khi phát hiện người lạ hoặc tài xế sai xe.
9. `ghi_chu`: Thông báo quản lý & hệ thống gửi cho tài xế (`da_doc`, `thoi_gian`).
10. `bao_cao_su_co`: Báo cáo sự cố từ tài xế (bao gồm sự cố tự động sinh khi Checklist `KHONG_DAT`) & phản hồi từ quản lý.
11. `lich_su_thao_tac`: Audit log bất biến kèm `du_lieu_truoc (JSONB)`, `du_lieu_sau (JSONB)` và `ly_do`.
12. `du_lieu_khuon_mat`: Vector khuôn mặt **128 chiều** dạng JSON.
13. `anh_khuon_mat`: Bản sao nhị phân ảnh khuôn mặt đăng ký (`BYTEA`).
14. `thiet_bi_thong_bao`: `expo_push_token` theo tài khoản & vai trò (hỗ trợ push đích danh tới từng tài khoản).
15. `su_kien_canh_bao`: Quản lý vòng đời sự kiện AI (`event_id` UUID `UNIQUE`, có trigger `trg_su_kien_canh_bao_immutable` khóa bất biến dữ liệu AI gốc).
16. `thiet_bi_camera`: Theo dõi trạng thái thiết bị camera biên (`device_id` `UNIQUE`, `xe_id`, `doi_xe_id`, `fps`, `outbox_pending`, `dead_letter_count`, `lan_cuoi_ket_noi`).

### 6.2. 13 bảng mở rộng V3.0 (P0 + P1)
17. `cong_ty`: Thông tin công ty & `cau_hinh_jsonb` (5 tham số nghiệp vụ cấu hình động).
18. `chi_nhanh`: Danh sách chi nhánh trực thuộc công ty.
19. `doi_xe`: Danh sách đội xe trực thuộc chi nhánh (trục lọc Data Scope).
20. `lich_su_chuyen_doi_xe`: Nhật ký điều chuyển tài xế/phương tiện giữa các đội xe (bắt buộc lý do).
21. `yeu_cau_thay_doi_lich`: Yêu cầu đổi giờ/đổi xe/hủy lịch của tài xế chờ quản lý duyệt (không sửa lịch gốc khi `CHO_DUYET`).
22. `lich_su_phan_cong`: Lịch sử thay đổi tài xế, xe, khung giờ trên từng lịch chạy.
23. `chuyen_thuc_te`: Vòng đời chuyến đi thực tế độc lập với phiên kỹ thuật (2 partial unique index chặn 2 chuyến `DANG_CHAY` cùng lúc; hỗ trợ kết thúc ngoại lệ có lý do).
24. `lich_su_ket_noi_camera`: Nhật ký các khoảng `ONLINE`/`UNSTABLE`/`OFFLINE`/`RECOVERING` kèm `thoi_luong_giay` gắn theo chuyến (Camera Offline Watcher cảnh báo 2 phía, không tự kết thúc chuyến).
25. `vi_pham`: Vi phạm chính thức do Quản lý xác minh có bằng chứng & lý do (`UNIQUE(su_kien_canh_bao_id)`).
26. `khieu_nai_vi_pham`: Khiếu nại & giải trình của tài xế (có trigger `trg_khieu_nai_immutable` khóa bất biến `noi_dung_giai_trinh` gốc; chấp nhận khiếu nại tự hủy vi phạm).
27. `lich_su_khieu_nai`: Nhật ký từng bước chuyển trạng thái xử lý khiếu nại.
28. `checklist_truoc_chuyen`: Kết quả kiểm tra an toàn xe trước chuyến (`DAT`/`KHONG_DAT`, tự liên kết `bao_cao_su_co_id` nếu không đạt).
29. `checklist_truoc_chuyen_chi_tiet`: Chi tiết 6 hạng mục kiểm tra an toàn bắt buộc.
* **Supabase Storage**: Bucket `snapshots` (hỗ trợ Public URL & Private Signed URL).

---

## 7. Kiểm thử tự động & Đóng gói triển khai

* **Bộ test tự động (`tests/`, chạy bằng `pytest -v`) — 38 tests**:
  * `tests/test_detection.py` (9 tests): EAR, MAR, EyeCalibration, 4 trạng thái `DrowsinessAnalyzer`, tần suất ngáp, hồi phục Fatigue Score, xác suất 3 lớp SVM.
  * `tests/test_auth_and_security.py` (4 tests): `bcrypt` hash/verify, auto-upgrade mật khẩu cũ, so khớp Face Embedding 128D, chặn `401` API quản trị & internal alert.
  * `tests/test_storage.py` (3 tests): Chuẩn hóa URL ảnh, fallback local và upload Supabase Storage.
  * `tests/test_expo_push.py` (2 tests): Định dạng Expo Push Token và gửi batch thông báo.
  * `tests/test_p0_upgrades.py` (5 tests): `OfflineOutbox` bền vững/retry/chống trùng `event_id`/`DEAD_LETTER`, Event Contract, Private Bucket Signed URL, `auth_guard` thu hồi tài khoản khóa, state machine cảnh báo + Device Health 3 mức + che CCCD/GPLX.
  * `tests/test_v3_sprint1_org_rbac.py` (3 tests): RBAC 6 vai trò, Data Scope isolation (Chi nhánh A vs B), phân tách quyền Điều phối viên / Giám sát / Quản trị công ty / Tài xế.
  * `tests/test_v3_sprint2_schedules.py` (4 tests): Chống trùng lịch nửa mở `[start, end)`, bắt buộc xác nhận lại khi sửa lịch đã xác nhận, validate lý do từ chối/hủy/đổi lịch, phân quyền duyệt đổi lịch.
  * `tests/test_v3_sprint3_trips_camera.py` (3 tests): Chuyến thực tế, kết thúc ngoại lệ bắt buộc lý do, Camera Offline cảnh báo 2 phía không kết thúc chuyến.
  * `tests/test_v3_sprint4_violations_appeals.py` (3 tests): Xác minh sự kiện AI → Vi phạm (chống trùng `409`), Khiếu nại vi phạm & Mobile Backup ghi `su_kien_canh_bao`.
  * `tests/test_v3_p1_checklist_analytics.py` (2 tests): Checklist kiểm tra xe trước chuyến (`DAT`/`KHONG_DAT`) & API Cảnh báo ưu tiên + Thống kê đa cấp V3.
* **Đóng gói Docker**: `Dockerfile`, `docker-compose.yml`, `requirements-web.txt`, `.dockerignore`.
* **Build App Android/iOS**: `mobile/eas.json` (`preview` xuất `.apk`, `production` xuất `.aab`).

---

## 8. Bảng truy vết triển khai P0 & P0+ (Code ↔ Schema ↔ Test)

| Hạng mục | Thành phần / File triển khai | Bảng / Index DB | Unit Test xác minh |
| :--- | :--- | :--- | :--- |
| **P0-1: Chống trùng lịch & phiên** | `database/mysql_service.py` (`kiem_tra_trung_lich_chay`, `tao_lich_chay`, `cap_nhat_lich_chay`, `tao_phien_lai_xe`) | `lich_chay`, `phien_lai_xe`, `uq_phien_lai_xe_tai_xe_dang_mo` | Đã áp dụng ràng buộc cả tầng ứng dụng & PostgreSQL |
| **P0-2: Alert Lifecycle + Optimistic Lock** | `core/ops_rules.py`, `database/mysql_service.py`, `backend/routes/realtime_routes.py`, `backend/routes/admin_routes.py`, `backend/templates/admin/dashboard.html` | `su_kien_canh_bao` (`event_id` UNIQUE), `lich_su_thao_tac` | `test_alert_state_machine_and_device_health_and_masking` |
| **P0-3: Device Heartbeat 3 mức Health** | `core/ops_rules.py` (`phan_loai_suc_khoe_thiet_bi`), `services/realtime_client.py`, `main.py`, `backend/routes/realtime_routes.py`, `backend/templates/admin/dashboard.html` | `thiet_bi_camera` (`device_id` UNIQUE, `fps`, `outbox_pending`, `dead_letter_count`) | `test_alert_state_machine_and_device_health_and_masking` |
| **P0-4: SQLite Offline Outbox + Dead-letter** | `services/offline_outbox.py`, `services/realtime_client.py` (Event Contract `payload_version`, `device_id`, `occurred_at`), `main.py` | SQLite cục bộ `logs/offline_outbox.db` (`PENDING` / `DEAD_LETTER`) | `test_offline_outbox_persists_retries_deduplicates_and_dead_letters`, `test_realtime_client_event_contract_and_status_codes` |
| **P0-5: Thu hồi JWT/Session + Private Signed URL + Bảo vệ CCCD/Ảnh** | `backend/middleware/auth_guard.py`, `services/storage_service.py`, `backend/routes/admin_routes.py` (`mask_sensitive_id`), `backend/routes/realtime_routes.py` (`/api/snapshots/<filename>`) | `tai_khoan`, `anh_canh_bao`, `su_kien_canh_bao`, Supabase Bucket `snapshots` | `test_storage_service_private_bucket_signed_url`, `test_auth_guard_revokes_locked_account_and_invalidates_cache` |
| **P0+ AI: Chống Data Leakage & Lý do đóng phiên** | `ai/collect_dataset.py` (`SessionId`), `ai/train_model.py` (`GroupShuffleSplit` + `GroupKFold` + `Pipeline`), `database/mysql_service.py` (`ly_do_ket_thuc`), `main.py` | `phien_lai_xe.ly_do_ket_thuc`, `model/model_meta.json` | `tests/test_detection.py` (9 tests) |

---

## 9. Hướng dẫn khởi chạy nhanh

1. **Cơ sở dữ liệu Supabase (29 bảng):**
   ```powershell
   .\venv\Scripts\python.exe scripts\run_v3_migrations.py
   ```
   *(Hoặc chạy `database/schema_postgres.sql` rồi lần lượt `database/migrations/v3_001..v3_005.sql` trong Supabase SQL Editor.)*
2. **Backend Web & API:** Nhấp đúp **[run_web.bat](../run_web.bat)** (tự bind `0.0.0.0:5000` cho cả Web máy tính lẫn điện thoại trong cùng Wi-Fi).
   - Web Quản trị: `http://127.0.0.1:5000/admin/dashboard` và Trung tâm Vận hành V3: `http://127.0.0.1:5000/admin/operations`.
3. **Camera AI Edge (Windows / RTSP):**
   ```powershell
   .\venv\Scripts\python.exe main.py
   ```
   Phím điều khiển: `1` (Tạm dừng), `2` (Chạy lại & hiệu chuẩn/xác thực lại), `Q` (Thoát).
4. **App Điện thoại Expo (SDK 58):** Nhấp đúp **[run_expo.bat](../run_expo.bat)** rồi quét mã QR bằng **Expo Go (SDK 58)** trên điện thoại cùng Wi-Fi và nhập `http://<IP_LAN>:5000` trong Server URL.
5. **Chạy kiểm thử tự động (38 tests):**
   ```powershell
   .\venv\Scripts\python.exe -m pytest -v
   ```
