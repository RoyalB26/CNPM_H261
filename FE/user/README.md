# Frontend User Application - Smart E-Mobility Hub (ĐHQG-HCM)

Ứng dụng web di động mô phỏng giao diện người dùng (End-User) theo sát 58 bản vẽ wireframe tại thư mục `PIC-UI-USER/` và tài liệu đặc tả dự án.

## Cấu trúc thư mục (Kiến trúc Modular & Partials)

```text
FE/
├── shared/
│   └── js/
│       ├── config.js               # Cấu hình chung (API endpoints, tọa độ Map, chu kỳ đồng bộ)
│       ├── http.js                 # HTTP Client dùng chung có cache-busting & fallback
│       ├── utils.js                # Tiện ích thao tác DOM & định dạng tiền tệ / phần trăm
│       └── include.js              # HTML Partial Loader (tải động các phần tử [data-include])
└── user/
    ├── index.html                  # Giao diện chính tinh gọn (~60 dòng, nạp partials)
    ├── css/
    │   └── app.css                 # Stylesheet thiết kế hiện đại, layout mobile frame
    ├── partials/                   # Các khối giao diện con được chia nhỏ theo chức năng
    │   ├── layout/                 # Status bar, toast notification, bottom navigation
    │   └── screens/                # Auth, profile, map, booking, services, payment, incidents
    └── js/
        ├── places-data.js          # Dữ liệu địa điểm nội khu ĐHQG-HCM
        ├── state.js                # Reactive Data Store & Quản lý trạng thái phiên làm việc
        ├── api.js                  # Giao tiếp API tới Backend (tự fallback nếu chạy offline)
        ├── app.js                  # Bộ khởi tạo trung tâm & kết hợp các module (Aggregator)
        └── modules/
            ├── router.js           # Điều hướng màn hình (Router), Bottom Bar & Toast
            ├── auth-profile.js     # Xác thực đăng nhập/đăng ký & quản lý hồ sơ cá nhân
            ├── map-hubs.js         # Bản đồ MapLibre GL, lớp GeoJSON, Hub Sheet & tìm kiếm
            ├── booking.js          # Đặt xe, kiểm tra xung đột 409, hủy đặt & lịch sử
            ├── active-services.js  # Theo dõi chuyến đi thực tế, đỗ xe, sạc điện & trả xe
            ├── payment.js          # Xử lý hóa đơn & thanh toán
            └── incidents.js        # Báo cáo sự cố & lịch sử phản ánh
```

## Tính năng nổi bật

1. **Chuẩn thiết kế Wireframe**:
   - Tái hiện chính xác phong cách màu đơn sắc (monochrome/minimalist) sắc nét của bản thiết kế EU-01 đến EU-58.
   - Hỗ trợ khung mô phỏng Smartphone (Mobile Device Preview) trên màn hình máy tính và tương thích cảm ứng đầy đủ trên điện thoại.
2. **Kiến trúc Modular & HTML Partials dễ bảo trì**:
   - `index.html` được tinh gọn tối đa; các màn hình và modal được chia nhỏ vào thư mục `partials/` giúp dễ tìm kiếm và chỉnh sửa.
   - Module `FE/shared/js/include.js` tự động nạp bất đồng bộ toàn bộ các phần tử giao diện con khi khởi động.
   - Tách biệt rõ ràng từng miền nghiệp vụ (`modules/*`), tầng dữ liệu (`state.js`), tầng giao tiếp API (`api.js`) và tầng cấu hình dùng chung (`FE/shared/js/*`).
3. **Đầy đủ 7 nhóm chức năng của End-User**:
   - **Xác thực & Hồ sơ**: Đăng nhập, Đăng ký, Quên mật khẩu, Hồ sơ, Đổi mật khẩu, Phương thức thanh toán.
   - **Bản đồ & Tra cứu Hub**: Bản đồ tương tác Khu đô thị ĐHQG-HCM, tìm kiếm theo khoảng cách, Bottom Sheet thông tin Hub (xe, chỗ đỗ, cổng sạc, tủ pin).
   - **Đặt trước tài nguyên**: Thuê xe dùng chung (kèm kiểm tra chống đặt trùng xe `409 Conflict`), Đặt chỗ đỗ xe cá nhân, Đặt lịch sạc nhanh/tiêu chuẩn, Đặt dịch vụ đổi pin.
   - **Quản lý Đặt chỗ**: Danh sách sắp tới, chi tiết đặt trước, quy trình xác nhận hủy đặt và lịch sử đặt chỗ.
   - **Vận hành & Theo dõi thời gian thực**: Quét QR nhận xe, đồng hồ đếm thời gian chuyến đi thực tế, kiểm tra định vị trả xe tại Hub, bãi đỗ xe cá nhân, phiên sạc pin.
   - **Hóa đơn & Thanh toán**: Hóa đơn tiền thuê, tiền điện sạc, tiền đổi pin qua Ví điện tử/Thẻ ngân hàng và thu phí gửi xe tiền mặt với Bảo vệ tại Hub.
   - **Báo cáo sự cố**: Gửi phản ánh kèm mã thiết bị/quét QR, chuyển tiếp sự cố đến Nhân viên vận hành (Operator) và theo dõi trạng thái xử lý.

## Cách chạy thử

> [!IMPORTANT]
> Do ứng dụng sử dụng cơ chế nạp động HTML Partials (`fetch()`), **bắt buộc phải chạy thông qua máy chủ HTTP** (tránh bị chặn bởi chính sách CORS khi mở bằng `file://`).

Khởi chạy máy chủ HTTP từ thư mục gốc dự án:
```powershell
python -m http.server 3000 --directory FE
```
Mở trình duyệt truy cập: **`http://localhost:3000/user/`** (hoặc mở `http://localhost:3000` để truy cập Cổng điều hướng chung).

## Ra bãi và kết thúc gửi xe

Nút **Hướng dẫn ra bãi** đưa User đến hướng dẫn thanh toán tại quầy bảo vệ.
User không tự đóng vé hoặc giải phóng chỗ đỗ. Staff xem phí và xác nhận
checkout bằng đúng mã vé/biển số; với gói đỗ + sạc cần kết thúc sạc trước.

Khi mở lại **Đang dùng**, FE tải trạng thái từ BE. Staff chưa checkout thì
xe vẫn đang đỗ; BE trả `parking: null` thì FE xóa phiên khỏi cache và giao
diện. Lỗi mạng/phiên đăng nhập hiện thông báo thử lại, không dùng dữ liệu
dự phòng để báo đã hoàn tất hoặc phục hồi một phiên gửi xe cũ.

## Nhận, trả xe thuê và thanh toán

Luồng thuê xe: đặt xe → xác nhận nhận xe → sử dụng → trả xe thành công →
xem hóa đơn đúng chuyến → chọn thanh toán. Nhận xe gọi API `start`, chưa
gọi thanh toán. Cước vẫn tính theo quy tắc BE từ lúc đặt thành công đến khi trả.

FE giữ đầy đủ `trip_id` của chuyến đang chạy. Khi trả xe thành công, truy vấn
`/api/invoices/current?type=rental&trip_id=...` và dùng ID/số tiền của hóa đơn
đó để thanh toán. Chuyến trả xe lỗi vẫn đang hoạt động; không mở hóa đơn.
Trả xe thành công nhưng tải hóa đơn lỗi thì giữ mã chuyến để thử tải lại,
khóa thanh toán, không lấy hóa đơn chuyến cũ thay thế. Mã chuyến vừa trả đang
giữ trong state của trang; reload trang xóa context này, không tự chọn hóa đơn cũ.

Thanh toán xong trở về trang chính, không tự gọi nhận xe. VNPAY vẫn cần cấu
hình Backend và IPN hợp lệ; kiểm thử dưới đây không gọi cổng thanh toán thật.

Có Node.js thì chạy kiểm thử độc lập (HTTP/DOM giả lập, không đổi dữ liệu demo):

```bash
node FE/user/tests/rental-flow.test.cjs
```

### Thanh toán demo

FE gửi `simulate: true` tới API thanh toán. BE đối chiếu chủ hóa đơn, trạng thái dịch vụ và số tiền, sau đó lưu `paid` cùng mã `DEMO-...` trước khi trả thành công. Không trừ tiền thật, không cần cấu hình VNPAY. Request không có cờ này vẫn dùng VNPAY; hóa đơn đã trả hoặc đang chờ VNPAY không được mô phỏng lại. Trang thành công hiển thị mã giao dịch từ BE; lỗi hiển thị trên trang thất bại.
