"""Các API giám sát dashboard và ghi Emergen halt."""

import json
from datetime import datetime

from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..store import db, persist_change
from ..schemas.dashboard import (
    KPISummary,
    TelemetryEvent,
    AlertLevel,
    HubLiveStatus,
    EmergencyHaltRequest,
    EmergencyHaltErrorResponse,
    EmergencyHaltResponse,
)


async def get_kpis(request: Request) -> JSONResponse:
    """Trả các chỉ số tổng quan từ dữ liệu hiện có."""
    kpis = db.get_kpis()
    alerts_count = sum(
        1
        for event in db.telemetry_events
        if event.get("level") in ("WARNING", "ALERT", "DANGER")
    )

    response_data = KPISummary(
        total_hubs=kpis["total_hubs"],
        available_bikes=kpis["available_bikes"],
        total_bikes=kpis["total_bikes"],
        available_chargers=kpis["available_chargers"],
        active_alerts=alerts_count,
    )

    return JSONResponse(
        content=response_data.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


async def get_telemetry_feed(request: Request) -> JSONResponse:
    """Trả danh sách sự kiện vận hành theo model TelemetryEvent."""
    events: list[TelemetryEvent] = []
    level_map = {
        "INFO": AlertLevel.NORMAL,
        "SUCCESS": AlertLevel.NORMAL,
        "WARNING": AlertLevel.WARNING,
        "ALERT": AlertLevel.ALERT,
        "DANGER": AlertLevel.ALERT,
    }

    for event in db.telemetry_events:
        events.append(
            TelemetryEvent(
                id=event.get("id", "EVT-100"),
                hub_id=event.get("hub_id", "HUB-METRO"),
                hub_name=event.get("hub_name", "Hub Ga Metro ĐHQG"),
                level=level_map.get(event.get("level"), AlertLevel.NORMAL),
                title=event.get("event_type", "Thông báo vận hành"),
                message=event.get("message", "Sự kiện hệ thống"),
                created_at_relative="Vừa xong",
                timestamp_iso=datetime.utcnow().isoformat(),
            )
        )

    # Response là mảng nên chuyển từng model thành dữ liệu JSON.
    return JSONResponse(
        content=[event.model_dump(mode="json") for event in events],
        status_code=status.HTTP_200_OK,
    )


async def get_hubs_live(request: Request) -> JSONResponse:
    """Trả danh sách trạng thái Hub theo model HubLiveStatus."""
    hubs: list[HubLiveStatus] = []

    for hub in db.get_hubs():
        hubs.append(
            HubLiveStatus(
                hub_id=hub["id"].upper(),
                hub_code=hub.get("hub_code", hub["id"].upper()),
                name=hub["name"],
                status_label=(
                    "Bình thường" if hub.get("status") == "ACTIVE"
                    else "Tạm ngưng"
                ),
                is_high_load=hub.get("available_bikes", 0) <= 2,
                parking_free=hub.get("available_parking", 8),
                parking_total=hub.get("parking_capacity", 20),
                chargers_free=hub.get("available_chargers", 2),
                chargers_total=hub.get("charger_capacity", 4),
                current_power_kw=hub.get("max_power_kw", 100.0) * 0.45,
                max_power_kw=hub.get("max_power_kw", 100.0),
                lat=hub["lat"],
                lng=hub["lng"],
                color_code=hub.get("color", "#10b981"),
                available_bikes=hub.get("available_bikes", 0),
            )
        )

    return JSONResponse(
        content=[hub.model_dump(mode="json") for hub in hubs],
        status_code=status.HTTP_200_OK,
    )



async def emergency_halt(request: Request) -> JSONResponse:
    """
    Kiểm tra dữ liệu đầu vào 
    ghi nhận sự kiện dừng khẩn cấp.
    """

    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        err_data = EmergencyHaltErrorResponse(
            status_code="400",
            error=1,
            detail="JSON không hợp lệ",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        req = EmergencyHaltRequest.model_validate(body)
    except ValidationError:
        # Không đưa dữ liệu đầu vào, đặc biệt token, vào thông báo lỗi.
        err_data = EmergencyHaltErrorResponse(
            status_code="422",
            error=1,
            detail=(
                "Dữ liệu dừng khẩn cấp không hợp lệ: reason, operator_id "
                "và confirmation_token phải là chuỗi không để trống"
            ),
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    response_data = EmergencyHaltResponse(
        success=True,
        status="EMERGENCY_HALT_ACTIVATED",
        message=f"Đã kích hoạt ngắt khẩn cấp toàn hệ thống: {req.reason}",
        affected_hubs=len(db.get_hubs()),
        timestamp_iso=datetime.utcnow().isoformat(),
    )

    # Chỉ ghi sự kiện sau khi yêu cầu đã vượt qua kiểm tra.
    content = response_data.model_dump(mode="json")

    def change(candidate):
        candidate.telemetry_events.insert(
            0,
            {
                "id": f"TLM-{len(candidate.telemetry_events) + 100}",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "hub_name": "Toàn hệ thống",
                "event_type": "EMERGENCY_HALT",
                "message": f"DỪNG KHẨN CẤP: {req.reason}",
                "level": "ALERT",
            },
        )

        return JSONResponse(
            content=content,
            status_code=status.HTTP_200_OK,
        )

    return persist_change(change)

routes = [
    Route("/api/v1/operator/dashboard/kpis", get_kpis, methods=["GET"]),
    Route("/api/v1/operator/dashboard/telemetry", get_telemetry_feed, methods=["GET"]),
    Route("/api/v1/operator/dashboard/hubs-live", get_hubs_live, methods=["GET"]),
    Route("/api/v1/operator/dashboard/emergency-halt", emergency_halt, methods=["POST"]),

]