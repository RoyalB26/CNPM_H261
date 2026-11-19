# BÁO CÁO TỔNG HỢP LỖI TỒN ĐỌNG & KHOẢNG TRỐNG KIỂM THỬ (BUG & GAP REPORT)

- **Tên dự án:** Smart E-Mobility Hub – Hệ thống điều phối phương tiện điện trong Khu đô thị ĐHQG-HCM (CO3001)
- **Nhóm thực hiện:** Nhóm 6 — Khoa Khoa học và Kỹ thuật Máy tính, Trường ĐH Bách khoa – ĐHQG-HCM
- **Ngày cập nhật:** 19/11/2026
- **Môi trường kiểm thử:** Windows / Python 3.11.9 / Pytest 9.2.0 / Playwright 0.10.0 / Starlette Unified Mock Backend (`127.0.0.1:8000`) & Static FE (`127.0.0.1:3000`)
- **Bằng chứng thực thi tham chiếu:** `tests/pytest_execution.log` (chạy lệnh `NFR11_RUNS=20 pytest tests -v -s`)
- **Phạm vi đánh giá:** Đối chiếu đồng thời giữa (1) Đặc tả đề bài gốc (`BTL_SoftwareEngineering_HK261_v1.pdf`), (2) Đặc tả kiểm thử Chương 5 (`BTL3_REPORT.pdf`, `test_spec.docx`) và (3) Mã nguồn thực tế (`BE/`, `FE/`, `tests/`).

> **Lưu ý phương pháp luận:** Không coi mọi trường hợp `XFAIL` là lỗi đã được chứng minh hoàn toàn. Báo cáo này tách bạch rõ **Lỗi chức năng & tích hợp (Functional/Integration Bugs)**, **Khoảng trống triển khai phi chức năng (NFR Implementation Gaps)** và **Lỗi thiết kế kiểm thử (Test Defects)** đã được xác minh trực tiếp qua mã nguồn.

---

## I. TIÊU CHÍ PHÂN LOẠI & TỔNG QUAN

### 1.1. Tiêu chí mức độ nghiêm trọng (Severity)

| Mức độ | Tiêu chí đánh giá |
| :--- | :--- |
| 🔴 **Critical** | Gây sai lệch nghiêm trọng dữ liệu nghiệp vụ cốt lõi (VD: đặt trùng tài nguyên nhưng báo thành công) hoặc làm ngừng hoàn toàn luồng vận hành chính. |
| 🟠 **High** | Làm hỏng một chức năng/quy trình nghiệp vụ quan trọng, sai lệch trạng thái tài nguyên hoặc gây lỗ hổng kiểm soát truy cập, nhưng các phân hệ khác vẫn hoạt động. |
| 🟡 **Medium** | Thiếu cơ chế đồng bộ thời gian thực hoặc kiểm tra tính tươi dữ liệu theo ngưỡng NFR đã cam kết trong đặc tả kiểm thử; có ảnh hưởng trải nghiệm nhưng có phương án tạm thời ở bản Prototype. |
| 🟢 **Low** | Thiếu thông tin truy vết/kiểm toán (Audit Log) hoặc sai lệch nhỏ về chuẩn hóa trường dữ liệu log, chưa ảnh hưởng trực tiếp tới luồng đặt chỗ/vận hành. |

### 1.2. Trạng thái xác minh (Verification Status)

- **Confirmed:** Đã xác minh lỗi thực sự tồn tại trong mã nguồn BE/FE và có bằng chứng tái hiện rõ ràng.
- **Confirmed + Test Defect:** Đã xác minh lỗi có thật trong mã nguồn ứng dụng, đồng thời test case hiện tại cũng có sai sót về dữ liệu đầu vào, tiền điều kiện hoặc assertion cần sửa song song.
- **Pending Verification:** Có dấu hiệu lỗi nhưng cần bổ sung/chạy lại kịch bản test đúng điều kiện để chốt kết quả.
- **Resolved:** Đã vá mã nguồn, gỡ `xfail` và regression test đạt `PASSED`.

### 1.3. Bảng tổng hợp 9 vấn đề tồn đọng

| Mã lỗi | Phân loại | Mức độ | Verification Status | Test Case liên kết | Hướng xử lý |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `BUG-FE-01` | Frontend Bug | 🔴 Critical | Confirmed + Test Defect | `NFR03` (`test_user_flow.py`) | Vá nhánh fallback `409` ở FE; tách test đồng thời BE (`NFR03-A`) và xử lý `409` ở FE (`NFR03-B`) |
| `BUG-FE-05` | Integration Bug (FE–BE) | 🟠 High | Confirmed | `TC-O03` (`test_operator_dashboard.py`) | Đồng bộ schema `RelocationCommandCreate` và đọc `data.items`; bổ sung assert DB |
| `BUG-BE-01` | Functional Bug | 🟠 High | Confirmed | `TC-U03` (`test_user_booking_service.py`) | Bổ sung logic trừ `available_parking` & khóa cổng `S03` cho `personal`; bổ sung E2E combo |
| `BUG-BE-02` | Functional / Integration Bug | 🟠 High | Confirmed + Test Defect | `TC-S02` (`test_staff_maintenance.py`, `test_staff_flow.py`) | Sửa cả 3 tầng FE–API–BE & đồng bộ seed `MT-102`/`BK-EB-018`; sửa test truyền rõ `outcome` |
| `BUG-FE-04` | NFR Gap (Safety) | 🟠 High | Confirmed + Test Defect | `NFR06` (`test_operator_dashboard.py`) | Thêm cờ `system_halted`, chặn API booking (`503`) & đồng bộ khóa UI `< 2s`; sửa test đo thời gian thực |
| `BUG-FE-03` | NFR Gap (Security) | 🟠 High | Confirmed | `NFR05` (`test_user_flow.py`, `test_auth.py`) | Áp đặt middleware RBAC/2FA trên route Operator; bổ sung test API trả `401`/`403` |
| `BUG-FE-02` | NFR Gap (Data Consistency) | 🟡 Medium | Confirmed + Test Defect | `NFR04` (`test_user_flow.py`) | Thêm `last_updated_at` (> 30s) & cơ chế SSE/polling `<= 1s`; tách thành `NFR04-A` và `NFR04-B` |
| `BUG-BE-03` | NFR Gap (Audit Log) | 🟢 Low | Confirmed + Test Defect | `NFR07` (`test_user_flow.py`) | Ghi Audit Log 4 trường trong `api_pay_invoice()`; sửa test assert đủ 4 trường & giá trị hợp lệ |
| `BUG-BE-04` | NFR Gap (Audit Log) | 🟢 Low | Confirmed + Test Defect | `NFR07` (`test_operator_dashboard.py`) | Bổ sung `actor`, `action`, `result` cho telemetry Operator; thống nhất tên trường `timestamp` |

---

## II. LỖI CHỨC NĂNG & TÍCH HỢP (4 FUNCTIONAL / INTEGRATION BUGS)

### 🔴 BUG-FE-01: Frontend báo đặt xe thành công giả dù Backend đã từ chối trùng lặp (`409 Conflict`)

- **Phân loại:** Frontend Bug | **Mức độ:** Critical | **Trạng thái:** Confirmed + Test Defect
- **Phạm vi ảnh hưởng:** `FE/user/js/api.js::createBooking()`
- **Preconditions:** Xe `XE-024` tại `hub-01` đã có booking hợp lệ trong `MockDatabaseStore`.
- **Steps to Reproduce:**
  1. Người dùng đăng nhập ứng dụng End-User (`FE/user/`).
  2. Chọn `hub-01`, chọn xe `XE-024` và xác nhận đặt xe (`App.confirmRental()`).
- **Expected Result:** Khi Backend trả HTTP `409 Conflict`, giao diện phải hiển thị thông báo xe đã có người đặt và giữ người dùng ở màn hình chọn xe.
- **Actual Result:** Giao diện vẫn hiển thị trạng thái `"Đã xác nhận"` và điều hướng sang `#screen-booking-success`.
- **Evidence:** `POST /api/bookings` trả HTTP `409`; nhánh `if (res.ok)` trong `api.js::createBooking()` thất bại nhưng hàm không `throw` mà rơi xuống nhánh fallback offline trả về object giả `{ id: "EMH-...", status: "Đã xác nhận" }`.
- **Root Cause:** Lỗi xử lý HTTP error status ở lớp gọi API Frontend, gộp chung lỗi nghiệp vụ `4xx` với trường hợp mất kết nối mạng.
- **Related Test & Lưu ý kiểm thử:** `test_nfr03_*` (`tests/e2e/test_user_flow.py`). Test ban đầu gọi `confirmRental()` tuần tự trên 2 trang nên chưa chứng minh được chống race condition; cần tách thành **NFR03-A** (bắn 2 request đồng thời vào Backend) và **NFR03-B** (kiểm tra Frontend xử lý `409`).

---

### 🟠 BUG-FE-05: Lệch Contract API và Crash `TypeError` khi tạo lệnh điều phối xe

- **Phân loại:** Integration Bug (FE–BE) | **Mức độ:** High | **Trạng thái:** Confirmed
- **Phạm vi ảnh hưởng:** `FE/operator/js/operator.js` (`loadRelocations`, `submitRelocation`) ↔ `BE/operator/main.py` (`list_relocations`, `RelocationCommandCreate`)
- **Preconditions:** Operator đang mở tab Điều phối trên Operator Dashboard (`FE/operator/`), Hub nguồn có sẵn xe.
- **Steps to Reproduce:**
  1. Mở modal tạo lệnh điều phối (`openCreateRelocationModal`).
  2. Nhập số lượng xe `2` và nhấn xác nhận (`submitRelocation`).
- **Expected Result:** Backend lưu lệnh điều phối mới vào `db.relocations` (`200/201`), modal đóng, hiện thông báo thành công và bảng `#relocationTableBody` cập nhật dòng mới.
- **Actual Result:** Không có thông báo thành công, modal bị treo và bảng danh sách không cập nhật.
- **Evidence:**
  1. `GET /api/v1/operator/relocation/commands` trả `{"total": int, "items": [...]}` nhưng `loadRelocations()` gọi trực tiếp `list.map(...)` gây `TypeError: list.map is not a function`.
  2. `submitRelocation()` gửi `{source_hub, dest_hub, vehicle_count, assigned_staff}` tới `POST /api/v1/operator/relocation/commands`, lệch hoàn toàn với schema `RelocationCommandCreate` (`{source_hub_id, target_hub_id, bike_count, assigned_staff_id}`) gây HTTP `422 Unprocessable Entity`.
- **Root Cause:** Bất đồng bộ API contract giữa Frontend và Backend ở cả chiều đọc danh sách lẫn chiều gửi payload tạo lệnh.
- **Related Test & Biện pháp khắc phục:** `test_tc_o03_create_relocation_command_via_dashboard_ui` (`tests/e2e/test_operator_dashboard.py`). Sửa `loadRelocations()` đọc `Array.isArray(list) ? list : (list.items || [])`, chuẩn hóa payload khớp `RelocationCommandCreate`, và bổ sung assertion kiểm tra `len(db.relocations)` tăng thêm 1.

---

### 🟠 BUG-BE-01: Đặt combo đỗ xe và sạc cho xe cá nhân chưa cập nhật tài nguyên trên Backend

- **Phân loại:** Functional Bug | **Mức độ:** High | **Trạng thái:** Confirmed
- **Phạm vi ảnh hưởng:** `BE/mock_db.py::MockDatabaseStore.create_booking()`
- **Preconditions:** `hub-01` có `available_parking > 0` và cổng sạc `S03` trong danh sách `hub["ports"]` có `is_available == True`.
- **Steps to Reproduce:**
  1. Gửi `POST /api/v1/user/bookings` với `plan_type: "personal"`, `hub_id: "hub-01"`, `personal_plate: "59-X1 123.45"`, `parking_slot: "P01"`, `charging_port: "S03"`, `duration_hours: 2`.
  2. Kiểm tra lại trạng thái `hub-01` trong `MockDatabaseStore`.
- **Expected Result:** `hub["available_parking"]` giảm đi 1 và phần tử có `id == "S03"` trong `hub["ports"]` chuyển `is_available = False` (theo yêu cầu đặt chỗ đỗ & lịch sạc xe cá nhân trong đề bài gốc và TC-U03).
- **Actual Result:** API trả thành công và thêm bản ghi vào `self.bookings`, nhưng `available_parking` giữ nguyên và cổng `S03` vẫn có `is_available == True`.
- **Evidence:** Trong `tests/unit/test_user_booking_service.py`, `hub_after["available_parking"] == parking_before` và `next(p for p in hub_after["ports"] if p["id"] == "S03")["is_available"] is True`.
- **Root Cause:** `MockDatabaseStore.create_booking()` mới cài đặt logic kiểm tra và trừ tài nguyên cho nhánh `plan_type == "rental"`, bỏ trống nhánh cập nhật bãi đỗ/cổng sạc cho `plan_type == "personal"`.
- **Related Test & Lưu ý kiểm thử:** `test_tc_u03_combo_parking_and_charging_updates_mock_db` (Unit) đã đúng hướng; cần bổ sung luồng E2E hoàn chỉnh chọn cổng `S03` + xác nhận combo + kiểm tra trạng thái DB trong `test_tc_u03_book_rental_and_combo_parking_charging_ui`.

---

### 🟠 BUG-BE-02: Gửi kết quả bảo trì "Cần chuyển về xưởng" không khóa thiết bị và lệch dữ liệu 3 tầng

- **Phân loại:** Functional / Integration Bug | **Mức độ:** High | **Trạng thái:** Confirmed + Test Defect
- **Phạm vi ảnh hưởng:** `FE/staff/js/staff.js`, `BE/staff/main.py`, `BE/mock_db.py`
- **Preconditions:** Nhân viên bảo trì tiếp nhận phiếu bảo trì thiết bị đang hoạt động tại Hub.
- **Steps to Reproduce:**
  1. Chọn phương án kết quả `"Cần chuyển về xưởng"` (`ResolutionOutcome.TRANSFER_TO_WORKSHOP`) và gửi `POST /api/v1/staff/maintenance/resolve`.
  2. Kiểm tra trạng thái thiết bị và `available_bikes` của Hub tương ứng trong `MockDatabaseStore`.
- **Expected Result:** Thiết bị được chuyển sang trạng thái khóa/bảo trì và `available_bikes` của Hub giảm đi 1 (TC-S02, BTL3 trang 73).
- **Actual Result:** Backend luôn xử lý như đã sửa xong tại chỗ, không khóa thiết bị và không giảm `available_bikes`.
- **Evidence:**
  1. **Tầng API (`BE/staff/main.py::resolve_maintenance`):** Chỉ gọi `db.resolve_maintenance(req.task_code, req.technical_notes)`, bỏ rơi tham số `req.outcome`.
  2. **Tầng Data (`BE/mock_db.py`):** Chưa có logic khóa xe và trừ `available_bikes` khi `outcome == TRANSFER_TO_WORKSHOP`; dữ liệu seed dùng `TICK-801..803` (`hub-03`, `XE-019`) lệch với đặc tả TC-S02 (`MT-102`, `BK-EB-018`, `Hub KTX Khu A`).
  3. **Tầng FE (`FE/staff/js/staff.js::submitMaintResult`):** Hardcode `outcome: "FIXED_ON_SITE"` và gửi sai key `technician_notes` thay vì `technical_notes`.
- **Root Cause:** Đứt gãy truyền tham số `outcome` và sai lệch schema xuyên suốt cả 3 tầng FE – API – State Management.
- **Related Test & Lưu ý kiểm thử:** `test_tc_s02_send_to_workshop_locks_bike_and_decrements_available_bikes` ban đầu không truyền trường `"outcome": "Cần chuyển về xưởng"` (Test Defect — đã sửa trong kế hoạch cập nhật test); E2E `TC-S02` cũng cần kiểm tra trạng thái DB sau khi gửi kết quả thay vì chỉ đọc hộp thoại `alert`.

---

## III. KHOẢNG TRỐNG PHI CHỨC NĂNG (5 NFR IMPLEMENTATION GAPS)

### 🟠 BUG-FE-04: Chế độ "Dừng khẩn cấp" (Emergency Halt) chưa khóa đặt chỗ và UI User trong `< 2s`

- **Phân loại:** NFR Gap (An toàn vận hành — NFR06) | **Mức độ:** High | **Trạng thái:** Confirmed + Test Defect
- **Phạm vi ảnh hưởng:** `BE/operator/main.py::emergency_halt()`, `BE/mock_db.py`, `FE/operator`, `FE/user`
- **Preconditions:** Cả phiên Operator Dashboard và phiên End-User đều đang mở song song.
- **Steps to Reproduce:**
  1. Operator nhấn nút "Dừng khẩn cấp" và xác nhận (`confirmEmergency`).
  2. Đo thời gian phản hồi khóa giao diện bên User và thử gửi `POST /api/bookings`.
- **Expected Result:** Giao diện End-User hiển thị trạng thái tạm dừng trong `< 2000ms` và mọi yêu cầu tạo booking mới đều bị Backend từ chối (`503 Service Unavailable`).
- **Actual Result:** UI User không nhận tín hiệu khóa và Backend vẫn cho phép tạo booking mới bình thường.
- **Evidence:** `emergency_halt()` chỉ chèn bản ghi `EMERGENCY_HALT` vào `db.telemetry_events`, không đặt cờ khóa toàn cục (`system_halted`). Ngoài ra, payload từ `FE/operator` gửi `{halt_reason, confirmation_code}` lệch schema `{reason, confirmation_token}` của Backend, nhưng lỗi contract này đang bị nhánh `try/except` fallback dữ liệu mặc định ở Backend che khuất.
- **Root Cause:** Chưa triển khai cơ chế trạng thái khóa toàn cục ở Backend và kênh nhận tín hiệu dừng khẩn cấp ở Frontend User.
- **Related Test & Lưu ý kiểm thử:** `test_nfr06_emergency_halt_locks_user_ui_under_2s` ban đầu đợi `alert` xong mới kiểm tra `timeout=2000` và chưa thử đặt booking sau halt; cần sửa để bấm giờ từ lúc kích hoạt và assert API booking bị từ chối.

---

### 🟠 BUG-FE-03: Chưa áp đặt kiểm soát truy cập theo vai trò (RBAC) và xác thực 2FA cho phân hệ Operator

- **Phân loại:** NFR Gap (Bảo mật — NFR05) | **Mức độ:** High | **Trạng thái:** Confirmed
- **Phạm vi ảnh hưởng:** `FE/operator/js/operator.js`, các route trong `BE/operator/main.py`
- **Preconditions:** Người dùng chưa đăng nhập Operator hoặc đang dùng phiên có vai trò Sinh viên (`student`).
- **Steps to Reproduce:**
  1. Truy cập trực tiếp URL `/operator/` hoặc gọi `GET /api/v1/operator/dashboard/kpis` không kèm token / kèm token của `student`.
  2. Gọi `OperatorApp.completeLogin()` bỏ qua mã OTP 2FA.
- **Expected Result:** API Operator trả `401 Unauthorized` (thiếu token) hoặc `403 Forbidden` (sai vai trò / chưa qua 2FA); giao diện chặn truy cập Dashboard khi chưa xác thực 2FA thành công (NFR05, BTL3 trang 75).
- **Actual Result:** Trang `/operator/` tải thẳng KPI mà không yêu cầu đăng nhập; `completeLogin()` chỉ ẩn `#operatorLoginView` và bật `alert`, không gọi `/api/v1/operator/auth/verify-2fa`; các API Backend trả `200 OK` cho mọi request.
- **Evidence:** Khối `#operatorLoginView` mặc định `display: none`; `OperatorApp.init()` gọi `loadKpis()` ngay khi tải trang; các route trong `BE/operator/main.py` không có middleware kiểm tra token/role.
- **Root Cause:** Lớp bảo mật RBAC và xác thực 2FA mới dừng ở mức giao diện minh họa trên bản Prototype.
- **Related Test & Biện pháp khắc phục:** Bổ sung test tầng API (`test_nfr05_operator_api_enforces_rbac_and_2fa`) kiểm tra `401`/`403` song song với E2E `test_nfr05_student_role_blocked_from_operator_and_2fa_enforced`. *(Ghi chú phạm vi: yêu cầu ngưỡng chi tiết RBAC/2FA được nhóm cụ thể hóa trong BTL3/test_spec.)*

---

### 🟡 BUG-FE-02: Thiếu kiểm tra độ tươi dữ liệu (`> 30s`) và đồng bộ User → Operator `<= 1s`

- **Phân loại:** NFR Gap (Nhất quán dữ liệu — NFR04) | **Mức độ:** Medium | **Trạng thái:** Confirmed + Test Defect
- **Phạm vi ảnh hưởng:** `BE/mock_db.py`, `BE/user/main.py`, `FE/operator/js/operator.js`
- **Preconditions:** Operator Dashboard đã mở sẵn hiển thị KPI xe khả dụng; hoặc dữ liệu cảm biến của Hub có mốc cập nhật cũ hơn 30 giây.
- **Steps to Reproduce:**
  1. **(Stale data):** Thiết lập dữ liệu trạng thái `hub-01` quá hạn `> 30s` rồi gửi yêu cầu đặt xe.
  2. **(Sync `<= 1s`):** Mở sẵn Operator Dashboard, sau đó User hoàn tất đặt 1 xe tại `hub-01` và quan sát KPI trên Dashboard không tải lại trang.
- **Expected Result:** (1) Từ chối đặt xe khi dữ liệu cũ `> 30s`; (2) KPI số xe khả dụng trên Operator Dashboard tự động giảm trong `<= 1000ms` (NFR04, BTL3 trang 74).
- **Actual Result:** (1) Hệ thống vẫn cho đặt xe do không lưu/kiểm tra `last_updated_at`; (2) Operator Dashboard giữ nguyên số liệu cũ cho tới khi tải lại trang.
- **Evidence:** `FE/operator/js/operator.js` chỉ gọi `loadKpis()` một lần trong `init()`, không có SSE/WebSocket hoặc short-polling; cấu trúc Hub trong `BE/mock_db.py` chưa có trường `last_updated_at`.
- **Root Cause:** Chưa cài đặt timestamp kiểm tra độ tươi dữ liệu ở Backend và cơ chế đẩy/kéo dữ liệu thời gian thực ở Frontend Operator.
- **Related Test & Lưu ý kiểm thử:** Test gộp cũ chỉ tua đồng hồ trình duyệt (`fast_forward(31000)`) và mở trang Operator *sau* khi User đã đặt xe (Test Defect); cần tách thành 2 test độc lập `NFR04-A` và `NFR04-B`.

---

### 🟢 BUG-BE-03: Giao dịch thanh toán hóa đơn của User chưa ghi nhận vào kho Audit Log

- **Phân loại:** NFR Gap (Kiểm toán — NFR07) | **Mức độ:** Low | **Trạng thái:** Confirmed + Test Defect
- **Phạm vi ảnh hưởng:** `BE/user/main.py::api_pay_invoice()`
- **Preconditions:** User có hóa đơn chờ thanh toán hợp lệ.
- **Steps to Reproduce:**
  1. Gửi yêu cầu thanh toán tới `POST /api/invoices/pay`.
  2. Truy vấn `GET /api/v1/operator/dashboard/telemetry` để kiểm tra bản ghi Audit Log tương ứng.
- **Expected Result:** Phát sinh bản ghi Audit Log chứa đủ 4 trường hợp lệ: `actor`, `timestamp`, `action`, `result` (NFR07, BTL3 trang 75).
- **Actual Result:** API trả `{"success": True, "transaction_id": ...}` nhưng không có bản ghi nào được thêm vào kho nhật ký.
- **Evidence:** Thân hàm `api_pay_invoice()` trong `BE/user/main.py` trả JSON trực tiếp mà không gọi ghi nhận vào `db.telemetry_events` hay bảng audit riêng.
- **Root Cause:** Thiếu bước ghi nhận Audit Log trong handler xử lý thanh toán.
- **Related Test & Lưu ý kiểm thử:** `test_nfr07_user_payment_creates_audit_log_entry` ban đầu chỉ kiểm tra `len(payment_logs) > 0`; cần bổ sung kiểm tra đủ 4 khóa bắt buộc và giá trị khác rỗng.

---

### 🟢 BUG-BE-04: Nhật ký sự kiện can thiệp của Operator thiếu 3 trường chuẩn Audit Log

- **Phân loại:** NFR Gap (Kiểm toán — NFR07) | **Mức độ:** Low | **Trạng thái:** Confirmed + Test Defect
- **Phạm vi ảnh hưởng:** `BE/operator/main.py` (`emergency_halt`, `/dashboard/telemetry`)
- **Preconditions:** Operator thực hiện một thao tác can thiệp vận hành (dừng khẩn cấp, điều phối, cấu hình Hub).
- **Steps to Reproduce:**
  1. Kích hoạt `POST /api/v1/operator/dashboard/emergency-halt`.
  2. Truy vấn `GET /api/v1/operator/dashboard/telemetry` và kiểm tra schema bản ghi mới nhất.
- **Expected Result:** Bản ghi tuân thủ hợp đồng Audit Log thống nhất gồm 4 trường: `{"actor": "OP-01", "timestamp": "<ISO-8601>", "action": "EMERGENCY_HALT", "result": "SUCCESS"}`.
- **Actual Result:** Bản ghi hiện chỉ có `id`, `timestamp`, `hub_name`, `event_type`, `message`, `level`; thiếu hoàn toàn `actor`, `action`, `result`.
- **Evidence:** Đối chiếu trực tiếp object chèn vào `db.telemetry_events` trong `BE/operator/main.py::emergency_halt()`.
- **Root Cause:** Cấu trúc `TelemetryEvent` hiện thiết kế cho bảng tin cảnh báo UI, chưa mở rộng sang schema kiểm toán 4 trường.
- **Related Test & Lưu ý kiểm thử:** `test_nfr07_operator_intervention_writes_complete_audit_log` trước đây kiểm tra tên trường `timestamp_iso` do test tự đặt trong khi NFR07 không ép tên trường này; đã thống nhất lại hợp đồng chung dùng khóa `timestamp`.

---

## IV. KẾ HOẠCH KHẮC PHỤC & MỞ RỘNG ĐỘ BAO PHỦ KIỂM THỬ

### 4.1. Thứ tự ưu tiên xử lý

1. **Ưu tiên 1 — Vá lỗi ảnh hưởng trực tiếp nghiệp vụ cốt lõi:**
   - `BUG-FE-01` (chặn fallback giả khi nhận `409 Conflict`).
   - `BUG-FE-05` (đồng bộ contract đọc/tạo lệnh điều phối).
   - `BUG-BE-01` (trừ chỗ đỗ & khóa cổng sạc cho gói `personal`).
   - `BUG-BE-02` (khóa thiết bị & trừ `available_bikes` khi chuyển xưởng trên cả 3 tầng FE–API–BE).
2. **Ưu tiên 2 — Chuẩn hóa & chống PASS giả trong bộ kiểm thử:**
   - Áp dụng `strict=True` cho toàn bộ 9 decorator `xfail`.
   - Vá lỗi PASS giả ở `TC-S03` E2E (`assert slots_after == slots_before - 1`), bổ sung kiểm tra DB cho `TC-O03` & `TC-S02` E2E, hoàn thiện luồng E2E combo cho `TC-U03`.
   - Tách `NFR03` (`A`/`B`), tách `NFR04` (`A`/`B`), sửa đo thời gian thực cho `NFR06`, sửa thứ tự mở trang cho `NFR10`, thiết lập tải `>= 90%` cho `NFR13`, chạy đủ `NFR11_RUNS=20` và xóa hàm khai báo trùng trong `test_user_booking_service.py`.
3. **Ưu tiên 3 — Hoàn thiện NFR cho giai đoạn nghiệm thu / Production:**
   - Triển khai cờ dừng khẩn cấp (`BUG-FE-04`), middleware RBAC/2FA (`BUG-FE-03`), đồng bộ thời gian thực & kiểm tra `last_updated_at` (`BUG-FE-02`) và chuẩn hóa Audit Log 4 trường (`BUG-BE-03`, `BUG-BE-04`).

### 4.2. Các kịch bản biên & toàn vẹn tài nguyên cần bổ sung ở Sprint kế tiếp

- **Toàn vẹn tài nguyên đa mục (Resource Consistency):** Đảm bảo rollback chỗ đỗ nếu bước khóa cổng sạc trong combo thất bại; ngăn số lượng tài nguyên (`available_bikes`, `available_parking`) giảm xuống giá trị âm.
- **Đặt trùng tài nguyên đồng thời:** Bổ sung kiểm thử concurrent cho đặt trùng 1 chỗ đỗ và đặt trùng 1 cổng sạc (tương tự `NFR03-A` của xe thuê).
- **Biên nghiệp vụ điều phối & bảo trì:** Điều chuyển vượt số xe khả dụng tại Hub nguồn; phân biệt rõ trạng thái kết thúc giữa `FIXED_ON_SITE` và `TRANSFER_TO_WORKSHOP`.
- **Biên kiểm toán:** Xác minh Audit Log vẫn được ghi nhận với `result: "FAILED"` khi thao tác thanh toán hoặc can thiệp thất bại.
