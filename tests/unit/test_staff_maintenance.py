"""Unit/API Test cho TC-S02: Bảo trì thiết bị hiện trường (UC9)."""

import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import STAFF_API, find_hub_in_db

pytestmark = pytest.mark.unit


def test_tc_s02_get_maintenance_task_tick801_returns_details(
    api_client: TestClient,
) -> None:
    """Tra cứu chi tiết phiếu bảo trì thực tế trong mock_db (TICK-801)."""
    response = api_client.get(f"{STAFF_API}/maintenance/tasks/TICK-801")
    assert response.status_code == 200
    body = response.json()
    assert body.get("task_code") == "TICK-801"


def test_tc_s02_verify_and_resolve_charger_s02_restores_port_in_mock_db(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """Xác thực và hoàn tất phiếu TICK-802 giúp khôi phục trụ sạc S02 trên hub-01."""
    verify_res = api_client.post(
        f"{STAFF_API}/maintenance/verify-device",
        json={"task_code": "TICK-802", "scanned_qr_code": "S02"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json().get("verified") is True

    resolve_res = api_client.post(
        f"{STAFF_API}/maintenance/resolve",
        json={
            "task_code": "TICK-802",
            "technical_notes": "Đã kiểm tra rơ-le nhiệt và reset trụ S02.",
        },
    )
    assert resolve_res.status_code == 200

    ticket = next(t for t in reset_shared_mock_db.maintenance_tickets if t["code"] == "TICK-802")
    assert ticket["status"] == "RESOLVED"

    hub = find_hub_in_db(reset_shared_mock_db, "hub-01")
    port_s02 = next(p for p in hub["ports"] if p["id"] == "S02")
    assert port_s02["is_available"] is True


@pytest.mark.xfail(
    reason="BUG-BE-02: BE/staff/main.py không truyền req.outcome xuống mock_db; mock_db chưa khóa thiết bị & giảm available_bikes; seed dùng TICK-801 thay vì MT-102/BK-EB-018",
    strict=True,
)
def test_tc_s02_send_to_workshop_locks_bike_and_decrements_available_bikes(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """TC-S02 (Unit): Gửi outcome='Cần chuyển về xưởng' phải khóa thiết bị và giảm available_bikes."""
    hub_id = "hub-03"
    hub_before = find_hub_in_db(reset_shared_mock_db, hub_id)
    bikes_before = hub_before["available_bikes"]

    resolve_res = api_client.post(
        f"{STAFF_API}/maintenance/resolve",
        json={
            "task_code": "TICK-801",
            "outcome": "Cần chuyển về xưởng",
            "technical_notes": "Hỏng mạch điều khiển nguồn, chuyển về xưởng trung tâm.",
        },
    )
    assert resolve_res.status_code == 200

    hub_after = find_hub_in_db(reset_shared_mock_db, hub_id)
    assert hub_after["available_bikes"] == bikes_before - 1
    locked_bikes = [
        b for b in hub_after.get("bikes", [])
        if str(b.get("status", "")).lower() in ("maintenance", "locked", "đang bảo trì", "đã khóa")
    ]
    assert len(locked_bikes) >= 1, "Không có xe nào được chuyển sang trạng thái khóa/bảo trì"