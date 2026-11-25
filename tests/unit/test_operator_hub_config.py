"""Unit/API Test cho TC-O05: Cấu hình sức chứa và tạm ngưng Hub (UC12)."""

import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import OPERATOR_API, find_hub_in_db, read_first_key

pytestmark = pytest.mark.unit


def test_tc_o05_update_metro_hub_capacity_persists_to_mock_db(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """TC-O05 (Unit): Cập nhật Hub Ga Metro ĐHQG thành 200 chỗ đỗ và 100 cổng sạc."""
    hub_id = "HUB-01"
    payload = {
        "parking_capacity": 200,
        "charger_capacity": 100,
    }
    response = api_client.put(f"{OPERATOR_API}/hubs/{hub_id}/config", json=payload)
    assert response.status_code == 200
    assert response.json().get("success") is True

    hub_after = find_hub_in_db(reset_shared_mock_db, hub_id)
    assert hub_after["parking_capacity"] == 200
    assert hub_after["charger_capacity"] == 100


def test_tc_o05_deactivate_hub_updates_status_to_deactivated(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """Kiểm thử API tạm ngưng Hub chuyển đúng trường status sang DEACTIVATED."""
    response = api_client.post(
        f"{OPERATOR_API}/hubs/HUB-01/deactivate",
        json={"reason": "Bảo trì lưới điện định kỳ"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    assert find_hub_in_db(reset_shared_mock_db, "HUB-01")["status"] == "DEACTIVATED"


def test_tc_o05_deactivate_unknown_hub_returns_404(api_client: TestClient) -> None:
    """Trường hợp thất bại: Tạm ngưng Hub không tồn tại phải trả 404."""
    response = api_client.post(
        f"{OPERATOR_API}/hubs/HUB-999/deactivate",
        json={"reason": "Kiểm thử biên"},
    )
    assert response.status_code == 404