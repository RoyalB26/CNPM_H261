"""Unit/API Test cho TC-O01: Thuật toán tính toán và tái mô phỏng What-If (UC10)."""

import pytest
from starlette.testclient import TestClient

from tests.unit.conftest import OPERATOR_API

pytestmark = pytest.mark.unit


def test_tc_o01_get_simulation_source_state_returns_hub_snapshots(
    api_client: TestClient,
    operator_headers: dict[str, str],
) -> None:
    """Lấy trạng thái nguồn làm đầu vào mô phỏng phải chứa snapshot các Hub hiện hữu."""
    response = api_client.get(
        f"{OPERATOR_API}/simulation/source-state",
        headers=operator_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body.get("hub_snapshots", [])) > 0


def test_tc_o01_validate_and_run_what_if_simulation_detects_shortage(
    api_client: TestClient,
    operator_headers: dict[str, str],
) -> None:
    """TC-O01: Chạy kịch bản tăng nhu cầu +150% và xác minh cấu trúc SimulationResultResponse."""
    scenario_payload = {
        "source_type": "LIVE_A",
        "config": {
            "scenario_name": "Tăng nhu cầu giờ cao điểm Ga Metro",
            "scenario_type": "Nhu cầu sạc tăng đột biến",
            "demand_increase_pct": 150,
            "duration_minutes": 120,
            "start_time": "17:00",
            "affected_chargers_count": 0,
            "lost_power_kw": 0.0,
            "additional_bikes_count": 0,
        },
    }

    val_res = api_client.post(
        f"{OPERATOR_API}/simulation/validate",
        headers=operator_headers,
        json=scenario_payload,
    )
    assert val_res.status_code == 200, val_res.text
    assert val_res.json().get("is_valid") is True

    run_res = api_client.post(
        f"{OPERATOR_API}/simulation/run",
        headers=operator_headers,
        json=scenario_payload,
    )
    assert run_res.status_code == 200, run_res.text
    result = run_res.json()

    assert result["is_mock"] is False
    assert len(result.get("load_chart_data", [])) > 0
    assert len(result.get("power_chart_data", [])) > 0
    assert len(result.get("hub_results", [])) > 0
    assert isinstance(result.get("recommendations"), list)
    assert result["unmet_power_kw"] > 0
    assert result["served_power_kw"] > 0
    assert result["peak_metro_load_pct"] >= 85
    assert result["peak_power_kw"] > 0
    assert int(result["overloaded_hubs"]) > 0
    assert int(result["overloaded_chargers"]) > 0
    assert len(result["recommendations"]) > 0


def test_tc_o01_validate_rejects_mixed_scenario_params_with_422(
    api_client: TestClient,
    operator_headers: dict[str, str],
) -> None:
    """Trường hợp thất bại: Tình huống DEMAND_SURGE kèm cổng hỏng khác 0 phải trả EX-10-01."""
    invalid_payload = {
        "source_type": "LIVE_A",
        "config": {
            "scenario_name": "Kịch bản trộn tham số",
            "scenario_type": "Nhu cầu sạc tăng đột biến",
            "demand_increase_pct": 100,
            "duration_minutes": 60,
            "start_time": "18:00",
            "affected_chargers_count": 3,
            "lost_power_kw": 0.0,
            "additional_bikes_count": 0,
        },
    }
    response = api_client.post(
        f"{OPERATOR_API}/simulation/validate",
        headers=operator_headers,
        json=invalid_payload,
    )
    assert response.status_code == 422, response.text
    assert response.json().get("error_code") == "EX-10-01"


def test_tc_o01_simulation_iot_timeout_returns_504_ex_10_02(
    api_client: TestClient,
    operator_headers: dict[str, str],
) -> None:
    """Trường hợp thất bại: Gián đoạn dữ liệu IoT khi mô phỏng phải trả 504 (EX-10-02)."""
    response = api_client.post(
        f"{OPERATOR_API}/simulation/run",
        headers=operator_headers,
        json={
            "source_type": "LIVE_A",
            "config": {
                "scenario_name": "Kiểm thử timeout IoT",
                "scenario_type": "Nhu cầu sạc tăng đột biến",
                "demand_increase_pct": 50,
                "duration_minutes": 60,
                "start_time": "18:00",
                "affected_chargers_count": 0,
                "lost_power_kw": 0.0,
                "additional_bikes_count": 0,
            },
            "trigger_timeout_error": True,
        },
    )
    assert response.status_code == 504, response.text
    assert response.json().get("error_code") == "EX-10-02"


def test_tc_o01_save_fallback_rule_and_query_history(
    api_client: TestClient,
    operator_headers: dict[str, str],
) -> None:
    """Chạy mô phỏng, lưu quy tắc ứng phó từ simulation_id thật và tra cứu lại lịch sử."""
    run_res = api_client.post(
        f"{OPERATOR_API}/simulation/run",
        headers=operator_headers,
        json={
            "source_type": "LIVE_A",
            "config": {
                "scenario_name": "Kịch bản cao điểm Ga Metro",
                "scenario_type": "Nhu cầu sạc tăng đột biến",
                "demand_increase_pct": 100,
                "duration_minutes": 60,
                "start_time": "17:00",
                "affected_chargers_count": 0,
                "lost_power_kw": 0.0,
                "additional_bikes_count": 0,
            },
        },
    )
    assert run_res.status_code == 200, run_res.text
    sim_id = run_res.json()["simulation_id"]

    save_res = api_client.post(
        f"{OPERATOR_API}/simulation/save-rule",
        headers=operator_headers,
        json={
            "simulation_id": sim_id,
            "rule_name": "Kịch bản ứng phó vỡ trận ga Metro giờ cao điểm",
            "operation_instructions": "Điều chuyển 20 xe từ Hub KTX Khu A sang Ga Metro.",
            "auto_match_on_high_load": True,
        },
    )
    assert save_res.status_code in (200, 201), save_res.text
    assert save_res.json().get("success") is True

    history_res = api_client.get(
        f"{OPERATOR_API}/simulation/history",
        headers=operator_headers,
    )
    assert history_res.status_code == 200, history_res.text
    assert history_res.json().get("total", 0) >= 1