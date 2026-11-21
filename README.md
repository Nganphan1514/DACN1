# DACN1 — Hệ thống Giám sát Tài xế & Cảnh báo Buồn ngủ bằng AI

Hệ thống kết hợp **AI Computer Vision thời gian thực** (MediaPipe, SVM, dlib Face Embedding 128D) và **Web Dashboard quản lý đội xe** (Flask + MySQL + Server-Sent Events).

---

## 1. Tính năng chính
* **Giám sát buồn ngủ thời gian thực (`main.py`)**:
  * Tính **EAR**, **MAR**, **PERCLOS**, **Head Pose (Pitch/Yaw)** và dự đoán trạng thái bằng **SVM**.
  * **Hiệu chuẩn mắt cá nhân 3 giây đầu** (`EyeCalibration`) giúp giảm báo sai cho người mắt nhỏ/híp.
  * **Cảnh báo giọng nói tiếng Việt** qua hàng đợi tuần tự (`pygame.mixer` + cache MP3 cục bộ + fallback offline `pyttsx3`).
  * **Gợi ý điểm dừng nghỉ gần nhất** bất đồng bộ (cache theo tọa độ, không làm giật camera).
* **Xác thực khuôn mặt tài xế**:
  * Nhận diện bằng **Face Embedding 128 chiều** lưu trong MySQL (tự động fallback sang LBPH nếu chưa có dữ liệu vector).
  * Chặn người lạ / tài xế lái sai xe được phân công, chụp ảnh snapshot và đẩy cảnh báo realtime lên Web.
  * Hỗ trợ **đăng ký khuôn mặt trực tiếp trên trình duyệt Web** (`/driver/register-face`).
* **Web Dashboard (Admin & Tài xế)**:
  * Đăng nhập bảo mật (`bcrypt` + JWT + Flask Session), phân quyền vai trò (`quan_ly` / `tai_xe`) và chống IDOR.
  * **Admin**: Dashboard realtime (SSE toast + ảnh vi phạm), quản lý tài xế, quản lý xe, điều phối lịch chạy, xử lý báo cáo sự cố, thống kê biểu đồ và **xuất báo cáo PDF tiếng Việt có dấu**.
  * **Tài xế**: Xem cabin/lịch chạy, thông báo từ quản lý, lịch sử vi phạm, gửi báo cáo sự cố, cập nhật hồ sơ & đăng ký khuôn mặt.

---

## 2. Cấu trúc thư mục chính
```text
DACN1/
├── main.py                     # Luồng camera AI giám sát realtime
├── backend/
│   ├── app.py                  # Flask server (threaded=True cho SSE)
│   ├── middleware/auth_guard.py# Bảo vệ JWT/Session & chống IDOR
│   ├── routes/                 # auth, admin, driver, dashboard, face, report, scheduler, realtime
│   └── templates/              # Giao diện HTML (auth/, admin/, driver/)
├── config/                     # app_config.py (.env), ai_config.py, vehicle_config.py, logger.py
├── core/                       # DrowsinessAnalyzer, HUD renderer
├── detection/                  # MediaPipe, EAR/MAR, Head Pose, EyeCalibration, SVM Predictor
├── face_auth/                  # Face Embedding 128D & LBPH fallback
├── alerts/                     # Voice queue/cache, smart voice cooldown, snapshot
├── services/                   # Location async cache, realtime alert client
├── database/
│   ├── schema.sql              # Cấu trúc 13 bảng MySQL
│   ├── seed_data.sql           # Dữ liệu mẫu
│   └── mysql_service.py        # MySQL Connection Pool & truy vấn nghiệp vụ
├── scripts/                    # Script test thủ công (camera, voice, db)
└── tests/                      # Bộ kiểm thử tự động (pytest)
```

---

## 3. Hướng dẫn nhanh cho thành viên nhóm (sau khi `git clone` / `git pull`)

> **Lưu ý quan trọng để chạy không lỗi trên Windows:**
> 1. **Cài đúng Python 3.11 (64-bit)** (khi cài bắt buộc tick **`Add python.exe to PATH`**; tránh Python 3.13 vì `mediapipe` chưa hỗ trợ).
> 2. **Xin file `.env` từ trưởng nhóm** (chứa `DATABASE_URL` Supabase) và đặt vào thư mục gốc `DACN1/.env` (file `.env` không đẩy lên Git để bảo mật).
> 3. **Không cần cài XAMPP** — cả nhóm dùng chung cơ sở dữ liệu online trên **Supabase**.
> 4. Nếu dùng **Git Bash** bị lỗi đường dẫn khi gọi `pip`/`python`, hãy gọi trực tiếp `./venv/Scripts/python.exe ...`.

### Bước 1: Tạo môi trường ảo & cài thư viện
```bash
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
```
*(Đã chuyển `dlib` sang `dlib-bin` nên cài trực tiếp trên Windows không cần CMake / Visual Studio).*

### Bước 2: Cấu hình biến môi trường (`.env`) với Supabase
1. Tạo project miễn phí trên [Supabase](https://supabase.com/).
2. Vào **Project Settings → Database → Connection string → URI (Session Pooler / Transaction Pooler)** để copy chuỗi `DATABASE_URL`.
3. Sao chép `.env.example` thành `.env` và dán `DATABASE_URL` vào:
```powershell
Copy-Item .env.example .env
```

### Bước 3: Khởi tạo cơ sở dữ liệu trên Supabase
Mở **Supabase → SQL Editor** và chạy:
1. Toàn bộ nội dung file `database/schema_postgres.sql` (tạo đủ 13 bảng PostgreSQL).
2. Chọn **1 trong 2 cách** nạp dữ liệu:
   * **Cách A (Nạp dữ liệu mẫu mới)**: Chạy tiếp `database/seed_data_postgres.sql` trong SQL Editor.
   * **Cách B (Chuyển dữ liệu hiện có từ MySQL XAMPP lên Supabase)**: Bật MySQL trong XAMPP, điền `MYSQL_*` trong `.env` rồi chạy:
     ```powershell
     python scripts/migrate_mysql_to_supabase.py
     ```

### Bước 4: Chạy Web Server (chọn 1 trong 2 cách)

* **Cách 1 — Chạy bằng Docker (khuyên dùng, tương thích mọi máy & sẵn sàng cho App Expo)**:
  ```bash
  docker compose up -d --build
  ```
  * Xem log: `docker compose logs -f`
  * Dừng server: `docker compose down`

* **Cách 2 — Chạy trực tiếp bằng Python `venv`**:
  ```powershell
  python -m backend.app
  ```

Truy cập: `http://127.0.0.1:5000/login`
* Tài khoản quản lý mẫu: `admin` / `123456`
* Tài khoản tài xế mẫu: `taixe01` / `123456`

### Bước 5: Chạy luồng AI Camera (và thu thập/train thêm dữ liệu)
Mở terminal mới tại thư mục gốc dự án:
```bash
# Chạy giám sát tài xế 4 trạng thái (Tỉnh táo / Mất tập trung / Mệt mỏi / Buồn ngủ)
./venv/Scripts/python.exe -u main.py

# (Tùy chọn) Thu thập thêm dữ liệu 5 đặc trưng (EAR, MAR, Pitch, Yaw, PERCLOS)
./venv/Scripts/python.exe -u ai/collect_dataset.py

# (Tùy chọn) Train lại model SVM sau khi thu thập thêm dữ liệu
./venv/Scripts/python.exe ai/train_model.py
```
* Phím `1`: Chuyển chế độ **Xe tạm dừng** (tạm ngừng nhận diện & cảnh báo).
* Phím `2`: Chuyển chế độ **Xe chạy lại** (hiệu chuẩn mắt & xác thực lại tài xế).
* Phím `q`: Thoát chương trình.

### Bước 6: Chạy App điện thoại Expo (`mobile/`)
Yêu cầu cài **Node.js LTS** và app **Expo Go** trên điện thoại (cùng Wi-Fi với máy tính):
```bash
cd mobile
npm install
npx expo start
```
Xem chi tiết tại [mobile/README.md](mobile/README.md).

---

## 4. Chạy kiểm thử tự động
```bash
./venv/Scripts/python.exe -m pytest -v
```
