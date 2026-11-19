"""Unit/API Test cho TC-S03: Bảo vệ check-in/check-out xe cá nhân (UC6)."""

import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import STAFF_API, find_hub_in_db

pytestmark = pytest.mark.unit


def test_tc_s03_personal_vehicle_checkin_decrements_available_slots(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """TC-S03 (Unit): Check-in xe cá nhân vào Hub Ga Metro làm giảm 1 chỗ trống trên mock_db."""
    hub_id = "hub-01"
    slots_before = find_hub_in_db(reset_shared_mock_db, hub_id)["available_parking"]

    checkin_res = api_client.post(
        f"{STAFF_API}/parking/checkin",
        json={
            "hub_id": hub_id,
            "hub_name": "Hub Ga Metro ĐHQG",
            "license_plate": "59-X1 999.88",
            "plate_number": "59-X1 999.88",
            "vehicle_type": "Xe máy điện",
        },
    )
    assert checkin_res.status_code in (200, 201)
    body = checkin_res.json()
    assert body.get("ticket_code") is not None

    slots_after = find_hub_in_db(reset_shared_mock_db, hub_id)["available_parking"]
    assert slots_after == slots_before - 1


def test_tc_s03_shift_summary_returns_reconciliation_data(api_client: TestClient) -> None:
    """Kiểm thử API tổng hợp đối soát doanh thu ca trực của bảo vệ."""
    response = api_client.get(f"{STAFF_API}/parking/shift-summary")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_tc_s03_personal_vehicle_checkout_preview_and_confirm(
    api_client: TestClient,
) -> None:
    """Kiểm thử tính cước và xác nhận thu tiền mặt khi xe cá nhân rời Hub."""
    checkin_res = api_client.post(
        f"{STAFF_API}/parking/checkin",
        json={
            "hub_id": "hub-01",
            "hub_name": "Hub Ga Metro ĐHQG",
            "license_plate": "59-X1 888.77",
            "vehicle_type": "Xe máy điện",
        },
    )
    ticket_code = checkin_res.json()["ticket_code"]

    preview_res = api_client.get(f"{STAFF_API}/parking/checkout/{ticket_code}")
    assert preview_res.status_code == 200
    assert preview_res.json().get("total_fee_vnd", 0) > 0

    confirm_res = api_client.post(
        f"{STAFF_API}/parking/checkout/confirm",
        json={"ticket_code": ticket_code},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json().get("success") is True