"""
Mock Backend Service for Operator Control Center
Smart E-Mobility Hub - ĐHQG-HCM
"""

import os
import sys
import json






from datetime import datetime
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Ensure parent directory is in sys.path to import mock_db
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mock_db import db, RelocationError
from pydantic import ValidationError



from schemas import (
    OperatorLoginRequest,
    Operator2FARequest,
    OperatorProfile,
    OperatorTokenResponse,
    KPISummary,
    TelemetryEvent,
    AlertLevel,
    HubLiveStatus,
    EmergencyHaltRequest,
    EmergencyHaltResponse,
    RelocationCommandCreate,
    RelocationCommandItem,
    RelocationCommandList,
    RelocationStatus,
    RelocationPriority,
    MaintenanceTicketItem,
    MaintenanceAssignRequest,
    MaintenanceCreateRequest,
    MaintenanceTicketList,
    FaultSeverity,
    MaintenanceStatus,
    HubConfig,
    HubConfigUpdate,
    HubDeactivateRequest,
    HubManageList,
    HubOperationalStatus,
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
)

# In-memory mock database
DB = {
    "kpis": KPISummary(
        total_hubs=50,
        available_bikes=120,
        total_bikes=500,
        available_chargers=300,
        active_alerts=2,
    ),
    "telemetry": [
        TelemetryEvent(
            id="EVT-1029",
            hub_id="HUB-B",
            hub_name="Hub B - KTX Khu B",
            level=AlertLevel.ALERT,
            title="Mất kết nối IoT Hub B",
            message="Cổng sạc C-02 không phản hồi dữ liệu Telemetry quá 60s.",
            created_at_relative="Vừa xong",
            timestamp_iso=datetime.utcnow().isoformat(),
        ),
        TelemetryEvent(
            id="EVT-1028",
            hub_id="HUB-A",
            hub_name="Hub A - Ga Metro ĐHQG",
            level=AlertLevel.WARNING,
            title="Nhiệt độ trạm sạc Hub A cao",
            message="Trạm sạc số 4 đang ở mức 58°C (Ngưỡng cảnh báo).",
            created_at_relative="2 phút trước",
            timestamp_iso=datetime.utcnow().isoformat(),
        ),
        TelemetryEvent(
            id="EVT-1027",
            hub_id="HUB-SYS",
            hub_name="Hệ thống Điều phối",
            level=AlertLevel.NORMAL,
            title="Điều phối xe tự động",
            message="Đã kích hoạt kịch bản điều 5 xe từ Hub A sang Hub B.",
            created_at_relative="15 phút trước",
            timestamp_iso=datetime.utcnow().isoformat(),
        ),
        TelemetryEvent(
            id="EVT-1026",
            hub_id="HUB-C",
            hub_name="Hub C - ĐH Bách Khoa",
            level=AlertLevel.NORMAL,
            title="Khôi phục Hub C hoàn tất",
            message="Bảo trì định kỳ đã xong, tài nguyên sẵn sàng.",
            created_at_relative="1 giờ trước",
            timestamp_iso=datetime.utcnow().isoformat(),
        ),
    ],
    "hubs_live": [
        HubLiveStatus(
            hub_id="HUB-01",
            hub_code="HUB-METRO-01",
            name="Hub A - Ga Metro ĐHQG",
            status_label="Bình thường",
            is_high_load=False,
            parking_free=45,
            parking_total=150,
            chargers_free=12,
            chargers_total=50,
            current_power_kw=120.0,
            max_power_kw=1000.0,
            lat=10.8753,
            lng=106.8005,
            color_code="#10b981",
        ),
        HubLiveStatus(
            hub_id="HUB-02",
            hub_code="HUB-KTX-B",
            name="Hub B - KTX Khu B",
            status_label="ĐANG TẢI CAO",
            is_high_load=True,
            parking_free=12,
            parking_total=150,
            chargers_free=0,
            chargers_total=50,
            current_power_kw=850.0,
            max_power_kw=1000.0,
            lat=10.8835,
            lng=106.7820,
            color_code="#ef4444",
        ),
        HubLiveStatus(
            hub_id="HUB-03",
            hub_code="HUB-BK",
            name="Hub C - ĐH Bách Khoa",
            status_label="Bình thường",
            is_high_load=False,
            parking_free=38,
            parking_total=120,
            chargers_free=14,
            chargers_total=40,
            current_power_kw=140.0,
            max_power_kw=800.0,
            lat=10.8805,
            lng=106.8055,
            color_code="#10b981",
        ),
        HubLiveStatus(
            hub_id="HUB-04",
            hub_code="HUB-IU",
            name="Hub D - ĐH Quốc Tế",
            status_label="Bảo trì",
            is_high_load=False,
            parking_free=0,
            parking_total=80,
            chargers_free=0,
            chargers_total=30,
            current_power_kw=0.0,
            max_power_kw=500.0,
            lat=10.8778,
            lng=106.8018,
            color_code="#f59e0b",
        ),
    ],
    "relocations": [
        RelocationCommandItem(
            id="CMD-1023",
            source_hub_name="Hub A (KTX Khu A)",
            target_hub_name="Hub B (Ga Metro A)",
            bike_count=5,
            assigned_staff_name="Nguyen Van B",
            status=RelocationStatus.IN_TRANSIT,
            progress_current=3,
            progress_total=5,
            created_at="2026-10-22 14:15",
            updated_at="2026-10-22 14:28",
        ),
        RelocationCommandItem(
            id="CMD-1024",
            source_hub_name="Hub C (ĐH Bách Khoa)",
            target_hub_name="Hub A (KTX Khu A)",
            bike_count=2,
            assigned_staff_name="Tran Van C",
            status=RelocationStatus.PENDING,
            progress_current=0,
            progress_total=2,
            created_at="2026-10-22 14:30",
            updated_at="2026-10-22 14:30",
        ),
    ],
    "maintenance": [
        MaintenanceTicketItem(
            id="TKT-001",
            ticket_code="ERR-8812",
            device_code="CS-02-HUB_A",
            hub_name="Hub KTX Khu A",
            source="Cảnh báo IoT",
            fault_category="Quá nhiệt cổng sạc",
            severity=FaultSeverity.URGENT,
            assigned_staff_id=None,
            assigned_staff_name="Chưa gán",
            status=MaintenanceStatus.PENDING,
            reported_at="2026-10-22 14:25",
            description="Trạm sạc số 4 đang ở mức 58°C, vượt ngưỡng giới hạn an toàn 55°C",
            photo_url=None,
        ),
        MaintenanceTicketItem(
            id="TKT-002",
            ticket_code="INC-2026-089",
            device_code="XE-024",
            hub_name="Hub ĐH Bách Khoa",
            source="End-User",
            fault_category="Không mở được khóa",
            severity=FaultSeverity.WARNING,
            assigned_staff_id="TECH-02",
            assigned_staff_name="Le Van D",
            status=MaintenanceStatus.IN_PROGRESS,
            reported_at="2026-10-22 13:40",
            description="Khóa thông minh không nhận lệnh Bluetooth sau khi quét QR",
            photo_url=None,
        ),
    ],
    "hubs_config": [
        HubConfig(
            id="HUB-01",
            hub_code="HUB-METRO-01",
            name="Hub Ga Metro ĐHQG",
            address="Khu đô thị ĐHQG - HCM",
            parking_capacity=150,
            charger_capacity=50,
            max_power_kw=1000.0,
            load_warning_threshold_pct=85,
            lat=10.8753,
            lng=106.8005,
            status=HubOperationalStatus.ACTIVE,
            availability_rate_pct=85,
        ),
        HubConfig(
            id="HUB-02",
            hub_code="HUB-BK-02",
            name="Hub Đại học Bách khoa",
            address="Đường D1, Khu ĐHQG",
            parking_capacity=120,
            charger_capacity=40,
            max_power_kw=800.0,
            load_warning_threshold_pct=85,
            lat=10.8805,
            lng=106.8055,
            status=HubOperationalStatus.ACTIVE,
            availability_rate_pct=92,
        ),
        HubConfig(
            id="HUB-03",
            hub_code="HUB-KTX-B-03",
            name="Hub KTX Khu B",
            address="Ký túc xá Khu B",
            parking_capacity=200,
            charger_capacity=60,
            max_power_kw=1200.0,
            load_warning_threshold_pct=80,
            lat=10.8835,
            lng=106.7820,
            status=HubOperationalStatus.WARNING,
            availability_rate_pct=40,
        ),
    ],
    "sim_history": [
        SimulationHistoryItem(
            id="SIM-108",
            title="Tăng sinh viên giờ cao điểm Metro",
            parameters_summary="Tham số: Nhu cầu +150%, Hub Metro A hỏng 3 cổng",
            executed_at="10/10/2026 16:30",
            duration_str="45s",
            created_by="Nguyen Van A",
            status="Thành công",
            what_if_params="Nhu cầu tăng +150%, 3 cổng sạc hỏng tại Hub Metro A, Thời gian giả định: 2 giờ.",
            recorded_result="2 Hub vượt ngưỡng 85% tải, thiếu hụt 35 xe đạp điện tại các trạm kết nối.",
            saved_rule="Tự động gửi lệnh điều chuyển 20 xe từ Hub KTX A sang Metro A khi nhu cầu > 80%.",
        ),
        SimulationHistoryItem(
            id="SIM-107",
            title="Quá tải sạc Hub KTX Khu A",
            parameters_summary="Tham số: 100% cổng sạc bận, thời gian đợi > 25p",
            executed_at="09/10/2026 09:15",
            duration_str="38s",
            created_by="Nguyen Van A",
            status="Thành công",
            what_if_params="100% cọc sạc bận, thời gian sạc trung bình 3.5h, thời tiết nắng nóng 36°C.",
            recorded_result="Công suất trạm chạm ngưỡng 98% giới hạn công tơ điện lực, nhiệt độ tăng vọt.",
            saved_rule="Tự động kích hoạt giảm công suất sạc các xe pin > 75% xuống mức 3.3kW.",
        ),
        SimulationHistoryItem(
            id="SIM-106",
            title="Sự cố gián đoạn IoT toàn hệ thống",
            parameters_summary="Mất tín hiệu telemetry 12 Hubs trên diện rộng",
            executed_at="08/10/2026 14:00",
            duration_str="12s",
            created_by="Nguyen Van A",
            status="Thất bại",
            what_if_params="Mất kết nối mạng 4G/NB-IoT giữa server trung tâm và gateway các trạm.",
            recorded_result="Không đồng bộ được trạng thái pin xe, hệ thống chuyển sang chế độ dự phòng Offline.",
            saved_rule="Chuyển cọc sạc sang chế độ xác thực thẻ RFID nội bộ không cần mạng.",
        ),
        SimulationHistoryItem(
            id="SIM-105",
            title="Hỏng 5 cổng sạc nhanh Ga Metro A",
            parameters_summary="Công suất trạm giảm 50%, cảnh báo nhiệt độ cao",
            executed_at="05/10/2026 06:00",
            duration_str="52s",
            created_by="Nguyen Van A",
            status="Thành công",
            what_if_params="5 trụ sạc DC 30kW ngừng cấp nguồn đột ngột giờ cao điểm sáng.",
            recorded_result="Hàng đợi trả xe tăng 40 xe, ùn tắc cục bộ tại lối vào bãi đỗ Metro.",
            saved_rule="Điều hướng người dùng sang Hub ĐH Khoa học Tự nhiên cách 400m.",
        ),
    ]
}


# ================= ROUTE HANDLERS =================

async def login(request):
    try:
        body = await request.json()
        req = OperatorLoginRequest(**body)
    except Exception:
        req = OperatorLoginRequest(email="admin@e-mobility.com", password="password123")

    return JSONResponse({
        "success": True,
        "requires_2fa": True,
        "email": req.email,
        "message": "Vui lòng nhập mã xác thực 6 chữ số từ Google Authenticator hoặc Email.",
    })


async def verify_2fa(request):
    try:
        body = await request.json()
        req = Operator2FARequest(**body)
    except Exception:
        req = Operator2FARequest(email="admin@e-mobility.com", otp_code="849201")

    profile = OperatorProfile(
        id="OP-001",
        full_name="Nhân viên 1",
        role="Nhân viên giám sát",
        email=req.email,
        shift="Ca chiều · 13:00 - 17:00",
        avatar_initials="OP",
    )
    token_resp = OperatorTokenResponse(
        access_token="mock-jwt-operator-session-token-99882",
        token_type="bearer",
        expires_in=28800,
        operator=profile,
    )
    return JSONResponse(token_resp.dict())


async def get_kpis(request):
    k = db.get_kpis()
    alerts_count = len([t for t in db.telemetry_events if t.get("level") in ["WARNING", "ALERT", "DANGER"]])
    return JSONResponse(KPISummary(
        total_hubs=k["total_hubs"],
        available_bikes=k["available_bikes"],
        total_bikes=k["total_bikes"],
        available_chargers=k["available_chargers"],
        active_alerts=alerts_count or 2,
    ).dict())


async def get_telemetry_feed(request):
    events = []
    level_map = {
        "INFO": AlertLevel.NORMAL,
        "SUCCESS": AlertLevel.NORMAL,
        "WARNING": AlertLevel.WARNING,
        "ALERT": AlertLevel.ALERT,
        "DANGER": AlertLevel.ALERT
    }
    for evt in db.telemetry_events:
        events.append(TelemetryEvent(
            id=evt.get("id", "EVT-100"),
            hub_id=evt.get("hub_id", "HUB-METRO"),
            hub_name=evt.get("hub_name", "Hub Ga Metro ĐHQG"),
            level=level_map.get(evt.get("level"), AlertLevel.NORMAL),
            title=evt.get("event_type", "Thông báo vận hành"),
            message=evt.get("message", "Sự kiện hệ thống"),
            created_at_relative="Vừa xong",
            timestamp_iso=datetime.utcnow().isoformat()
        ).dict())
    return JSONResponse(events)


async def get_hubs_live(request):
    live_list = []
    for h in db.get_hubs():
        live_list.append(HubLiveStatus(
            hub_id=h["id"].upper(),
            hub_code=h.get("hub_code", h["id"].upper()),
            name=h["name"],
            status_label="Bình thường" if h.get("status") == "ACTIVE" else "Tạm ngưng",
            is_high_load=h.get("available_bikes", 0) <= 2,
            parking_free=h.get("available_parking", 8),
            parking_total=h.get("parking_capacity", 20),
            chargers_free=h.get("available_chargers", 2),
            chargers_total=h.get("charger_capacity", 4),
            current_power_kw=h.get("max_power_kw", 100.0) * 0.45,
            max_power_kw=h.get("max_power_kw", 100.0),
            lat=h["lat"],
            lng=h["lng"],
            color_code=h.get("color", "#10b981"),
            available_bikes=h.get("available_bikes", 0)
        ).dict())
    return JSONResponse(live_list)


async def emergency_halt(request):
    try:
        body = await request.json()
        req = EmergencyHaltRequest(**body)
    except Exception:
        req = EmergencyHaltRequest(
            reason="Kích hoạt thủ công từ giao diện Operator",
            operator_id="OP-001",
            confirmation_token="HALT_CONFIRM",
        )

    db.telemetry_events.insert(0, {
        "id": f"TLM-{len(db.telemetry_events) + 100}",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "hub_name": "Toàn hệ thống",
        "event_type": "EMERGENCY_HALT",
        "message": f"DỪNG KHẨN CẤP: {req.reason}",
        "level": "ALERT"
    })
    return JSONResponse(
        EmergencyHaltResponse(
            success=True,
            status="EMERGENCY_HALT_ACTIVATED",
            message=f"Đã kích hoạt ngắt khẩn cấp toàn hệ thống: {req.reason}",
            affected_hubs=len(db.get_hubs()),
            timestamp_iso=datetime.utcnow().isoformat(),
        ).dict()
    )


def relocation_response(task):
    status_map = {
        "PENDING": RelocationStatus.PENDING,
        "IN_PROGRESS": RelocationStatus.IN_TRANSIT,
        "IN_TRANSIT": RelocationStatus.IN_TRANSIT,
        "COMPLETED": RelocationStatus.COMPLETED,
        "CANCELLED": RelocationStatus.CANCELLED,
    }

    item = RelocationCommandItem(
        id=task["task_id"],
        source_hub_name=task["source_hub_name"],
        target_hub_name=task["target_hub_name"],
        bike_count=task["total_bikes"],
        assigned_staff_name=task.get(
            "assigned_staff_name",
            task.get("assigned_to", "Chưa phân công"),
        ),
        status=status_map[task["status"]],
        progress_current=task["in_transit_bikes"],
        progress_total=task["total_bikes"],
        created_at=task["created_at"],
        updated_at=task.get("updated_at", task["created_at"]),
    ).model_dump(mode="json")

    item.update(
        source_hub_id=task["source_hub_id"],
        target_hub_id=task["target_hub_id"],
        assigned_staff_id=task.get("assigned_staff_id"),
        bike_ids=[entry["bike_id"] for entry in task["bikes"]],
        reserved_slot_ids=task.get("reserved_slot_ids", []),
        priority=task["priority"],
        notes=task.get("notes"),
    )
    return item


async def list_relocations(request):
    items = [relocation_response(task) for task in db.relocations]
    return JSONResponse({"total": len(items), "items": items})


async def create_relocation(request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            {"error": "JSON không hợp lệ"},
            status_code=400,
        )

    if not isinstance(body, dict):
        return JSONResponse(
            {"error": "Body phải là một JSON object"},
            status_code=422,
        )

    try:
        req = RelocationCommandCreate(**body)
    except ValidationError as exc:
        return JSONResponse(
            {"error": "Dữ liệu không hợp lệ", "details": str(exc)},
            status_code=422,
        )

    try:
        task = db.create_relocation_command(req.model_dump())
    except RelocationError as exc:
        return JSONResponse(
            {"error": str(exc)},
            status_code=exc.status_code,
        )

    return JSONResponse(relocation_response(task), status_code=201)


async def list_maintenance(request):
    severity_map = {
        "LOW": FaultSeverity.LOW,
        "MEDIUM": FaultSeverity.WARNING,
        "HIGH": FaultSeverity.URGENT,
        "URGENT": FaultSeverity.URGENT,
        "Thường": FaultSeverity.LOW,
        "Cảnh báo": FaultSeverity.WARNING,
        "Khẩn cấp": FaultSeverity.URGENT,
    }
    status_map = {
        "PENDING": MaintenanceStatus.PENDING,
        "ASSIGNED": MaintenanceStatus.ASSIGNED,
        "IN_PROGRESS": MaintenanceStatus.IN_PROGRESS,
        "RESOLVED": MaintenanceStatus.RESOLVED,
        "CLOSED": MaintenanceStatus.CLOSED,
    }

    items = []

    for ticket in db.maintenance_tickets:
        staff_id = ticket.get("assigned_staff_id")

        # Đọc ID trong phiếu seed cũ, ví dụ STF-02 (Nguyen Van B).
        if not staff_id:
            old_assignment = ticket.get("assigned_to", "")
            candidate = old_assignment.split()[0] if old_assignment else ""
            if candidate.startswith("STF-"):
                staff_id = candidate

        staff = next(
            (person for person in db.staff if person["id"] == staff_id),
            None,
        )

        if staff:
            staff_name = staff["full_name"]
        elif staff_id:
            staff_name = ticket.get("assigned_to", staff_id)
        else:
            staff_name = "Chưa gán"

        item = MaintenanceTicketItem(
            id=ticket["code"],
            ticket_code=ticket["code"],
            device_code=ticket["device_code"],
            hub_name=ticket["hub_name"],
            source=ticket.get("source", "Store dùng chung"),
            fault_category=ticket["title"],
            severity=severity_map[ticket["severity"]],
            assigned_staff_id=staff_id,
            assigned_staff_name=staff_name,
            status=status_map[ticket["status"]],
            reported_at=ticket.get(
                "reported_time", ticket["created_at"]
            ),
            description=ticket.get("description"),
            photo_url=ticket.get("photo_url"),
        )
        items.append(item.model_dump(mode="json"))

    return JSONResponse({"total": len(items), "items": items})


async def assign_maintenance(request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            {"error": "JSON không hợp lệ"},
            status_code=400,
        )

    if not isinstance(body, dict):
        return JSONResponse(
            {"error": "Body phải là một JSON object"},
            status_code=422,
        )

    try:
        req = MaintenanceAssignRequest(**body)
    except ValidationError as exc:
        return JSONResponse(
            {"error": "Dữ liệu không hợp lệ", "details": str(exc)},
            status_code=422,
        )

    ticket = next(
        (
            item for item in db.maintenance_tickets
            if item["code"] == req.ticket_code
        ),
        None,
    )
    if ticket is None:
        return JSONResponse(
            {"error": "Không tìm thấy mã phiếu bảo trì"},
            status_code=404,
        )

    technician = next(
        (
            person for person in db.staff
            if person["id"] == req.technician_id
        ),
        None,
    )
    if technician is None:
        return JSONResponse(
            {"error": "Không tìm thấy nhân viên"},
            status_code=404,
        )

    if technician["role"] != "MAINTENANCE":
        return JSONResponse(
            {"error": "Nhân viên không có vai trò bảo trì"},
            status_code=422,
        )

    if ticket["status"] not in ("PENDING", "ASSIGNED"):
        return JSONResponse(
            {"error": "Chỉ được giao phiếu đang chờ hoặc đã phân công"},
            status_code=409,
        )

    severity_map = {
        FaultSeverity.LOW: "LOW",
        FaultSeverity.WARNING: "MEDIUM",
        FaultSeverity.URGENT: "URGENT",
    }

    # Chỉ cập nhật sau khi toàn bộ kiểm tra đã thành công.
    # Tên nhân viên lấy từ store, không tin tên client gửi lên.
    ticket.update({
        "assigned_staff_id": technician["id"],
        "assigned_staff_name": technician["full_name"],
        "assigned_to": technician["full_name"],
        "severity": severity_map[req.priority],
        "priority": (
            "URGENT"
            if req.priority == FaultSeverity.URGENT
            else "NORMAL"
        ),
        "operator_notes": req.operator_notes,
        "status": "ASSIGNED",
        "updated_at": datetime.now().isoformat(),
    })

    return JSONResponse({
        "success": True,
        "message": (
            f"Đã phân công {technician['full_name']} "
            f"xử lý phiếu {ticket['code']}"
        ),
        "ticket": ticket,
    })

async def list_hubs_config(request):
    status_map = {
        "ACTIVE": HubOperationalStatus.ACTIVE,
        "WARNING": HubOperationalStatus.WARNING,
        "MAINTENANCE": HubOperationalStatus.MAINTENANCE,
        "DEACTIVATED": HubOperationalStatus.DEACTIVATED,
    }

    items = []

    for hub in db.get_hubs():
        item = HubConfig(
            id=hub["id"],
            hub_code=hub["hub_code"],
            name=hub["name"],
            address=hub["address"],
            parking_capacity=hub["parking_capacity"],
            charger_capacity=hub["charger_capacity"],
            max_power_kw=hub["max_power_kw"],
            load_warning_threshold_pct=hub["load_warning_threshold_pct"],
            lat=hub["lat"],
            lng=hub["lng"],
            status=status_map[hub["status"]],
            availability_rate_pct=hub.get("availability_rate_pct", 85),
        )

        items.append(item)

    response = HubManageList(
        total=len(items),
        items=items,
    )

    return JSONResponse(response.model_dump(mode="json"))




async def update_hub_config(request):
    hub_id = request.path_params["hub_id"].lower()

    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            {"error": "JSON không hợp lệ"},
            status_code=400,
        )

    if not isinstance(body, dict):
        return JSONResponse(
            {"error": "Body phải là một JSON object"},
            status_code=422,
        )

    if "hub_id" in body:
        body_hub_id = body["hub_id"]

        if (
            not isinstance(body_hub_id, str)
            or body_hub_id.lower() != hub_id
        ):
            return JSONResponse(
                {"error": "hub_id trong body phải khớp với đường dẫn"},
                status_code=422,
            )

    hub = db.get_hub(hub_id)

    if hub is None:
        return JSONResponse(
            {"error": "Hub không tồn tại"},
            status_code=404,
        )

    try:
        req = HubConfigUpdate(
            **{**body, "hub_id": hub_id}
        )
    except ValidationError as exc:
        return JSONResponse(
            {
                "error": "Dữ liệu cập nhật không hợp lệ",
                "details": str(exc),
            },
            status_code=422,
        )

    changes = req.model_dump(
        exclude_unset=True,
        exclude={"hub_id"},
    )

    if not changes:
        return JSONResponse(
            {"error": "Chưa gửi trường cấu hình cần cập nhật"},
            status_code=422,
        )

    if any(value is None for value in changes.values()):
        return JSONResponse(
            {"error": "Các trường cập nhật không được nhận null"},
            status_code=422,
        )

    if "status" in changes:
        changes["status"] = req.status.name

    candidate = {**hub, **changes}

    try:
        HubConfig(
            **{
                **candidate,
                "status": HubOperationalStatus[candidate["status"]],
            }
        )
    except ValidationError as exc:
        return JSONResponse(
            {
                "error": "Cấu hình mới vượt giới hạn cho phép",
                "details": str(exc),
            },
            status_code=422,
        )

    hub.update(changes)

    return JSONResponse({
        "success": True,
        "hub": hub,
    })


async def deactivate_hub(request):
    hub_id = request.path_params.get("hub_id", "HUB-01").lower()
    h = db.get_hub(hub_id) or db.get_hub(f"hub-{hub_id.split('-')[-1]}")
    if h:
        h["status"] = "DEACTIVATED"
        return JSONResponse({
            "success": True,
            "message": f"Hub {h['name']} đã chuyển sang trạng thái tạm ngưng (Deactivated).",
            "hub": h,
        })
    return JSONResponse({"error": "Hub không tồn tại"}, status_code=404)


# ================= WHAT-IF SIMULATION ROUTES =================

def build_simulation_source():
    import copy
    from datetime import timezone

    hubs = copy.deepcopy(db.get_hubs())
    snapshots = []

    for hub in hubs:
        # Bản cơ bản dùng danh sách thiết bị trong store.
        # Hub ngừng hoạt động không có cổng phục vụ mô phỏng.
        available_ports = [
            port
            for port in hub.get("ports", [])
            if hub["status"] == "ACTIVE"
            and port.get("is_available", False)
        ]

        # Store chưa có số đo công suất thực:
        # giả định tải nền = 50% tổng công suất cổng sẵn sàng.
        base_power_kw = sum(
            port["power_kw"] for port in available_ports
        ) * 0.5

        snapshot = HubStateSnapshot(
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
        snapshots.append(snapshot)

    result = SimulationSourceState(
        source_type=SourceStateType.LIVE_STATE_A,
        source_label="Snapshot từ store; công suất nền ước tính",
        hub_snapshots=snapshots,
    ).model_dump(mode="json")

    result["captured_at"] = datetime.now(timezone.utc).isoformat()
    result["power_basis"] = (
        "Ước tính 50% tổng công suất cổng sẵn sàng; "
        "không phải số đo IoT"
    )
    return result


def prepare_simulation_input(body):
    import copy
    import math
    from datetime import timezone

    if not isinstance(body, dict):
        raise ValueError("Body phải là JSON object")

    source_type = SourceStateType(
        body.get("source_type", "LIVE_A")
    )

    if source_type == SourceStateType.LIVE_STATE_A:
        # LIVE_A luôn đọc từ store, không tin snapshot client gửi.
        source = build_simulation_source()
    else:
        raw_snapshots = body.get("hub_snapshots")

        if not isinstance(raw_snapshots, list) or not raw_snapshots:
            raise ValueError("Bản manual phải có hub_snapshots không rỗng")

        integer_fields = (
            "total_parking_capacity",
            "current_bikes",
            "free_parking_slots",
            "total_chargers",
            "active_chargers",
        )
        power_fields = ("base_power_kw", "max_power_kw")

        for item in raw_snapshots:
            if not isinstance(item, dict):
                raise ValueError("Mỗi snapshot phải là JSON object")

            for field in integer_fields:
                if type(item.get(field)) is not int:
                    raise ValueError(f"{field} phải là số nguyên")

            for field in power_fields:
                value = item.get(field)
                if (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                ):
                    raise ValueError(f"{field} phải là số hữu hạn")

        source = SimulationSourceState(
            source_type=source_type,
            source_label="Bản sao chỉnh tay",
            hub_snapshots=raw_snapshots,
        ).model_dump(mode="json")
        source["captured_at"] = datetime.now(timezone.utc).isoformat()
        source["power_basis"] = "Dữ liệu manual do người chạy nhập"

    snapshots = source["hub_snapshots"]
    if not snapshots:
        raise ValueError("Không có Hub để mô phỏng")

    seen = set()
    known_ids = {hub["id"] for hub in db.get_hubs()}

    for hub in snapshots:
        hub_id = hub["hub_id"]

        if hub_id not in known_ids:
            raise ValueError(f"Hub không tồn tại: {hub_id}")
        if hub_id in seen:
            raise ValueError(f"Trùng hub_id: {hub_id}")
        seen.add(hub_id)

        capacity = hub["total_parking_capacity"]
        bikes = hub["current_bikes"]
        free_slots = hub["free_parking_slots"]
        chargers = hub["total_chargers"]
        active = hub["active_chargers"]
        base_power = hub["base_power_kw"]
        max_power = hub["max_power_kw"]

        if capacity <= 0:
            raise ValueError(f"{hub_id}: sức chứa phải lớn hơn 0")

        if not 0 <= bikes <= capacity:
            raise ValueError(f"{hub_id}: số xe ngoài sức chứa")

        if not 0 <= free_slots <= capacity:
            raise ValueError(f"{hub_id}: số chỗ trống ngoài sức chứa")

        if chargers < 0 or not 0 <= active <= chargers:
            raise ValueError(f"{hub_id}: số cổng sạc không hợp lệ")

        if (
            not math.isfinite(base_power)
            or not math.isfinite(max_power)
            or base_power < 0
            or max_power <= 0
            or base_power > max_power
        ):
            raise ValueError(f"{hub_id}: công suất nền/giới hạn không hợp lệ")

        if active == 0 and base_power != 0:
            raise ValueError(f"{hub_id}: không có cổng hoạt động nhưng có tải sạc")

    raw_config = body.get("config")
    if not isinstance(raw_config, dict):
        raise ValueError("Thiếu config dạng JSON object")

    config = SimulationScenarioConfig(**raw_config)

    if config.scenario_type.name != "DEMAND_SURGE":
        raise ValueError("Bản cơ bản hiện chỉ hỗ trợ tăng nhu cầu sạc")

    if config.demand_increase_pct < 0:
        raise ValueError("Tình huống tăng nhu cầu yêu cầu mức tăng từ 0 đến 300%")

    if not config.scenario_name.strip():
        raise ValueError("Tên tình huống không được để trống")

    try:
        start = datetime.strptime(config.start_time, "%H:%M")
    except ValueError:
        raise ValueError("start_time phải có dạng HH:MM")

    if start.strftime("%H:%M") != config.start_time:
        raise ValueError("start_time phải có dạng HH:MM")

    # Các cờ is_input_valid/is_grid_state_loaded không quyết định hợp lệ.
    # Những tham số của tình huống khác không được âm thầm bỏ qua.
    if (
        config.affected_chargers_count != 0
        or config.lost_power_kw != 0
        or config.additional_bikes_count != 0
    ):
        raise ValueError(
            "Tăng nhu cầu thuần túy cần affected_chargers_count, "
            "lost_power_kw, additional_bikes_count bằng 0"
        )

    return (
        copy.deepcopy(source),
        config.model_dump(mode="json"),
    )


async def get_simulation_source_state(request):
    return JSONResponse(build_simulation_source())


async def validate_simulation_parameters(request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            {"is_valid": False, "error": "JSON không hợp lệ"},
            status_code=400,
        )

    try:
        source, config = prepare_simulation_input(body)
    except (ValidationError, ValueError) as exc:
        return JSONResponse(
            {
                "is_valid": False,
                "error_code": "EX-10-01",
                "error_type": "INVALID_INPUT",
                "message": str(exc),
            },
            status_code=422,
        )

    return JSONResponse({
        "is_valid": True,
        "message": "Dữ liệu hợp lệ",
        "source": source,
        "config": config,
    })




async def run_simulation(request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    # If trigger timeout error test
    if body.get("trigger_timeout_error"):
        return JSONResponse({
            "error_code": "EX-10-02",
            "error_type": "IOT_TIMEOUT",
            "message": "Mô phỏng thất bại do sự cố gián đoạn dữ liệu giả lập/IoT hoặc mất kết nối.",
        }, status_code=504)

    # Return standard result from wireframe 19.jpg
    result = SimulationResultResponse(
        simulation_id="SIM-109",
        scenario_name="Nhu cầu sạc tăng 50%",
        status="Hoàn thành",
        executed_at="22/10/2026",
        load_chart_data=[
            HubLoadPoint(time_label="17:00", metro_hub_load_pct=48, bachkhoa_hub_load_pct=42, warning_threshold_pct=85),
            HubLoadPoint(time_label="17:20", metro_hub_load_pct=56, bachkhoa_hub_load_pct=47, warning_threshold_pct=85),
            HubLoadPoint(time_label="17:40", metro_hub_load_pct=67, bachkhoa_hub_load_pct=44, warning_threshold_pct=85),
            HubLoadPoint(time_label="18:00", metro_hub_load_pct=81, bachkhoa_hub_load_pct=51, warning_threshold_pct=85),
            HubLoadPoint(time_label="18:20", metro_hub_load_pct=92, bachkhoa_hub_load_pct=55, warning_threshold_pct=85),
            HubLoadPoint(time_label="18:40", metro_hub_load_pct=88, bachkhoa_hub_load_pct=53, warning_threshold_pct=85),
            HubLoadPoint(time_label="19:00", metro_hub_load_pct=94, bachkhoa_hub_load_pct=56, warning_threshold_pct=85),
        ],
        power_chart_data=[
            PowerLoadPoint(time_label="17:00", power_kw=70.0, station_limit_kw=180.0),
            PowerLoadPoint(time_label="17:20", power_kw=90.0, station_limit_kw=180.0),
            PowerLoadPoint(time_label="17:40", power_kw=115.0, station_limit_kw=180.0),
            PowerLoadPoint(time_label="18:00", power_kw=160.0, station_limit_kw=180.0),
            PowerLoadPoint(time_label="18:20", power_kw=185.0, station_limit_kw=180.0),
            PowerLoadPoint(time_label="18:40", power_kw=150.0, station_limit_kw=180.0),
            PowerLoadPoint(time_label="19:00", power_kw=120.0, station_limit_kw=180.0),
        ],
        peak_power_kw=185.0,
        peak_metro_load_pct=92,
        overloaded_hubs="2 / 12",
        overloaded_chargers="15 / 60",
        metro_deficit_bikes=35,
        recommendations=[
            DispatchRecommendationItem(
                title="Điều chuyển xe khẩn cấp",
                source_hub="Hub KTX Khu A",
                target_hub="Hub Ga Metro A",
                bike_count=20,
                vehicle_type="Xe đạp điện",
                details=["Nguồn: Hub KTX Khu A", "Đích: Hub Ga Metro A", "Số lượng: 20 xe đạp điện"]
            ),
            DispatchRecommendationItem(
                title="Ưu tiên lịch sạc thông minh",
                source_hub=None,
                target_hub="Hub Ga Metro",
                bike_count=None,
                vehicle_type=None,
                details=["Hub Ga Metro: Tăng công suất sạc cổng 1-5", "Tạm hoãn sạc các xe pin > 70%"]
            ),
            DispatchRecommendationItem(
                title="Điều hướng người dùng",
                source_hub=None,
                target_hub="Hub KTX Khu B",
                bike_count=None,
                vehicle_type=None,
                details=["Gợi ý trả xe sang Hub KTX Khu B để hưởng ưu đãi voucher 10.000đ"]
            ),
        ]
    )
    return JSONResponse(result.dict())


async def save_simulation_rule(request):
    try:
        body = await request.json()
        req = SimulationSaveRuleRequest(**body)
    except Exception:
        req = SimulationSaveRuleRequest(
            simulation_id="SIM-109",
            rule_name="Kịch bản ứng phó vỡ trận ga Metro giờ cao điểm",
            operation_instructions="Điều chuyển xe từ Hub KTX Khu A sang Hub Ga Metro.",
            auto_match_on_high_load=True,
        )

    # Insert into simulation history with saved rule
    history_entry = SimulationHistoryItem(
        id=f"SIM-{109 + len(DB['sim_history'])}",
        title=req.rule_name,
        parameters_summary="Nhu cầu +50%, Đỉnh tải 185 kW tại Metro",
        executed_at=datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        duration_str="50s",
        created_by="Nhân viên 1",
        status="Thành công",
        what_if_params="Mức tăng sạc 50%, thời lượng 60 phút, bù 30 xe",
        recorded_result="2 Hub quá tải, 15 cổng sạc cần theo dõi",
        saved_rule=req.operation_instructions,
    )
    DB["sim_history"].insert(0, history_entry)

    return JSONResponse({
        "success": True,
        "message": f"Đã lưu kịch bản dự phòng '{req.rule_name}' vào thư viện vận hành.",
        "history_id": history_entry.id,
    })


async def get_simulation_history(request):
    return JSONResponse(
        SimulationHistoryList(total=len(DB["sim_history"]), items=DB["sim_history"]).dict()
    )


# ================= APPLICATION SETUP =================

routes = [
    Route("/api/v1/operator/auth/login", login, methods=["POST"]),
    Route("/api/v1/operator/auth/verify-2fa", verify_2fa, methods=["POST"]),
    Route("/api/v1/operator/dashboard/kpis", get_kpis, methods=["GET"]),
    Route("/api/v1/operator/dashboard/telemetry", get_telemetry_feed, methods=["GET"]),
    Route("/api/v1/operator/dashboard/hubs-live", get_hubs_live, methods=["GET"]),
    Route("/api/v1/operator/dashboard/emergency-halt", emergency_halt, methods=["POST"]),
    Route("/api/v1/operator/relocation/commands", list_relocations, methods=["GET"]),
    Route("/api/v1/operator/relocation/commands", create_relocation, methods=["POST"]),
    Route("/api/v1/operator/maintenance/tickets", list_maintenance, methods=["GET"]),
    Route("/api/v1/operator/maintenance/assign", assign_maintenance, methods=["POST"]),
    Route("/api/v1/operator/hubs", list_hubs_config, methods=["GET"]),
    Route("/api/v1/operator/hubs/{hub_id}/config", update_hub_config, methods=["PUT"]),
    Route("/api/v1/operator/hubs/{hub_id}/deactivate", deactivate_hub, methods=["POST"]),
    Route("/api/v1/operator/simulation/source-state", get_simulation_source_state, methods=["GET"]),
    Route("/api/v1/operator/simulation/validate", validate_simulation_parameters, methods=["POST"]),
    Route("/api/v1/operator/simulation/run", run_simulation, methods=["POST"]),
    Route("/api/v1/operator/simulation/save-rule", save_simulation_rule, methods=["POST"]),
    Route("/api/v1/operator/simulation/history", get_simulation_history, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
