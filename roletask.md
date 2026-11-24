# Checklist triển khai BE theo thứ tự A → B → C → D

Mốc bắt đầu là commit 90bee7a. Triển khai từng mục, tạo test và chạy test tương ứng trước khi đánh dấu hoàn thành.

## A. Tài khoản và phân quyền
- [x] A1. Lưu đăng ký, băm mật khẩu, kiểm tra email/SĐT trùng, đăng nhập tài khoản mới.
- [x] A2. Session opaque phía server, xác thực Bearer và phân quyền User/Staff/Operator, dữ liệu cá nhân theo phiên.
- [x] A3. Operator kiểm tra mật khẩu → challenge 5 phút → TOTP → session. Giới hạn 5 lần thử, chặn OTP dùng lại.
- [x] Test đầu vào lỗi, thông tin đăng nhập sai, phiên hết hạn, sai vai trò, hai User độc lập, lưu runtime và lỗi lưu.

## B. Định tuyến và lịch sạc
- [ ] B1. Tuyến đường bộ, gợi ý Hub cho xe dùng chung và xe cá nhân. Chốt nhà cung cấp định tuyến.
- [ ] B2. Đặt sạc theo khoảng giờ, chặn trùng, hàng đợi ưu tiên pin thấp, cập nhật khi cổng đổi trạng thái, thông báo người đầu hàng.
- [ ] Kiểm thử tài nguyên, lịch giao nhau, hàng đợi và thay đổi trạng thái cổng.

## C. Vận hành
- [ ] C1. Tạo Hub và quản lý/tạm ngưng từng thiết bị. Khôi phục Hub qua PUT config.
- [ ] C2. Quét tải, chọn quy tắc, chống kích hoạt trùng, ghi tiến độ, cảnh báo Operator khi ngoài kịch bản.
- [ ] C3. What-if A/A′ JSON, chốt snapshot trước chạy, tăng nhu cầu sạc theo Hub, tính tải yêu cầu/phục vụ/vượt năng lực.
- [ ] C3. Ghi yêu cầu trước tính, retry cùng phiên/đầu vào, đổi tham số tạo phiên mới, lưu kết quả và phương án.
- [ ] C3. Bản đầu hiển thị đề xuất. Kịch bản mất công suất triển khai sau ca tăng nhu cầu.
- [ ] C4. Upload/lưu ảnh thật User/Staff và thông báo thay đổi sự cố.
- [ ] C5. BUG-BE-02 truyền đúng outcome/ghi chú, chuyển xưởng khóa đúng thiết bị, cập nhật số khả dụng một lần.

## D. Thanh toán và phí gửi xe
- [ ] D1. Nhóm chọn cổng thanh toán, xác thực webhook, đối chiếu giao dịch/hóa đơn/số tiền, chống ghi nhận lặp.
- [ ] D2. Chốt biểu phí, tính theo mốc vào/ra thực tế, thống nhất xem trước/xác nhận/hóa đơn.

## Các ca kiểm thử Operator
- [ ] TC-O01 — Unit UC10. Load lưới điện và Hub hiện hành, thuật toán tính/tái mô phỏng trả JSON hợp lệ và đúng thiếu hụt tài nguyên.
- [ ] TC-O02 — E2E UC10. Operator đăng nhập và TC-O01 pass, progress bar mượt, Dashboard hiển thị báo cáo đề xuất phân bổ.
- [ ] TC-O03 — E2E UC8. Operator đăng nhập, nguồn có xe sẵn sàng, tạo lệnh thành công và nhân viên điều phối nhận thông báo.
- [ ] TCO03-ERR — Unit UC8. Số xe vượt chỗ đích, báo Hub đích không khả dụng và giữ nguyên tài nguyên/lệnh.
- [ ] TC-O04 — E2E UC9. Operator đăng nhập, tạo phiếu thành công và gửi phân công cho nhân viên bảo trì.
- [ ] TC-O05 — Unit/E2E UC12. Operator đăng nhập, Hub tồn tại, cập nhật sức chứa/trạng thái, báo lưu thành công và màn hình đọc lại đúng.
- [ ] Bốn mục hồi quy đã có xử lý — personal BUG-BE-01, Gateway quét hết hạn, gợi ý khi đặt thất bại, tính cước thuê từ xác nhận đặt đến trả.

## Cách chạy test
Tại thư mục CNPM_H261 chạy lệnh sau.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m unittest discover -s BE/operator/test -v
```

## Thiết lập A1–A3
- Session có hạn 8 giờ, mất hiệu lực khi backend khởi động lại. Tài khoản và TOTP lưu cùng runtime JSON.
- Tài khoản seed User dùng mật khẩu 123456.
- Operator dùng email trong seed, mật khẩu khởi tạo operator123, có thể đặt OPERATOR_PASSWORD trước lần di trú đầu.
- Staff dùng staff_b / staff123, có thể đặt STAFF_PASSWORD trước lần di trú đầu.
- Chạy cục bộ `python BE/operator/setup_totp.py` để lấy URI đăng ký trong Authenticator. URI chứa bí mật TOTP, chỉ người vận hành máy chủ sử dụng.
- Operator login trả challenge_id. FE gửi email, challenge_id và otp_code khi verify-2fa.
- Client gửi Authorization Bearer token trên API có bảo vệ. FE cần nối hợp đồng mới khi ghép giao diện.

## Kết quả kiểm thử A1–A3
- [x] 9 test A1–A3 qua Gateway/ứng dụng chạy riêng, gồm vector TOTP RFC 6238.
- [x] TC-O05 phần API cập nhật công suất/sức chứa/trạng thái và đọc lại runtime.
- [x] TCO03-ERR phần API từ chối khi đích hết chỗ, trạng thái giữ nguyên.
- [ ] TC-O01/02/03/04 đang skip theo phụ thuộc trong test. Các ca UI TC-O05 cũng chờ ghép FE.
- Hợp đồng FE cần cập nhật gồm Bearer token và challenge_id của Operator.
- Thực thi session hiện dành cho một tiến trình backend. Khởi động lại yêu cầu đăng nhập lại.
