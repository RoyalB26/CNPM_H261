t

# Smart E-Mobility Hub · Hệ Thống Điều Phối Phương Tiện Điện Thông Minh ĐHQG-HCM

> **Đồ án môn học:** Công nghệ Phần mềm (CNPM)
> **Trường Đại học Bách khoa – ĐHQG-HCM**

---

## 📌 Mục Lục

1. [Giới Thiệu Dự Án](#1-giới-thiệu-dự-án)
2. [Hướng Dẫn Cài Đặt &amp; Khởi Chạy](#hướng-dẫn-cài-đặt--khởi-chạy)

---

## 1. Giới Thiệu Dự Án

Dự án **Smart E-Mobility Hub** giải quyết bài toán giao thông xanh nội bộ trong khuôn viên Khu đô thị Đại học Quốc gia TP.HCM (ĐHQG-HCM), kết nối các trường đại học thành viên, ký túc xá, thư viện trung tâm và ga tuyến Metro số 1 Bến Thành – Suối Tiên.

Hệ thống quản lý một mạng lưới các trạm **Hub đa năng**

Dự án bao gồm đầy đủ **3 đối tượng tác nhân (Actors)** theo đặc tả phần mềm:

* **End-User (Sinh viên, Cán bộ, Giảng viên)**: Sử dụng Mobile Web App.
* **Operator (Nhân viên vận hành)**: Sử dụng Web Dashboard toàn màn hình tại trung tâm chỉ huy.
* **Field Staff & Guard (Nhân viên bảo trì)**: Gồm nhân viên điều chuyển xe, kỹ thuật viên bảo trì và bảo vệ bãi đỗ.

## Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Yêu cầu môi trường

* **Hệ điều hành**: Windows 10/11, macOS hoặc Linux.
* **Python**: Phiên bản 3.10 trở lên.
* **Trình duyệt**: Google Chrome, Microsoft Edge, Mozilla Firefox hoặc Safari.

### 2. Cài đặt các gói thư viện Python cần thiết

Mở terminal tại thư mục gốc dự án và cài đặt:

```powershell
pip install -r requirements.txt
```

### 3. Khởi chạy Unified Mock Backend Server

Khởi chạy Gateway duy nhất phục vụ toàn bộ hệ thống:

```powershell
python BE/run_all.py
```

Server sẽ chạy tại địa chỉ: **`http://127.0.0.1:8000`**

### 4. Mở giao diện Frontend

Có thể chọn một trong hai cách:

* **Cách 1 (Đơn giản nhất)**: Mở trực tiếp file [`FE/index.html`](FE/index.html) bằng trình duyệt web.
* **Cách 2 (Khuyên dùng - chạy qua Live Server hoặc HTTP server)**:
  ```powershell
  python -m http.server 3000 --directory FE
  ```

  Sau đó mở trình duyệt truy cập: **`http://localhost:3000`**

---

**© 2026 Smart E-Mobility Hub · Môn học Công nghệ Phần mềm · ĐHQG-HCM**
