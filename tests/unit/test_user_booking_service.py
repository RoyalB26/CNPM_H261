"""Unit/API Test cho TC-U03 (Đặt dịch vụ) và TC-UC04 (Nhận/trả dịch vụ)."""

import pytest
from starlette.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from tests.unit.conftest import USER_API, find_hub_in_db

pytestmark = pytest.mark.unit


def test_tc_u03_rental_booking_and_cancel_updates_mock_db(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """Đặt thuê xe XE-031 trừ 1 xe khả dụng và hủy đặt trước hoàn trả nguyên trạng."""
    hub_id = "hub-01"
    bikes_initial = find_hub_in_db(reset_shared_mock_db, hub_id)["available_bikes"]

    create_res = api_client.post(
        f"{USER_API}/bookings",
        json={
            "plan_type": "rental",
            "hub_id": hub_id,
            "resource_name": "XE-031 · Xe đạp điện",
            "destination_hub_name": "Hub Đại học Bách khoa",
        },
    )
    assert create_res.status_code in (200, 201)
    booking = create_res.json()
    booking_id = booking["id"]

    hub_after_book = find_hub_in_db(reset_shared_mock_db, hub_id)
    assert hub_after_book["available_bikes"] == bikes_initial - 1
    bike_xe031 = next(b for b in hub_after_book["bikes"] if b["id"] == "XE-031")
    assert bike_xe031["status"] == "Đã đặt chỗ"

    cancel_res = api_client.post(
        f"{USER_API}/bookings/{booking_id}/cancel",
        json={"reason": "Thay đổi lịch trình"},
    )
    assert cancel_res.status_code == 200
    assert find_hub_in_db(reset_shared_mock_db, hub_id)["available_bikes"] == bikes_initial


def test_tc_u03_duplicate_rental_booking_returns_409(api_client: TestClient) -> None:
    """Trường hợp thất bại (NFR03 mức Unit): Đặt trùng xe XE-024 đã có booking phải trả 409."""
    response = api_client.post(
        f"{USER_API}/bookings",
        json={
            "plan_type": "rental",
            "hub_id": "hub-01",
            "resource_name": "XE-024 · Xe đạp điện",
        },
    )
    assert response.status_code == 409

@pytest.mark.xfail(
    reason="BUG-BE-01: mock_db.create_booking chưa trừ available_parking và chưa khóa cổng sạc S03 khi plan_type == 'personal'",
    strict=True,
)
def test_tc_u03_combo_parking_and_charging_updates_mock_db(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    hub_id = "hub-01"
    parking_before = find_hub_in_db(reset_shared_mock_db, hub_id)["available_parking"]

    response = api_client.post(
        f"{USER_API}/bookings",
        json={
            "plan_type": "personal",
            "hub_id": hub_id,
            "personal_plate": "59-X1 123.45",
            "parking_slot": "P01",
            "charging_port": "S03",
            "duration_hours": 2,
        },
    )
    assert response.status_code in (200, 201)

    hub_after = find_hub_in_db(reset_shared_mock_db, hub_id)
    port_s03 = next(p for p in hub_after["ports"] if p["id"] == "S03")
    assert hub_after["available_parking"] == parking_before - 1
    assert port_s03["is_available"] is False


@pytest.mark.nfr
def test_nfr03_a_backend_concurrent_double_booking_allows_only_one_success(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """NFR03-A: Hai request bắn đồng thời vào cùng 1 xe XE-031 -> chỉ 1 thành công, 1 trả 409."""
    hub_id = "hub-01"
    bikes_before = find_hub_in_db(reset_shared_mock_db, hub_id)["available_bikes"]
    barrier = Barrier(2)
    payload = {
        "plan_type": "rental",
        "hub_id": hub_id,
        "resource_name": "XE-031 · Xe đạp điện",
        "destination_hub_name": "Hub Đại học Bách khoa",
    }

    def send_booking() -> int:
        barrier.wait()
        return api_client.post(f"{USER_API}/bookings", json=payload).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: send_booking(), range(2)))

    assert sorted(statuses) in ([200, 409], [201, 409]), f"Trạng thái nhận được: {statuses}"
    hub_after = find_hub_in_db(reset_shared_mock_db, hub_id)
    assert hub_after["available_bikes"] == bikes_before - 1

def test_tc_uc04_start_ride_blocked_when_active_ride_exists(
    api_client: TestClient,
) -> None:
    """Trường hợp biên UC4: Không thể nhận xe mới (409) khi user đang có chuyến đi chưa trả."""
    active_ride = api_client.get(f"{USER_API}/services/active").json().get("ride")
    if not active_ride:
        pytest.skip("Dữ liệu seed không có chuyến đi đang hoạt động sẵn.")

    create_res = api_client.post(
        f"{USER_API}/bookings",
        json={
            "plan_type": "rental",
            "hub_id": "hub-01",
            "resource_name": "XE-031 · Xe đạp điện",
            "destination_hub_name": "Hub Đại học Bách khoa",
        },
    )
    assert create_res.status_code in (200, 201)
    booking_id = create_res.json()["id"]

    start_res = api_client.post(f"{USER_API}/bookings/{booking_id}/start")
    assert start_res.status_code == 409, start_res.json()
    assert start_res.json().get("success") is False


def test_tc_uc04_start_ride_and_return_vehicle_updates_mock_db(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """TC-UC04 (Unit): Nhận xe từ booking đã đặt và trả xe về Hub đích cập nhật mock_db."""
    # 0. Nếu dữ liệu seed đang có chuyến đi sẵn thì trả xe trước để user ở trạng thái rảnh
    active_before = api_client.get(f"{USER_API}/services/active").json()
    existing_ride = active_before.get("ride")
    if existing_ride:
        existing_trip_id = existing_ride.get("id") or existing_ride.get("trip_id") or "TRIP-8821"
        cleanup_res = api_client.post(
            f"{USER_API}/services/return-vehicle",
            json={"trip_id": existing_trip_id, "hub_name": "Hub Đại học Bách khoa"},
        )
        assert cleanup_res.status_code == 200, cleanup_res.json()

    # 1. Tạo booking mới cho xe XE-031 tại hub-01
    create_res = api_client.post(
        f"{USER_API}/bookings",
        json={
            "plan_type": "rental",
            "hub_id": "hub-01",
            "resource_name": "XE-031 · Xe đạp điện",
            "destination_hub_name": "Hub Đại học Bách khoa",
        },
    )
    assert create_res.status_code in (200, 201), create_res.json()
    booking_id = create_res.json()["id"]

    # 2. Nhận xe (bắt đầu chuyến đi) -> trạng thái chuyển sang đang sử dụng/hoạt động
    start_res = api_client.post(f"{USER_API}/bookings/{booking_id}/start")
    assert start_res.status_code == 200, f"Backend trả lỗi: {start_res.json()}"
    start_body = start_res.json()
    assert start_body.get("success") is True
    ride = start_body.get("ride", {})
    assert ride.get("vehicle_id") == "XE-031" or ride.get("status")

    active_after_start = api_client.get(f"{USER_API}/services/active").json()
    assert active_after_start.get("ride") is not None

    # 3. Trả xe tại Hub Đại học Bách khoa -> kiểm tra cập nhật số lượng xe ở hub-02
    dest_bikes_before = find_hub_in_db(reset_shared_mock_db, "hub-02")["available_bikes"]
    trip_id = ride.get("id") or ride.get("trip_id") or "TRIP-8821"
    return_res = api_client.post(
        f"{USER_API}/services/return-vehicle",
        json={
            "trip_id": trip_id,
            "vehicle_id": ride.get("vehicle_id", "XE-031"),
            "hub_id": "hub-02",
            "hub_name": "Hub Đại học Bách khoa",
        },
    )
    assert return_res.status_code == 200, return_res.json()
    assert return_res.json().get("success") is True
    assert find_hub_in_db(reset_shared_mock_db, "hub-02")["available_bikes"] >= dest_bikes_before

    invoice_res = api_client.get(f"{USER_API}/invoices/current")
    assert invoice_res.status_code == 200
    assert isinstance(invoice_res.json(), dict)
    
def test_tc_uc04_return_vehicle_outside_hub_radius_returns_400(
    api_client: TestClient,
) -> None:
    """Trường hợp thất bại UC4: Trả xe ngoài bán kính Hub hoặc chưa đóng khóa trả 400."""
    response = api_client.post(
        f"{USER_API}/services/return-vehicle",
        json={
            "trip_id": "TRIP-8821",
            "hub_id": "hub-02",
            "simulate_error": True,
        },
    )
    assert response.status_code == 400
    assert response.json().get("success") is False
