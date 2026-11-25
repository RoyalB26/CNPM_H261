"""Unit/API Test cho TC-S02: Bảo trì thiết bị hiện trường (UC9)."""

import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import OPERATOR_API, STAFF_API, find_hub_in_db

pytestmark = pytest.mark.unit


def test_tc_s02_get_maintenance_task_tick801_returns_details(
    api_client: TestClient,
    staff_headers: dict[str, str],
) -> None:
    """Tra cứu chi tiết phiếu bảo trì thực tế trong mock_db (TICK-801)."""
    response = api_client.get(
        f"{STAFF_API}/maintenance/tasks/TICK-801",
        headers=staff_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("task_code") == "TICK-801"


def test_tc_s02_verify_and_resolve_charger_s02_restores_port_in_mock_db(
    api_client: TestClient,
    operator_headers: dict[str, str],
    staff_headers: dict[str, str],
    reset_shared_mock_db,
) -> None:
    """Phân công, xác thực và hoàn tất phiếu TICK-802 giúp khôi phục trụ sạc S02 trên hub-01."""
    assign_res = api_client.post(
        f"{OPERATOR_API}/maintenance/assign",
        headers=operator_headers,
        json={
            "ticket_code": "TICK-802",
            "technician_id": "STF-02",
            "technician_name": "Nguyen Van B",
            "priority": "Khẩn cấp",
            "operator_notes": "Kiểm tra trụ sạc nhanh S02",
        },
    )
    assert assign_res.status_code == 200, assign_res.text

    verify_res = api_client.post(
        f"{STAFF_API}/maintenance/verify-device",
        headers=staff_headers,
        json={"task_code": "TICK-802", "scanned_qr_code": "S02"},
    )
    assert verify_res.status_code == 200, verify_res.text
    assert verify_res.json().get("verified") is True

    resolve_res = api_client.post(
        f"{STAFF_API}/maintenance/resolve",
        headers=staff_headers,
        json={
            "task_code": "TICK-802",
            "technical_notes": "Đã kiểm tra rơ-le nhiệt và reset trụ S02.",
        },
    )
    assert resolve_res.status_code == 200, resolve_res.text

    ticket = next(t for t in reset_shared_mock_db.maintenance_tickets if t["code"] == "TICK-802")
    assert ticket["status"] == "RESOLVED"

    hub = find_hub_in_db(reset_shared_mock_db, "hub-01")
    port_s02 = next(p for p in hub["ports"] if p["id"] == "S02")
    assert port_s02["is_available"] is True


def test_tc_s02_send_to_workshop_locks_bike_and_decrements_available_bikes(
    api_client: TestClient,
    operator_headers: dict[str, str],
    staff_headers: dict[str, str],
    reset_shared_mock_db,
) -> None:
    """TC-S02 (Unit): Gửi outcome='Cần chuyển về xưởng' phải khóa xe và giảm available_bikes."""
    hub_id = "hub-02"
    hub_before = find_hub_in_db(reset_shared_mock_db, hub_id)
    bikes_before = hub_before["available_bikes"]

    create_res = api_client.post(
        f"{OPERATOR_API}/maintenance/tickets",
        headers=operator_headers,
        json={
            "device_code": "XE-052",
            "hub_name": hub_before["name"],
            "source": "Operator thủ công",
            "fault_category": "Hỏng mạch điều khiển nguồn",
            "severity": "Khẩn cấp",
            "description": "Xe XE-052 không lên nguồn, cần kiểm tra tại xưởng.",
            "assigned_staff_id": "STF-02",
        },
    )
    assert create_res.status_code == 201, create_res.text
    task_code = create_res.json()["ticket"]["ticket_code"]

    resolve_res = api_client.post(
        f"{STAFF_API}/maintenance/resolve",
        headers=staff_headers,
        json={
            "task_code": task_code,
            "outcome": "Cần chuyển về xưởng",
            "technical_notes": "Hỏng mạch điều khiển nguồn, chuyển về xưởng trung tâm.",
        },
    )
    assert resolve_res.status_code == 200, resolve_res.text

    hub_after = find_hub_in_db(reset_shared_mock_db, hub_id)
    assert hub_after["available_bikes"] == bikes_before - 1
    bike_xe052 = next(b for b in hub_after["bikes"] if b["id"] == "XE-052")
    assert bike_xe052["workshop"] is True
    assert bike_xe052["status"] == "Chuyển xưởng"