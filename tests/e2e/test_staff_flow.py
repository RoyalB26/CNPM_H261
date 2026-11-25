"""Kiểm thử E2E cho ứng dụng Nhân viên hiện trường & Bảo vệ (FE/staff/)."""

from playwright.sync_api import Page, expect
import pytest

from tests.e2e.conftest import (
    ACTIVE_CLASS_RE,
    BACKEND_URL,
    api_operator_headers,
    login_staff,
    wait_for_new_dialog,
)
from tests.unit.conftest import find_hub_in_db


@pytest.mark.e2e
def test_tc_s01_relocation_staff_scan_qr_and_complete_handover(page: Page) -> None:
    """TC-S01 (UC8): NV Điều chuyển đăng nhập, quét QR đối soát xe thành Done và bàn giao tại Hub đích."""
    dialogs = login_staff(page, username="staff_01", password="staff123")

    page.evaluate("() => { StaffApp.switchRole('relocation'); }")
    expect(page.locator("#screen-reloc-route")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    page.evaluate("() => { StaffApp.goToScreen('screen-reloc-handover'); }")
    waiting_row = page.locator("#reconcileRows .reconcile-row.waiting").first
    expect(waiting_row).to_be_visible(timeout=5000)

    prev = len(dialogs)
    waiting_row.click()
    scan_msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)
    assert "đã quét xác nhận xe" in scan_msg.lower(), f"Thông điệp thực tế: {scan_msg}"

    prev = len(dialogs)
    page.evaluate("() => { void StaffApp.completeHandover(); }")
    handover_msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)
    assert "hoàn tất bàn giao" in handover_msg.lower(), (
        f"Thông điệp thực tế: {handover_msg}"
    )
    expect(page.locator("#screen-reloc-route")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)


@pytest.mark.e2e
def test_tc_s02_maintenance_technician_resolve_task_ui(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """TC-S02 (UC9): NV Bảo trì tiếp nhận phiếu gán cho STF-02, xác thực thiết bị và gửi kết quả chuyển xưởng."""
    hub_before = find_hub_in_db(reset_shared_mock_db, "hub-02")
    bikes_before = hub_before["available_bikes"]

    # Tạo phiếu bảo trì hợp lệ cho XE-052 tại hub-02 và gán trực tiếp cho STF-02 (staff_b)
    op_headers = api_operator_headers(page)
    create_res = page.request.post(
        f"{BACKEND_URL}/api/v1/operator/maintenance/tickets",
        headers=op_headers,
        data={
            "device_code": "XE-052",
            "hub_name": hub_before["name"],
            "source": "Operator thủ công",
            "fault_category": "Xe XE-052 không khởi động",
            "severity": "Khẩn cấp",
            "description": "Xe XE-052 không lên nguồn, cần kiểm tra tại xưởng.",
            "assigned_staff_id": "STF-02",
        },
    )
    assert create_res.status == 201, create_res.text()
    task_code = create_res.json()["ticket"]["ticket_code"]

    dialogs = login_staff(page, username="staff_b", password="staff123")
    page.evaluate("() => { StaffApp.switchRole('maintenance'); }")
    expect(page.locator("#screen-maint-list")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    ticket_card = page.locator("#maintTasksContainer .staff-card", has_text=task_code).first
    expect(ticket_card).to_be_visible(timeout=5000)
    ticket_card.locator("button", has_text="XEM VÀ TIẾP NHẬN").click()
    expect(page.locator("#screen-maint-detail")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    page.locator("#screen-maint-detail .btn-staff-primary").click()
    expect(page.locator("#screen-maint-scan")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    page.locator("#screen-maint-scan .btn-staff-primary").click()
    notes_box = page.locator("#maintTechNotes")
    expect(notes_box).to_be_visible(timeout=5000)

    workshop_card = page.locator(".radio-card-select", has_text="xưởng").first
    expect(workshop_card).to_be_visible(timeout=5000)
    workshop_card.click()
    notes_box.fill("Xe XE-052 hỏng mạch điều khiển nguồn, cần chuyển về xưởng kiểm tra.")

    prev = len(dialogs)
    page.evaluate("() => { void StaffApp.submitMaintResult(); }")
    msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)
    assert "chuyển thiết bị về xưởng" in msg.lower(), f"Thông điệp thực tế: {msg}"
    expect(page.locator("#screen-maint-list")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    hub_after = find_hub_in_db(reset_shared_mock_db, "hub-02")
    assert hub_after["available_bikes"] == bikes_before - 1
    bike_xe052 = next(b for b in hub_after["bikes"] if b["id"] == "XE-052")
    assert bike_xe052["workshop"] is True
    assert bike_xe052["status"] == "Chuyển xưởng"


@pytest.mark.e2e
def test_tc_s03_security_guard_personal_vehicle_checkin_and_checkout(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """TC-S03 (UC6): Bảo vệ check-in xe cá nhân (giảm chỗ trống) và thu tiền mặt check-out trên UI."""
    dialogs = login_staff(page, username="staff_b", password="staff123")

    page.evaluate("() => { StaffApp.switchRole('security'); }")
    expect(page.locator("#screen-guard-checkin")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    hub = find_hub_in_db(reset_shared_mock_db, "hub-02")
    slots_before = hub["available_parking"]

    # Gọi StaffApi.parkingCheckin với Hub/ô đỗ thật trong mock_seed.json (hub-02 / P11)
    checkin_res = page.evaluate(
        """async (hubName) => {
            return await StaffApi.parkingCheckin({
                license_plate: "59-B2 777.88",
                parking_bay: "Khu A",
                parking_slot: "P11",
                hub_name: hubName,
                guard_id: "STF-02"
            });
        }""",
        hub["name"],
    )
    ticket_code = checkin_res.get("ticket_code", "")
    assert ticket_code.startswith("PRK-"), f"Check-in rơi xuống mock fallback: {checkin_res}"

    slots_after_checkin = find_hub_in_db(reset_shared_mock_db, "hub-02")["available_parking"]
    assert slots_after_checkin == slots_before - 1, (
        f"Số chỗ trống hub-02 không giảm sau check-in: trước={slots_before}, sau={slots_after_checkin}"
    )

    page.wait_for_timeout(50)
    page.evaluate("(code) => { void StaffApp.openCheckoutScreen(code); }", ticket_code)
    expect(page.locator("#screen-guard-checkout")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)
    expect(page.locator("#checkoutTicketCode")).to_contain_text(ticket_code)

    prev = len(dialogs)
    page.evaluate("() => { void StaffApp.confirmCashReceived(); }")
    checkout_msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)
    assert "tiền mặt thành công" in checkout_msg.lower(), f"Thông điệp thực tế: {checkout_msg}"
    expect(page.locator("#screen-guard-shift")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    slots_after_checkout = find_hub_in_db(reset_shared_mock_db, "hub-02")["available_parking"]
    assert slots_after_checkout == slots_before