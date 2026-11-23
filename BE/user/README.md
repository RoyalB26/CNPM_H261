# Backend Mock Service - Smart E-Mobility Hub (End-User)

## Đối chiếu đặc tả và phạm vi bản demo

Đối chiếu ba tài liệu nhóm đã gửi: `Đặc tả CNPM (1) (1).docx` (mô tả),
`Đặc tả CNPM (2) (1).docx` (use case) và `Đặc tả CNPM (3).docx` (requirements).
Các trạng thái dưới đây đánh giá Backend User ở mức mock, không đánh giá
toàn bộ hệ thống, giao diện hoặc chất lượng production; không quy đổi thành
phần trăm khi nhóm chưa thống nhất trọng số nghiệm thu.

| Spec / use case | Đã có trong Backend User | Giới hạn còn lại |
| --- | --- | --- |
| FR-I01 / UC1 – Tài khoản | Đăng nhập tài khoản seed bằng email/điện thoại; đọc/sửa hồ sơ; xem xe cá nhân | Đăng ký chỉ là stub trả thành công, không lưu tài khoản; chưa có xác thực token, phân quyền hoặc nhiều tài khoản |
| FR-I02 / UC2 – Tra cứu Hub | Tìm tên/địa chỉ không dấu; chi tiết tài nguyên; gợi ý Hub lấy/trả xe dùng chung từ tọa độ | Khoảng cách đường chim bay; chưa định tuyến đường bộ hoặc gợi ý riêng theo nhu cầu xe cá nhân |
| FR-I03 / UC3 – Đặt trước | Thuê xe, giữ ô đỗ, giữ cổng sạc ngay, giữ pin; xem/hủy booking; kiểm tra tài nguyên | Chưa có lịch sạc theo giờ, gói ghép `personal` hoặc gợi ý thay thế tự động trong response đặt thất bại |
| FR-I04 / UC4 – Sử dụng dịch vụ | Nhận/trả xe; trạng thái đang sử dụng; bắt đầu/kết thúc sạc; xác nhận đổi pin; gửi xe liên thông bảo vệ | Chưa có khóa xe/thiết bị thật; kWh nhập mô phỏng; giữ chỗ và phiên sạc không phải lịch sạc tối ưu |
| FR-I05 / UC5 – Báo sự cố | Tạo báo cáo và phiếu bảo trì liên kết; đọc lại trạng thái/kết quả Staff | Chưa có push/SMS; chưa kiểm chứng tải ảnh thực tế; phân quyền theo tài khoản chưa triển khai |
| FR-I11 / UC6 – Thu phí | Hóa đơn thuê theo phút, sạc theo kWh, đổi pin theo số lượng; thanh toán mock một lần; hóa đơn gửi xe từ vé bãi | Chưa có cổng thanh toán thật/đối soát; phí gửi xe vẫn theo mock Staff, chưa tính thời gian đỗ thực |
| FR-N01, N02, N03 – Trạng thái và giữ tài nguyên | Cập nhật RAM/JSON dùng chung; chặn đặt trùng, xe đang đi, bảo trì/điều chuyển; hoàn tài nguyên khi hủy/hết hạn | Hết hạn cần gọi API thủ công; thời hạn 10/15 phút còn cố định; chưa xử lý nhiều tiến trình hoặc khóa phân tán |
| FR-N08, N09, N10 – Liên thông và lịch sử | Báo cáo nối phiếu bảo trì; User đọc thay đổi Hub từ Operator; lưu lịch sử booking/chuyến/phiên và hóa đơn | Chưa chứng minh mọi nhánh điều chuyển; chưa có audit log đầy đủ hoặc thời hạn lưu trữ theo NFR |
| FR-N12 – Dữ liệu mô phỏng | Seed JSON, runtime JSON, kiểm thử độc lập không dùng runtime demo | Chưa thay thế nguồn mock bằng IoT chỉ qua cấu hình |

FR-I06–I10, I12 và các yêu cầu điều phối/mô phỏng toàn mạng do phần Operator,
Staff hoặc hệ thống chung phụ trách; không lấy các phần đó làm chức năng
BE User đã hoàn thành. FR-N04 (lịch sạc), N11 (thông báo), N14 (IoT thời gian
thực), N15 (tác vụ nền khi ngừng thiết bị) chưa được coi là đáp ứng trong BE User.
Các chỉ tiêu tải, SLA, bảo mật và triển khai của NFR chưa được đo/nghiệm thu
bằng bộ test chức năng hiện tại.

**Điểm cần nhóm chốt:** tài liệu mô tả có câu tính thời gian thuê “sau khi đặt
xe”; code hiện tính từ khi nhận xe (`start`) đến khi trả thành công. Checklist
ghi nhận khác biệt này, chưa tự đổi quy tắc tính phí. Trước khi báo hoàn thành
theo spec, nhóm cần chọn mốc tính tiền và cập nhật code hoặc đặc tả tương ứng.

## Kịch bản trình bày demo BE User

Demo tự động có thể chạy bằng một lệnh, không cần bật server và không thay
đổi dữ liệu demo hiện tại:

```bash
.venv/bin/python -B -m unittest discover -s BE/user/tests -p test_gateway_integration.py -v
```

Đây là kiểm thử HTTP qua ứng dụng Gateway bằng `TestClient`, không phải demo
giao diện. Trình bày theo các bước sau; mã booking, chuyến và hóa đơn mới phải
lấy từ response, không dùng lại mã của một lần chạy trước.

| Bước | Hành động / endpoint (prefix `/api/v1/user`) | Kết quả cần trình bày |
| --- | --- | --- |
| 1 | `POST /auth/login`, `GET /profile`, `GET /vehicles` | Tài khoản seed đăng nhập được; sai mật khẩu 401, thiếu mật khẩu 422, JSON hỏng 400 |
| 2 | `GET /hubs?keyword=bach%20khoa`, `GET /hubs/hub-02` | Hub và tài nguyên hiện tại; Hub không tồn tại trả 404 |
| 3 | Kết thúc chuyến `TRIP-8821` và phiên sạc `CHG-302` của seed | Chuẩn bị tài khoản một người dùng cho luồng mới, không xóa dữ liệu bằng tay |
| 4 | Hai request `POST /bookings` cùng `XE-052` tại `hub-02`, đích `hub-04` | Một request 200 và một request 409; không giữ xe hai lần |
| 5 | `POST /bookings/{id}/start` → `POST /services/return-vehicle` → `GET /invoices/current?type=rental&trip_id=...` | Booking hoàn thành; xe về Hub thực tế; phí và hóa đơn cùng kết quả |
| 6 | Đặt `plan_type=swap`, pin `B48`, Hub `hub-02` → `POST /bookings/{id}/swap` | Chỉ trừ pin một lần; hóa đơn theo số lượng × đơn giá |
| 7 | Đặt sạc `S01` tại `hub-01` → `/bookings/{id}/charging/start` → `/services/charging/stop` với tổng 2,4 kWh | Hóa đơn 8.400đ ở đơn giá seed 3.500đ/kWh; trả cổng một lần |
| 8 | Đặt `plan_type=parking`, ô `P11` tại `hub-02`; gọi API check-in/check-out Staff | Dùng đúng ô đã giữ; không trừ ô lần nữa; hóa đơn tiền mặt `paid` |
| 9 | `POST /incidents`; xem và xử lý phiếu bằng API Staff; `GET /incidents` | Báo cáo User phản ánh kết quả xử lý mới nhất |
| 10 | Operator tạm ngưng `hub-02`; User thử đặt pin; Operator mở lại Hub | User nhận 409 trong thời gian Hub ngừng hoạt động |
| 11 | `POST /invoices/pay` cho thuê xe/đổi pin/sạc, rồi gọi lại | Lần đầu thành công, lần sau 409; không tạo giao dịch thứ hai |
| 12 | Giả lập lỗi ghi JSON trong test; khởi động tiến trình kiểm tra mới | Lỗi lưu trả 503 và hoàn nguyên; hóa đơn đã thanh toán vẫn còn sau khởi động lại |

Kịch bản test dọn phiên parking seed trước bước gửi xe. Khi thao tác thủ công,
kiểm tra `GET /services/active` trước vì runtime của nhóm có thể đã khác seed.
Không reset runtime chung chỉ để làm giống kịch bản.

Trước khi chốt demo: chạy toàn bộ test ở phần dưới, chạy `git diff --check`,
kiểm tra `git status --short` để rà file mới/chưa commit. Chưa tính việc FE gọi
được mọi API là đã hoàn thành; cần kiểm thử UI riêng nếu nhóm demo bằng FE.

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
Endpoint thanh toán nhận hóa đơn thuê xe, đổi pin và sạc đã lưu. Gửi xe cá
nhân thanh toán trực tiếp cho bảo vệ; hóa đơn gửi xe không được thanh toán
qua endpoint trực tuyến này.

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

## Booking thuê xe hết hạn

Booking mới có `expires_at` ISO 8601 với múi giờ UTC; thuê xe được giữ 10 phút.
`hold_until` tiếp tục dùng để hiển thị như cũ. Nhận xe tại hoặc sau `expires_at`
trả 409, không tạo chuyến đi. Thời hạn chỉ do Backend đặt, không nhận từ client.

Để demo giải phóng xe, gọi `POST /api/v1/user/bookings/expire` (alias
`POST /api/bookings/expire`), không cần body. API trả `expired_booking_ids` và
`expired_count`, chuyển booking đang giữ sang `Hết hạn`, ghi `expired_at` và
hoàn xe khi xe vẫn đủ điều kiện. Gọi lặp không tăng lại số xe; không thay đổi
chuyến đang sử dụng hoặc xe bảo trì. Gateway lưu thay đổi vào runtime JSON.

Bản demo hiện cần gọi API xử lý hết hạn, chưa có tác vụ nền định kỳ. GET không
tự giải phóng xe. Booking seed/runtime cũ thiếu `expires_at` không được suy đoán
ngày hết hạn từ chuỗi giờ `hold_until`, nên không được quét trong bước này.

## Đặt chỗ gửi xe cá nhân cho demo

Gửi `POST /api/v1/user/bookings` với `plan_type=parking`, `hub_id`,
`personal_plate`. Có thể gửi `parking_slot` (hoặc `resource_id`) như `P11`;
nếu không gửi thì Backend chọn một chỗ còn trống. Response có `parking_slot`,
`resource_id`, `resource_name` và `expires_at` (giữ chỗ 15 phút).

Backend kiểm tra Hub hoạt động, biển số chưa đặt/đang gửi, chỗ chưa bị vé bãi,
booking hoặc điều chuyển giữ. Thành công đặt `is_available=false` và giảm
`available_parking`; hủy hoàn lại chỗ một lần. Endpoint `/bookings/expire`
cũng xử lý booking `parking` mới. Gói ghép `personal` chưa được nâng cấp thành
đặt gửi xe và sạc đồng thời trong bước này.

Staff check-in cùng biển số/Hub sẽ dùng chỗ đã giữ dù request Staff chứa tên
chỗ hiển thị khác; không trừ chỗ lần nữa. Booking hết hạn/Hub ngừng hoạt động
bị từ chối 409. Người dùng demo chỉ có một phiên parking hiện tại; cần kết thúc
phiên cũ trước khi check-in phiên mới. Check-out liên kết booking mới sẽ chuyển
booking sang `Hoàn thành`, xóa phiên đang đỗ và trả chỗ một lần.

`price` khi đặt là ước tính đơn giá giờ × số giờ dự kiến (mặc định 2).
Chưa tính phí theo thời gian đỗ thực; response thu phí Staff vẫn là mock cũ.
Nhánh Staff walk-in không có booking tiếp tục dùng logic cũ; chưa hoàn thiện
toàn bộ kiểm tra bãi đỗ walk-in trong bước BE User này.

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


## Đổi pin theo số lượng cho demo

Tạo booking với `plan_type=swap` hoặc `battery_swap`, `hub_id`, `battery_type`
(ví dụ `B48`), `battery_quantity` (số nguyên dương, mặc định 1). Nếu không gửi
loại pin, cần gửi biển số phương tiện cá nhân đã lưu để lấy loại tương thích.
Không phân tích số lượng từ chuỗi `services.detail`; số lượng chính thức là
`battery_quantity`. Hub phải hoạt động và có đủ pin đầy của đúng loại.

Đặt thành công giảm `batteries[].available_count` và `available_batteries` một
lần, chốt đơn giá `swap_fee` của loại pin. Hủy hoặc gọi `/bookings/expire` khi
quá hạn 15 phút hoàn pin đã giữ; thao tác lặp không hoàn thêm.

`POST /api/v1/user/bookings/{id}/swap` (alias `/api/bookings/{id}/swap`) không
cần body, xác nhận đã đổi pin. Booking chuyển `Hoàn thành`, tồn kho không trừ
lần hai, tạo `battery_swap_invoice` theo số lượng × đơn giá đã giữ. Xác nhận
lặp, quá hạn hoặc Hub/loại pin bị ngừng hoạt động trả 409. Phiên swap cũ chưa
lưu thông tin giữ pin không được coi là có pin để xác nhận.

`GET /api/v1/user/invoices/current?type=swap&booking_id={id}` lấy hóa đơn.
Thanh toán bằng `/invoices/pay` như thuê xe, dùng `invoice_id` thực nhận từ
Backend; chặn thanh toán lặp. Đổi 2 pin B48 với giá 25.000đ/pin là 50.000đ.
Luồng FE cũ chưa gọi API xác nhận đổi pin; demo đầy đủ qua API/curl, chưa sửa FE.
Pin cũ nhận lại không được cộng ngay vào kho pin đầy; chưa mô phỏng chu kỳ sạc
và đo chất lượng từng viên pin, cũng chưa có tích hợp thiết bị vật lý.

## Giữ cổng sạc ngay cho demo

Tạo booking với `plan_type=charging`, `hub_id`, `personal_plate` và tùy chọn
`charging_port` (mã cổng như `S01`, cũng chấp nhận `resource_id`). Nếu không chọn
cổng thì Backend chọn một cổng sẵn sàng. Kiểm tra phiên đang sạc, booking khác,
phiếu bảo trì và trạng thái Hub/cổng trước khi xác nhận. Một phương tiện không
được giữ nhiều cổng cùng lúc.

Đặt thành công chuyển cổng sang `Đã đặt chỗ`, `is_available=false`, giảm
`available_chargers` một lần và lưu `charging_rate_per_kwh`. Hủy hoặc gọi API
`/bookings/expire` sau 15 phút sẽ trả cổng nếu cổng chưa chuyển sang bảo trì hoặc
đang sạc. Trạng thái mới được Gateway lưu xuống runtime JSON.

Đây là giữ cổng độc quyền ngay, chưa có lịch theo khung giờ. Request có
`arrival_time` hoặc `services[].time_slot` bị từ chối 422 thay vì được xác nhận
như một lịch sạc đã xử lý. `price=0` ở booking là chưa chốt phí điện, không có
nghĩa sạc miễn phí. API bắt đầu/kết thúc sạc và hóa đơn theo kWh được mô tả dưới đây.
Chưa sửa FE và gói ghép `personal`.


## Phiên sạc và hóa đơn điện năng mô phỏng

Sau khi đặt cổng, gọi `POST /api/v1/user/bookings/{id}/charging/start`, không
cần body. Response chứa `charging.session_id`, đơn giá đã chốt, mốc bắt đầu.
Booking chuyển `Đang sử dụng`; cổng chuyển `Đang sạc`, không trừ thêm bộ đếm.
Chặn nhận booking hết hạn/không đúng chủ giữ cổng/bảo trì hoặc khi đang có
phiên sạc khác. Các phép đo trong phiên mới bắt đầu từ 0 để demo, chưa lấy IoT.

Kết thúc bằng `POST /api/v1/user/services/charging/stop`:

```json
{"session_id":"CHG-...","power_consumed_kwh":2.4,"final_charge":80}
```

`power_consumed_kwh` là tổng điện năng của phiên do người demo nhập, không phải
số kWh cộng thêm; không được nhỏ hơn số đã ghi nhận. `final_charge` tùy chọn,
trong khoảng 0–100 và không nhỏ hơn mức đã ghi nhận. Backend tính phí = kWh ×
đơn giá chốt, làm tròn lên 1 đồng (2,4 × 3.500 = 8.400đ), tạo `charging_invoice`
và lưu `charging_session` vào booking. Đánh dấu `measurement_source=mock_input`.
Trả cổng một lần khi cổng đủ điều kiện; không bật lại cổng bảo trì hoặc bị khóa.

`GET /api/v1/user/invoices/current?type=charging&session_id=CHG-...` lấy hóa đơn
phiên; cũng hỗ trợ query `booking_id`. Chưa có hóa đơn trả 404. Thanh toán qua
`/invoices/pay` như thuê xe/đổi pin; chặn trả phiên và thanh toán lặp.
Các endpoint mới có alias `/api/...` tương ứng.

Với seed `CHG-302` chưa có booking/thời điểm bắt đầu, có thể kết thúc bằng tổng
kWh ít nhất 2,4. Backend tạo booking lịch sử riêng, lấy đơn giá cổng hiện tại,
không tự bịa thời điểm bắt đầu và không tăng bộ đếm nếu seed đã đánh dấu cổng
khả dụng. Chưa tự chuẩn hóa toàn bộ bộ đếm seed. Gateway lưu cả lịch sử và hóa
đơn vào runtime; kiểm thử dùng `BE_RUNTIME_PATH` tạm, không ghi đè runtime demo.

Chưa có đo điện năng thật, thanh toán thật, hàng đợi hoặc lịch sạc tối ưu.
FE cũ chưa gọi các endpoint mới; demo đầy đủ qua API/curl.

## Kiểm thử trước khi demo hoặc commit

Chạy tại thư mục gốc repository:

```bash
.venv/bin/python -B -m unittest discover -s BE/user/tests -v
git diff --check
```

Bộ kiểm thử gồm các luồng nghiệp vụ trên `MockDatabaseStore` riêng và một
kịch bản HTTP qua Gateway bằng `TestClient`, không cần mở cổng 8000. Kịch bản
Gateway chạy trong tiến trình con, đặt `BE_RUNTIME_PATH` vào thư mục tạm trước
khi import backend, rồi tự dọn dữ liệu sau test. Không dùng runtime demo của nhóm.

Kịch bản HTTP kiểm tra:

- Thuê xe: đặt, nhận, trả, xem hóa đơn, thanh toán và chặn thanh toán lặp.
- Đổi pin và sạc: hoàn thành dịch vụ, chốt phí, thanh toán hóa đơn tương ứng.
- Hai request đặt cùng xe: chỉ một request được xác nhận.
- Gửi xe: User giữ ô; API bảo vệ check-in/check-out không trừ hoặc hoàn ô hai lần.
- Báo sự cố: phiếu xuất hiện tại Staff; kết quả xử lý được User đọc lại.
- Operator tạm ngưng Hub: User không thể đặt tài nguyên tại Hub đó.
- GET và request lỗi không thay đổi dữ liệu; lỗi ghi JSON trả 503 và hoàn nguyên RAM.
- Một tiến trình Python mới đọc lại được hóa đơn đã thanh toán từ runtime JSON.

Có thể chỉ chạy kiểm thử Gateway bằng:

```bash
.venv/bin/python -B -m unittest discover -s BE/user/tests -p test_gateway_integration.py -v
```

Các kiểm thử này chưa thay thế việc kiểm tra giao diện FE hoặc xác nhận toàn
bộ đặc tả. Chưa triển khai nhiều tài khoản/phân quyền thật, gói ghép `personal`,
lịch sạc theo giờ, IoT và thanh toán thực. Những phần đó nằm ngoài bản demo
đã thống nhất; API và dữ liệu mock không được xem là hệ thống production.

## Quy tắc chọn hóa đơn và Hub đích

`GET /api/v1/user/invoices/current` chấp nhận `type` là `rental`, `charging`,
`swap`/`battery_swap` hoặc `parking`. Có thể chọn bằng `booking_id` hoặc
`invoice_id`; `trip_id` chỉ dành cho thuê xe, `session_id` chỉ dành cho sạc.
Các bộ lọc được kết hợp, không bỏ qua bộ lọc không khớp. Sai loại/bộ lọc trả
422; chưa có hóa đơn phù hợp trả 404. Không truyền định danh thì chọn hóa đơn
có thời điểm tạo mới nhất, kể cả khi danh sách booking không được sắp xếp.

Hóa đơn gửi xe được đọc từ vé thực trong `parking_records`, theo biển số xe
của tài khoản demo hoặc biển số đã đặt; giữ kênh tiền mặt `cash_guard`.
Không trả hóa đơn mẫu khi không tìm thấy vé. GET không tạo giao dịch.

Booking thuê xe kiểm tra Hub đích tồn tại và hoạt động trước khi giữ xe.
Nếu gửi cả `destination_hub_id` và `destination_hub_name`, hai trường phải
chỉ cùng một Hub. Mã Hub đích được giữ trong booking và chuyến đi để client
có thể dùng lại khi trả xe. Khi trả xe vẫn kiểm tra Hub thực tế và chỗ đỗ.

## Bảo vệ xe đang đi và quyền giữ xe

Booking thuê xe mới ghi `reserved_by` trên xe. Nhận hoặc hủy xe phải khớp mã
giữ chỗ và chỉ có một booking đang xác nhận cho xe đó. Runtime cũ thiếu
`reserved_by` vẫn dùng được nếu xác định duy nhất booking giữ xe. Mã booking
trùng hoặc nhiều booking cùng giữ xe trả xung đột, không tự chọn bản ghi đầu.
API hết hạn kiểm tra các xung đột này trước khi giải phóng bất kỳ tài nguyên nào.

Booking có chuyến đi đang hoạt động không được hủy, kể cả seed cũ còn ghi
`Đã xác nhận`. Cần kết thúc bằng API trả xe để giữ liên kết chuyến và hóa đơn.

Trả xe vẫn kết thúc chuyến và chốt phí khi xe đang có phiếu bảo trì/điều
chuyển, nhưng không tự chuyển xe đó thành `Sẵn sàng` hoặc tăng bộ đếm xe khả
dụng. Xe bảo trì mang trạng thái `Đang bảo trì`; xe bị khóa điều chuyển mang
trạng thái `Không khả dụng`. Vẫn trừ một chỗ đỗ vì xe đã về Hub thực tế.
Thao tác trả xe không thay thế việc nhân viên kiểm tra và mở lại tài nguyên.
