# Checklist triển khai BE theo thứ tự A → B → C → D

Mốc bắt đầu là commit 90bee7a. Triển khai từng mục, tạo test và chạy test tương ứng trước khi đánh dấu hoàn thành.

## A. Tài khoản và phân quyền
- [x] A1. Lưu đăng ký, băm mật khẩu, kiểm tra email/SĐT trùng, đăng nhập tài khoản mới.
- [x] A2. Session opaque phía server, xác thực Bearer và phân quyền User/Staff/Operator, dữ liệu cá nhân theo phiên.
- [x] A3. Operator kiểm tra mật khẩu → challenge 5 phút → TOTP → session. Giới hạn 5 lần thử, chặn OTP dùng lại.
- [x] Test đầu vào lỗi, thông tin đăng nhập sai, phiên hết hạn, sai vai trò, hai User độc lập, lưu runtime và lỗi lưu.

## B. Định tuyến và lịch sạc
- [x] B1. Tuyến đường bộ, gợi ý Hub cho xe dùng chung và xe cá nhân. Chốt nhà cung cấp định tuyến.
- [x] B2. Đặt sạc theo khoảng giờ, chặn trùng, hàng đợi ưu tiên pin thấp, cập nhật khi cổng đổi trạng thái, thông báo người đầu hàng.
- [x] Kiểm thử tài nguyên, lịch giao nhau, hàng đợi và thay đổi trạng thái cổng.

## C. Vận hành
- [x] C1. Tạo Hub và quản lý/tạm ngưng từng thiết bị. Khôi phục Hub qua PUT config.
- [x] C2. Quét tải, chọn quy tắc, chống kích hoạt trùng, ghi tiến độ, cảnh báo Operator khi ngoài kịch bản.
- [x] C3. What-if A/A′ JSON, chốt snapshot trước chạy, tăng nhu cầu sạc theo Hub, tính tải yêu cầu/phục vụ/vượt năng lực.
- [x] C3. Ghi yêu cầu trước tính, retry cùng phiên/đầu vào, đổi tham số tạo phiên mới, lưu kết quả và phương án.
- [x] C3. Bản đầu hiển thị đề xuất. Kịch bản mất công suất triển khai sau ca tăng nhu cầu.
- [x] C4. Upload/lưu ảnh thật User/Staff và thông báo thay đổi sự cố.
- [x] C5. BUG-BE-02 truyền đúng outcome/ghi chú, chuyển xưởng khóa đúng thiết bị, cập nhật số khả dụng một lần.

## D. Thanh toán và phí gửi xe
- [ ] D1. Nhóm chọn cổng thanh toán, xác thực webhook, đối chiếu giao dịch/hóa đơn/số tiền, chống ghi nhận lặp.
- [ ] D2. Chốt biểu phí, tính theo mốc vào/ra thực tế, thống nhất xem trước/xác nhận/hóa đơn.

## Các ca kiểm thử Operator
- [x] TC-O01 — Unit UC10. Load lưới điện và Hub hiện hành, thuật toán tính/tái mô phỏng trả JSON hợp lệ và đúng thiếu hụt tài nguyên.
- [ ] TC-O02 — E2E UC10. Operator đăng nhập và TC-O01 pass, progress bar mượt, Dashboard hiển thị báo cáo đề xuất phân bổ.
- [ ] TC-O03 — E2E UC8. Operator đăng nhập, nguồn có xe sẵn sàng, tạo lệnh thành công và nhân viên điều phối nhận thông báo.
- [x] TCO03-ERR — Unit UC8. Số xe vượt chỗ đích, báo Hub đích không khả dụng và giữ nguyên tài nguyên/lệnh.
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
- [x] TC-O01 có test thuật toán. TC-O03/04 có test API/thông báo. TC-O02/03/04 phần UI đang skip, UI TC-O05 chờ ghép FE.
- Hợp đồng FE cần cập nhật gồm Bearer token và challenge_id của Operator.
- Thực thi session hiện dành cho một tiến trình backend. Khởi động lại yêu cầu đăng nhập lại.

## Hợp đồng B–C

Phạm vi hoàn thành của B–C là nghiệp vụ BE và test API. Nhóm pin trong dữ liệu cũ được quản lý theo battery_type, dữ liệu chưa định danh từng viên pin.

### B1 — OSRM

Chọn OSRM làm nguồn tuyến đường bộ. OSRM_BASE_URL mặc định https://router.project-osrm.org, OSRM_PROFILE mặc định driving. Muốn tuyến dành riêng cho xe đạp cần máy chủ OSRM có dữ liệu/profile cycling phù hợp rồi cấu hình biến môi trường. Backend xét tối đa 3 Hub gần mỗi đầu, xếp hạng tuyến ứng viên theo thời gian OSRM. Dịch vụ không trả được tuyến thì báo 503.

POST /api/v1/user/hubs/suggest-route hoặc alias /api/hubs/suggest-route nhận tọa độ cũ, vehicle_type là bike/personal, service là parking/charging. Trả geometry GeoJSON, routing_provider, routing_profile, distance_km, estimated_minutes và Hub phù hợp. Khoảng cách gồm đường từ điểm đi qua các Hub đến điểm đến. Test sử dụng OSRM mock, kết nối dịch vụ thực chưa kiểm chứng tại môi trường này.

### B2 — Lịch sạc

- POST/GET /api/v1/user/charging/schedules.
- Body gồm hub_id, port_id tùy chọn, plate_number, starts_at, ends_at ISO 8601 có múi giờ, battery_pct 0–100, join_queue tùy chọn.
- Lịch tối đa 12 giờ, trong tương lai. Khoảng [starts_at, ends_at) cho phép hai lịch liền nhau. Cùng xe/tài khoản không có lịch giao nhau.
- POST /api/v1/user/charging/schedules/{id}/start hoặc /cancel. Start chỉ hợp lệ trong giờ đã giữ, tạo booking/phiên sạc qua nghiệp vụ hiện có. Trả cổng dùng API stop charging hiện có.
- Khi cổng còn đang phục vụ một phiên khác, lịch kế tiếp giữ trong hàng đợi đến khi cổng được hoàn, kể cả quá giờ dự kiến. Backend giữ an toàn tài nguyên.
- Trạng thái RESERVED/WAITING/IN_SERVICE/COMPLETED/CANCELLED/MISSED. Pin thấp ưu tiên trước, cùng mức pin theo thứ tự đăng ký.
- GET /api/v1/operator/charging/schedules xem lịch toàn hệ thống.

### C1 — Hub/thiết bị

- POST /api/v1/operator/hubs nhận hub_code, name, address, lat, lng, parking_capacity, charger_capacity, max_power_kw và ngưỡng tải tùy chọn.
- GET/POST /api/v1/operator/hubs/{id}/devices. Body tạo thiết bị gồm kind port/slot/bike/battery, id, name và thông số loại tương ứng. battery dùng available_count và swap_fee.
- PUT /api/v1/operator/hubs/{id}/devices/{kind}/{device_id} với enabled true/false. Từ chối thiết bị đang bị giữ/đang phục vụ.
- Khôi phục Hub qua PUT config với status Hoạt động. Cổng riêng đã tạm ngưng cần kích hoạt riêng.
- Hub mới có cấu hình sức chứa, tài nguyên khả dụng tăng khi thêm thiết bị thật vào store.

### C2 — Tải cao và tác vụ nền

Gateway quét lịch sạc/tải cao mỗi 5 giây, cùng khóa với HTTP và quét booking hết hạn. Ứng dụng chạy riêng có API quét thủ công.

- PUT /api/v1/operator/hubs/{id}/load nhận power_demand_kw để nhập mẫu tải. Gắn nguồn operator_input.
- POST /api/v1/operator/automation/scan, GET /api/v1/operator/automation/runs.
- PUT /api/v1/operator/automation/runs/{id} nhận action pause/resume/resolve và rule_id khi chọn quy tắc khác.
- Tải là giá trị lớn hơn giữa tỷ lệ sức chứa bãi đang không khả dụng và tỷ lệ nhu cầu công suất/max_power_kw.
- Quy tắc save-rule bổ sung hub_ids, threshold_pct, actions. actions hỗ trợ notify với message hoặc relocation với payload đúng contract tạo lệnh.
- Chuỗi hướng dẫn văn bản được giữ để Operator xem. Thực thi tự động dùng actions có cấu trúc.
- Mỗi đợt vượt ngưỡng chỉ tạo một phiên, kể cả reload. Tải giảm dưới ngưỡng kết thúc đợt. Thất bại lưu tiến độ và chờ Operator can thiệp, khi resume bỏ qua hành động đã xong.
- Emergency halt chặn phát sinh hành động tự động mới.

### C3 — What-if

- POST /api/v1/operator/simulation/snapshots nhận source_type và hub_snapshots cho A′, trả snapshot_id. Có thể chụp nguồn trước khi cấu hình kịch bản.
- POST validate/run nhận snapshot_id và config, gồm target_hub_ids, demand_increase_pct, duration_minutes, start_time. Request cũ không gửi snapshot_id vẫn lấy nguồn một lần khi run.
- Tải nền A ước tính 50% công suất cổng sẵn sàng. A′ có available_power_kw tùy chọn.
- Yêu cầu = nền × (1 + mức tăng/100). Năng lực = min(công suất cổng hoạt động, giới hạn Hub). Phục vụ = min(yêu cầu, năng lực). Phần thiếu = yêu cầu − phục vụ.
- Tải tăng giữ đều trong (0, duration], điểm 0 và duration+10 phút dùng tải nền. hub_results chứa chuỗi số liệu từng Hub. Giữ các field biểu đồ cũ để FE chuyển tiếp.
- Ghi RUNNING trước tính. Lỗi có FAILED và simulation_id. POST /simulation/{id}/retry dùng snapshot/config cũ, tăng attempts. Phiên RUNNING bị gián đoạn cũng khôi phục được bằng retry.
- Đổi tham số gọi run tạo ID mới. POST /simulation/{id}/save với operation_plan lưu kết quả kèm phương án.
- GET /simulation/history/{id} xem lại đầy đủ. Đề xuất dùng để Operator xem xét, công suất mất triển khai sau kịch bản tăng nhu cầu.

### C4 — Ảnh/thông báo

- POST /api/v1/user/incidents/{id}/photos hoặc /api/v1/staff/maintenance/{code}/photos, gửi multipart trường file hoặc body nhị phân.
- Nhận JPEG/PNG tối đa 2 MiB, kiểm tra giải mã ảnh. Bytes được lưu base64 trong runtime JSON cùng metadata để commit/rollback đồng bộ với phiếu.
- GET /api/v1/{role}/attachments/{attachment_id}, vai trò là user/staff/operator. Caller dùng đường dẫn tương ứng vai trò của mình. Kiểm tra người sở hữu hoặc người được giao phiếu, Operator có quyền xem.
- GET /api/v1/{role}/notifications. Thông báo lưu bền, chống trùng theo sự kiện, client đọc qua API.
- POST /api/v1/operator/maintenance/tickets tạo phiếu, tùy chọn assigned_staff_id để phân công và thông báo ngay.

### C5 — Chuyển xưởng

Staff resolve nhận task_code, outcome FIXED_ON_SITE/TRANSFER_TO_WORKSHOP (cũng nhận giá trị enum tiếng Việt cũ), technical_notes. Ảnh tải lên đúng phiếu trước nếu muốn đính kèm. Kiểm tra phiếu được giao đúng Staff. Thiết bị được đối chiếu đúng Hub, loại và mã. Gửi lặp cùng kết quả giữ nguyên tài nguyên.

FE Staff đã nối lựa chọn onsite/workshop và technical_notes, hiển thị message từ BE. StaffApi.login lưu staff_access_token trong sessionStorage để các thao tác đã nối gửi Bearer token. Giao diện đăng nhập và các màn FE còn lại cần được nhóm FE ghép hợp đồng A–C.

## Kết quả kiểm thử B–C

- [x] Bộ chạy tổng cộng 37 test, 34 pass và 3 skip cho phần E2E trình duyệt.
- [x] B1 test tuyến OSRM và phản hồi khi nhà cung cấp lỗi, cho xe dùng chung/xe cá nhân.
- [x] B2 test lịch giao nhau/liền nhau, ưu tiên pin thấp, thông báo, đổi trạng thái cổng, nhận/trả cổng và kiểm tra quyền.
- [x] C1 test tạo Hub/thiết bị, trùng mã, bộ đếm khả dụng, nhóm pin, khôi phục Hub.
- [x] C2 test tải cao, chống trùng qua reload, tiến độ một phần, can thiệp và tạo lệnh điều chuyển thật.
- [x] C3/TC-O01 test phép tính, A′, snapshot cố định, lỗi timeout, retry và lưu phương án/lịch sử.
- [x] C4 test bytes ảnh thực, upload multipart/nhị phân, lưu/đọc lại runtime và quyền đọc.
- [x] C5 test sửa tại chỗ/chuyển xưởng, đúng thiết bị, gửi lặp an toàn và request sai.
- [x] node --check trên FE/staff/js/api.js và FE/staff/js/modules/maintenance-role.js.
- [ ] OSRM thực và UI E2E chờ kiểm chứng khi ghép FE.

Tài khoản Staff từ seed được bổ sung khi di trú accounts. Nhân viên STF-01 dùng staff_01, mật khẩu khởi tạo STAFF_PASSWORD hoặc staff123. STF-02 giữ username staff_b. Hồ sơ và thông báo được lấy đúng ID nhân viên đăng nhập.
