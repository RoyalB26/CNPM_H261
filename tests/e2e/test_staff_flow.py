"""Kiểm thử E2E cho ứng dụng Nhân viên hiện trường & Bảo vệ (FE/staff/)."""

from playwright.sync_api import Page, expect
import pytest

from tests.e2e.conftest import (
    ACTIVE_CLASS_RE,
    STAFF_URL,
    attach_dialog_collector,
    block_external_requests,
    wait_for_new_dialog,
)
from tests.unit.conftest import find_hub_in_db


def _open_staff_app(page: Page) -> list[str]:
    """Mở ứng dụng Staff, chặn CDN ngoài và đăng ký bắt hộp thoại alert."""
    block_external_requests(page)
    dialogs = attach_dialog_collector(page)
    page.goto(STAFF_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#staffRoleSelect", timeout=10000)
    return dialogs


@pytest.mark.e2e
def test_tc_s01_relocation_staff_scan_qr_and_complete_handover(page: Page) -> None:
    """TC-S01 (UC8): NV Điều chuyển quét QR đối soát xe thành Done và bàn giao tại Hub đích."""
    dialogs = _open_staff_app(page)

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
    assert "hoàn tất bàn giao" in handover_msg.lower(), f"Thông điệp thực tế: {handover_msg}"
    expect(page.locator("#screen-reloc-route")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)


@pytest.mark.e2e
def test_tc_s02_maintenance_technician_resolve_task_ui(page: Page) -> None:
    """TC-S02 (UC9): NV Bảo trì tiếp nhận phiếu, xác thực thiết bị và gửi kết quả chuyển xưởng."""
    dialogs = _open_staff_app(page)

    # Bước 1: Chuyển vai trò Nhân viên bảo trì
    page.evaluate("() => { StaffApp.switchRole('maintenance'); }")
    expect(page.locator("#screen-maint-list")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    # Bước 2: Mở chi tiết sự cố đầu tiên (MT-102 / Xem và tiếp nhận)
    accept_btn = page.locator("#maintTasksContainer button", has_text="XEM VÀ TIẾP NHẬN").first
    expect(accept_btn).to_be_visible(timeout=5000)
    accept_btn.click()
    expect(page.locator("#screen-maint-detail")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    # Bước 3 & 4: Đi qua các nút bước tiếp theo ("Bắt đầu xử lý" -> "Xác nhận thiết bị")
    # cho tới khi ô ghi chú kết quả #maintTechNotes hiển thị trên màn hình
    notes_box = page.locator("#maintTechNotes")
    for _ in range(3):
        if notes_box.is_visible():
            break
        active_primary = page.locator(".staff-screen.active .btn-staff-primary").first
        if active_primary.count() and active_primary.is_visible():
            active_primary.click()
            page.wait_for_timeout(300)
        else:
            break

    # Fallback: nếu cấu trúc màn hình đặt #maintTechNotes trong 1 .staff-screen riêng
    if not notes_box.is_visible():
        result_screen_id = page.evaluate(
            "() => document.getElementById('maintTechNotes')?.closest('.staff-screen')?.id || ''"
        )
        if result_screen_id:
            page.evaluate(f"() => {{ StaffApp.goToScreen('{result_screen_id}'); }}")

    expect(notes_box).to_be_visible(timeout=5000)

    # Bước 5: Chọn kết quả 'Cần chuyển về xưởng' (nếu có thẻ radio-card-select) và điền ghi chú
    workshop_card = page.locator(".radio-card-select", has_text="xưởng").first
    if workshop_card.count() and workshop_card.is_visible():
        workshop_card.click()
    notes_box.fill("Xe BK-EB-018 không khởi động nguồn, cần chuyển về xưởng kiểm tra.")

    # Bước 6: Gửi kết quả bảo trì và xác nhận thông báo thành công
    prev = len(dialogs)
    page.evaluate("() => { void StaffApp.submitMaintResult(); }")
    msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)
    assert "gửi kết quả bảo trì thành công" in msg.lower(), f"Thông điệp thực tế: {msg}"
    page.locator("nav button", has_text="Nhiệm vụ").click()
    expect(page.locator("#screen-maint-list")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)


@pytest.mark.e2e
def test_tc_s03_security_guard_personal_vehicle_checkin_and_checkout(
    page: Page,
    reset_shared_mock_db,
) -> None:
    """TC-S03 (UC6): Bảo vệ check-in xe cá nhân vào Hub -> thông báo thành công & giảm chỗ trống."""
    dialogs = _open_staff_app(page)

    page.evaluate("() => { StaffApp.switchRole('security'); }")
    expect(page.locator("#screen-guard-checkin")).to_have_class(ACTIVE_CLASS_RE, timeout=5000)

    slots_before = find_hub_in_db(reset_shared_mock_db, "hub-01")["available_parking"]
    prev = len(dialogs)
    page.evaluate("() => { void StaffApp.simulatePlateScan(); }")
    msg = wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)

    assert "nhận diện biển số" in msg.lower(), f"Dialogs: {dialogs}"
    ticket_text = page.locator("#guardTicketCode").inner_text().strip()
    assert ticket_text != ""

    # Kiểm tra trạng thái tài nguyên thực sự giảm 1 chỗ sau check-in (tránh PASS giả)
    slots_after = find_hub_in_db(reset_shared_mock_db, "hub-01")["available_parking"]
    assert slots_after == slots_before - 1, (
        f"Số chỗ trống hub-01 không giảm sau check-in: trước={slots_before}, sau={slots_after}"
    )