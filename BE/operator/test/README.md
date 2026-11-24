# Test Operator

Chạy từ CNPM_H261 bằng python -m unittest discover -s BE/operator/test -v.

Test API gọi trực tiếp Gateway ASGI bằng runtime tạm. Event loop trong test không mở socket để chạy được ở môi trường hạn chế mạng. Chưa đo hiệu năng HTTP mạng.

## Các ca nghiệm thu UI

| Mã | Tiền điều kiện và thao tác | Kết quả phải kiểm tra |
| --- | --- | --- |
| TC-O01 | Load lưới/Hub. Chạy cùng snapshot với +20%, +80%, sau đó chạy lại bộ tham số đầu | JSON hợp lệ, tính đúng thiếu hụt theo công thức đã chốt, đổi input làm đổi số liệu, chạy lại cho cùng kết quả |
| TC-O02 | Operator đăng nhập, TC-O01 pass. Chọn nguồn và kịch bản, bấm Chạy | Progress bar cập nhật theo tiến trình, kết quả/đề xuất xuất hiện Dashboard, báo lỗi rõ khi chạy thất bại |
| TC-O03 | Operator đăng nhập. Hub nguồn có xe sẵn sàng, Hub đích đủ chỗ. Chọn nhân viên, tạo lệnh | Báo thành công, lệnh đọc lại đúng, nhân viên nhận đúng một thông báo |
| TCO03-ERR | Operator đăng nhập. Đặt số xe lớn hơn chỗ trống đích, gửi tạo lệnh | Báo Hub đích không khả dụng, lệnh/xe/chỗ trống giữ nguyên |
| TC-O04 | Operator đăng nhập. Chọn thiết bị, mô tả lỗi và nhân viên bảo trì, tạo phiếu | Báo thành công, đọc lại đúng phiếu/phân công, nhân viên nhận thông báo |
| TC-O05 | Operator đăng nhập. Mở Hub tồn tại, sửa sức chứa/trạng thái, lưu và tải lại trang | Báo lưu thành công, màn hình phản ánh đúng dữ liệu đã lưu. Dữ liệu lỗi bị từ chối |

TC-O01–TC-O04 có phần chờ được đánh dấu skip trong bộ chạy. TC-O05 API readback và TCO03-ERR có test tự động. Toàn bộ ca UI cần chạy qua trình duyệt khi ghép FE.
