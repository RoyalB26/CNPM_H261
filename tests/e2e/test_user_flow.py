"""Kiểm thử E2E & NFR Nhóm 1 cho phân hệ End-User (FE/user/)."""

from datetime import datetime, timedelta, timezone
import os
import time

from playwright.sync_api import Browser, Page, Route, expect
import pytest

from shared.authentication import sessions
from shared.database import storage
from tests.e2e.conftest import (
    ACTIVE_CLASS_RE,
    BACKEND_URL,
    OPERATOR_URL,
    SHOW_CLASS_RE,
    api_operator_headers,
    attach_dialog_collector,
    block_external_requests,
    build_vnpay_ipn_params,
    get_user_auth_headers,
    login_end_user,
    open_operator_dashboard,
)
from tests.unit.conftest import find_hub_in_db

# Đặt NFR11_RUNS=5 để chạy nhanh local; mặc định 20 vòng theo báo cáo chính thức
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
    """NFR11: Thời gian thao tác đặt chỗ < 30s và tỷ lệ thành công >= 95%."""
    success_count = 0
    durations: list[float] = []

    for _ in range(NFR11_ITERATIONS):
        storage.reset_to_seed()
        sessions.clear()
        context = browser.new_context()
        block_external_requests(context)
        page = context.new_page()
        try:
            login_end_user(page)
            page.evaluate("() => { void App.selectHubAndOpenDetail('hub-01'); }")
            expect(page.locator("#screen-hub-detail")).to_have_class(
                ACTIVE_CLASS_RE, timeout=5000
            )

            start_ts = time.perf_counter()
            page.evaluate("() => { App.navigateTo('screen-select-bike'); }")
            expect(page.locator("#screen-select-bike")).to_have_class(
                ACTIVE_CLASS_RE, timeout=5000
            )
            page.evaluate(
                "() => { App.selectBike('XE-031', 92, 'bike-item-2'); void App.confirmRental(); }"
            )
            expect(page.locator("#screen-booking-success")).to_have_class(
                ACTIVE_CLASS_RE, timeout=30000
            )
            elapsed = time.perf_counter() - start_ts

            assert elapsed < 30.0, f"Thời gian đặt chỗ vượt 30s: {elapsed:.2f}s"
            durations.append(elapsed)
            success_count += 1
        finally:
            context.close()

    success_rate = (success_count / NFR11_ITERATIONS) * 100
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
    expect(page.locator("#screen-report-incident")).to_have_class(
        ACTIVE_CLASS_RE, timeout=5000
    )

    if page.locator("#incDescription").count():
        page.fill("#incDescription", "Khóa điện tử xe XE-024 không mở được tại Hub Ga Metro.")
    page.evaluate("() => { void App.handleIncidentSubmit(); }")

    expect(page.locator("#screen-report-sent")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#createdIncidentId")).to_contain_text("INC-")


@pytest.mark.e2e
def test_tc_u06_payment_service_navigates_to_payment_success(page: Page) -> None:
    """TC-U06 (UC6): Trả xe tạo hóa đơn thật -> khởi tạo thanh toán VNPAY trên UI -> xác nhận IPN paid."""
    login_end_user(page)
    user_headers = get_user_auth_headers(page)

    pay_capture: list[tuple[int, dict]] = []

    def _capture_pay(route: Route) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        resp = route.fetch()
        pay_capture.append((resp.status, resp.json()))
        route.fulfill(response=resp)

    def _mock_external_gateway_nav(route: Route) -> None:
        url = route.request.url
        if (
            route.request.is_navigation_request()
            and not url.startswith("http://127.0.0.1")
            and not url.startswith("http://localhost")
        ):
            route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><body>VNPAY Sandbox Mock</body></html>",
            )
            return
        route.fallback()

    page.route("**/*", _mock_external_gateway_nav)
    page.route("**/invoices/pay", _capture_pay)

    # Bước 1: Trả chuyến seed TRIP-8821 qua UI để sinh hóa đơn rental_invoice chưa thanh toán
    page.evaluate("() => { void App.loadActiveServices(); App.navigateTo('screen-ride-active'); }")
    expect(page.locator("#screen-ride-active")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    page.evaluate("() => { void App.finishReturnRental(); }")
    expect(page.locator("#screen-invoice-rental")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    inv_res = page.request.get(
        f"{BACKEND_URL}/api/invoices/current?type=rental&trip_id=TRIP-8821",
        headers=user_headers,
    )
    assert inv_res.status == 200, inv_res.text()
    invoice = inv_res.json()
    invoice_id = invoice["id"]
    total_amount = invoice["total_amount"]

    # Bước 2: Thiết lập hóa đơn xong rồi kích hoạt thanh toán (đọc body trước khi browser redirect VNPAY)
    page.evaluate(
        "(amount) => App.setupInvoiceAndPay('rental', amount, 'screen-invoice-rental', false)",
        total_amount,
    )
    page.evaluate("() => { void App.executePaymentProcess(); }")

    deadline = time.perf_counter() + 10.0
    while not pay_capture and time.perf_counter() < deadline:
        page.wait_for_timeout(50)

    assert pay_capture, "Không bắt được request POST /invoices/pay từ UI"
    pay_status, pay_data = pay_capture[0]
    assert pay_status == 200, pay_data
    assert pay_data.get("status") in ("pending", "completed"), pay_data

    # Bước 3: Với hóa đơn > 0đ (VNPAY D1), hoàn tất bằng callback IPN có chữ ký hợp lệ
    if pay_data["status"] == "pending":
        assert pay_data.get("payment_url")
        ipn_params = build_vnpay_ipn_params(pay_data["transaction_id"], total_amount)
        ipn_res = page.request.get(
            f"{BACKEND_URL}/api/v1/payments/vnpay/ipn",
            params=ipn_params,
        )
        assert ipn_res.status == 200, ipn_res.text()
        assert ipn_res.json().get("RspCode") == "00", ipn_res.text()
    else:
        expect(page.locator("#screen-payment-success")).to_have_class(
            ACTIVE_CLASS_RE, timeout=5000
        )

    # Xác minh hóa đơn đã chuyển sang trạng thái 'paid' trên Backend
    after_res = page.request.get(
        f"{BACKEND_URL}/api/invoices/current?type=rental&invoice_id={invoice_id}",
        headers=user_headers,
    )
    assert after_res.status == 200, after_res.text()
    assert after_res.json().get("status") == "paid"

@pytest.mark.e2e
@pytest.mark.nfr
def test_nfr03_b_frontend_rejects_409_conflict_without_fake_confirmation(
    browser: Browser,
) -> None:
    """NFR03-B (FE): Khi xe XE-024 đã bị đặt (BE trả 409), UI không được mở screen-booking-success."""
    ctx = browser.new_context()
    block_external_requests(ctx)
    try:
        page = ctx.new_page()
        login_end_user(page)

        page.evaluate("() => { void App.selectHubAndOpenDetail('hub-01'); }")
        expect(page.locator("#screen-hub-detail")).to_have_class(
            ACTIVE_CLASS_RE, timeout=5000
        )

        with page.expect_response(
            lambda r: "/bookings" in r.url and r.request.method == "POST"
        ) as resp_info:
            page.evaluate("() => { App.selectedBike = 'XE-024'; void App.confirmRental(); }")
        assert resp_info.value.status == 409

        expect(page.locator("#screen-booking-success")).not_to_have_class(
            ACTIVE_CLASS_RE, timeout=2000
        )
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
    login_end_user(page)
    user_headers = get_user_auth_headers(page)

    hub = find_hub_in_db(reset_shared_mock_db, "hub-01")
    hub["last_updated_at"] = (datetime.now(timezone.utc) - timedelta(seconds=31)).isoformat()

    res = page.request.post(
        f"{BACKEND_URL}/api/bookings",
        headers=user_headers,
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

        open_operator_dashboard(op_page)
        kpi_locator = op_page.locator("#kpiAvailableBikes")
        initial_kpi = kpi_locator.inner_text().strip()

        login_end_user(user_page)
        user_headers = get_user_auth_headers(user_page)
        res = user_page.request.post(
            f"{BACKEND_URL}/api/bookings",
            headers=user_headers,
            data={
                "plan_type": "rental",
                "hub_id": "hub-01",
                "resource_name": "XE-031 · Xe đạp điện",
            },
        )
        assert res.status in (200, 201), res.text()

        expect(kpi_locator).not_to_have_text(initial_kpi, timeout=1000)
    finally:
        op_ctx.close()
        user_ctx.close()


@pytest.mark.e2e
@pytest.mark.nfr
def test_nfr05_student_role_blocked_from_operator_and_2fa_enforced(browser: Browser) -> None:
    """NFR05: Sinh viên mở trang Operator bị khóa sau màn hình 2FA và API Operator từ chối với 403."""
    ctx = browser.new_context()
    block_external_requests(ctx)
    try:
        page = ctx.new_page()
        attach_dialog_collector(page)
        login_end_user(page)
        student_headers = get_user_auth_headers(page)

        # Kiểm tra API Operator chặn token role End-User (403 Forbidden)
        api_res = page.request.get(
            f"{BACKEND_URL}/api/v1/operator/dashboard/kpis",
            headers=student_headers,
        )
        assert api_res.status == 403, f"Token sinh viên phải bị 403, thực tế: {api_res.status}"

        # Kiểm tra FE/operator bắt buộc hiện cổng đăng nhập 2FA, không tự cấp phiên Operator
        page.goto(OPERATOR_URL, wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('[data-include]').length === 0 && Boolean(window.OperatorApp)",
            timeout=10000,
        )
        expect(page.locator("#operatorLoginView")).to_have_class(SHOW_CLASS_RE, timeout=5000)
        assert not page.evaluate("() => sessionStorage.getItem('operator_access_token')")
    finally:
        ctx.close()


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-BE-03 (NFR07): BE/user/payments.py chưa ghi bản ghi Audit Log 4 trường vào telemetry_events sau khi thanh toán",
    strict=True,
)
def test_nfr07_user_payment_creates_complete_audit_log_entry(page: Page) -> None:
    """NFR07 (User): Thanh toán hóa đơn hợp lệ phải sinh Audit Log đủ 4 trường."""
    login_end_user(page)
    user_headers = get_user_auth_headers(page)
    op_headers = api_operator_headers(page)

    ret_res = page.request.post(
        f"{BACKEND_URL}/api/services/return-vehicle",
        headers=user_headers,
        data={"trip_id": "TRIP-8821", "hub_id": "hub-04"},
    )
    assert ret_res.status == 200, ret_res.text()

    inv_res = page.request.get(
        f"{BACKEND_URL}/api/invoices/current?type=rental&trip_id=TRIP-8821",
        headers=user_headers,
    )
    assert inv_res.status == 200, inv_res.text()
    invoice = inv_res.json()

    pay_res = page.request.post(
        f"{BACKEND_URL}/api/invoices/pay",
        headers=user_headers,
        data={"invoice_id": invoice["id"], "method": "wallet"},
    )
    assert pay_res.status == 200, pay_res.text()
    pay_data = pay_res.json()

    if pay_data.get("status") == "pending":
        ipn_params = build_vnpay_ipn_params(
            pay_data["transaction_id"], invoice["total_amount"]
        )
        ipn_res = page.request.get(
            f"{BACKEND_URL}/api/v1/payments/vnpay/ipn",
            params=ipn_params,
        )
        assert ipn_res.status == 200 and ipn_res.json().get("RspCode") == "00"

    telemetry_res = page.request.get(
        f"{BACKEND_URL}/api/v1/operator/dashboard/telemetry",
        headers=op_headers,
    )
    assert telemetry_res.status == 200, telemetry_res.text()
    events = telemetry_res.json()
    payment_logs = [
        e for e in events if "pay" in str(e).lower() or "thanh toán" in str(e).lower()
    ]
    assert len(payment_logs) > 0, "Không tìm thấy bản ghi Audit Log cho giao dịch thanh toán"

    latest = payment_logs[0]
    required_fields = {"actor", "timestamp", "action", "result"}
    assert required_fields.issubset(latest.keys()), f"Thiếu trường Audit Log: {latest}"