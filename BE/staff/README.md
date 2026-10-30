# Backend Service: Field Staff & Security Guard
Smart E-Mobility Hub - ĐHQG-HCM

## 1. Giới thiệu
Dịch vụ Mock Backend và Schema Pydantic phục vụ toàn bộ các luồng thao tác hiện trường của nhân viên vận hành (Field Staff) và bảo vệ bãi đỗ Hub (Security Guard):
- **Điều phối phương tiện (Relocation)**:
  - Bản đồ tuyến đường di chuyển đề xuất (2.5 km, 10 phút, 20 xe)
  - Quét mã QR đối soát từng phương tiện & cọc sạc (Bảng tiến độ 18/20 -> 20/20)
  - Báo cáo sự cố phát sinh trong quá trình vận chuyển (loại sự cố, GPS, ảnh đính kèm)
  - Hoàn tất bàn giao phương tiện tại trạm đích
- **Kỹ thuật & Bảo dưỡng (Maintenance)**:
  - Danh sách phiếu bảo trì theo trạng thái (Mới tiếp nhận MT-102, MT-098, MT-091)
  - Chi tiết phiếu sự cố MT-102 (BK-EB-018 không khởi động, vị trí ô số 018)
  - Quét mã QR xác thực thiết bị và ô đỗ tại hiện trường
  - Báo cáo kết quả bảo trì (Đã sửa tại chỗ / Cần chuyển về xưởng, ghi chú kỹ thuật, ảnh)
  - Báo cáo sự cố mới phát sinh trong lúc kiểm tra
- **Bảo vệ Hub & Dịch vụ gửi xe cá nhân (Security Guard & User Parking)**:
  - Tiếp nhận xe vào bãi: Quét biển số xe `59-B2 123.45`, phân bổ vị trí Dãy A - Ô 018, phát mã vé QR `SG-20261022-018`
  - Xác nhận trả xe & Thu cước: Tính toán thời gian thực gửi (2 giờ 06 phút), thu cước tiền mặt 25.000 VNĐ
  - Nhật ký ca trực & Đối soát tiền mặt: Tổng kết ca 48 lượt, 1.200.000 VNĐ, bàn giao tiền và chốt ca

## 2. Cấu trúc thư mục
```
BE/staff/
├── schemas/
│   ├── __init__.py        # Export toàn bộ schemas
│   ├── auth.py            # Staff authentication & Profile
│   ├── relocation.py      # Điều phối, quét QR bàn giao, báo cáo sự cố
│   ├── maintenance.py     # Phiếu bảo trì, quét QR thiết bị, báo cáo sửa chữa
│   └── parking.py         # Tiếp nhận xe vào, trả xe, thu cước, chốt ca trực
├── main.py                # Starlette API Server (Port 8002)
└── README.md
```

## 3. Khởi chạy
```powershell
& "D:\apps\miniconda\python.exe" D:\Study\University\H261\CNPM\BTL3\BE\staff\main.py
```
Hoặc chạy gateway tập trung:
```powershell
& "D:\apps\miniconda\python.exe" D:\Study\University\H261\CNPM\BTL3\BE\run_all.py
```

## 4. Danh sách API Endpoints chính
| Phương thức | Endpoint | Chức năng |
|---|---|---|
| `POST` | `/api/v1/staff/auth/login` | Đăng nhập nhân viên hiện trường |
| `GET` | `/api/v1/staff/profile` | Thông tin nhân viên, ca làm việc |
| `GET` | `/api/v1/staff/relocation/task/{id}` | Chi tiết lộ trình & bảng đối soát xe |
| `POST` | `/api/v1/staff/relocation/scan-bike` | Quét QR đối soát xe vào cọc sạc |
| `POST` | `/api/v1/staff/relocation/handover` | Xác nhận hoàn tất bàn giao |
| `POST` | `/api/v1/staff/relocation/incident` | Báo cáo sự cố khi điều chuyển |
| `GET` | `/api/v1/staff/maintenance/tasks` | Danh sách phiếu sự cố cần bảo trì |
| `GET` | `/api/v1/staff/maintenance/tasks/{code}` | Chi tiết sự cố MT-102 |
| `POST` | `/api/v1/staff/maintenance/verify-device` | Quét QR xác thực thiết bị tại chỗ |
| `POST` | `/api/v1/staff/maintenance/resolve` | Gửi kết quả sửa chữa / chuyển xưởng |
| `POST` | `/api/v1/staff/maintenance/incident` | Ghi nhận sự cố mới phát sinh |
| `POST` | `/api/v1/staff/parking/checkin` | Ghi nhận xe cá nhân vào Hub |
| `GET` | `/api/v1/staff/parking/checkout/{id}` | Tính cước gửi xe cá nhân |
| `POST` | `/api/v1/staff/parking/checkout/confirm` | Xác nhận đã thu tiền mặt |
| `GET` | `/api/v1/staff/parking/shift-summary` | Nhật ký & đối soát doanh thu ca |
| `POST` | `/api/v1/staff/parking/shift-close` | Chốt ca trực & nộp tiền quầy |
