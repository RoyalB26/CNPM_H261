# BÁO CÁO TỔNG HỢP LỖI & KHOẢNG TRỐNG KIỂM THỬ (BUG REPORT LOG)

- **Dự án:** Smart E-Mobility Hub – Hệ thống điều phối phương tiện điện trong Khu đô thị ĐHQG-HCM (CO3001)
- **Nhóm thực hiện:** Nhóm 6 – HK261 (Hồ Quang Minh – 2412047, Trần Quỳnh Anh – 2533002)
- **GVHD:** Trần Thị Ngọc Trâm
- **Ngày cập nhật:** 23/11/2026 (sau khi đồng bộ nhánh `main` mới và chạy hồi quy toàn bộ bộ kiểm thử)
- **Kết quả thực thi tham chiếu:** `pytest tests -v -s` — **56 test cases**: **47 PASSED**, **9 XFAILED (`strict=True`)**, **0 FAILED**, **0 XPASSED** (61.01s)

---

## I. TỔNG QUAN & TIÊU CHÍ PHÂN LOẠI

Đối chiếu giữa Đặc tả bài toán, Đặc tả kiểm thử (BTL3 – Chương 5) và mã nguồn hiện hành (`BE/`, `FE/`):

- **2 lỗi cũ đã được khắc phục (`Resolved`)** trên nhánh `main` mới và đã vượt qua kiểm thử hồi quy (`PASSED`): `BUG-FE-01`, `BUG-FE-05`.
- **7 vấn đề còn tồn đọng (`Confirmed`)** được phản ánh qua **9 test `XFAIL (strict=True)`**, gồm:
  - **2 Lỗi chức năng & tích hợp (Functional / Integration Bugs):** `BUG-BE-01`, `BUG-BE-02`.
  - **5 Khoảng trống phi chức năng (NFR Nhóm 1 Gaps — 7 test `XFAIL`):** `BUG-FE-04` (NFR06), `BUG-FE-02` (NFR04-A & NFR04-B), `BUG-FE-03` (NFR05 FE & BE), `BUG-BE-03` (NFR07 User), `BUG-BE-04` (NFR07 Operator).

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
| **Resolved** | Đã được sửa trên nhánh `main` và vượt qua kiểm thử hồi quy (`PASSED`). |

### Bảng tổng hợp theo dõi lỗi

| Mã lỗi | Phân loại | Severity | Verification Status | Số test liên kết | Trạng thái test |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `BUG-FE-01` | Frontend Bug (NFR03) | Critical | **Resolved** | 2 | `PASSED` |
| `BUG-FE-05` | Integration Bug (TC-O03 / UC8) | High | **Resolved** | 1 | `PASSED` |
| `BUG-BE-01` | Functional Bug (TC-U03 / UC3) | High | **Confirmed** | 1 | `XFAIL` |
| `BUG-BE-02` | Functional & Integration Bug (TC-S02 / UC9) | High | **Confirmed** | 1 | `XFAIL` |
| `BUG-FE-04` | NFR Gap (NFR06 – Emergency Halt) | High | **Confirmed** | 1 | `XFAIL` |
| `BUG-FE-03` | Security / NFR Gap (NFR05 – RBAC & 2FA) | High | **Confirmed** | 2 | `XFAIL` |
| `BUG-FE-02` | NFR Gap (NFR04 – Stale Data & Sync <= 1s) | Medium | **Confirmed** | 2 | `XFAIL` |
| `BUG-BE-03` | Audit / NFR Gap (NFR07 – User Payment Log) | Low | **Confirmed** | 1 | `XFAIL` |
| `BUG-BE-04` | Audit / NFR Gap (NFR07 – Operator Audit Log) | Low | **Confirmed** | 1 | `XFAIL` |

---

## II. CÁC LỖI CHỨC NĂNG & TÍCH HỢP CÒN TỒN ĐỌNG (2 OPEN BUGS)

### 1. `BUG-BE-01` — Đặt gói ghép chỗ đỗ & sạc (`plan_type="personal"`) chưa trừ chỗ đỗ và chưa khóa cổng sạc

- **Phân loại:** Confirmed Functional Bug (TC-U03 / UC3)
- **Severity:** High
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/shared/memory_store.py::MockDatabaseStore.create_booking()`
- **Preconditions:** Store đã được khôi phục về dữ liệu seed (`mock_seed.json`); `hub-01` (`Hub Ga Metro ĐHQG`) ở trạng thái `ACTIVE`, `available_parking = 8`, danh sách `hub["ports"]` có cổng `S03` với `is_available = True`.
- **Steps to reproduce:**
  1. Gửi `POST /api/v1/user/bookings` với payload:
     `{"plan_type": "personal", "hub_id": "hub-01", "personal_plate": "59-X1 123.45", "parking_slot": "P01", "charging_port": "S03", "duration_hours": 2}`.
  2. Đọc lại đối tượng `hub-01` trong `db.hubs`.
- **Expected result:** `hub["available_parking"]` giảm đi 1 (còn `7`) và phần tử `port_s03 = next(p for p in hub["ports"] if p["id"] == "S03")` chuyển sang `is_available = False`.
- **Actual result:** API trả về `200 OK` và chèn booking vào `db.bookings`, nhưng `hub["available_parking"]` giữ nguyên `8` và `port_s03["is_available"]` vẫn là `True`.
- **Evidence:** Kiểm tra trực tiếp trạng thái `db.get_hub("hub-01")` sau request trong Unit test thất bại ở `assert hub_after["available_parking"] == parking_before - 1`; tài liệu `BE/user/README.md` cũng xác nhận gói ghép `personal` chưa được nâng cấp thành đặt gửi xe và sạc đồng thời.
- **Root cause:** `BE/shared/memory_store.py::create_booking()` đã xử lý tách lẻ cho `plan_type == "parking"` (qua `choose_parking_slot`) và `plan_type == "charging"` (qua `select_charging_port`), nhưng chưa xử lý giao dịch đa tài nguyên cho `plan_type == "personal"` nên rơi vào nhánh `else:` chỉ ghi bản ghi booking.
- **Hướng khắc phục:** Bổ sung nhánh xử lý nguyên tử (atomic) cho `plan_type == "personal"`: kiểm tra đồng thời chỗ đỗ và cổng sạc trước khi giữ chỗ; nếu một trong hai không khả dụng thì trả `409 Conflict` và không thay đổi tài nguyên nào.
- **Related test:** `tests/unit/test_user_booking_service.py::test_tc_u03_combo_parking_and_charging_updates_mock_db` (`XFAIL`, `strict=True`).

---

### 2. `BUG-BE-02` — Kỹ thuật viên chọn `"Cần chuyển về xưởng"` không khóa thiết bị và không giảm số xe sẵn sàng

- **Phân loại:** Confirmed Functional & Integration Bug (TC-S02 / UC9)
- **Severity:** High
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/staff/main.py::resolve_maintenance()`, `BE/shared/memory_store.py::resolve_maintenance()`, `FE/staff/js/modules/maintenance-role.js::submitMaintResult()`
- **Preconditions:** Store ở trạng thái seed; phiếu `TICK-801` thuộc `hub-03` (`Hub KTX Khu B`) đang ở trạng thái `ASSIGNED`.
- **Steps to reproduce:**
  1. Gửi `POST /api/v1/staff/maintenance/resolve` với `{"task_code": "TICK-801", "outcome": "Cần chuyển về xưởng", "technical_notes": "Cần chuyển về xưởng"}`.
  2. Kiểm tra trạng thái thiết bị và `available_bikes` của `hub-03` trong `db.hubs`.
- **Expected result:** Khi `outcome == "Cần chuyển về xưởng"`, thiết bị bị khóa trên store chung và `available_bikes` của Hub giảm đi 1 (theo đặc tả TC-S02).
- **Actual result:** API trả `200 OK`, phiếu chuyển trạng thái `"RESOLVED"`, nhưng không khóa thiết bị và `available_bikes` của Hub giữ nguyên.
- **Evidence:** Sau khi gọi `POST /api/v1/staff/maintenance/resolve`, `find_hub_in_db(db, "hub-03")["available_bikes"]` bằng nguyên giá trị `bikes_before` (`12 == 12`, không giảm xuống `11`).
- **Root cause:** Tồn tại đồng thời ở 3 tầng:
  1. `BE/staff/main.py::resolve_maintenance()` gọi `db.resolve_maintenance(req.task_code, req.technical_notes)` nhưng bỏ qua không truyền `req.outcome`.
  2. `BE/shared/memory_store.py::resolve_maintenance()` chưa có nhánh xử lý `ResolutionOutcome.TRANSFER_TO_WORKSHOP` để khóa xe và giảm `available_bikes` (chỉ có nhánh khôi phục trụ sạc `S02`).
  3. `FE/staff/js/modules/maintenance-role.js::submitMaintResult()` đang hardcode `outcome: "FIXED_ON_SITE"` và gửi sai tên trường `technician_notes` thay vì `technical_notes`; đồng thời dữ liệu seed dùng `TICK-801..803` chưa đồng nhất với mã tĩnh `MT-102` / `BK-EB-018` trên giao diện.
- **Hướng khắc phục:** Truyền `req.outcome` xuống `db.resolve_maintenance()` để khóa thiết bị và trừ `available_bikes` khi chuyển xưởng; sửa FE đọc đúng giá trị radio `maintOutcome` đang chọn và gửi đúng key `technical_notes`.
- **Related test:** `tests/unit/test_staff_maintenance.py::test_tc_s02_send_to_workshop_locks_bike_and_decrements_available_bikes` (`XFAIL`, `strict=True`).

---

## III. CÁC KHOẢNG TRỐNG PHI CHỨC NĂNG — NFR NHÓM 1 GAPS (5 GAPS / 7 XFAIL)

### 3. `BUG-FE-04` — Lệnh "Dừng khẩn cấp" chưa khóa UI End-User và chưa chặn đặt chỗ mới trong `< 2s` (NFR06)

- **Phân loại:** Confirmed NFR Gap (An toàn vận hành – NFR06)
- **Severity:** High
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/operator/handlers/dashboard.py::emergency_halt()`, `BE/shared/memory_store.py`, `FE/operator/js/api.js::emergencyHalt()`, `FE/user/`
- **Preconditions:** Mở song song 2 browser context: Operator Dashboard và End-User đã đăng nhập.
- **Steps to reproduce:**
  1. Ghi nhận `t0 = time.perf_counter()` và kích hoạt `OperatorApp.openEmergencyModal(); OperatorApp.confirmEmergency()`.
  2. Kiểm tra giao diện End-User hiển thị cảnh báo khóa trong `2000ms`.
  3. Gửi thử `POST /api/bookings` đặt xe `XE-031` tại `hub-01`.
- **Expected result:** Giao diện End-User bị khóa đặt mới trong `< 2000ms`; Backend từ chối yêu cầu `POST /api/bookings` (`403`/`423`/`503`) và không phát sinh booking mới.
- **Actual result:** Giao diện Operator đổi `#kpiAlerts` thành `"DỪNG TOÀN BỘ"`, nhưng giao diện End-User không có tín hiệu khóa sau `2000ms` và Backend vẫn cho phép tạo booking mới (`200 OK`).
- **Evidence:** Playwright timeout `2000ms` khi chờ trạng thái `"Tạm dừng khẩn cấp"` trên `user_page`; đồng thời payload FE gửi lên `/dashboard/emergency-halt` bị Backend từ chối `422`.
- **Root cause:**
  1. `BE/operator/handlers/dashboard.py::emergency_halt()` chỉ chèn sự kiện `EMERGENCY_HALT` vào `db.telemetry_events`, chưa đặt cờ `system_halted` toàn cục trên store để chặn `create_booking()`.
  2. `FE/operator/js/api.js::emergencyHalt()` gửi `{halt_reason, operator_id, confirmation_code}`, lệch tên trường so với `EmergencyHaltRequest` (`{reason, operator_id, confirmation_token}`), khiến Backend trả `422` và Frontend rơi vào nhánh fallback trả `{success: true}` giả.
  3. `FE/user/` chưa có cơ chế nhận trạng thái dừng khẩn cấp để khóa thao tác đặt chỗ.
- **Hướng khắc phục:** Chuẩn hóa payload FE gửi đúng `{reason, operator_id, confirmation_token}`; bổ sung cờ `system_halted` trong `MockDatabaseStore` chặn `POST /api/bookings` (trả `503`); đẩy tín hiệu khóa về `FE/user/` qua SSE/WebSocket hoặc polling `< 1s`.
- **Related test:** `tests/e2e/test_operator_dashboard.py::test_nfr06_emergency_halt_locks_user_ui_and_blocks_booking_under_2s` (`XFAIL`, `strict=True`).

---

### 4. `BUG-FE-03` — Chưa áp đặt kiểm soát truy cập RBAC và xác thực 2FA thực tế cho phân hệ Operator (NFR05)

- **Phân loại:** Confirmed Security / NFR Gap (Bảo mật phân quyền & 2FA – NFR05)
- **Severity:** High *(đánh giá theo chuẩn Broken Access Control; hiện ở phạm vi Prototype cục bộ chưa có auth middleware)*
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/operator/handlers/*.py`, `FE/operator/partials/layout/login-2fa.html`, `FE/operator/js/operator.js`, `FE/operator/js/modules/overview.js`
- **Preconditions:** Tài khoản End-User (Sinh viên) đã đăng nhập; hoặc client gọi trực tiếp API Operator không kèm token Operator/2FA.
- **Steps to reproduce:**
  1. (E2E) Đăng nhập vai trò End-User, sau đó điều hướng trực tiếp sang `http://127.0.0.1:3000/operator/`, chờ nạp xong toàn bộ `[data-include]`.
  2. (Unit) Gọi trực tiếp `GET /api/v1/operator/dashboard/kpis` và `PUT /api/v1/operator/hubs/hub-01/config` không có header xác thực Operator/2FA.
- **Expected result:** Trang `/operator/` từ chối phiên Sinh viên hoặc khóa sau màn hình 2FA (không hiển thị `#kpiTotalHubs`); API Operator trả `401 Unauthorized` hoặc `403 Forbidden`.
- **Actual result:** `#kpiTotalHubs` hiển thị trực tiếp trên trình duyệt; mọi API Operator trả `200 OK` không yêu cầu token hay xác thực 2FA.
- **Evidence:** `page.locator("#kpiTotalHubs").is_visible()` trả `True` trong phiên Sinh viên; `TestClient` gọi `GET /api/v1/operator/dashboard/kpis` không kèm token trả `HTTP 200`.
- **Root cause:** `#operatorLoginView` không có class `show` mặc định; `OperatorApp.init()` tự tải toàn bộ KPI khi vừa mở trang; `completeLogin()` chỉ ẩn overlay mà không gọi `/api/v1/operator/auth/verify-2fa`; các route trong `BE/operator/handlers/` chưa có middleware kiểm tra JWT, vai trò và cờ 2FA.
- **Hướng khắc phục:** Bổ sung Auth/RBAC middleware cho nhóm route `/api/v1/operator/*` xác thực token đã qua bước `verify-2fa`; trên FE mặc định bật `#operatorLoginView.show` và chỉ gọi `loadKpis()` sau khi xác thực 2FA thành công.
- **Related tests:**
  - `tests/e2e/test_user_flow.py::test_nfr05_student_role_blocked_from_operator_and_2fa_enforced` (`XFAIL`, `strict=True`)
  - `tests/unit/test_auth.py::test_nfr05_operator_api_enforces_rbac_and_2fa` (`XFAIL`, `strict=True`)

---

### 5. `BUG-FE-02` — Chưa từ chối đặt chỗ khi dữ liệu cảm biến cũ `> 30s` và chưa đồng bộ KPI Operator trong `≤ 1s` (NFR04)

- **Phân loại:** Confirmed NFR Gap (Nhất quán dữ liệu – NFR04-A & NFR04-B)
- **Severity:** Medium
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/data/mock_seed.json`, `BE/shared/memory_store.py`, `FE/operator/js/operator.js`, `FE/shared/js/config.js`
- **Preconditions:** Hệ thống đang chạy trên Gateway dùng chung; kiểm chứng tách làm 2 kịch bản độc lập (NFR04-A và NFR04-B).
- **Steps to reproduce:**
  1. **NFR04-A:** Cài đặt đồng hồ ảo / mô phỏng Hub ngừng cập nhật quá 30 giây (`> 30s`), sau đó gửi yêu cầu đặt xe.
  2. **NFR04-B:** Mở sẵn Operator Dashboard và chờ `#kpiAvailableBikes` cập nhật từ placeholder `120` về giá trị thật `33`. Mở phiên End-User đặt xe `XE-031` tại `hub-01` qua `POST /api/bookings`. Theo dõi `#kpiAvailableBikes` trong `1000ms` (không tải lại trang).
- **Expected result:** (NFR04-A) Hệ thống từ chối đặt chỗ khi dữ liệu trạng thái cũ `> 30s`; (NFR04-B) `#kpiAvailableBikes` tự động giảm từ `33` xuống `32` trong `≤ 1000ms`.
- **Actual result:** (NFR04-A) Hệ thống vẫn xác nhận đặt chỗ bình thường; (NFR04-B) `#kpiAvailableBikes` giữ nguyên `33` sau `1000ms`.
- **Evidence:** Playwright báo `AssertionError: Locator expected not to have text '33' (Actual value: 33)` sau timeout `1000ms` dù `POST /api/bookings` đã trả `200 OK` và giảm `available_bikes` trong `db`.
- **Root cause:** Dữ liệu Hub trong `mock_seed.json`/`memory_store.py` chưa có trường `last_updated_at` để kiểm tra ngưỡng tươi `30s`; `FE/operator/js/operator.js` chỉ gọi `loadKpis()` một lần trong `init()`, còn `autoSyncTimer` có chu kỳ `8000ms` (`POLLING.operatorSyncMs`) và chỉ làm mới `loadRelocations()`, chưa có WebSocket/SSE hoặc short-polling KPI `≤ 1s`.
- **Hướng khắc phục:** Gắn `last_updated_at` cho dữ liệu Hub và kiểm tra điều kiện `now - last_updated_at <= 30s` trước khi đặt chỗ; bổ sung kênh đẩy thời gian thực (WebSocket/SSE) hoặc polling KPI `≤ 1000ms` trên Operator Dashboard.
- **Related tests:**
  - `tests/e2e/test_user_flow.py::test_nfr04_a_rejects_booking_when_hub_sensor_data_stale_over_30s` (`XFAIL`, `strict=True`)
  - `tests/e2e/test_user_flow.py::test_nfr04_b_cross_actor_sync_updates_operator_kpi_under_1s` (`XFAIL`, `strict=True`)

---

### 6. `BUG-BE-03` — Giao dịch thanh toán hóa đơn của User chưa ghi nhận vào Audit Log (NFR07)

- **Phân loại:** Confirmed Audit / NFR Gap (Kiểm toán – NFR07)
- **Severity:** Low
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/user/payments.py::pay_invoice()`, `BE/user/main.py::api_pay_invoice()`
- **Preconditions:** Chuyến đi seed `TRIP-8821` đã được trả tại `hub-04` để sinh hóa đơn `rental_invoice` trạng thái `unpaid`.
- **Steps to reproduce:**
  1. Lấy `invoice_id` thật từ `GET /api/invoices/current?type=rental&trip_id=TRIP-8821`.
  2. Gửi `POST /api/invoices/pay` với `{"invoice_id": invoice_id, "method": "wallet"}` (trả `200 OK`).
  3. Gọi `GET /api/v1/operator/dashboard/telemetry` để kiểm tra nhật ký kiểm toán.
- **Expected result:** Xuất hiện bản ghi Audit Log cho giao dịch thanh toán chứa đủ 4 trường không rỗng: `actor`, `timestamp`, `action`, `result`.
- **Actual result:** Thanh toán thành công (`status="paid"`), nhưng danh sách nhật ký không có bất kỳ bản ghi thanh toán nào.
- **Evidence:** `payment_logs` lọc từ `GET /api/v1/operator/dashboard/telemetry` có độ dài bằng `0` sau giao dịch `POST /api/invoices/pay` trả `200 OK`.
- **Root cause:** `BE/user/payments.py::pay_invoice()` mới cập nhật trạng thái hóa đơn và trả `PaymentProcessResult`, chưa ghi nhận sự kiện kiểm toán vào `db.telemetry_events` hoặc kho Audit Log chung.
- **Hướng khắc phục:** Ghi bổ sung bản ghi kiểm toán đủ 4 trường (`actor`, `timestamp`, `action`, `result`) vào store dùng chung sau mỗi lần xử lý thanh toán (cả thành công lẫn thất bại).
- **Related test:** `tests/e2e/test_user_flow.py::test_nfr07_user_payment_creates_complete_audit_log_entry` (`XFAIL`, `strict=True`).

---

### 7. `BUG-BE-04` — Nhật ký can thiệp của Operator thiếu 3 trường chuẩn Audit Log (`actor`, `action`, `result`) (NFR07)

- **Phân loại:** Confirmed Audit / NFR Gap (Kiểm toán – NFR07)
- **Severity:** Low
- **Verification Status:** Confirmed
- **Phạm vi mã nguồn:** `BE/operator/handlers/dashboard.py::emergency_halt()`, `BE/operator/handlers/dashboard.py::get_telemetry_feed()`, `BE/operator/schemas/dashboard.py::TelemetryEvent`
- **Preconditions:** Operator Dashboard đã sẵn sàng kết nối Backend.
- **Steps to reproduce:**
  1. Kích hoạt thao tác can thiệp dừng khẩn cấp.
  2. Gọi `GET /api/v1/operator/dashboard/telemetry` và kiểm tra bản ghi mới nhất.
- **Expected result:** Bản ghi sự kiện chứa đầy đủ 4 trường kiểm toán khác rỗng: `actor`, `timestamp`, `action`, `result`.
- **Actual result:** Bản ghi trả về chỉ gồm `id`, `hub_id`, `hub_name`, `level`, `title`, `message`, `created_at_relative`, `timestamp_iso` — thiếu 3 trường `actor`, `action`, `result` và chưa thống nhất tên trường `timestamp`.
- **Evidence:** Kiểm tra JSON trả về từ `GET /api/v1/operator/dashboard/telemetry` không tồn tại khóa `actor`, `action`, `result` và `timestamp`.
- **Root cause:** `emergency_halt()` không lưu `operator_id` hay kết quả thực thi vào bản ghi trong `db.telemetry_events`, đồng thời schema `TelemetryEvent` chưa định nghĩa các trường chuẩn Audit Log.
- **Hướng khắc phục:** Mở rộng cấu trúc bản ghi sự kiện và schema `TelemetryEvent` (hoặc tạo endpoint `/audit-logs` riêng) để lưu và trả về đầy đủ 4 trường `actor`, `timestamp`, `action`, `result`.
- **Related test:** `tests/e2e/test_operator_dashboard.py::test_nfr07_operator_intervention_writes_complete_audit_log` (`XFAIL`, `strict=True`).

---

## IV. CÁC LỖI ĐÃ KHẮC PHỤC & XÁC MINH HỒI QUY (2 RESOLVED BUGS)

### 8. `BUG-FE-01` [Resolved] — Frontend không còn tự tạo booking giả `'Đã xác nhận'` khi Backend trả `409 Conflict` (NFR03)

- **Mức độ trước khi vá:** Critical
- **Tình trạng hiện tại:** **Resolved** — Đã sửa trong `FE/user/js/api.js::createBooking()` (khi `isBackendAvailable` là `true` và `!res.ok`, hàm ném ngoại lệ `Error` thay vì rơi xuống nhánh fallback mock `'Đã xác nhận'`).
- **Kết quả kiểm thử hồi quy:**
  - `tests/unit/test_user_booking_service.py::test_nfr03_a_backend_concurrent_double_booking_allows_only_one_success` — **PASSED**
  - `tests/e2e/test_user_flow.py::test_nfr03_b_frontend_rejects_409_conflict_without_fake_confirmation` — **PASSED**

### 9. `BUG-FE-05` [Resolved] — Khắc phục lỗi `TypeError: list.map is not a function` và lệch payload khi tạo lệnh điều phối (TC-O03 / UC8)

- **Mức độ trước khi vá:** High
- **Tình trạng hiện tại:** **Resolved** — Đã sửa trong `FE/operator/js/modules/relocation.js`: `loadRelocations()` đã tách mảng từ `raw.items`, và `submitRelocation()` đã gửi đúng schema `RelocationCommandCreate` (`{source_hub_id, target_hub_id, bike_count, assigned_staff_id, priority, notes}`) tới `POST /api/v1/operator/relocation/commands`.
- **Kết quả kiểm thử hồi quy:**
  - `tests/e2e/test_operator_dashboard.py::test_tc_o03_create_relocation_command_via_dashboard_ui` — **PASSED** (xác minh thành công cả thông báo UI, bảng danh sách và bản ghi mới trong `db.relocations`).

---

## V. LỘ TRÌNH ƯU TIÊN XỬ LÝ TIẾP THEO

1. **Ưu tiên 1 — Hoàn thiện nghiệp vụ tài nguyên Backend/Staff:**
   - Vá `BUG-BE-01` (gói ghép `personal` trừ chỗ đỗ + khóa cổng sạc nguyên tử).
   - Vá `BUG-BE-02` (truyền `outcome` qua 3 tầng FE → API → store để khóa xe khi chuyển xưởng).
2. **Ưu tiên 2 — Bảo mật & An toàn vận hành (NFR05, NFR06):**
   - Vá `BUG-FE-04` (sửa payload `emergencyHalt()`, thêm cờ `system_halted` chặn đặt chỗ và khóa UI User `< 2s`).
   - Vá `BUG-FE-03` (bắt buộc 2FA trên FE và gắn middleware kiểm tra quyền/token trên `BE/operator`).
3. **Ưu tiên 3 — Đồng bộ thời gian thực & Audit Log (NFR04, NFR07):**
   - Vá `BUG-FE-02` (thêm `last_updated_at` kiểm tra ngưỡng `30s` và cơ chế SSE/WebSocket đồng bộ KPI `≤ 1s`).
   - Vá `BUG-BE-03` và `BUG-BE-04` (ghi nhận đầy đủ 4 trường `actor`, `timestamp`, `action`, `result` cho thanh toán và can thiệp Operator).
