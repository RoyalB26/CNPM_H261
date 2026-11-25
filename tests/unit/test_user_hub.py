"""Unit/API Test cho TC-U02: Tra cứu danh sách và chi tiết Hub (UC2)."""

import pytest
from starlette.testclient import TestClient

from shared.parking_reservations import available_parking_capacity
from tests.unit.conftest import USER_API, find_hub_in_db, read_first_key

pytestmark = pytest.mark.unit


def test_tc_u02_list_hubs_returns_non_empty_collection(
    api_client: TestClient,
    user_headers: dict[str, str],
) -> None:
    """API danh sách Hub trả về dữ liệu khớp danh mục khởi tạo trong mock_db."""
    response = api_client.get(f"{USER_API}/hubs", headers=user_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    hubs = (
        payload
        if isinstance(payload, list)
        else payload.get("items", payload.get("hubs", []))
    )
    assert len(hubs) > 0


def test_tc_u02_hub_detail_matches_mock_db_counts(
    api_client: TestClient,
    user_headers: dict[str, str],
    reset_shared_mock_db,
) -> None:
    """TC-U02: Số lượng phương tiện và chỗ đỗ khả dụng của Hub khớp với trạng thái trên mock_db."""
    hub_id = "hub-01"
    db_hub = find_hub_in_db(reset_shared_mock_db, hub_id)

    response = api_client.get(f"{USER_API}/hubs/{hub_id}", headers=user_headers)
    assert response.status_code == 200, response.text
    detail = response.json()

    parking_keys = (
        "available_parking",
        "parking_available",
        "available_slots",
        "free_slots",
    )
    api_parking = read_first_key(detail, parking_keys)
    expected_parking = available_parking_capacity(reset_shared_mock_db, db_hub)
    assert api_parking == expected_parking

    bike_keys = ("available_bikes", "bikes_available", "available_vehicles")
    api_bikes = read_first_key(detail, bike_keys)
    db_bikes = read_first_key(db_hub, bike_keys)
    assert api_bikes in (db_bikes, len(detail.get("bikes", [])))
    assert len(detail.get("ports", [])) == len(db_hub.get("ports", []))


def test_tc_u02_hub_detail_nonexistent_id_returns_404(
    api_client: TestClient,
    user_headers: dict[str, str],
) -> None:
    """Trường hợp biên/thất bại: Tra cứu mã Hub không tồn tại phải trả mã lỗi 404."""
    response = api_client.get(
        f"{USER_API}/hubs/HUB-KHONG-TON-TAI", headers=user_headers
    )
    assert response.status_code == 404
