
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

from ..store import db, persist_change
from ..schemas.simulation import (
    SimulationSourceState,
    HubStateSnapshot,
    SourceStateType,
    SimulationScenarioConfig,
    SimulationValidationResult,
    SimulationResultResponse,
    HubLoadPoint,
    PowerLoadPoint,
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
                    available_power_kw=sum(port["power_kw"] for port in available_ports),
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
    if req.snapshot_id:
        stored = db.operator_mock.get("simulation_snapshots", {}).get(req.snapshot_id)
        if stored is None:
            raise ValueError("Snapshot không tồn tại")
        source = SimulationSourceState.model_validate(copy.deepcopy(stored))
    elif req.source_type == SourceStateType.LIVE_STATE_A:
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

    if config.target_hub_ids and (
        len(set(config.target_hub_ids)) != len(config.target_hub_ids)
        or not set(config.target_hub_ids).issubset(seen)
    ):
        raise ValueError("Hub bị ảnh hưởng phải có trong snapshot và không trùng")
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

    return source, config, None


def calculate_simulation_result(simulation_id, source, config, executed_at):
    """Tải yêu cầu = nền × (1 + % tăng). Phục vụ = min(yêu cầu, năng lực).

    Tải tăng giữ đều trong (0, duration], t=0 và duration+10 là tải nền.
    Cổng thiếu tính theo công suất trung bình của cổng trong snapshot.
    """
    import math
    from datetime import timedelta
    start = datetime.strptime(config.start_time, "%H:%M")
    minutes = sorted(set([0, config.duration_minutes, config.duration_minutes + 10]
                         + list(range(10, config.duration_minutes, 10))))
    hub_results, load_points, power_points = [], [], []
    selected = set(config.target_hub_ids or [h.hub_id for h in source.hub_snapshots])
    for hub in source.hub_snapshots:
        rated = hub.available_power_kw
        if rated is None:
            rated = (hub.base_power_kw * 2 if hub.base_power_kw else
                     hub.max_power_kw * hub.active_chargers / max(1, hub.total_chargers))
        capacity = min(hub.max_power_kw, rated) if hub.active_chargers else 0
        points = []
        for minute in minutes:
            multiplier = 1 + config.demand_increase_pct / 100 if (
                hub.hub_id in selected and 0 < minute <= config.duration_minutes) else 1
            requested = hub.base_power_kw * multiplier
            served = min(requested, capacity)
            points.append({
                "time_label": (start + timedelta(minutes=minute)).strftime("%H:%M"),
                "requested_power_kw": round(requested, 4), "served_power_kw": round(served, 4),
                "unmet_power_kw": round(requested - served, 4),
                "load_pct": round(requested / capacity * 100, 2) if capacity else (100 if requested else 0),
                "overloaded": requested > capacity,
            })
        peak = max(p["requested_power_kw"] for p in points)
        per_port = rated / hub.active_chargers if hub.active_chargers else 0
        deficit = max(0, math.ceil(peak / per_port) - hub.active_chargers) if per_port else 0
        hub_results.append({
            "hub_id": hub.hub_id, "name": hub.name, "capacity_kw": capacity,
            "peak_requested_power_kw": peak,
            "peak_served_power_kw": min(peak, capacity),
            "peak_unmet_power_kw": max(0, peak - capacity),
            "charger_deficit": deficit, "points": points,
        })
    for i, minute in enumerate(minutes):
        label = (start + timedelta(minutes=minute)).strftime("%H:%M")
        power_points.append(PowerLoadPoint(time_label=label,
            power_kw=sum(h["points"][i]["requested_power_kw"] for h in hub_results),
            station_limit_kw=sum(h["capacity_kw"] for h in hub_results)))
        load_points.append(HubLoadPoint(time_label=label,
            metro_hub_load_pct=round(hub_results[0]["points"][i]["load_pct"]),
            bachkhoa_hub_load_pct=round(hub_results[min(1, len(hub_results)-1)]["points"][i]["load_pct"])))
    overloaded = [h for h in hub_results if h["peak_unmet_power_kw"] > 0]
    recommendations = [{
        "title": "Giảm hoặc chuyển nhu cầu sạc tại " + h["name"],
        "source_hub": h["hub_id"],
        "details": [f"Công suất chưa phục vụ {h['peak_unmet_power_kw']:.2f} kW",
                    "Operator xem xét xếp hàng hoặc chuyển sang Hub còn công suất"],
    } for h in overloaded]
    return SimulationResultResponse(
        simulation_id=simulation_id, scenario_name=config.scenario_name,
        status="COMPLETED", executed_at=executed_at, is_mock=False,
        result_basis="Tính từ snapshot; tải nền ước tính nếu nguồn store chưa có IoT. Tăng nhu cầu sạc không suy ra thiếu xe.",
        load_chart_data=load_points, power_chart_data=power_points,
        peak_power_kw=max(p.power_kw for p in power_points),
        peak_metro_load_pct=max(p.metro_hub_load_pct for p in load_points),
        overloaded_hubs=str(len(overloaded)),
        overloaded_chargers=str(sum(h["charger_deficit"] for h in hub_results)),
        metro_deficit_bikes=0, recommendations=recommendations, hub_results=hub_results,
        unmet_power_kw=sum(h["peak_unmet_power_kw"] for h in hub_results),
        served_power_kw=sum(h["peak_served_power_kw"] for h in hub_results),
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


def finish_run(simulation_id, fail=False):
    row = next(r for r in db.simulation_history if r.get("id") == simulation_id)
    started = perf_counter()
    try:
        if fail:
            raise TimeoutError("Mô phỏng timeout theo yêu cầu kiểm thử")
        source = SimulationSourceState.model_validate(row["source"])
        config = SimulationScenarioConfig.model_validate(row["config"])
        result = calculate_simulation_result(simulation_id, source, config, row["executed_at"])
        updated = {"status": "COMPLETED", "result": result.model_dump(mode="json"),
                   "error": None, "recorded_result": result.result_basis}
    except (TimeoutError, ValueError, RuntimeError) as exc:
        updated = {"status": "FAILED", "error": str(exc), "recorded_result": str(exc)}
        result = None
    updated["duration_str"] = f"{perf_counter() - started:.3f}s"

    def change(candidate):
        target = next(r for r in candidate.simulation_history if r.get("id") == simulation_id)
        target.update(updated)
    failure = persist_change(change)
    if failure is not None:
        return failure
    if result is None:
        response = simulation_error_response(504, updated["error"], "EX-10-02", "SIMULATION_FAILED")
        import json
        content = json.loads(response.body)
        content["simulation_id"] = simulation_id
        return JSONResponse(content, status_code=504)
    return JSONResponse(result.model_dump(mode="json"))


async def run_simulation(request: Request):
    source, config, failure = await read_simulation_input(request)
    if failure is not None:
        return failure
    simulation_id = next_sequential_id(db.simulation_history, "SIM")
    executed_at = datetime.now(timezone.utc).isoformat()
    summary = f"Nhu cầu +{config.demand_increase_pct}%, thời lượng {config.duration_minutes} phút"
    row = SimulationHistoryItem(
        id=simulation_id, title=config.scenario_name, parameters_summary=summary,
        executed_at=executed_at, duration_str="0s",
        created_by=request.state.account["id"], status="RUNNING",
        what_if_params=summary, recorded_result="", source=source, config=config,
    ).model_dump(mode="json")
    def change(candidate):
        candidate.simulation_history.insert(0, row)
    failure = persist_change(change)
    if failure is not None:
        return failure
    body = await request.json()
    return finish_run(simulation_id, body.get("trigger_timeout_error", False))


async def retry_simulation(request: Request):
    simulation_id = request.path_params["simulation_id"]
    row = next((r for r in db.simulation_history if r.get("id") == simulation_id), None)
    if row is None:
        return simulation_error_response(404, "Phiên không tồn tại")
    if row["status"] not in ("FAILED", "RUNNING"):
        return simulation_error_response(409, "Chỉ thử lại phiên thất bại")
    def change(candidate):
        target = next(r for r in candidate.simulation_history if r.get("id") == simulation_id)
        target.update(status="RUNNING", attempts=target.get("attempts", 1) + 1)
    failure = persist_change(change)
    if failure is not None:
        return failure
    return finish_run(simulation_id)


async def capture_snapshot(request: Request):
    try:
        body = await request.json()
    except (ValueError, UnicodeError):
        return simulation_error_response(400, "JSON không hợp lệ")
    if not isinstance(body, dict):
        return simulation_error_response(422, "Cần JSON object")
    body.setdefault("config", {"scenario_name": "Snapshot"})
    try:
        req = SimulationRunRequest.model_validate(body)
        source, config = prepare_simulation_input(req)
    except (ValidationError, ValueError) as exc:
        return simulation_error_response(422, "Nguồn snapshot không hợp lệ")
    except SimulationSourceError as exc:
        return simulation_error_response(503, str(exc), "EX-10-02", "SOURCE_UNAVAILABLE")
    from uuid import uuid4
    snapshot_id = "SNAP-" + uuid4().hex
    data = source.model_dump(mode="json")
    def change(candidate):
        candidate.operator_mock.setdefault("simulation_snapshots", {})[snapshot_id] = data
        return JSONResponse({"snapshot_id": snapshot_id, "source": data}, status_code=201)
    return persist_change(change)


async def simulation_detail(request: Request):
    row = next((r for r in db.simulation_history
                if r.get("id", r.get("run_id")) == request.path_params["simulation_id"]), None)
    if row is None:
        return simulation_error_response(404, "Phiên không tồn tại")
    return JSONResponse(simulation_history_response(row).model_dump(mode="json"))


async def save_result(request: Request):
    try:
        body = await request.json()
    except (ValueError, UnicodeError):
        return simulation_error_response(400, "JSON không hợp lệ")
    if not isinstance(body, dict) or not isinstance(body.get("operation_plan"), str) or not body["operation_plan"].strip():
        return simulation_error_response(422, "Cần phương án vận hành")
    simulation_id = request.path_params["simulation_id"]
    def change(candidate):
        row = next((r for r in candidate.simulation_history if r.get("id") == simulation_id), None)
        from starlette.exceptions import HTTPException
        if row is None:
            raise HTTPException(404, "Phiên không tồn tại")
        if row["status"] != "COMPLETED" or not row.get("result"):
            raise HTTPException(409, "Phiên chưa có kết quả thành công")
        row.update(operation_plan=body["operation_plan"].strip(), saved_at=datetime.now(timezone.utc).isoformat())
        return JSONResponse({"success": True, "simulation_id": simulation_id})
    return persist_change(change)


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

    from shared.automation import validate_rule
    try:
        validate_rule(db, req.hub_ids, req.actions)
    except ValueError as exc:
        return simulation_error_response(422, str(exc))

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
        "hub_ids": req.hub_ids,
        "threshold_pct": req.threshold_pct,
        "actions": req.actions,
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

    def change(candidate):
        candidate.simulation_rules.insert(0, rule)

        candidate_history = next(
            row
            for row in candidate.simulation_history
            if row.get("id", row.get("run_id")) == req.simulation_id
        )
        candidate_history.update(updated_history)

        return JSONResponse(
            content=content,
            status_code=200,
        )

    return persist_change(change)


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
    Route("/api/v1/operator/simulation/snapshots", capture_snapshot, methods=["POST"]),
    Route("/api/v1/operator/simulation/{simulation_id}/retry", retry_simulation, methods=["POST"]),
    Route("/api/v1/operator/simulation/{simulation_id}/save", save_result, methods=["POST"]),
    Route("/api/v1/operator/simulation/history/{simulation_id}", simulation_detail, methods=["GET"]),
    Route("/api/v1/operator/simulation/source-state", get_simulation_source_state, methods=["GET"]),
    Route("/api/v1/operator/simulation/validate", validate_simulation_parameters, methods=["POST"]),
    Route("/api/v1/operator/simulation/run", run_simulation, methods=["POST"]),
    Route("/api/v1/operator/simulation/save-rule", save_simulation_rule, methods=["POST"]),
    Route("/api/v1/operator/simulation/history", get_simulation_history, methods=["GET"]),
]
