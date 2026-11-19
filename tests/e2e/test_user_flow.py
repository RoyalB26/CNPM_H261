"""Kiểm thử E2E & NFR Nhóm 1 cho phân hệ End-User (FE/user/)."""

import os
import time, datetime
from datetime import timedelta, timezone

from playwright.sync_api import Browser, Page, expect
import pytest

from tests.e2e.conftest import (
    ACTIVE_CLASS_RE,
    OPERATOR_URL,
    attach_dialog_collector,
    block_external_requests,
    login_end_user,
    open_operator_dashboard,
)
from tests.unit.conftest import find_hub_in_db
# Mặc định 5 vòng để chạy nhanh local; đặt NFR11_RUNS=20 khi lấy số liệu báo cáo chính thức
NFR11_ITERATIONS = int(os.getenv("NFR11_RUNS", "20"))


@pytest.mark.e2e
def test_tc_u01_end_user_login_in_incognito_navigates_to_home(incognito_context) -> None:
    """TC-U01 (UC1): Đăng nhập từ trình duyệt ẩn danh sạch -> điều hướng màn hình chính."""
    page = incognito_context.new_page()
    login_end_user(page)

    expect(page.locator("#screen-map-home")).to_have_class(ACTIVE_CLASS_RE)
    expect(page.locator("#screen-login")).not_to_have_class(ACTIVE_CLASS_RE)


@pytest.mark.e2e
def test_tc_u03_book_rental_and_combo_parking_charging_ui(page: Page) -> None:
    """TC-U03 (UC3): Đặt trước dịch vụ (thuê xe dùng chung & combo chỗ đỗ + sạc S03)."""
    login_end_user(page)

    page.evaluate("() => { void App.selectHubAndOpenDetail('hub-01'); }")
    expect(page.locator("#screen-hub-detail")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    page.evaluate("() => { App.navigateTo('screen-select-bike'); }")
    expect(page.locator("#screen-select-bike")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    page.evaluate("() => { App.selectBike('XE-031', 92, 'bike-item-2'); void App.confirmRental(); }")

    expect(page.locator("#screen-booking-success")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#successBookingId")).to_contain_text("Mã đặt:")

    # Luồng combo xe cá nhân 59-X1 123.45 (chỗ đỗ 2 giờ + lịch sạc trụ S03)
    page.evaluate("() => { App.navigateTo('screen-select-parking'); }")
    expect(page.locator("#screen-select-parking")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    if page.locator("#parkingDuration").count():
        page.select_option("#parkingDuration", label="2 giờ")
    page.evaluate("() => { App.updateReviewParkingView(); App.navigateTo('screen-select-charging'); }")
    expect(page.locator("#screen-select-charging")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    page.evaluate("() => { App.navigateTo('screen-my-bookings'); }")
    expect(page.locator("#screen-my-bookings")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#screen-my-bookings")).to_contain_text("Đã xác nhận")


@pytest.mark.e2e
@pytest.mark.nfr
def test_nfr11_booking_usability_under_30s_and_95pct_success_rate(browser: Browser) -> None:
    """NFR11 (tích hợp TC-U03): Đặt chỗ < 30s, tối đa 3 màn hình, tỷ lệ thành công >= 95%."""
    success_count = 0
    durations: list[float] = []

    for _ in range(NFR11_ITERATIONS):
        context = browser.new_context()
        block_external_requests(context)
        page = context.new_page()
        try:
            login_end_user(page)
            page.evaluate("() => { void App.selectHubAndOpenDetail('hub-01'); }")
            expect(page.locator("#screen-hub-detail")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

            start_ts = time.perf_counter()
            page.evaluate("() => { App.navigateTo('screen-select-bike'); }")
            expect(page.locator("#screen-select-bike")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
            page.evaluate("() => { void App.confirmRental(); }")
            expect(page.locator("#screen-booking-success")).to_have_class(
                ACTIVE_CLASS_RE,
                timeout=30000,
            )
            elapsed = time.perf_counter() - start_ts

            assert elapsed < 30.0, f"Thời gian đặt chỗ vượt 30s: {elapsed:.2f}s"
            durations.append(elapsed)
            success_count += 1
        finally:
            context.close()

    success_rate = (success_count / NFR11_ITERATIONS) * 100
    avg_time = sum(durations) / len(durations)
    print(f"\n[NFR11] Thanh cong: {success_count}/{NFR11_ITERATIONS} ({success_rate:.1f}%), TB: {avg_time:.2f}s")
    assert success_rate >= 95.0


@pytest.mark.e2e
def test_tc_uc04_receive_and_return_service_navigates_to_invoice(page: Page) -> None:
    """TC-UC04 (UC4): Nhận dịch vụ -> theo dõi chuyến đang hoạt động -> trả xe -> màn hình hóa đơn."""
    login_end_user(page)

    page.evaluate("() => { void App.loadActiveServices(); App.navigateTo('screen-ride-active'); }")
    expect(page.locator("#screen-ride-active")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#rideStatusBadge")).to_contain_text("Đang sử dụng")

    page.evaluate("() => { void App.finishReturnRental(); }")
    expect(page.locator("#screen-invoice-rental")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)


@pytest.mark.e2e
def test_tc_u05_report_incident_navigates_to_report_sent(page: Page) -> None:
    """TC-U05 (UC5): Gửi báo cáo sự cố -> chuyển sang màn hình screen-report-sent."""
    login_end_user(page)

    page.evaluate("() => { App.prepareReport('Phương tiện', 'XE-024'); }")
    expect(page.locator("#screen-report-incident")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    if page.locator("#incDescription").count():
        page.fill("#incDescription", "Khóa điện tử xe XE-024 không mở được tại Hub Ga Metro.")
    page.evaluate("() => { void App.handleIncidentSubmit(); }")

    expect(page.locator("#screen-report-sent")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#createdIncidentId")).to_contain_text("INC-")


@pytest.mark.e2e
def test_tc_u06_payment_service_navigates_to_payment_success(page: Page) -> None:
    """TC-U06 (UC6): Thanh toán cước dịch vụ -> chuyển sang screen-payment-success."""
    login_end_user(page)

    page.evaluate(
        "() => { void App.setupInvoiceAndPay('rental', 15000, 'screen-invoice-rental', false); void App.executePaymentProcess(); }"
    )
    expect(page.locator("#screen-payment-success")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-FE-01 (NFR03): FE/user/js/api.js::createBooking() rơi vào nhánh fallback mock 'Đã xác nhận' khi Backend trả 409 Conflict",
    strict=True,
)
def test_nfr03_b_frontend_rejects_409_conflict_without_fake_confirmation(browser: Browser) -> None:
    """NFR03-B (FE): Khi xe XE-024 đã bị đặt (BE trả 409), UI không được mở screen-booking-success."""
    ctx = browser.new_context()
    block_external_requests(ctx)
    try:
        page = ctx.new_page()
        login_end_user(page)

        # XE-024 đã có booking trong seed -> đặt lại sẽ nhận 409 từ Backend
        page.evaluate("() => { void App.selectHubAndOpenDetail('hub-01'); }")
        expect(page.locator("#screen-hub-detail")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

        with page.expect_response(lambda r: "/bookings" in r.url and r.request.method == "POST") as resp_info:
            page.evaluate("() => { App.selectedBike = 'XE-024'; void App.confirmRental(); }")
        assert resp_info.value.status == 409

        expect(page.locator("#screen-booking-success")).not_to_have_class(ACTIVE_CLASS_RE, timeout=2000)
    finally:
        ctx.close()


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-FE-02 (NFR04-A): mock_db chưa lưu trường last_updated_at và create_booking chưa từ chối dữ liệu cũ > 30s",
    strict=True,
)
def test_nfr04_a_rejects_booking_when_hub_sensor_data_stale_over_30s(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """NFR04-A: Gán last_updated_at của hub-01 cũ hơn 30 giây -> yêu cầu đặt xe phải bị từ chối."""
    hub = find_hub_in_db(reset_shared_mock_db, "hub-01")
    hub["last_updated_at"] = (datetime.now(timezone.utc) - timedelta(seconds=31)).isoformat()

    res = page.request.post(
        "http://127.0.0.1:8000/api/bookings",
        data={
            "plan_type": "rental",
            "hub_id": "hub-01",
            "resource_name": "XE-031 · Xe đạp điện",
        },
    )
    assert res.status in (409, 422, 503), f"Dữ liệu cũ > 30s nhưng vẫn trả {res.status}"


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-FE-02 (NFR04-B): Operator Dashboard chỉ gọi loadKpis() lúc init(), chưa có WebSocket/SSE/polling <= 1s",
    strict=True,
)
def test_nfr04_b_cross_actor_sync_updates_operator_kpi_under_1s(browser: Browser) -> None:
    """NFR04-B: Mở sẵn Operator Dashboard -> User đặt xe -> KPI Operator tự cập nhật trong <= 1s."""
    op_ctx = browser.new_context()
    user_ctx = browser.new_context()
    block_external_requests(op_ctx)
    block_external_requests(user_ctx)
    try:
        op_page = op_ctx.new_page()
        user_page = user_ctx.new_page()

        # Mở Operator TRƯỚC khi User thao tác đặt xe
        open_operator_dashboard(op_page)
        kpi_locator = op_page.locator("#kpiAvailableBikes")
        initial_kpi = kpi_locator.inner_text().strip()

        login_end_user(user_page)
        res = user_page.request.post(
            "http://127.0.0.1:8000/api/bookings",
            data={
                "plan_type": "rental",
                "hub_id": "hub-01",
                "resource_name": "XE-031 · Xe đạp điện",
            },
        )
        assert res.status in (200, 201)

        # Operator không reload trang; KPI phải tự đổi trong <= 1000ms
        expect(kpi_locator).not_to_have_text(initial_kpi, timeout=1000)
    finally:
        op_ctx.close()
        user_ctx.close()


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-FE-03 (NFR05): FE/operator chỉ hiển thị overlay 2FA ở phía client, chưa chặn RBAC vai trò Sinh viên và chưa ép xác thực server",
    strict=False,
)
def test_nfr05_student_role_blocked_from_operator_and_2fa_enforced(browser: Browser) -> None:
    """NFR05: Sinh viên mở trang Operator bị từ chối; bỏ qua 2FA không truy cập được Dashboard."""
    ctx = browser.new_context()
    block_external_requests(ctx)
    try:
        page = ctx.new_page()
        attach_dialog_collector(page)
        login_end_user(page)

        page.goto(OPERATOR_URL, wait_until="domcontentloaded")
        assert not page.locator("#kpiTotalHubs").is_visible()
    finally:
        ctx.close()


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-BE-03 (NFR07): BE/user/main.py::api_pay_invoice() chưa ghi bản ghi Audit Log 4 trường sau khi thanh toán",
    strict=True,
)
def test_nfr07_user_payment_creates_complete_audit_log_entry(page: Page) -> None:
    """NFR07 (User): Thanh toán hóa đơn phải sinh Audit Log đủ 4 trường (actor, timestamp, action, result)."""
    pay_res = page.request.post(
        "http://127.0.0.1:8000/api/invoices/pay",
        data={"invoice_id": "INV-001", "method": "momo"},
    )
    assert pay_res.status == 200

    telemetry_res = page.request.get("http://127.0.0.1:8000/api/v1/operator/dashboard/telemetry")
    assert telemetry_res.status == 200
    events = telemetry_res.json()
    payment_logs = [e for e in events if "pay" in str(e).lower() or "thanh toán" in str(e).lower()]
    assert len(payment_logs) > 0, "Không tìm thấy bản ghi Audit Log cho giao dịch thanh toán"

    latest = payment_logs[0]
    required_fields = {"actor", "timestamp", "action", "result"}
    assert required_fields.issubset(latest.keys()), f"Thiếu trường Audit Log: {latest}"
    for field in required_fields:
        assert str(latest[field]).strip() != "", f"Trường '{field}' đang rỗng: {latest}"