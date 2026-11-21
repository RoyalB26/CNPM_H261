# Backend Mock Service - Smart E-Mobility Hub (End-User)

## Cước thuê xe hiện tại

Thời gian tính tiền bắt đầu khi nhận xe thành công (`start`), kết thúc khi
trả xe thành công. Thời gian giữ chỗ chưa tính phí. Đơn giá lấy từ
`pricing.rental_bike_hourly` của Hub nguồn và lưu trong chuyến đi lúc nhận xe.
Quy ước mock: làm tròn lên phút, cước = số phút × đơn giá giờ / 60,
làm tròn lên 1 đồng. Ví dụ 30 phút với 10.000đ/giờ là 5.000đ.

Trả xe tạo `rental_invoice` trong booking; response trả xe, lịch sử và hóa đơn
dùng chung kết quả tính cước. `GET /api/invoices/current?type=rental` lấy hóa đơn
đã kết thúc gần nhất; thêm `trip_id` để chọn chuyến cụ thể. Chưa có hóa đơn trả
HTTP 404. Chuyến seed/runtime cũ thiếu `started_at` dùng số phút snapshot đã lưu,
ghi `billing_source=legacy_elapsed_minutes`; không tự tạo mốc bắt đầu.
`POST /api/invoices/pay` ghi nhận thanh toán mô phỏng cho hóa đơn thuê xe đã
hoàn tất. Body gồm `invoice_id`, `method` (`wallet` hoặc `bank_transfer`), và
`amount` tùy chọn để đối chiếu. Chấp nhận tên FE `Ví điện tử`/`Thẻ ngân hàng`.
Số tiền chính thức lấy từ hóa đơn Backend. Thành công lưu `paid`, `paid_at`,
`transaction_id`, `payment_method`; chưa tích hợp cổng thanh toán thật.
Thanh toán lặp/sai số tiền/tiền mặt trả 409; không tìm thấy hóa đơn trả 404;
sai schema trả 422. Gateway ghi JSON lỗi trả 503 và phục hồi trạng thái cũ.
Endpoint thanh toán hiện chỉ nhận hóa đơn thuê xe đã lưu; hóa đơn mẫu của
các dịch vụ khác chưa có luồng thanh toán và sẽ trả 404 khi gửi tới endpoint này.

Chạy kiểm thử: `.venv/bin/python -B -m unittest discover -s BE/user/tests -v`.

## Tra cứu Hub cho demo

`GET /api/hubs?keyword=bach%20khoa&status=ACTIVE` tìm tên/địa chỉ không dấu,
không phân biệt hoa thường. `vehicle_type=bike` lọc Hub có xe thực sự có thể
đặt; `vehicle_type=personal` lọc Hub hoạt động còn chỗ đỗ. Không gửi bộ lọc
thì API trả toàn bộ Hub, bao gồm trạng thái ngừng hoạt động.

`POST /api/hubs/suggest-route` nhận `origin_lat`, `origin_lng`, `dest_lat`,
`dest_lng`, `vehicle_type=bike` (mặc định). Gợi ý loại xe đã đặt, đang đi,
điều chuyển hoặc bảo trì và Hub trả hết chỗ/ngừng hoạt động. Khoảng cách là
đường chim bay, thời gian là ước tính demo. Không có phương án trả 409;
tọa độ sai trả 422. Kết quả gợi ý chưa giữ tài nguyên, lúc đặt phải kiểm tra lại.

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
