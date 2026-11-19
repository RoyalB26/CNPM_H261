"""Unit/API Test cho UC8: Lệnh điều phối xe và ngoại lệ RelocationError (TC-O03-ERR)."""

import pytest
from starlette.testclient import TestClient

from BE.mock_db import RelocationError
from tests.unit.conftest import OPERATOR_API, find_hub_in_db

pytestmark = pytest.mark.unit


def test_relocation_error_carries_status_code_and_message() -> None:
    """Pure Unit: Kiểm tra lớp ngoại lệ RelocationError lưu đúng status_code và thông điệp."""
    err = RelocationError(409, "Hub đích không đủ chỗ trống")
    assert err.status_code == 409
    assert "không đủ chỗ trống" in str(err)


def test_tc_o03_create_valid_relocation_command_succeeds(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """Trường hợp thành công: Điều 1 xe từ hub-02 (2 xe sẵn sàng) sang hub-04 (1 chỗ trống)."""
    total_before = len(reset_shared_mock_db.relocations)
    payload = {
        "source_hub_id": "hub-02",
        "target_hub_id": "hub-04",
        "bike_count": 1,
        "assigned_staff_id": "STF-01",
        "notes": "Cân bằng tải giờ cao điểm",
    }
    response = api_client.post(f"{OPERATOR_API}/relocation/commands", json=payload)
    assert response.status_code == 201
    assert len(reset_shared_mock_db.relocations) == total_before + 1


def test_tc_o03_err_exceeding_target_capacity_is_rejected_without_mutating_db(
    api_client: TestClient,
    reset_shared_mock_db,
) -> None:
    """TC-O03-ERR: Điều 2 xe từ hub-02 sang hub-04 (chỉ có 1 chỗ trống) bị từ chối 409."""
    total_before = len(reset_shared_mock_db.relocations)
    source_before = dict(find_hub_in_db(reset_shared_mock_db, "hub-02"))
    target_before = dict(find_hub_in_db(reset_shared_mock_db, "hub-04"))

    excessive_payload = {
        "source_hub_id": "hub-02",
        "target_hub_id": "hub-04",
        "bike_count": 2,
        "assigned_staff_id": "STF-01",
    }
    response = api_client.post(f"{OPERATOR_API}/relocation/commands", json=excessive_payload)
    assert response.status_code == 409
    assert "chỗ trống" in response.json().get("error", "").lower()

    assert len(reset_shared_mock_db.relocations) == total_before
    assert find_hub_in_db(reset_shared_mock_db, "hub-02") == source_before
    assert find_hub_in_db(reset_shared_mock_db, "hub-04") == target_before