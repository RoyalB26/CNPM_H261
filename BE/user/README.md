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
| FR-I03 / UC3 – Đặt trước | Thuê xe, giữ ô đỗ, giữ cổng sạc ngay, giữ pin; gói ghép đỗ + sạc `personal`; xem/hủy booking; tối đa 3 gợi ý khi đặt thất bại | Chưa có lịch sạc theo giờ; gợi ý chỉ đổi nơi/tài nguyên nhận, giữ nguyên Hub trả xe |
| FR-I04 / UC4 – Sử dụng dịch vụ | Nhận/trả xe; trạng thái đang sử dụng; bắt đầu/kết thúc sạc; xác nhận đổi pin; gửi xe liên thông bảo vệ | Chưa có khóa xe/thiết bị thật; kWh nhập mô phỏng; giữ chỗ và phiên sạc không phải lịch sạc tối ưu |
| FR-I05 / UC5 – Báo sự cố | Tạo báo cáo và phiếu bảo trì liên kết; đọc lại trạng thái/kết quả Staff | Chưa có push/SMS; chưa kiểm chứng tải ảnh thực tế; phân quyền theo tài khoản chưa triển khai |
| FR-I11 / UC6 – Thu phí | Hóa đơn thuê theo phút, sạc theo kWh, đổi pin theo số lượng; thanh toán mock một lần; hóa đơn gửi xe từ vé bãi | Chưa có cổng thanh toán thật/đối soát; phí gửi xe vẫn theo mock Staff, chưa tính thời gian đỗ thực |
| FR-N01, N02, N03 – Trạng thái và giữ tài nguyên | Cập nhật RAM/JSON dùng chung; chặn đặt trùng, xe đang đi, bảo trì/điều chuyển; tự quét hết hạn qua Gateway và hoàn tài nguyên một lần | Thời hạn 10/15 phút còn cố định; chưa xử lý nhiều tiến trình hoặc khóa phân tán |
| FR-N08, N09, N10 – Liên thông và lịch sử | Báo cáo nối phiếu bảo trì; User đọc thay đổi Hub từ Operator; lưu lịch sử booking/chuyến/phiên và hóa đơn | Chưa chứng minh mọi nhánh điều chuyển; chưa có audit log đầy đủ hoặc thời hạn lưu trữ theo NFR |
| FR-N12 – Dữ liệu mô phỏng | Seed JSON, runtime JSON, kiểm thử độc lập không dùng runtime demo | Chưa thay thế nguồn mock bằng IoT chỉ qua cấu hình |

FR-I06–I10, I12 và các yêu cầu điều phối/mô phỏng toàn mạng do phần Operator,
Staff hoặc hệ thống chung phụ trách; không lấy các phần đó làm chức năng
BE User đã hoàn thành. FR-N04 (lịch sạc), N11 (thông báo), N14 (IoT thời gian
thực), N15 (tác vụ nền khi ngừng thiết bị) chưa được coi là đáp ứng trong BE User.
Các chỉ tiêu tải, SLA, bảo mật và triển khai của NFR chưa được đo/nghiệm thu
bằng bộ test chức năng hiện tại.

**Quy tắc tính phí đã chọn:** booking thuê xe mới tính tiền từ lúc Backend
xác nhận đặt xe thành công đến khi trả xe thành công, bao gồm thời gian chờ
nhận xe. Chưa bổ sung phí cho booking hủy/hết hạn mà không nhận xe vì đặc tả
chưa quy định khoản này. Dữ liệu cũ được xử lý theo phần cước bên dưới.

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

Booking thuê xe mới lưu `billing_started_at` ISO 8601 UTC khi được Backend
xác nhận; đây là mốc bắt đầu tính tiền. Cước kết thúc lúc trả xe thành công.
Đơn giá lấy từ `pricing.rental_bike_hourly` của Hub nguồn, lưu vào
`rental_hourly_rate` tại lúc đặt, rồi sao chép vào chuyến đi khi nhận xe.
Đổi giá Hub sau khi đặt không thay đổi đơn giá của booking đã xác nhận.
`started_at` vẫn là thời điểm nhận xe thực tế, tách với mốc bắt đầu tính phí.
Quy ước mock: làm tròn lên phút, cước = số phút × đơn giá giờ / 60,
làm tròn lên 1 đồng. Ví dụ đặt 08:00, nhận 08:08, trả 08:30 với 10.000đ/giờ
là 30 phút, 5.000đ. `elapsed_minutes` trong kết quả trả xe là số phút tính phí;
lịch sử ghi `billing_source=billing_started_at` cho các booking mới này.

Trả xe tạo `rental_invoice` trong booking; response trả xe, lịch sử và hóa đơn
dùng chung kết quả tính cước. `GET /api/invoices/current?type=rental` lấy hóa đơn
đã kết thúc gần nhất; thêm `trip_id` để chọn chuyến cụ thể. Chưa có hóa đơn trả
HTTP 404. Booking/phiên cũ thiếu `billing_started_at` tiếp tục tính từ
`started_at` nếu có, ghi `billing_source=started_at`. Nếu thiếu cả hai mốc,
dùng số phút snapshot đã lưu, ghi `billing_source=legacy_elapsed_minutes`.
Không đoán ngày đặt từ `created_at`/`hold_until` chỉ có giờ và không tính lại
các hóa đơn đã tạo/thanh toán. Request client không được quyết định mốc hay
đơn giá tính phí. Booking mới có đơn giá hoặc mốc thời gian sai bị từ chối
trước khi chuyển xe hoặc thay đổi tài nguyên.
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

## Tự động xử lý booking hết hạn

Booking mới có `expires_at` ISO 8601 với múi giờ UTC; thuê xe được giữ 10 phút.
`hold_until` tiếp tục dùng để hiển thị như cũ. Nhận xe tại hoặc sau `expires_at`
trả 409, không tạo chuyến đi. Thời hạn chỉ do Backend đặt, không nhận từ client.

Để demo giải phóng xe, gọi `POST /api/v1/user/bookings/expire` (alias
`POST /api/bookings/expire`), không cần body. API trả `expired_booking_ids` và
`expired_count`, chuyển booking đang giữ sang `Hết hạn`, ghi `expired_at` và
hoàn xe khi xe vẫn đủ điều kiện. Gọi lặp không tăng lại số xe; không thay đổi
chuyến đang sử dụng hoặc xe bảo trì. Gateway lưu thay đổi vào runtime JSON.

Gateway (`BE/run_all.py`) khởi động worker quét ngay rồi mỗi 5 giây cho booking
`rental`, `parking`, `charging`, `swap` và `battery_swap`. Chỉ booking đang
`Đã xác nhận` có hạn đầy đủ mới được chuyển sang `Hết hạn`; không kết thúc
chuyến đi/phiên dịch vụ đã nhận tài nguyên. Worker tự dừng khi Gateway tắt.
API `/bookings/expire` vẫn dùng được để yêu cầu quét ngay; GET không tự sửa dữ liệu.

Worker và mọi request HTTP User/Operator/Staff dùng cùng một `asyncio.Lock`.
Một lượt quét có thể chờ request đang chạy. Lượt quét chuẩn bị trên bản sao,
ghi JSON nguyên tử rồi mới cập nhật RAM; không có booking hết hạn thì không
ghi file. Lỗi dữ liệu/lỗi lưu được ghi log và thử lại ở lượt sau, không áp dụng
một phần thay đổi vào store thật. Tài nguyên bị khóa bảo trì/điều chuyển không
được tự bật lại khi hết hạn. Booking hết hạn chưa nhận xe không tạo hóa đơn thuê.

Có thể đổi chu kỳ quét bằng biến môi trường khi chạy, đơn vị giây:

```bash
BE_BOOKING_EXPIRY_INTERVAL_SECONDS=2 .venv/bin/python -B BE/run_all.py
```

Giá trị phải dương và hữu hạn; cấu hình sai làm Gateway từ chối khởi động.
Chu kỳ quét khác với thời hạn giữ tài nguyên 10/15 phút. Cơ chế chỉ áp dụng
khi chạy Gateway một tiến trình; chạy riêng `BE/user/main.py` không có worker
này, và chưa hỗ trợ nhiều worker/tiến trình cùng ghi chung runtime JSON.
Booking seed/runtime cũ thiếu `expires_at` không được suy đoán ngày hết hạn
từ chuỗi giờ `hold_until`, nên vẫn giữ nguyên.

## Đặt chỗ gửi xe cá nhân cho demo

Gửi `POST /api/v1/user/bookings` với `plan_type=parking`, `hub_id`,
`personal_plate`. Có thể gửi `parking_slot` (hoặc `resource_id`) như `P11`;
nếu không gửi thì Backend chọn một chỗ còn trống. Response có `parking_slot`,
`resource_id`, `resource_name` và `expires_at` (giữ chỗ 15 phút).

Backend kiểm tra Hub hoạt động, biển số chưa đặt/đang gửi, chỗ chưa bị vé bãi,
booking hoặc điều chuyển giữ. Thành công đặt `is_available=false` và giảm
`available_parking`; hủy hoàn lại chỗ một lần. Endpoint `/bookings/expire`
cũng xử lý booking `parking` mới. Gói ghép `personal` giữ cả chỗ đỗ và cổng
sạc, được mô tả riêng bên dưới.

Staff check-in cùng biển số/Hub sẽ dùng chỗ đã giữ dù request Staff chứa tên
chỗ hiển thị khác; không trừ chỗ lần nữa. Booking hết hạn/Hub ngừng hoạt động
bị từ chối 409. Người dùng demo chỉ có một phiên parking hiện tại; cần kết thúc
phiên cũ trước khi check-in phiên mới. Check-out liên kết booking mới sẽ chuyển
booking sang `Hoàn thành`, xóa phiên đang đỗ và trả chỗ một lần.

Check-in lặp, kể cả vé seed/walk-in cũ, trả lại vé đang mở duy nhất tại đúng
Hub; không tạo vé mới hoặc giảm số chỗ lần hai. Có nhiều vé/booking khớp hoặc
xe đang gửi ở Hub khác trả 409. Chỗ bị báo bảo trì sau khi giữ không được check-in.

Check-out ưu tiên mã vé chính xác; nếu dùng biển số thì chọn vé đang mở duy
nhất, không lấy nhầm lượt gửi cũ trong lịch sử. Không có vé trả 404; nhiều vé
khớp trả 409. Vé liên kết booking phải khớp trạng thái, Hub, biển số, chủ sở
hữu và ô đang chiếm trước khi ghi nhận thu tiền. Lỗi đối chiếu không cập nhật
dở dang vé, booking hoặc số chỗ. Check-out lặp bằng mã vé đã thu tiền trả lại
kết quả cũ; không hoàn chỗ lần nữa, kể cả vé legacy không có booking.

Hủy hoặc check-out không tự mở lại ô đang bảo trì/bị khóa. Xe vẫn có thể ra
bãi và kết thúc lượt gửi, nhưng ô đó không được cộng vào số chỗ khả dụng cho
đến khi trạng thái tài nguyên được xử lý. Vé mới lưu thời điểm check-out ISO
UTC; booking liên kết lưu `completed_at`. Chưa có điều khiển barrier vật lý.

`price` khi đặt là ước tính đơn giá giờ × số giờ dự kiến (mặc định 2).
Chưa tính phí theo thời gian đỗ thực; response thu phí Staff vẫn là mock cũ.
Nhánh Staff walk-in không có booking đã được bảo vệ khỏi tạo/hoàn vé lặp;
việc chọn ô lúc tạo vé mới vẫn theo logic mock cũ, chưa hoàn thiện toàn bộ
kiểm tra đầu vào walk-in hoặc lỗi JSON fallback trong handler Staff.

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

Giữ và xác nhận đổi pin đều kiểm tra lại cờ/trạng thái hoạt động, phiếu bảo
trì khớp mã loại pin (hoặc ID nhóm pin nếu có) tại đúng Hub. Loại pin trùng
trong cùng Hub bị từ chối thay vì chọn nhóm đầu tiên. Số lượng và đơn giá đã
giữ phải là số nguyên hợp lệ trước khi chốt hóa đơn. Giá Hub thay đổi sau
khi đặt không thay đổi đơn giá đã chốt của booking.

Hủy/hết hạn hoàn số pin đầy đã giữ về kho, không sửa cờ khóa/bảo trì của nhóm
pin. Response Hub cho User tính số pin có thể cấp từ nhóm đang hoạt động;
nhóm bị khóa hiển thị 0 pin khả dụng, nhưng số tồn vật lý trong store không
bị xóa. Khi phiếu được xử lý và nhóm đủ điều kiện, số pin đó lại được xét.

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
Không sửa FE; gói ghép `personal` dùng lại các API sạc này sau khi vào bãi.


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

Phiên sạc mới chỉ được kết thúc khi mã phiên lưu trong booking, đơn giá đã
giữ, mốc bắt đầu và quyền `occupied_by` của cổng khớp phiên hiện tại. Mã cổng
trùng, marker chiếm cổng khác hoặc dữ liệu phiên mâu thuẫn bị từ chối trước
khi tạo hóa đơn. Không tự lấy đơn giá cổng hiện tại thay cho snapshot bị thiếu
ở phiên mới. 0 kWh là hợp lệ, tạo hóa đơn 0 đồng và vẫn chặn thanh toán lặp.

Hub bị tạm ngưng/bảo trì trong lúc sạc không cản việc kết thúc và chốt phí
phiên hợp lệ, nhưng cổng không được chuyển `Sẵn sàng` hoặc tăng bộ đếm khả
dụng. Hủy booking đang giữ tại Hub ngừng hoạt động cũng không bật lại cổng.
Các cờ bảo trì có sẵn được giữ nguyên; phục hồi Hub/thiết bị cần xử lý ở luồng
vận hành, không tự mở lại chỉ vì User kết thúc dịch vụ.

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
- Worker tự xử lý booking hết hạn qua lifecycle Gateway, chờ khóa HTTP và được
  hủy khi shutdown; kiểm tra lỗi ghi file không mất tài nguyên và lượt sau thử lại.

Có thể chỉ chạy kiểm thử Gateway bằng:

```bash
.venv/bin/python -B -m unittest discover -s BE/user/tests -p test_gateway_integration.py -v
```

Các kiểm thử này chưa thay thế việc kiểm tra giao diện FE hoặc xác nhận toàn
bộ đặc tả. Chưa triển khai nhiều tài khoản/phân quyền thật,
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

Chỗ đỗ tiếp nhận xe được tính bằng bộ đếm tổng `available_parking` trừ số
chỗ dành cho các lệnh điều chuyển đến Hub đang `PENDING`, `IN_PROGRESS` hoặc
`IN_TRANSIT`. Lệnh cũ chỉ có tổng xe vẫn được tính; lệnh có cả tổng xe và ID
chỗ giữ không bị trừ hai lần. Booking gửi xe đã giảm bộ đếm lúc giữ chỗ nên
không bị trừ thêm một lần trong phép tính này.

`GET /hubs`, `GET /hubs/{id}` và response gợi ý Hub của User hiển thị số chỗ
sau phép trừ trên. Đây là response được tính khi đọc, không sửa bộ đếm chung
trong store hoặc dữ liệu Operator/Staff. Hub đích đã hết chỗ tiếp nhận không
được chọn khi đặt thuê xe; lúc trả vẫn kiểm tra lại vì chỗ trống có thể thay
đổi trong lúc di chuyển. Không giữ trước chỗ trả xe chỉ vì đã chọn Hub đích.

Nếu trả xe bị từ chối, chuyến vẫn hoạt động và chưa lập hóa đơn. Người dùng
có thể chọn một Hub khác đủ điều kiện bằng `hub_id`/`hub_name` trong request
trả xe. API vẫn chặn Hub không tồn tại/ngừng hoạt động và các định danh mâu thuẫn.
Danh sách `slots` trong seed chỉ là mẫu một phần của bãi; luồng thuê xe dùng
bộ đếm tổng, chưa gắn xe đạp điện vào từng ô đỗ vật lý.

## Chuẩn bị chủ sở hữu dữ liệu trước khi mở nhiều tài khoản

Booking, chuyến đi, phiên sạc, hóa đơn trực tuyến và báo cáo User mới có
`user_id` do Backend lấy từ hồ sơ hiện tại. Mã chủ gửi trong request không
được dùng để quyết định chủ sở hữu. Vé gửi xe và phiên parking liên kết
booking giữ cùng chủ của booking; không ghi phiên thuộc chủ khác vào hồ sơ seed.

`get_bookings()` và `get_user_incidents()` là danh sách cá nhân. User không
được nhận/hủy booking, nhận cổng, hoàn tất đổi pin, xem hoặc thanh toán hóa
đơn mang chủ khác, kể cả biết mã bản ghi. Các truy vấn theo mã không thuộc
tài khoản trả 404 để không xác nhận sự tồn tại của bản ghi của người khác.
Hóa đơn trực tuyến cũng phải có chủ khớp với tài khoản đang được Backend dùng.

Operator, kiểm tra tài nguyên và worker hết hạn vẫn dùng `db.bookings` toàn
cục. Worker gọi đường hủy nội bộ cho mọi chủ đã quá hạn, còn API hủy của User
luôn kiểm tra chủ. Lọc danh sách cá nhân không được làm tài nguyên đang được
người khác giữ trở thành khả dụng.

Khi nạp seed/runtime cũ, loader bổ sung chủ tài khoản seed cho booking/báo cáo
thiếu `user_id`, vì dữ liệu cũ được tạo trong bản demo một tài khoản. Chuyến,
phiên và hóa đơn nằm trong booking kế thừa chủ đó. Chủ tường minh đã lưu được
giữ nguyên; quan hệ cha/con mang chủ mâu thuẫn bị từ chối. Vé bãi liên kết
booking kế thừa chủ booking; vé walk-in không rõ chủ không tự gán hàng loạt.
Vé cũ chưa có chủ/liên kết vẫn theo quy tắc một tài khoản đối chiếu biển số;
vé đã có chủ khác không được xem chỉ vì trùng biển số. Việc chuẩn hóa xảy ra
trong RAM, file seed không bị sửa; runtime lưu metadata ở lần cập nhật thành công.

Đây là bước chuẩn bị dữ liệu, **chưa phải xác thực API hoặc hỗ trợ nhiều tài
khoản hoàn chỉnh**. Backend vẫn dùng hồ sơ `db.user` của seed; đăng ký còn là
stub, login còn token mock. Chưa có kiểm tra Bearer token, phiên hết hạn hay
RBAC giữa User/Operator/Staff. Chỉ sau khi bổ sung kho tài khoản, mật khẩu băm
và danh tính xác thực theo request mới có thể coi phần nhiều tài khoản hoàn tất.

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

## Gợi ý khi đặt dịch vụ thất bại

`POST /bookings` và alias versioned vẫn trả HTTP 409 khi không đặt được.
Response giữ `success: false`, `error` và bổ sung `alternatives`, tối đa 3
lựa chọn, mỗi Hub một lựa chọn. Mỗi phần tử có `hub` và `request` có thể gửi
lại tới API đặt chỗ. Không có lựa chọn phù hợp thì danh sách rỗng.

Backend ưu tiên tài nguyên khác tại Hub ban đầu rồi các Hub gần đó theo
khoảng cách đường chim bay. Giữ nguyên loại dịch vụ, biển số, số lượng/loại
pin, thời lượng gửi xe và Hub trả xe đã chọn; thay mã tài nguyên theo Hub
thay thế. Backend kiểm chứng bằng cùng logic đặt chỗ trên bản sao, không
tạo booking, giữ tài nguyên, sinh giao dịch hoặc ghi runtime thật.

Gợi ý là trạng thái tại thời điểm trả lỗi; client cần gửi request mới sau khi
người dùng chọn, và vẫn có thể nhận 409 nếu tài nguyên vừa được người khác
giữ. Nếu Hub đích thuê xe hết chỗ, danh sách có thể rỗng vì Backend không tự
đổi Hub đích. Cần chọn Hub trả xe khác rồi thử lại.

Gói `personal` cũng được gợi ý nhưng chỉ chọn Hub đồng thời giữ được cả hai
tài nguyên, không gợi ý một chỗ đỗ hoặc một cổng sạc đơn lẻ.

## Demo gói ghép gửi xe và sạc `personal`

Gửi `POST /api/v1/user/bookings` với body tối thiểu:

```json
{
  "plan_type": "personal",
  "hub_id": "hub-02",
  "personal_plate": "59-A1 888.88"
}
```

Có thể chọn riêng `parking_slot` và `charging_port`; nếu bỏ trống Backend
chọn tài nguyên trống. Không dùng `resource_id` chung vì gói có hai mã khác
nhau. Cần biển số; chưa nhận lịch theo giờ. Giá và danh sách `services` được
Backend dựng từ tài nguyên thực, không dùng giá ước tính do client gửi.

Backend kiểm tra cả chỗ đỗ và cổng sạc trước khi giữ. Thành công giảm mỗi bộ
đếm một lần và ghi `reserved_by` trên cả hai; thất bại trả 409, không giữ bên
còn lại. Response có `personal_bundle=true`, `parking_slot`, `charging_port`
và đơn giá điện đã chốt. Chặn đặt trùng biển số với các booking gửi xe/sạc
liên quan. Hủy hoặc tự hết hạn 15 phút trước khi vào bãi hoàn cả hai một lần,
không mở lại tài nguyên đang bảo trì.

Thứ tự demo:

1. User đặt gói ghép.
2. Staff gọi API check-in hiện có bằng đúng biển số/Hub, dùng chỗ đã giữ,
   không trừ chỗ đỗ lần hai. Booking chuyển `Đang sử dụng`.
3. User gọi `POST /bookings/{id}/charging/start`, dùng cổng đã giữ. Sau khi
   vào bãi, thời hạn giữ chỗ ban đầu không làm mất quyền bắt đầu sạc.
4. User gọi `POST /services/charging/stop` với mã phiên và kWh mô phỏng.
   Cổng được hoàn nếu đủ điều kiện; booking vẫn `Đang sử dụng` vì xe còn đỗ.
5. Phí điện xem bằng `GET /invoices/current?type=charging&booking_id=...`
   và thanh toán trực tuyến mock như sạc riêng, có thể thanh toán trước khi ra bãi.
6. Staff xác nhận checkout sau khi kết thúc sạc, thu phí gửi xe theo luồng
   tiền mặt hiện có và hoàn chỗ đỗ. Booking chuyển `Hoàn thành`.

`price` của gói là khoản gửi xe ước tính đã chốt, không cộng phí điện; hóa đơn
sạc tính riêng theo kWh. Hóa đơn gửi xe truy vấn `type=parking` với cùng
`booking_id`. Không tự thu điện lần nữa khi ra bãi. Gói đã vào bãi không hủy
bằng API hủy booking; phải kết thúc sạc rồi checkout. Hai dịch vụ riêng vẫn
giữ cách sử dụng cũ. Booking `personal` seed cũ chưa giữ đủ tài nguyên không
được coi là gói ghép hợp lệ để mở cổng sạc.

## Kiểm tra báo cáo sự cố và hóa đơn đã chốt

`POST /incidents` kiểm tra loại và mã tài nguyên tại đúng Hub trước khi tạo
báo cáo cùng phiếu bảo trì. Các loại được hỗ trợ là `Phương tiện`, `Chỗ đỗ`,
`Cổng sạc`, `Pin`, `Trạm pin` và `Cơ sở hạ tầng`. Mã xe, ô đỗ, cổng sạc,
nhóm pin phải thuộc Hub được chọn; cơ sở hạ tầng dùng mã Hub. Xe trong chuyến
đang hoạt động của tài khoản có thể báo về Hub tiếp nhận. Mã được đối chiếu
không phân biệt chữ hoa/thường và lưu theo mã chuẩn trong store.

Không tìm thấy Hub/tài nguyên trả 404; loại tài nguyên không hỗ trợ trả 422.
Chưa có API tải ảnh nên `image_attached` chỉ chấp nhận `false` hoặc bỏ trống;
không coi cờ `true` từ client là bằng chứng đã lưu ảnh.

GET báo cáo đọc trạng thái mới từ phiếu bảo trì liên kết, không sửa bản ghi.
Mã phiếu trùng hoặc quan hệ phiếu/báo cáo mâu thuẫn trả 409. Các báo cáo seed
cũ thiếu metadata liên kết vẫn được đọc theo dữ liệu hiện có.

Thanh toán trực tuyến đối chiếu schema, loại dịch vụ, mã tham chiếu, tổng các
khoản phí và kết quả thuê xe/sạc/đổi pin đã chốt trong booking. Dữ liệu lệch
trả 409 và không tạo giao dịch. Giá Hub hiện tại không thay thế đơn giá đã
lưu. Tra cứu gặp mã hóa đơn trùng cũng trả 409 thay vì chọn ngẫu nhiên.

Chuyến mới có `booking_id` chỉ được trả khi booking vẫn `Đang sử dụng` và
`rental_trip.trip_id` khớp phiên hiện tại. Nếu xe của chuyến mới đã xuất hiện
trong danh sách xe tại một Hub, hoặc xe legacy xuất hiện ở nhiều Hub, trả xe
bị từ chối thay vì tự xóa/chuyển các bản ghi mâu thuẫn. Seed một chuyến cũ
chưa có `booking_id` vẫn nối booking duy nhất theo mã xe như quy tắc tương thích.

## Phân chia handler BE User theo sơ đồ module

`main.py` ghép routes và tạo app Starlette. Các handler HTTP được tách vào
`handlers/`; giữ nguyên URL, phương thức HTTP, request/response và nghiệp vụ.

| Module | Trách nhiệm |
| --- | --- |
| `handlers/auth.py` | Health, đăng nhập/đăng ký mock, hồ sơ, xe cá nhân |
| `handlers/hub.py` | Danh sách, chi tiết và gợi ý Hub |
| `handlers/booking.py` | Liệt kê, tạo, hủy và xử lý hết hạn booking |
| `handlers/service.py` | Trạng thái dịch vụ, nhận/trả xe, bắt đầu/kết thúc sạc, đổi pin |
| `handlers/incident.py` | Tạo và xem báo cáo sự cố |
| `handlers/payment.py` | Tra cứu hóa đơn, thanh toán mock |

`schemas/` tiếp tục kiểm tra dữ liệu. Các module nghiệp vụ như `charging.py`,
`swaps.py`, `payments.py`, `incidents.py` không bị chuyển vào handler: handler
nhận HTTP và gọi các hàm đó. Tên hàm handler vẫn được import ở `main.py` để
giữ cách ghép routes và tương thích với Gateway hiện có.

Handler User đọc `db` qua đầu mối công khai `shared.database`. Các thao tác
ghi (hồ sơ, booking, sử dụng dịch vụ, báo cáo, thanh toán) gọi callback đồng
bộ `change(candidate)` rồi `return persist_change(change)`. Callback chỉ
đổi candidate và chuẩn bị response; không sửa singleton thật hoặc dùng await.

`persist_change()` yêu cầu ghi JSON thành công trước khi áp dụng candidate
vào RAM. Response lỗi HTTP từ callback bị bỏ toàn bộ thay đổi; exception cũng
không áp dụng candidate. Lỗi ghi trả 503 và giữ RAM/file cũ. Callback không
đổi dữ liệu không ghi lại file (ví dụ hết hạn không có kết quả, cập nhật hồ sơ
cùng giá trị). Đăng nhập/đăng ký mock và các GET không ghi dữ liệu.

Middleware Gateway vẫn khóa chung mọi request cùng worker hết hạn. Chỉ
Staff còn dùng nhánh lưu tự động của middleware; User/Operator tự commit ở
handler nên không lưu hai lần. Handler User cũng lưu được khi chạy app User
riêng, nhưng demo toàn hệ thống vẫn chạy `BE/run_all.py` để có khóa chung,
quét hết hạn và các API Operator/Staff.

Kiểm thử trong tiến trình con với runtime tạm kiểm tra cả 11 thao tác ghi
qua app User độc lập (`/api/...`) và Gateway (`/api/v1/user/...`): lỗi ghi
không đổi RAM/file, tại thời điểm `_write` RAM vẫn là trạng thái trước request,
request thành công chỉ ghi đúng một lần. Lỗi nghiệp vụ sau khi sửa candidate
cũng bị bỏ, không tạo giao dịch một phần.

Phần triển khai lưu trữ đã chuyển vào thư mục nội bộ:

```text
BE/shared/
├── database.py              # Đầu mối db, persist_change và lỗi dùng chung
├── persistence/
│   ├── memory_store.py      # Store RAM, nghiệp vụ hiện có, một singleton db
│   ├── json_store.py        # Snapshot, ghi JSON an toàn, áp dụng RAM
│   └── seed_loader.py       # Đọc/kiểm tra seed và runtime JSON
├── memory_store.py          # Giữ tương thích đường import cũ
├── json_store.py            # Giữ tương thích đường import cũ
└── seed_loader.py           # Giữ tương thích đường import cũ
```

Các module tương thích chỉ re-export lớp/hàm từ `persistence`, không tạo
store hoặc singleton riêng. `mock_db.py` và adapter Operator cũng lấy db/lỗi
qua `shared.database`. Seed vẫn là `BE/data/mock_seed.json`; runtime mặc định
vẫn là `BE/data/runtime_db.json`, cấu hình `BE_RUNTIME_PATH` giữ nguyên.

`run_all.py` ghép routes bằng import theo package `BE.user.main`,
`BE.operator.main`, `BE.staff.main`; không nạp main bằng tên giả và không
xóa cache `schemas`. Staff dùng `BE.staff.schemas` để chọn đúng schema khi
chạy Gateway hoặc nạp độc lập; chỉ đổi import/bootstrap, không đổi nghiệp vụ
Staff. Chưa tách các handler Staff ra khỏi `staff/main.py` vì phần đó thuộc
phạm vi nhóm Staff. Operator đã có thư mục handlers riêng.

Kiểm thử import từ thư mục làm việc bên ngoài repository xác nhận cả ba
role dùng chung db, các import cũ trỏ về cùng lớp/hàm mới, đường dẫn JSON
không đổi và module `schemas` không liên quan không bị xóa hoặc thay thế.
