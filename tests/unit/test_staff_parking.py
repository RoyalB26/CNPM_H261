"""Unit/API Test cho TC-S03: Bảo vệ check-in/check-out xe cá nhân (UC6)."""

import time
import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import STAFF_API, find_hub_in_db

pytestmark = pytest.mark.unit


def test_tc_s03_personal_vehicle_checkin_decrements_available_slots(
    api_client: TestClient,
    staff_headers: dict[str, str],
    reset_shared_mock_db,
) -> None:
    """TC-S03 (Unit): Check-in xe cá nhân vào Hub làm giảm 1 chỗ trống trên mock_db."""
    hub_id = "hub-02"
    hub = find_hub_in_db(reset_shared_mock_db, hub_id)
    slots_before = hub["available_parking"]

    checkin_res = api_client.post(
        f"{STAFF_API}/parking/checkin",
        headers=staff_headers,
        json={
            "hub_name": hub["name"],
            "license_plate": "59-X1 999.88",
            "parking_bay": "Khu A",
            "parking_slot": "P11",
        },
    )
    assert checkin_res.status_code in (200, 201), checkin_res.text
    body = checkin_res.json()
    assert body.get("ticket_code") is not None

    slots_after = find_hub_in_db(reset_shared_mock_db, hub_id)["available_parking"]
    assert slots_after == slots_before - 1


def test_tc_s03_shift_summary_returns_reconciliation_data(
    api_client: TestClient,
    staff_headers: dict[str, str],
) -> None:
    """Kiểm thử API tổng hợp đối soát doanh thu ca trực của bảo vệ."""
    response = api_client.get(
        f"{STAFF_API}/parking/shift-summary",
        headers=staff_headers,
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), dict)


def test_tc_s03_personal_vehicle_checkout_preview_and_confirm(
    api_client: TestClient,
    staff_headers: dict[str, str],
    reset_shared_mock_db,
) -> None:
    """Kiểm thử tính cước và xác nhận thu tiền mặt khi xe cá nhân rời Hub."""
    hub = find_hub_in_db(reset_shared_mock_db, "hub-02")
    checkin_res = api_client.post(
        f"{STAFF_API}/parking/checkin",
        headers=staff_headers,
        json={
            "hub_name": hub["name"],
            "license_plate": "59-X1 888.77",
            "parking_bay": "Khu A",
            "parking_slot": "P11",
        },
    )
    assert checkin_res.status_code in (200, 201), checkin_res.text
    ticket_code = checkin_res.json()["ticket_code"]

    time.sleep(0.02)
    preview_res = api_client.get(
        f"{STAFF_API}/parking/checkout/{ticket_code}",
        headers=staff_headers,
    )
    assert preview_res.status_code == 200, preview_res.text
    preview = preview_res.json()
    assert preview.get("total_fee_vnd", 0) > 0

    confirm_res = api_client.post(
        f"{STAFF_API}/parking/checkout/confirm",
        headers=staff_headers,
        json={
            "ticket_code": ticket_code,
            "quote_token": preview["quote_token"],
            "cash_received": preview["total_fee_vnd"],
        },
    )
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json().get("success") is True