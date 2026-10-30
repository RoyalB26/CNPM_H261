# Frontend User Application - Smart E-Mobility Hub (ĐHQG-HCM)

Ứng dụng web di động mô phỏng giao diện người dùng (End-User) theo sát 58 bản vẽ wireframe tại thư mục `PIC-UI-USER/` và tài liệu đặc tả dự án.

## Cấu trúc thư mục

```
FE/user/
├── index.html           # File giao diện Single Page Application (chứa đầy đủ các luồng)
├── css/
│   └── app.css          # Toàn bộ stylesheet thiết kế hiện đại, typography, layout mobile frame
├── js/
│   ├── state.js         # Reactive Data Store & Quản lý trạng thái phiên làm việc
│   ├── api.js           # Giao tiếp API tới Mock Backend (tự fallback nếu chạy standalone)
│   └── app.js           # Bộ điều hướng màn hình (Router), xử lý tương tác người dùng
└── assets/              # Tài nguyên hình ảnh, icon
```

## Tính năng nổi bật

1. **Chuẩn thiết kế Wireframe**:
   - Tái hiện chính xác phong cách màu đơn sắc (monochrome/minimalist) sắc nét của bản thiết kế EU-01 đến EU-58.
   - Hỗ trợ khung mô phỏng Smartphone (Mobile Device Preview) trên màn hình máy tính và tương thích cảm ứng đầy đủ trên điện thoại.
2. **Bộ chọn màn hình nhanh (Quick Screen Switcher)**:
   - Một menu dropdown nổi ở góc trên bên trái cho phép giảng viên / người đánh giá có thể nhảy ngay lập tức tới bất kỳ màn hình nào trong số 58 bản vẽ giao diện để kiểm tra.
3. **Đầy đủ 7 nhóm chức năng của End-User**:
   - **Xác thực & Hồ sơ**: Đăng nhập, Đăng ký, Quên mật khẩu, Hồ sơ, Đổi mật khẩu, Phương thức thanh toán.
   - **Bản đồ & Tra cứu Hub**: Bản đồ tương tác Khu đô thị ĐHQG-HCM, tìm kiếm theo khoảng cách, Bottom Sheet thông tin Hub (xe, chỗ đỗ, cổng sạc, tủ pin).
   - **Đặt trước tài nguyên**: Thuê xe dùng chung, Đặt chỗ đỗ xe cá nhân, Đặt lịch sạc nhanh/tiêu chuẩn, Đặt dịch vụ đổi pin.
   - **Quản lý Đặt chỗ**: Danh sách sắp tới, chi tiết đặt trước, quy trình xác nhận hủy đặt.
   - **Vận hành & Theo dõi thời gian thực**: Quét QR nhận xe, đồng hồ đếm thời gian chuyến đi thực tế, kiểm tra định vị trả xe tại Hub, bãi đỗ xe cá nhân, phiên sạc pin.
   - **Hóa đơn & Thanh toán**: Hóa đơn tiền thuê, tiền điện sạc, tiền đổi pin qua Ví điện tử/Thẻ ngân hàng và thu phí gửi xe tiền mặt với Bảo vệ tại Hub.
   - **Báo cáo sự cố**: Gửi phản ánh kèm mã thiết bị/quét QR, chuyển tiếp sự cố đến Nhân viên vận hành (Operator) và theo dõi trạng thái xử lý.

## Cách chạy thử

Chỉ cần mở trực tiếp file `FE/user/index.html` bằng bất kỳ trình duyệt web nào (Chrome, Edge, Firefox, Safari) hoặc chạy qua Live Server:

```bash
# Hoặc dùng python http server đơn giản:
cd FE/user
python -m http.server 3000
```
Truy cập tại: `http://localhost:3000`
