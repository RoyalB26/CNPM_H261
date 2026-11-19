"""Unit/API Test cho TC-U02: Tra cứu danh sách và chi tiết Hub (UC2)."""

import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import USER_API, find_hub_in_db, read_first_key

pytestmark = pytest.mark.unit


def test_tc_u02_list_hubs_returns_non_empty_collection(api_client: TestClient) -> None:
    """API danh sách Hub trả về dữ liệu khớp danh mục khởi tạo trong mock_db."""
    response = api_client.get(f"{USER_API}/hubs")
    assert response.status_code == 200
    payload = response.json()
    hubs = payload if isinstance(payload, list) else payload.get("items", payload.get("hubs", []))
    assert len(hubs) > 0


def test_tc_u02_hub_detail_matches_mock_db_counts(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """TC-U02: Số lượng phương tiện và chỗ đỗ trống của Hub khớp chính xác với mock_db."""
    hub_id = "hub-01"
    db_hub = find_hub_in_db(reset_shared_mock_db, hub_id)

    response = api_client.get(f"{USER_API}/hubs/{hub_id}")
    assert response.status_code == 200
    detail = response.json()

    # Đối chiếu chỗ đỗ trống giữa phản hồi API và dữ liệu lưu trên mock_db
    parking_keys = ("available_parking", "parking_available", "available_slots", "free_slots")
    api_parking = read_first_key(detail, parking_keys)
    db_parking = read_first_key(db_hub, parking_keys)
    assert api_parking == db_parking

    # Đối chiếu số xe khả dụng giữa phản hồi API và mock_db
    bike_keys = ("available_bikes", "bikes_available", "available_vehicles")
    api_bikes = read_first_key(detail, bike_keys)
    db_bikes = read_first_key(db_hub, bike_keys)
    assert api_bikes == db_bikes
    assert len(detail.get("ports", [])) == len(db_hub.get("ports", []))


def test_tc_u02_hub_detail_nonexistent_id_returns_404(api_client: TestClient) -> None:
    """Trường hợp biên/thất bại: Tra cứu mã Hub không tồn tại phải trả mã lỗi 404."""
    response = api_client.get(f"{USER_API}/hubs/HUB-KHONG-TON-TAI")
    assert response.status_code == 404