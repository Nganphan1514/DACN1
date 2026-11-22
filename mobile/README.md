# DACN1 Mobile App (Expo React Native)

Ứng dụng di động dành cho **Tài xế** và **Quản lý đội xe**, kết nối trực tiếp với Backend Docker/Flask qua JWT REST API và cơ sở dữ liệu chung **Supabase**.

## Tính năng
* **Đăng nhập JWT** (tự lưu phiên, cho phép đổi địa chỉ IP Backend ngay trên màn hình đăng nhập).
* **Tổng quan**:
  * Tài xế: Xem xe phụ trách, tuyến hiện tại, trạng thái đăng ký khuôn mặt 128D.
  * Quản lý: Xem số liệu đội xe, xe đang chạy, cảnh báo hôm nay, sự cố chờ xử lý.
* **Lịch chạy**: Xem danh sách lịch phân công (kéo xuống để làm mới).
* **Báo cáo sự cố**: Tài xế gửi báo cáo sự cố; Quản lý xác nhận `Đã xử lý`.
* **Đăng ký khuôn mặt 128D**: Chụp liên tiếp 3 mẫu bằng camera trước điện thoại và lưu thẳng vector 128D lên Supabase.

## Cách chạy trên điện thoại thật (Expo Go)
1. Cài **Node.js LTS** (nếu chưa có) trên máy tính và cài app **Expo Go** trên điện thoại Android/iOS.
2. Đảm bảo điện thoại và máy tính dùng **chung Wi-Fi**.
3. Xem IP LAN của máy tính Windows (chạy `ipconfig` → dòng `IPv4 Address`, ví dụ `192.168.1.15`).
4. Chạy Backend Docker (`docker compose up -d --build`) hoặc Flask (`FLASK_HOST=0.0.0.0`).
5. Mở terminal trong thư mục `mobile/`:
   ```bash
   cd mobile
   npm install
   npx expo start
   ```
6. Mở **Expo Go** trên điện thoại quét mã QR → bấm **"Cấu hình địa chỉ máy chủ (IP LAN)"** nhập `http://<IP_MAY_TINH>:5000` → đăng nhập `taixe01` / `123456` hoặc `admin` / `123456`.

## Build file `.apk` (cài trực tiếp Android) hoặc `.aab` (up CH Play)
Cài EAS CLI và đăng nhập tài khoản Expo (miễn phí tại https://expo.dev):
```bash
cd mobile
npx eas-cli login

# Build file .apk cài thử trực tiếp lên điện thoại Android (miễn phí)
npx eas-cli build -p android --profile preview

# Build file .aab để phát hành lên Google Play Store (CH Play)
npx eas-cli build -p android --profile production
```
