# BÁO CÁO TỔNG HỢP LỖI & KHOẢNG TRỐNG KIỂM THỬ (BUG REPORT LOG)

- **Dự án:** Smart E-Mobility Hub – Hệ thống điều phối phương tiện điện trong Khu đô thị ĐHQG-HCM (CO3001)
- **Nhóm thực hiện:** Nhóm 6 – HK261 (Hồ Quang Minh – 2412047, Trần Quỳnh Anh – 2533002)
- **GVHD:** Trần Thị Ngọc Trâm
- **Ngày cập nhật:** 25/11/2026 (sau khi đồng bộ toàn bộ nâng cấp Auth/2FA, VNPAY D1, Parking Pricing D2, thiết bị/bảo trì C1–C5 và chạy hồi quy toàn bộ bộ kiểm thử)
- **Kết quả thực thi tham chiếu:** `pytest tests -v -s -q` — **56 test cases**: **51 PASSED** (34 Unit + 17 E2E), **5 XFAILED (`strict=True`)**, **0 FAILED**, **0 XPASSED** (188.53s / 0:03:08)

---

## I. TỔNG QUAN & TIÊU CHÍ PHÂN LOẠI

Đối chiếu giữa Đặc tả bài toán, Đặc tả kiểm thử (BTL3 – Chương 5) và mã nguồn hiện hành (`BE/`, `FE/`):

- **5 lỗi đã được khắc phục (`Resolved`)** và xác minh vượt qua kiểm thử hồi quy (`PASSED`), bao gồm toàn bộ các lỗi chức năng & tích hợp cốt lõi cùng lỗ hổng phân quyền/2FA: `BUG-FE-01`, `BUG-FE-05`, `BUG-BE-01`, `BUG-BE-02`, `BUG-FE-03`.
- **4 vấn đề còn tồn đọng (`Confirmed`)** đều thuộc nhóm **Khoảng trống phi chức năng (NFR Nhóm 1 Gaps)**, được phản ánh chính xác qua **5 test `XFAIL (strict=True)`**: `BUG-FE-04` (NFR06), `BUG-FE-02` (NFR04-A & NFR04-B), `BUG-BE-03` (NFR07 User), `BUG-BE-04` (NFR07 Operator).

### Định nghĩa mức độ nghiêm trọng (Severity)

| Mức độ | Tiêu chí đánh giá |
| :--- | :--- |
| **Critical** | Gây sai lệch nghiêm trọng dữ liệu nghiệp vụ hoặc làm mất hoàn toàn khả năng thực hiện luồng cốt lõi. |
| **High** | Làm hỏng một nghiệp vụ quan trọng hoặc bỏ qua kiểm soát an toàn/truy cập cốt lõi, nhưng hệ thống vẫn hoạt động được các luồng khác. |
| **Medium** | Thiếu cơ chế bảo vệ hoặc đồng bộ dữ liệu theo ngưỡng NFR, có ảnh hưởng nhưng có phương án tạm thời. |
| **Low** | Thiếu thông tin truy vết/kiểm toán (Audit Log), ít ảnh hưởng trực tiếp đến luồng nghiệp vụ chính. |

### Định nghĩa trạng thái xác minh (Verification Status)

| Trạng thái | Ý nghĩa |
| :--- | :--- |
| **Confirmed** | Đã xác minh trực tiếp trong mã nguồn và tái hiện bằng test case đúng hợp đồng (`XFAIL strict=True`). |
| **Resolved** | Đã được sửa trong mã nguồn và vượt qua kiểm thử hồi quy (`PASSED`). |

### Bảng tổng hợp theo dõi lỗi

| Mã lỗi | Phân loại | Severity | Verification Status | Số test liên kết | Trạng thái test |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `BUG-FE-01` | Frontend Bug (NFR03) | Critical | **Resolved** | 2 | `PASSED` |
| `BUG-FE-05` | Integration Bug (TC-O03 / UC8) | High | **Resolved** | 1 | `PASSED` |
| `BUG-BE-01` | Functional Bug (TC-U03 / UC3) | High | **Resolved** | 1 | `PASSED` |
| `BUG-BE-02` | Functional & Integration Bug (TC-S02 / UC9) | High | **Resolved** | 2 | `PASSED` |
| `BUG-FE-03` | Security / NFR Gap (NFR05 – RBAC & 2FA) | High | **Resolved** | 2 | `PASSED` |
| `BUG-FE-04` | NFR Gap (NFR06 – Emergency Halt) | High | **Confirmed** | 1 | `XFAIL` |
| `BUG-FE-02` | NFR Gap (NFR04 – Stale Data & Sync <= 1s) | Medium | **Confirmed** | 2 | `XFAIL` |
| `BUG-BE-03` | Audit / NFR Gap (NFR07 – User Payment Log) | Low | **Confirmed** | 1 | `XFAIL` |
| `BUG-BE-04` | Audit / NFR Gap (NFR07 – Operator Audit Log) | Low | **Confirmed** | 1 | `XFAIL` |

---

## II. CÁC KHOẢNG TRỐNG PHI CHỨC NĂNG CÒN TỒN ĐỌNG — NFR NHÓM 1 GAPS (4 GAPS / 5 XFAIL)

### 1. `BUG-FE-04` — Lệnh "Dừng khẩn cấp" chưa khóa UI End-User và chưa chặn đặt chỗ mới trong `< 2s` (NFR06)

- **Phân loại:** Confirmed NFR Gap (An toàn vận hành – NFR06)
- **Severity:** High
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/operator/handlers/dashboard.py::emergency_halt()`, `BE/shared/persistence/memory_store.py::create_booking()`, `FE/operator/js/api.js::emergencyHalt()`, `FE/user/`
- **Preconditions:** Mở song song 2 browser context: Operator Dashboard đã qua 2FA và End-User đã đăng nhập.
- **Steps to reproduce:**
  1. Ghi nhận `t0 = time.perf_counter()` và kích hoạt `OperatorApp.openEmergencyModal(); OperatorApp.confirmEmergency()`.
  2. Kiểm tra giao diện End-User hiển thị cảnh báo khóa `"Tạm dừng khẩn cấp"` trong `2000ms`.
  3. Gửi thử `POST /api/bookings` (kèm Bearer token End-User) đặt xe `XE-031` tại `hub-01`.
- **Expected result:** Giao diện End-User bị khóa đặt mới trong `< 2000ms`; Backend từ chối yêu cầu `POST /api/bookings` (`403`/`423`/`503`) và không phát sinh booking mới.
- **Actual result:** Giao diện Operator đổi `#kpiAlerts` thành `"DỪNG TOÀN BỘ"`, nhưng giao diện End-User không nhận được tín hiệu khóa sau `2000ms` và Backend vẫn cho phép tạo booking mới (`200 OK`).
- **Evidence:** Playwright timeout `2000ms` khi chờ thông báo `"Tạm dừng khẩn cấp"` trên `user_page`; đồng thời payload FE gửi lên `/dashboard/emergency-halt` vẫn bị Backend từ chối `422`.
- **Root cause:**
  1. `BE/operator/handlers/dashboard.py::emergency_halt()` đã bật cờ `candidate.operator_mock["emergency_halt"] = True` (chặn vòng quét tự động trong `shared/automation.py`), nhưng `BE/shared/persistence/memory_store.py::create_booking()` chưa kiểm tra cờ này để từ chối đặt chỗ mới từ End-User.
  2. `FE/operator/js/api.js::emergencyHalt()` vẫn gửi `{halt_reason, operator_id, confirmation_code}`, lệch tên trường so với `EmergencyHaltRequest` (`{reason, operator_id, confirmation_token}`), khiến Backend trả `422` và Frontend rơi vào nhánh fallback trả `{success: true}` giả.
  3. `FE/user/` chưa có cơ chế lắng nghe trạng thái dừng khẩn cấp (SSE/WebSocket hoặc polling `< 1s`) để khóa thao tác đặt chỗ trên giao diện.
- **Hướng khắc phục:** Chuẩn hóa payload FE gửi đúng `{reason, operator_id, confirmation_token}`; kiểm tra `self.operator_mock.get("emergency_halt")` trong `create_booking()` để chặn đặt mới (trả `503`); đẩy tín hiệu khóa về `FE/user/` trong `< 2s`.
- **Related test:** `tests/e2e/test_operator_dashboard.py::test_nfr06_emergency_halt_locks_user_ui_and_blocks_booking_under_2s` (`XFAIL`, `strict=True`).

---

### 2. `BUG-FE-02` — Chưa từ chối đặt chỗ khi dữ liệu cảm biến cũ `> 30s` và chưa đồng bộ KPI Operator trong `<= 1s` (NFR04)

- **Phân loại:** Confirmed NFR Gap (Nhất quán dữ liệu – NFR04-A & NFR04-B)
- **Severity:** Medium
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/data/mock_seed.json`, `BE/shared/persistence/memory_store.py`, `FE/operator/js/operator.js`, `FE/shared/js/config.js`
- **Preconditions:** Hệ thống chạy trên Gateway dùng chung với đầy đủ xác thực Bearer token; kiểm chứng tách làm 2 kịch bản độc lập (NFR04-A và NFR04-B).
- **Steps to reproduce:**
  1. **NFR04-A:** Gán `hub["last_updated_at"]` của `hub-01` lùi 31 giây so với thời điểm hiện tại (`> 30s`), sau đó gửi `POST /api/bookings` (kèm token End-User) đặt xe `XE-031`.
  2. **NFR04-B:** Mở sẵn Operator Dashboard (đã qua 2FA và tải xong KPI thật `33`). Mở phiên End-User gửi `POST /api/bookings` đặt xe `XE-031` tại `hub-01`. Theo dõi `#kpiAvailableBikes` trong `1000ms` (không tải lại trang).
- **Expected result:** (NFR04-A) Hệ thống từ chối đặt chỗ (`409`/`422`/`503`) khi dữ liệu cảm biến cũ `> 30s`; (NFR04-B) `#kpiAvailableBikes` tự động giảm từ `33` xuống `32` trong `<= 1000ms`.
- **Actual result:** (NFR04-A) Hệ thống vẫn xác nhận đặt chỗ bình thường (`200 OK`); (NFR04-B) `#kpiAvailableBikes` giữ nguyên `33` sau `1000ms`.
- **Evidence:** NFR04-A trả `HTTP 200` dù `last_updated_at` cũ 31 giây; NFR04-B báo `AssertionError: Locator expected not to have text '33' (Actual value: 33)` sau timeout `1000ms`.
- **Root cause:** Dữ liệu Hub trong `mock_seed.json` và `memory_store.py::create_booking()` chưa kiểm tra độ tươi `last_updated_at` (`<= 30s`); trên FE, `FE/operator/js/operator.js` chỉ gọi `loadKpis()` lúc `loadDashboardData()`, còn `autoSyncTimer` chạy chu kỳ `8000ms` (`POLLING.operatorSyncMs`) và chỉ làm mới `loadRelocations()`, chưa có WebSocket/SSE hoặc polling KPI `<= 1s`.
- **Hướng khắc phục:** Gắn và xác thực `last_updated_at` (`now - last_updated_at <= 30s`) trước khi giữ tài nguyên; bổ sung kênh đẩy thời gian thực (WebSocket/SSE) hoặc short-polling KPI `<= 1000ms` trên Operator Dashboard.
- **Related tests:**
  - `tests/e2e/test_user_flow.py::test_nfr04_a_rejects_booking_when_hub_sensor_data_stale_over_30s` (`XFAIL`, `strict=True`)
  - `tests/e2e/test_user_flow.py::test_nfr04_b_cross_actor_sync_updates_operator_kpi_under_1s` (`XFAIL`, `strict=True`)

---

### 3. `BUG-BE-03` — Giao dịch thanh toán hóa đơn của User chưa ghi nhận vào Audit Log (NFR07)

- **Phân loại:** Confirmed Audit / NFR Gap (Kiểm toán – NFR07)
- **Severity:** Low
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/user/payments.py::pay_invoice()`, `BE/user/payment_gateway.py::create_payment()`, `BE/user/payment_gateway.py::vnpay_ipn()`
- **Preconditions:** End-User đã đăng nhập; chuyến đi seed `TRIP-8821` đã được trả tại `hub-04` để sinh hóa đơn `rental_invoice` trạng thái `unpaid`.
- **Steps to reproduce:**
  1. Lấy hóa đơn từ `GET /api/invoices/current?type=rental&trip_id=TRIP-8821`.
  2. Gửi `POST /api/invoices/pay` với `{"invoice_id": invoice_id, "method": "wallet"}` (trả `200 OK`, `status="pending"`) và gửi callback IPN VNPAY hợp lệ tới `GET /api/v1/payments/vnpay/ipn` (`RspCode="00"`).
  3. Gọi `GET /api/v1/operator/dashboard/telemetry` (kèm token Operator) để kiểm tra nhật ký kiểm toán.
- **Expected result:** Xuất hiện bản ghi Audit Log cho giao dịch thanh toán chứa đủ 4 trường không rỗng: `actor`, `timestamp`, `action`, `result`.
- **Actual result:** Thanh toán hoàn tất (`status="paid"`), nhưng danh sách nhật ký telemetry không có bản ghi thanh toán nào.
- **Evidence:** `payment_logs` lọc từ `GET /api/v1/operator/dashboard/telemetry` có độ dài bằng `0` sau khi giao dịch VNPAY đã được IPN chốt `paid`.
- **Root cause:** `BE/user/payment_gateway.py::vnpay_ipn()` mới ghi thông báo cho User vào `operator_mock["notifications"]` qua `notify(...)`, chưa ghi bản ghi kiểm toán chuẩn 4 trường vào `db.telemetry_events` hoặc kho Audit Log chung.
- **Hướng khắc phục:** Ghi bổ sung bản ghi kiểm toán đủ 4 trường (`actor`, `timestamp`, `action`, `result`) vào store dùng chung sau mỗi giao dịch thanh toán (cả thành công lẫn thất bại).
- **Related test:** `tests/e2e/test_user_flow.py::test_nfr07_user_payment_creates_complete_audit_log_entry` (`XFAIL`, `strict=True`).

---

### 4. `BUG-BE-04` — Nhật ký can thiệp của Operator thiếu 3 trường chuẩn Audit Log (`actor`, `action`, `result`) (NFR07)

- **Phân loại:** Confirmed Audit / NFR Gap (Kiểm toán – NFR07)
- **Severity:** Low
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/operator/handlers/dashboard.py::emergency_halt()`, `BE/operator/handlers/dashboard.py::get_telemetry_feed()`, `BE/operator/schemas/dashboard.py::TelemetryEvent`
- **Preconditions:** Operator Dashboard đã đăng nhập 2FA và kết nối Backend.
- **Steps to reproduce:**
  1. Kích hoạt thao tác can thiệp dừng khẩn cấp.
  2. Gọi `GET /api/v1/operator/dashboard/telemetry` (kèm token Operator) và kiểm tra bản ghi sự kiện dừng khẩn cấp mới nhất.
- **Expected result:** Bản ghi sự kiện chứa đầy đủ 4 trường kiểm toán không rỗng: `actor`, `timestamp`, `action`, `result`.
- **Actual result:** Bản ghi trả về theo schema `TelemetryEvent` chỉ gồm `id`, `hub_id`, `hub_name`, `level`, `title`, `message`, `created_at_relative`, `timestamp_iso` — thiếu 3 trường `actor`, `action`, `result` và chưa thống nhất trường `timestamp`.
- **Evidence:** Kiểm tra JSON trả về từ `GET /api/v1/operator/dashboard/telemetry` không tồn tại khóa `actor`, `action`, `result`, `timestamp`.
- **Root cause:** `emergency_halt()` không lưu `operator_id` hay kết quả thực thi vào bản ghi trong `db.telemetry_events`, đồng thời schema `TelemetryEvent` chưa định nghĩa các trường chuẩn Audit Log.
- **Hướng khắc phục:** Mở rộng cấu trúc bản ghi sự kiện và schema `TelemetryEvent` (hoặc bổ sung endpoint `/audit-logs` riêng) để lưu và trả về đầy đủ 4 trường `actor`, `timestamp`, `action`, `result`.
- **Related test:** `tests/e2e/test_operator_dashboard.py::test_nfr07_operator_intervention_writes_complete_audit_log` (`XFAIL`, `strict=True`).

---

## III. CÁC LỖI ĐÃ KHẮC PHỤC & XÁC MINH HỒI QUY (5 RESOLVED BUGS)

### 5. `BUG-BE-01` [Resolved] — Gói ghép chỗ đỗ & sạc (`plan_type="personal"`) đã trừ chỗ đỗ và khóa cổng sạc nguyên tử (TC-U03 / UC3)

- **Mức độ trước khi vá:** High
- **Tình trạng hiện tại:** **Resolved** — `BE/shared/persistence/memory_store.py::create_booking()` đã xử lý nguyên tử cho `plan_type == "personal"` (kiểm tra đồng thời qua `choose_parking_slot` và `select_charging_port`, đặt `personal_bundle=True`, trừ `available_parking` và `available_chargers`, khóa `is_available=False` cho cả hai tài nguyên).
- **Kết quả kiểm thử hồi quy:**
  - `tests/unit/test_user_booking_service.py::test_tc_u03_combo_parking_and_charging_updates_mock_db` — **PASSED**

### 6. `BUG-BE-02` [Resolved] — Chuyển thiết bị về xưởng (`"Cần chuyển về xưởng"`) đã khóa xe và giảm `available_bikes` đồng bộ 3 tầng (TC-S02 / UC9)

- **Mức độ trước khi vá:** High
- **Tình trạng hiện tại:** **Resolved** — Đã sửa đồng bộ cả BE và FE: `BE/staff/main.py::resolve_maintenance()` truyền đầy đủ `outcome` (`FIXED_ON_SITE` / `TRANSFER_TO_WORKSHOP`) xuống `BE/shared/devices.py::resolve_ticket()` để đặt `workshop=True`, `status="Chuyển xưởng"` và giảm `available_bikes` của đúng Hub; `FE/staff/js/modules/maintenance-role.js` đã đọc đúng radio `maintOutcome` và gửi trường `technical_notes`.
- **Kết quả kiểm thử hồi quy:**
  - `tests/unit/test_staff_maintenance.py::test_tc_s02_send_to_workshop_locks_bike_and_decrements_available_bikes` — **PASSED**
  - `tests/e2e/test_staff_flow.py::test_tc_s02_maintenance_technician_resolve_task_ui` — **PASSED**

### 7. `BUG-FE-03` [Resolved] — Đã áp đặt kiểm soát truy cập RBAC và xác thực 2FA (TOTP) cho phân hệ Operator (NFR05)

- **Mức độ trước khi vá:** High
- **Tình trạng hiện tại:** **Resolved** — `BE/shared/authentication.py::AuthenticationMiddleware` đã kiểm tra Bearer token, thời hạn phiên và phân quyền vai trò (`401` khi thiếu token, `403` khi gọi chéo vai trò); `BE/operator/handlers/auth.py` áp đặt luồng mật khẩu + `challenge_id` + TOTP RFC 6238 chống replay; `FE/operator/js/operator.js` bắt buộc hiển thị màn hình `#operatorLoginView.show` và chỉ tải KPI sau khi xác thực 2FA thành công.
- **Kết quả kiểm thử hồi quy:**
  - `tests/unit/test_auth.py::test_nfr05_operator_api_enforces_rbac_and_2fa` — **PASSED**
  - `tests/e2e/test_user_flow.py::test_nfr05_student_role_blocked_from_operator_and_2fa_enforced` — **PASSED**

### 8. `BUG-FE-01` [Resolved] — Frontend không còn tự tạo booking giả `'Đã xác nhận'` khi Backend trả `409 Conflict` (NFR03)

- **Mức độ trước khi vá:** Critical
- **Tình trạng hiện tại:** **Resolved** — `FE/user/js/api.js::createBooking()` ném ngoại lệ `Error` khi Backend trả lỗi thay vì rơi xuống nhánh fallback mock `'Đã xác nhận'`.
- **Kết quả kiểm thử hồi quy:**
  - `tests/unit/test_user_booking_service.py::test_nfr03_a_backend_concurrent_double_booking_allows_only_one_success` — **PASSED**
  - `tests/e2e/test_user_flow.py::test_nfr03_b_frontend_rejects_409_conflict_without_fake_confirmation` — **PASSED**

### 9. `BUG-FE-05` [Resolved] — Khắc phục lỗi `TypeError: list.map is not a function` và lệch payload khi tạo lệnh điều phối (TC-O03 / UC8)

- **Mức độ trước khi vá:** High
- **Tình trạng hiện tại:** **Resolved** — `FE/operator/js/modules/relocation.js` đã tách đúng mảng từ `raw.items` và gửi payload đúng schema `RelocationCommandCreate` tới `POST /api/v1/operator/relocation/commands`.
- **Kết quả kiểm thử hồi quy:**
  - `tests/e2e/test_operator_dashboard.py::test_tc_o03_create_relocation_command_via_dashboard_ui` — **PASSED**

---

## IV. GHI CHÚ BỔ SUNG KHI KIỂM THỬ GIAO DIỆN (MINOR FE OBSERVATIONS)

Trong quá trình chạy E2E trên bản mã nguồn mới, ghi nhận thêm 1 điểm lệch dữ liệu mặc định ở giao diện Bảo vệ (`FE/staff/`):

- **Phạm vi:** `FE/staff/js/modules/guard-role.js::simulatePlateScan()` và `confirmVehicleCheckin()`.
- **Hiện trạng:** Hai hàm này vẫn gửi cứng `hub_name: "Hub KTX Khu A"` và `parking_slot: "Ô số 018"` không tồn tại trong `BE/data/mock_seed.json` (chỉ có `hub-01` đến `hub-05` với các ô `P01..P41`), khiến request `POST /api/v1/staff/parking/checkin` trả `404` và `StaffApi.parkingCheckin()` rơi xuống nhánh fallback mock.
- **Khuyến nghị:** Cập nhật danh sách chọn Hub/ô đỗ mặc định trên màn hình `FE/staff/partials/screens/guard/checkin.html` và `guard-role.js` sang dữ liệu thật từ `mock_seed.json` (ví dụ `"Hub Đại học Bách khoa"` / `"P11"`).

---

## V. LỘ TRÌNH ƯU TIÊN XỬ LÝ TIẾP THEO

1. **Ưu tiên 1 — An toàn vận hành (NFR06):**
   - Vá `BUG-FE-04`: sửa payload `FE/operator/js/api.js::emergencyHalt()` theo đúng `EmergencyHaltRequest`, chặn `create_booking()` khi `operator_mock["emergency_halt"] == True`, và đẩy tín hiệu khóa giao diện sang `FE/user/` trong `< 2s`.
2. **Ưu tiên 2 — Đồng bộ thời gian thực & Độ tươi dữ liệu (NFR04):**
   - Vá `BUG-FE-02`: thêm kiểm tra `last_updated_at <= 30s` khi đặt chỗ và bổ sung SSE/WebSocket hoặc short-polling KPI `<= 1s` trên Operator Dashboard.
3. **Ưu tiên 3 — Nhật ký kiểm toán Audit Log (NFR07) & Dọn dữ liệu tĩnh FE Staff:**
   - Vá `BUG-BE-03` và `BUG-BE-04`: chuẩn hóa bản ghi kiểm toán đủ 4 trường (`actor`, `timestamp`, `action`, `result`) cho giao dịch thanh toán và các thao tác can thiệp của Operator.
   - Đồng bộ dữ liệu Hub/ô đỗ mặc định trong `FE/staff/js/modules/guard-role.js` với `mock_seed.json`.
