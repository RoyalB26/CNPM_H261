# Backend Service: Operator Control Center

Smart E-Mobility Hub - ĐHQG-HCM

## 1. Giới thiệu

Dịch vụ Mock Backend và Schema Pydantic phục vụ toàn bộ các chức năng của bảng điều hành mạng lưới (Operator Control Center):

- Xác thực 2 lớp (2FA - OTP) cho tài khoản quản trị/giám sát
- Giám sát thời gian thực (KPIs, Telemetry Log Feed, Bản đồ tải Hub)
- Lệnh Dừng khẩn cấp toàn hệ thống (Emergency Halt)
- Quản lý & Tạo lệnh điều phối xe (Relocation Commands)
- Quản lý & Phân công phiếu bảo trì/sự cố (Maintenance Tickets)
- Quản lý thông số kỹ thuật Hub & Tạm ngưng Hub (Deactivate)
- Hệ thống mô phỏng What-if toàn diện 3 bước:
  - **Bước 1**: Chọn nguồn dữ liệu (Trạng thái A thực tế vs Trạng thái A' giả lập thủ công qua CSV/JSON, kiểm tra tham số EX-10-01)
  - **Bước 2**: Cấu hình kịch bản (Tình huống, thời lượng, mức tăng sạc %, công suất mất, xe bổ sung)
  - **Bước 3**: Kết quả phân tích (Biểu đồ tải & lưu lượng theo thời gian, Biểu đồ công suất trạm kW, Đề xuất điều phối tự động)
  - Lưu quy tắc ứng phó dự phòng & Quản lý lịch sử mô phỏng (#SIM-108 -> #SIM-105)

## 2. Cấu trúc thư mục

```
BE/operator/
├── main.py                # Khởi tạo app, middleware và tập hợp các route
├── store.py               # Truy cập store chung và quản lý dữ liệu riêng của Operator
├── handlers/
│   ├── __init__.py        # Đánh dấu package handlers
│   ├── auth.py            # Xử lý đăng nhập và xác thực 2FA
│   ├── dashboard.py       # Xử lý KPI, telemetry, Hub live và dừng khẩn cấp
│   ├── relocation.py      # Xử lý xem và tạo lệnh điều chuyển xe
│   ├── maintenance.py     # Xử lý danh sách và phân công phiếu bảo trì
│   ├── hub_manage.py      # Xử lý cấu hình và tạm ngưng Hub
│   └── simulation.py      # Xử lý nguồn dữ liệu, mô phỏng, quy tắc và lịch sử
├── schemas/
│   ├── __init__.py        # Export các schema dùng trong Operator
│   ├── auth.py            # Model request/response đăng nhập và 2FA
│   ├── dashboard.py       # Model KPI, telemetry, Hub live và dừng khẩn cấp
│   ├── relocation.py      # Model lệnh điều chuyển xe
│   ├── maintenance.py     # Model phiếu bảo trì và phân công kỹ thuật
│   ├── hub_manage.py      # Model cấu hình và tạm ngưng Hub
│   └── simulation.py      # Model đầu vào, kết quả và lịch sử mô phỏng
└── README.md              # Giới thiệu, cách chạy và danh sách API Operator
```

## 3. Khởi chạy

```powershell
& "D:\apps\miniconda\python.exe" D:\Study\University\H261\CNPM\BTL3\BE\operator\main.py
```

Hoặc chạy gateway tập trung:

```powershell
& "D:\apps\miniconda\python.exe" D:\Study\University\H261\CNPM\BTL3\BE\run_all.py
```

## 4. Danh sách API Endpoints chính

| Phương thức     | Endpoint                                      | Chức năng                               |
| ------------------ | --------------------------------------------- | ----------------------------------------- |
| `POST`           | `/api/v1/operator/auth/login`               | Đăng nhập tài khoản điều hành     |
| `POST`           | `/api/v1/operator/auth/verify-2fa`          | Xác thực OTP 6 số                      |
| `GET`            | `/api/v1/operator/dashboard/kpis`           | Lấy 4 chỉ số KPI tổng quan            |
| `GET`            | `/api/v1/operator/dashboard/telemetry`      | Lấy nhật ký telemetry thời gian thực |
| `GET`            | `/api/v1/operator/dashboard/hubs-live`      | Lấy danh sách trạng thái tải Hub     |
| `POST`           | `/api/v1/operator/dashboard/emergency-halt` | Kích hoạt dừng khẩn cấp              |
| `GET` / `POST` | `/api/v1/operator/relocation/commands`      | Xem / Tạo lệnh điều phối xe          |
| `GET`            | `/api/v1/operator/maintenance/tickets`      | Danh sách phiếu bảo trì               |
| `POST`           | `/api/v1/operator/maintenance/assign`       | Phân công kỹ thuật viên (ERR-8812)   |
| `GET`            | `/api/v1/operator/hubs`                     | Danh sách cấu hình Hub                 |
| `PUT`            | `/api/v1/operator/hubs/{id}/config`         | Cập nhật cấu hình thông số Hub      |
| `POST`           | `/api/v1/operator/hubs/{id}/deactivate`     | Tạm ngưng trạm sạc & khóa Hub        |
| `GET`            | `/api/v1/operator/simulation/source-state`  | Tải trạng thái nền A (8 Hubs)         |
| `POST`           | `/api/v1/operator/simulation/validate`      | Kiểm tra tham số (Báo lỗi EX-10-01)   |
| `POST`           | `/api/v1/operator/simulation/run`           | Chạy thuật toán mô phỏng What-if     |
| `POST`           | `/api/v1/operator/simulation/save-rule`     | Lưu kịch bản dự phòng                |
| `GET`            | `/api/v1/operator/simulation/history`       | Lấy lịch sử 28 phiên mô phỏng       |
