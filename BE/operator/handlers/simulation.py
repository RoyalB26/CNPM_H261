
import copy
import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any




from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..store import db
from ..schemas.simulation import (
    SimulationSourceState,
    HubStateSnapshot,
    SourceStateType,
    SimulationScenarioConfig,
    SimulationValidationResult,
    SimulationResultResponse,
    HubLoadPoint,
    PowerLoadPoint,
    DispatchRecommendationItem,
    SimulationSaveRuleRequest,
    SimulationHistoryItem,
    SimulationHistoryList,
        
    SimulationRunRequest,
    SimulationErrorResponse,
    SimulationSaveRuleResponse,
)






# ================= WHAT-IF SIMULATION ROUTES =================



def next_sequential_id(
    records: list[dict[str, Any]],
    prefix: str,
) -> str:
    """Tạo mã tăng dần theo mã số lớn nhất đang có trong store để làm khóa 
    vì không thích mã random do uuid4 tạo :))))
    """
    marker = f"{prefix}-"
    largest_number = 0

    for record in records:
        # Lịch sử seed cũ dùng run_id; bản ghi mới dùng id.
        record_id = record.get("id") or record.get("run_id")

        if not isinstance(record_id, str):
            continue

        if not record_id.startswith(marker):
            continue

        suffix = record_id[len(marker):]

        # Bỏ qua mã cũ dạng ngày hoặc UUID.
        if not suffix.isascii() or not suffix.isdigit():
            continue

        largest_number = max(largest_number, int(suffix))

    return f"{prefix}-{largest_number + 1:03d}"



class SimulationSourceError(Exception):
    """Không lấy được nguồn dữ liệu hợp lệ để mô phỏng."""


def simulation_error_response(
    status_code: int,
    detail: str,
    error_code: str = "EX-10-01",
    error_type: str = "INVALID_INPUT",
) -> JSONResponse:
    """Tạo response lỗi thống nhất, giữ mã lỗi nghiệp vụ mô phỏng."""
    response = SimulationErrorResponse(
        status_code=str(status_code),
        detail=detail,
        error_code=error_code,
        error_type=error_type,
        message=detail,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=status_code,
    )


def build_simulation_source() -> SimulationSourceState:
    """Chụp trạng thái từ store, không sửa dữ liệu vận hành."""
    try:
        hubs = copy.deepcopy(db.get_hubs())
        if not hubs:
            raise SimulationSourceError("Nguồn dữ liệu không có Hub")

        snapshots = []

        for hub in hubs:
            available_ports = [
                port
                for port in hub.get("ports", [])
                if hub["status"] == "ACTIVE"
                and port.get("is_available", False)
            ]

            # Store chưa có số đo IoT, sử dụng giả định tải nền hiện có.
            base_power_kw = sum(
                port["power_kw"] for port in available_ports
            ) * 0.5

            snapshots.append(
                HubStateSnapshot(
                    hub_id=hub["id"],
                    hub_code=hub["hub_code"],
                    name=hub["name"],
                    total_parking_capacity=hub["parking_capacity"],
                    current_bikes=len(hub.get("bikes", [])),
                    free_parking_slots=sum(
                        1
                        for slot in hub.get("slots", [])
                        if slot.get("is_available", False)
                    ),
                    total_chargers=hub["charger_capacity"],
                    active_chargers=len(available_ports),
                    base_power_kw=base_power_kw,
                    max_power_kw=hub["max_power_kw"],
                )
            )

        return SimulationSourceState(
            source_type=SourceStateType.LIVE_STATE_A,
            source_label="Snapshot từ store; công suất nền ước tính",
            captured_at=datetime.now(timezone.utc).isoformat(),
            power_basis=(
                "Ước tính 50% tổng công suất cổng sẵn sàng; "
                "không phải số đo IoT"
            ),
            hub_snapshots=snapshots,
        )
    except (
        ValidationError,
        KeyError,
        TypeError,
        OSError,
        RuntimeError,
    ) as exc:
        raise SimulationSourceError(
            "Không đọc được trạng thái Hub từ store"
        ) from exc


def prepare_simulation_input(
    req: SimulationRunRequest,
) -> tuple[SimulationSourceState, SimulationScenarioConfig]:
    """Chuẩn hóa nguồn và kiểm tra các ràng buộc nghiệp vụ."""
    if req.source_type == SourceStateType.LIVE_STATE_A:
        # LIVE_A luôn lấy trạng thái từ store.
        source = build_simulation_source()
    else:
        if not req.hub_snapshots:
            raise ValueError("Bản manual phải có hub_snapshots không rỗng")

        source = SimulationSourceState(
            source_type=SourceStateType.MANUAL_STATE_A_PRIME,
            source_label="Bản sao chỉnh tay",
            captured_at=datetime.now(timezone.utc).isoformat(),
            power_basis="Dữ liệu manual do người chạy nhập",
            hub_snapshots=[
                item.model_copy(deep=True)
                for item in req.hub_snapshots
            ],
        )

    known_ids = {hub["id"] for hub in db.get_hubs()}
    seen = set()

    for hub in source.hub_snapshots:
        hub_id = hub.hub_id

        if hub_id not in known_ids:
            raise ValueError(f"Hub không tồn tại: {hub_id}")
        if hub_id in seen:
            raise ValueError(f"Trùng hub_id: {hub_id}")
        seen.add(hub_id)

        if hub.current_bikes > hub.total_parking_capacity:
            raise ValueError(f"{hub_id}: số xe ngoài sức chứa")

        if hub.free_parking_slots > hub.total_parking_capacity:
            raise ValueError(f"{hub_id}: số chỗ trống ngoài sức chứa")

        if hub.active_chargers > hub.total_chargers:
            raise ValueError(f"{hub_id}: số cổng sạc không hợp lệ")

        if hub.base_power_kw > hub.max_power_kw:
            raise ValueError(f"{hub_id}: công suất nền vượt giới hạn")

        if hub.active_chargers == 0 and hub.base_power_kw != 0:
            raise ValueError(
                f"{hub_id}: không có cổng hoạt động nhưng có tải sạc"
            )

    config = req.config.model_copy(deep=True)

    if config.scenario_type.name != "DEMAND_SURGE":
        raise ValueError("Bản cơ bản hiện chỉ hỗ trợ tăng nhu cầu sạc")

    if config.demand_increase_pct < 0:
        raise ValueError("Mức tăng nhu cầu phải từ 0 đến 300%")

    try:
        start = datetime.strptime(config.start_time, "%H:%M")
    except ValueError as exc:
        raise ValueError("start_time phải có dạng HH:MM") from exc

    if start.strftime("%H:%M") != config.start_time:
        raise ValueError("start_time phải có dạng HH:MM")

    if (
        config.affected_chargers_count != 0
        or config.lost_power_kw != 0
        or config.additional_bikes_count != 0
    ):
        raise ValueError(
            "Tăng nhu cầu thuần túy cần affected_chargers_count, "
            "lost_power_kw, additional_bikes_count bằng 0"
        )

    config.scenario_name = config.scenario_name.strip()
    return source, config


async def read_simulation_input(
    request: Request,
) -> tuple[
    SimulationSourceState | None,
    SimulationScenarioConfig | None,
    JSONResponse | None,
]:
    """Đọc và kiểm tra request dùng chung cho validate và run."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, None, simulation_error_response(
            400, "JSON không hợp lệ"
        )

    try:
        req = SimulationRunRequest.model_validate(body)
    except ValidationError:
        return None, None, simulation_error_response(
            422, "Dữ liệu mô phỏng không đúng cấu trúc hoặc giới hạn"
        )

    try:
        source, config = prepare_simulation_input(req)
    except SimulationSourceError as exc:
        return None, None, simulation_error_response(
            503, str(exc), "EX-10-02", "SOURCE_UNAVAILABLE"
        )
    except ValueError as exc:
        return None, None, simulation_error_response(422, str(exc))

    if req.trigger_timeout_error:
        return None, None, simulation_error_response(
            504,
            "Mô phỏng lỗi timeout theo yêu cầu kiểm thử",
            "EX-10-02",
            "IOT_TIMEOUT",
        )

    return source, config, None


def build_demo_simulation_result(
    simulation_id: str,
    config: SimulationScenarioConfig,
    executed_at: str,
) -> SimulationResultResponse:
    """Đóng gói biểu đồ mẫu; chưa phải thuật toán tính theo đầu vào."""
    load_rows = [
        ("17:00", 48, 42),
        ("17:20", 56, 47),
        ("17:40", 67, 44),
        ("18:00", 81, 51),
        ("18:20", 92, 55),
        ("18:40", 88, 53),
        ("19:00", 94, 56),
    ]
    power_rows = [
        ("17:00", 70.0),
        ("17:20", 90.0),
        ("17:40", 115.0),
        ("18:00", 160.0),
        ("18:20", 185.0),
        ("18:40", 150.0),
        ("19:00", 120.0),
    ]

    return SimulationResultResponse(
        simulation_id=simulation_id,
        scenario_name=config.scenario_name,
        status="Hoàn thành (dữ liệu mẫu)",
        executed_at=executed_at,
        is_mock=True,
        result_basis="Biểu đồ mẫu, chưa tính theo snapshot/config",
        load_chart_data=[
            HubLoadPoint(
                time_label=time_label,
                metro_hub_load_pct=metro,
                bachkhoa_hub_load_pct=bachkhoa,
            )
            for time_label, metro, bachkhoa in load_rows
        ],
        power_chart_data=[
            PowerLoadPoint(time_label=time_label, power_kw=power)
            for time_label, power in power_rows
        ],
        peak_power_kw=max(power for _, power in power_rows),
        peak_metro_load_pct=max(metro for _, metro, _ in load_rows),
        overloaded_hubs="2 / 12",
        overloaded_chargers="15 / 60",
        metro_deficit_bikes=35,
        recommendations=[
            DispatchRecommendationItem(
                title="Đề xuất mẫu: điều chuyển xe khẩn cấp",
                source_hub="Hub KTX Khu A",
                target_hub="Hub Ga Metro A",
                bike_count=20,
                vehicle_type="Xe đạp điện",
                details=[
                    "Đây là đề xuất mẫu, chưa tính từ nguồn dữ liệu.",
                    "Chưa tạo lệnh điều chuyển trong store.",
                ],
            )
        ],
    )


def simulation_history_response(
    row: dict[str, Any],
) -> SimulationHistoryItem:
    """Đọc bản ghi mới và chuyển seed cũ sang model lịch sử."""
    if "id" in row:
        return SimulationHistoryItem.model_validate(row)

    # Seed hiện tại trong mock_db dùng run_id/name/summary.
    return SimulationHistoryItem(
        id=row["run_id"],
        title=row["name"],
        parameters_summary=(
            f"Thời lượng kịch bản: {row['duration_minutes']} phút"
        ),
        executed_at=row["created_at"],
        duration_str="Chưa có số đo thời gian chạy",
        created_by="Chưa có thông tin",
        status=(
            "Thành công"
            if row["status"] == "COMPLETED"
            else row["status"]
        ),
        what_if_params=row["scenario"],
        recorded_result=row["summary"],
        saved_rule="",
    )


async def get_simulation_source_state(
    request: Request,
) -> JSONResponse:
    """Trả snapshot LIVE_A từ store; manual được gửi trong body POST."""
    try:
        response = build_simulation_source()
    except SimulationSourceError as exc:
        return simulation_error_response(
            503, str(exc), "EX-10-02", "SOURCE_UNAVAILABLE"
        )

    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=200,
    )


async def validate_simulation_parameters(
    request: Request,
) -> JSONResponse:
    """Kiểm tra đầu vào mà không ghi dữ liệu."""
    source, config, error_response = await read_simulation_input(request)
    if error_response is not None:
        return error_response

    response = SimulationValidationResult(
        is_valid=True,
        message="Dữ liệu đầu vào hợp lệ",
        source=source,
        config=config,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=200,
    )


async def run_simulation(request: Request) -> JSONResponse:
    """Kiểm tra đầu vào, tạo kết quả mẫu và lưu lịch sử riêng."""


    started_at = perf_counter()
    source, config, error_response = await read_simulation_input(request)
    if error_response is not None:
        return error_response

    simulation_id = next_sequential_id(
        db.simulation_history,
        "SIM",
    )
    executed_at = datetime.now(timezone.utc).isoformat()

    result = build_demo_simulation_result(
        simulation_id=simulation_id,
        config=config,
        executed_at=executed_at,
    )
    summary = (
        f"Nhu cầu +{config.demand_increase_pct}%, "
        f"thời lượng {config.duration_minutes} phút, "
        f"bắt đầu {config.start_time}"
    )

    history = SimulationHistoryItem(
        id=simulation_id,
        title=config.scenario_name,
        parameters_summary=summary,
        executed_at=executed_at,
        duration_str=f"{perf_counter() - started_at:.3f}s",
        created_by="Chưa xác định người dùng đăng nhập",
        status=result.status,
        what_if_params=summary,
        recorded_result=result.result_basis,
        saved_rule="",
        source=source,
        config=config,
        result=result,
    )

    # Serialize và kiểm tra model trước khi thay đổi store.
    content = result.model_dump(mode="json")
    history_data = history.model_dump(mode="json")
    db.simulation_history.insert(0, history_data)

    return JSONResponse(content=content, status_code=200)


async def save_simulation_rule(request: Request) -> JSONResponse:
    """Lưu quy tắc cho phiên đã chạy, không tạo thêm phiên lịch sử."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return simulation_error_response(400, "JSON không hợp lệ")

    try:
        req = SimulationSaveRuleRequest.model_validate(body)
    except ValidationError:
        return simulation_error_response(
            422, "Dữ liệu lưu quy tắc không hợp lệ"
        )

    history_row = next(
        (
            row
            for row in db.simulation_history
            if row.get("id", row.get("run_id")) == req.simulation_id
        ),
        None,
    )
    if history_row is None:
        return simulation_error_response(
            404, "Phiên mô phỏng không tồn tại"
        )

    if history_row.get("result") is None:
        return simulation_error_response(
            409, "Phiên này chưa có kết quả đầy đủ để lưu quy tắc"
        )

    rule_id = next_sequential_id(
        db.simulation_rules,
        "RULE",
    )
    rule_name = req.rule_name.strip()
    instructions = req.operation_instructions.strip()

    # Giữ cấu trúc id/name/trigger/action/active của store hiện có.
    rule = {
        "id": rule_id,
        "simulation_id": req.simulation_id,
        "name": rule_name,
        "trigger": "Tải Hub cao",
        "action": instructions,
        "active": req.auto_match_on_high_load,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    response = SimulationSaveRuleResponse(
        success=True,
        message=f"Đã lưu quy tắc '{rule_name}' vào store",
        rule_id=rule_id,
        simulation_id=req.simulation_id,
        history_id=req.simulation_id,
    )

    updated_history = {
        **history_row,
        "saved_rule": instructions,
    }
    SimulationHistoryItem.model_validate(updated_history)
    content = response.model_dump(mode="json")

    db.simulation_rules.insert(0, rule)
    history_row.update(updated_history)

    return JSONResponse(content=content, status_code=200)


async def get_simulation_history(request: Request) -> JSONResponse:
    """Trả lịch sử từ store chung, bao gồm dữ liệu seed cũ."""
    items = [
        simulation_history_response(row)
        for row in db.simulation_history
    ]
    response = SimulationHistoryList(
        total=len(items),
        items=items,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=200,
    )





routes = [
    Route("/api/v1/operator/simulation/source-state", get_simulation_source_state, methods=["GET"]),
    Route("/api/v1/operator/simulation/validate", validate_simulation_parameters, methods=["POST"]),
    Route("/api/v1/operator/simulation/run", run_simulation, methods=["POST"]),
    Route("/api/v1/operator/simulation/save-rule", save_simulation_rule, methods=["POST"]),
    Route("/api/v1/operator/simulation/history", get_simulation_history, methods=["GET"]),
]