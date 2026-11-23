"""Kiểm thử E2E & NFR Nhóm 1 cho Bảng Điều Hành Operator (FE/operator/)."""

from playwright.sync_api import Browser, Page, expect
import pytest
import time

from tests.e2e.conftest import (
    ACTIVE_CLASS_RE,
    SHOW_CLASS_RE,
    block_external_requests,
    login_end_user,
    open_operator_dashboard,
    switch_operator_tab,
    wait_for_new_dialog,
)
from tests.unit.conftest import find_hub_in_db


@pytest.mark.e2e
def test_tc_o02_what_if_simulation_progress_bar_and_recommendations_ui(page: Page) -> None:
    """TC-O02 (UC10): Chạy mô phỏng What-If trên UI -> modal loading hiển thị và xuất đề xuất."""
    open_operator_dashboard(page)

    switch_operator_tab(page, "sim")
    page.evaluate("() => { OperatorApp.goToSimStep(2); }")
    expect(page.locator("#simStep2View")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    # Kích hoạt mô phỏng -> modal-backdrop.show xuất hiện, progress bar chạy mượt rồi chuyển Bước 3
    page.evaluate("() => { OperatorApp.triggerSimulationCalculation(); }")
    expect(page.locator("#modalSimLoading")).to_have_class(SHOW_CLASS_RE, timeout=3000)

    expect(page.locator("#simStep3View")).to_have_class(ACTIVE_CLASS_RE, timeout=10000)
    expect(page.locator("#simStep3View")).to_contain_text("Điều chuyển")


@pytest.mark.e2e
def test_tc_o03_create_relocation_command_via_dashboard_ui(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """TC-O03 (UC8): Tạo lệnh điều phối từ UI -> hiện thông báo thành công & lưu vào mock_db."""
    reloc_before = len(reset_shared_mock_db.relocations)
    dialogs = open_operator_dashboard(page)

    switch_operator_tab(page, "reloc")
    page.evaluate("() => { OperatorApp.openCreateRelocationModal(); }")
    expect(page.locator("#modalCreateRelocation")).to_have_class(SHOW_CLASS_RE, timeout=5000)

    if page.locator("#relocCount").count():
        page.fill("#relocCount", "2")

    prev = len(dialogs)
    page.evaluate("() => { void OperatorApp.submitRelocation(); }")
    msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)

    assert "lệnh điều phối thành công" in msg.lower(), f"Thông điệp thực tế: {msg}"
    assert len(reset_shared_mock_db.relocations) == reloc_before + 1
    expect(page.locator("#relocationTableBody")).not_to_be_empty()

@pytest.mark.e2e
def test_tc_o04_assign_maintenance_ticket_via_dashboard_ui(page: Page,reset_shared_mock_db,) -> None:
    dialogs = open_operator_dashboard(page)

    switch_operator_tab(page, "maint")
    expect(page.locator("#maintenanceTableBody tr").first).to_be_visible(timeout=5000)

    # Dùng mã phiếu PENDING có thật trong mock_seed.json thay vì 'ERR-8812'
    page.evaluate("() => { OperatorApp.openAssignMaintenanceModal('TICK-802'); }")
    expect(page.locator("#modalAssignMaintenance")).to_have_class(SHOW_CLASS_RE, timeout=5000)

    # Đảm bảo chọn đúng kỹ thuật viên có role MAINTENANCE (STF-02) nếu modal có dropdown
    tech_select = page.locator("#modalAssignMaintenance select").first
    if tech_select.count() and tech_select.locator("option[value='STF-02']").count():
        tech_select.select_option("STF-02")

    if page.locator("#assignNotes").count():
        page.fill("#assignNotes", "Kiểm tra quá nhiệt cổng sạc S02 ngay lập tức.")

    prev = len(dialogs)
    page.evaluate("() => { void OperatorApp.submitMaintenanceAssign(); }")
    msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)

    assert "phân công" in msg.lower() and "không thể" not in msg.lower(), f"Thông điệp thực tế: {msg}"
    ticket = next(t for t in reset_shared_mock_db.maintenance_tickets if t["code"] == "TICK-802")
    assert ticket["status"] == "ASSIGNED"


@pytest.mark.e2e
def test_tc_o05_configure_metro_hub_capacity_updates_ui_and_mock_db(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """TC-O05 (UC12): Chỉnh Hub Ga Metro ĐHQG thành 200 chỗ đỗ, 100 cổng sạc -> verify UI + mock_db."""
    dialogs = open_operator_dashboard(page)

    switch_operator_tab(page, "hub")
    expect(page.locator("#hubsTableBody tr").first).to_be_visible(timeout=5000)

    page.evaluate(
        "() => { OperatorApp.openHubConfigModal('HUB-01', 'Hub Ga Metro ĐHQG', 150, 50, 10.8753, 106.8005); }"
    )
    expect(page.locator("#modalHubConfig")).to_have_class(SHOW_CLASS_RE, timeout=5000)

    page.fill("#configParkingCap", "200")
    page.fill("#configChargerCap", "100")

    prev = len(dialogs)
    page.evaluate("() => { void OperatorApp.saveHubConfig(); }")
    msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)

    assert "lưu cấu hình mới" in msg.lower(), f"Thông điệp thực tế: {msg}"
    expect(page.locator("#hubsTableBody")).to_contain_text("200")
    expect(page.locator("#hubsTableBody")).to_contain_text("100")

    metro_hub = find_hub_in_db(reset_shared_mock_db, "HUB-01")
    assert metro_hub["parking_capacity"] == 200
    assert metro_hub["charger_capacity"] == 100


@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-FE-04 (NFR06): BE chưa bật cờ system_halted chặn booking; FE/user chưa nhận tín hiệu khóa UI trong < 2s",
    strict=True,
)
def test_nfr06_emergency_halt_locks_user_ui_and_blocks_booking_under_2s(
    browser: Browser,
    reset_shared_mock_db,
) -> None:
    op_ctx = browser.new_context()
    user_ctx = browser.new_context()
    block_external_requests(op_ctx)
    block_external_requests(user_ctx)
    try:
        op_page = op_ctx.new_page()
        user_page = user_ctx.new_page()

        open_operator_dashboard(op_page)
        login_end_user(user_page)
        bookings_before = len(reset_shared_mock_db.bookings)

        # Ghi nhận mốc thời gian ngay khi Operator kích hoạt Dừng khẩn cấp
        t0 = time.perf_counter()
        op_page.evaluate("() => { OperatorApp.openEmergencyModal(); void OperatorApp.confirmEmergency(); }")

        expect(user_page.locator("body")).to_contain_text("Tạm dừng khẩn cấp", timeout=2000)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 2000, f"Thời gian khóa UI vượt ngưỡng: {elapsed_ms:.1f}ms"

        # Thử tạo booking mới sau khi halt -> phải bị từ chối và không phát sinh booking mới
        res = user_page.request.post(
            "http://127.0.0.1:8000/api/bookings",
            data={
                "plan_type": "rental",
                "hub_id": "hub-01",
                "resource_name": "XE-031 · Xe đạp điện",
            },
        )
        assert res.status in (403, 423, 503), f"Hệ thống đã halt nhưng API booking vẫn trả {res.status}"
        assert len(reset_shared_mock_db.bookings) == bookings_before
    finally:
        op_ctx.close()
        user_ctx.close()
@pytest.mark.e2e
@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-BE-04 (NFR07): Telemetry sự kiện can thiệp của Operator thiếu 3 trường chuẩn Audit Log (actor, action, result)",
    strict=True,
)
def test_nfr07_operator_intervention_writes_complete_audit_log(page: Page) -> None:
    dialogs = open_operator_dashboard(page)
    prev = len(dialogs)
    page.evaluate("() => { void OperatorApp.confirmEmergency(); }")
    wait_for_new_dialog(page, dialogs, prev, timeout_ms=3000)

    res = page.request.get("http://127.0.0.1:8000/api/v1/operator/dashboard/telemetry")
    assert res.status == 200
    events = res.json()
    halt_events = [e for e in events if "khẩn cấp" in str(e).lower() or "halt" in str(e).lower()]
    assert len(halt_events) > 0

    latest = halt_events[0]
    required_fields = ("actor", "timestamp", "action", "result")
    for field in required_fields:
        assert field in latest and str(latest[field]).strip() != "", (
            f"Bản ghi kiểm toán thiếu hoặc rỗng trường '{field}': {latest}"
        )

@pytest.mark.e2e
@pytest.mark.nfr
def test_nfr10_hub_config_change_propagates_to_user_within_60s(browser: Browser) -> None:
    """NFR10: Mở sẵn trang User trước -> Operator đổi sức chứa Hub -> User thấy giá trị mới trong <= 60s."""
    op_ctx = browser.new_context()
    user_ctx = browser.new_context()
    block_external_requests(op_ctx)
    block_external_requests(user_ctx)
    try:
        op_page = op_ctx.new_page()
        user_page = user_ctx.new_page()

        # Mở cả 2 phía trước khi thay đổi cấu hình
        dialogs = open_operator_dashboard(op_page)
        login_end_user(user_page)
        user_page.evaluate("() => { void App.selectHubAndOpenDetail('hub-01'); }")
        expect(user_page.locator("#screen-hub-detail")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

        op_page.evaluate(
            "() => { OperatorApp.openHubConfigModal('HUB-01', 'Hub Ga Metro ĐHQG', 150, 50, 10.8753, 106.8005); }"
        )
        op_page.fill("#configParkingCap", "220")
        op_page.fill("#configChargerCap", "110")

        prev = len(dialogs)
        op_page.evaluate("() => { void OperatorApp.saveHubConfig(); }")
        wait_for_new_dialog(op_page, dialogs, prev, timeout_ms=5000)

        # Kiểm tra dữ liệu trả về cho phiên User đang mở cập nhật trong ngưỡng <= 60s
        deadline = time.perf_counter() + 60
        while time.perf_counter() < deadline:
            hub_data = user_page.request.get("http://127.0.0.1:8000/api/hubs/hub-01").json()
            if hub_data.get("parking_capacity") == 220 and hub_data.get("charger_capacity") == 110:
                break
            user_page.wait_for_timeout(500)
        assert hub_data["parking_capacity"] == 220
        assert hub_data["charger_capacity"] == 110
    finally:
        op_ctx.close()
        user_ctx.close()

@pytest.mark.e2e
@pytest.mark.nfr
def test_nfr13_high_load_response_and_dispatch_recommendations_timing(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """NFR13: Đẩy tải Hub Ga Metro >= 90% -> Dashboard kích hoạt ứng phó <= 5s và đề xuất phân bổ <= 10s."""
    hub = find_hub_in_db(reset_shared_mock_db, "hub-01")
    hub["available_parking"] = max(1, int(hub["parking_capacity"] * 0.05))
    hub["available_bikes"] = 1

    open_operator_dashboard(page)
    switch_operator_tab(page, "sim")
    page.evaluate("() => { OperatorApp.goToSimStep(2); OperatorApp.triggerSimulationCalculation(); }")

    expect(page.locator("#simStep3View")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#simStep3View")).to_contain_text("Điều chuyển", timeout=10000)