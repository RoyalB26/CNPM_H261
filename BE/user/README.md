# Backend Mock Service - Smart E-Mobility Hub (End-User)

Cung cấp REST API Mock mô phỏng toàn bộ dữ liệu cho ứng dụng User của hệ thống điều phối phương tiện điện Thông minh ĐHQG-HCM.

## Cấu trúc thư mục

```
BE/user/
├── main.py              # Ứng dụng Starlette/Uvicorn REST API Server
└── schemas/             # Pydantic Schemas riêng biệt, quy chuẩn từng luồng dữ liệu
    ├── __init__.py      # Export tất cả các schema
    ├── auth.py          # Schemas xác thực: Login, Register, Profile, Security
    ├── hub.py           # Schemas thông tin Hub, bản đồ, phương tiện xe điện
    ├── booking.py       # Schemas đặt trước: Thuê xe dùng chung, Đặt chỗ đỗ, Lịch sạc
    ├── service.py       # Schemas theo dõi dịch vụ đang sử dụng thời gian thực
    ├── incident.py      # Schemas báo cáo sự cố & phản hồi từ điều hành viên
    └── payment.py       # Schemas hóa đơn điện tử, kênh thanh toán trực tuyến & bảo vệ
```

## Chạy Server Backend

Yêu cầu Python 3.10+ đã cài đặt `uvicorn`, `starlette`, `pydantic`.

```bash
cd BE/user
python main.py
```

Server sẽ khởi chạy tại: `http://127.0.0.1:8000`

### Danh sách Endpoint chính

| Method | Endpoint | Mô tả | Schema Input / Output |
|--------|----------|-------|-----------------------|
| `POST` | `/api/auth/login` | Đăng nhập tài khoản | `UserLoginRequest` -> Token + `UserProfileResponse` |
| `POST` | `/api/auth/register` | Đăng ký tài khoản | `UserRegisterRequest` |
| `GET`  | `/api/user/profile` | Xem hồ sơ cá nhân | `UserProfileResponse` |
| `GET`  | `/api/hubs` | Danh sách các Hub và tài nguyên | `List[HubSummary]` |
| `GET`  | `/api/hubs/{id}` | Chi tiết Hub, danh sách xe | `HubDetailResponse` |
| `GET`  | `/api/bookings` | Danh sách đặt trước cá nhân | `List[BookingResponse]` |
| `POST` | `/api/bookings` | Tạo đặt trước mới | `CreateBookingRequest` -> `BookingResponse` |
| `POST` | `/api/bookings/{id}/cancel` | Hủy đặt trước | `CancelBookingRequest` |
| `GET`  | `/api/services/active` | Trạng thái dịch vụ đang dùng | `ActiveRideResponse`, `ActiveParkingResponse`, `ActiveChargingResponse` |
| `GET`  | `/api/incidents` | Lịch sử báo cáo sự cố | `List[IncidentReportResponse]` |
| `POST` | `/api/incidents` | Gửi báo cáo sự cố | `CreateIncidentReportRequest` -> `IncidentReportResponse` |
| `GET`  | `/api/invoices/current` | Lấy chi tiết hóa đơn dịch vụ | `InvoiceResponse` |
| `POST` | `/api/invoices/pay` | Thanh toán hóa đơn | `PaymentSubmitRequest` -> `PaymentProcessResult` |
