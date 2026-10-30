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

from mock_db import db

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


async def list_relocations(request):
    items = []
    for r in db.relocations:
        status_enum = RelocationStatus.IN_TRANSIT if r["status"] in ["IN_PROGRESS", "IN_TRANSIT"] else (RelocationStatus.COMPLETED if r["status"] == "COMPLETED" else RelocationStatus.PENDING)
        items.append(RelocationCommandItem(
            id=r["task_id"],
            source_hub_name=r["source_hub_name"],
            target_hub_name=r["target_hub_name"],
            bike_count=r["total_bikes"],
            assigned_staff_name=r.get("assigned_to", "Nguyen Van B"),
            status=status_enum,
            progress_current=r.get("in_transit_bikes", 0),
            progress_total=r.get("total_bikes", 5),
            created_at=r.get("created_at", "2026-10-18 08:30"),
            updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        ).dict())
    return JSONResponse(
        RelocationCommandList(total=len(items), items=items).dict()
    )


async def create_relocation(request):
    try:
        body = await request.json()
        req = RelocationCommandCreate(**body)
    except Exception:
        req = RelocationCommandCreate(
            source_hub_id="hub-03",
            target_hub_id="hub-01",
            bike_count=5,
            assigned_staff_id="STF-02",
            priority=RelocationPriority.NORMAL,
            notes="Điều chuyển xe thử nghiệm",
        )

    task = db.create_relocation_command(req.dict())
    item = RelocationCommandItem(
        id=task["task_id"],
        source_hub_name=task["source_hub_name"],
        target_hub_name=task["target_hub_name"],
        bike_count=task["total_bikes"],
        assigned_staff_name=task.get("assigned_to", "Nguyen Van B"),
        status=RelocationStatus.IN_TRANSIT,
        progress_current=0,
        progress_total=task["total_bikes"],
        created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        updated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    )
    return JSONResponse(item.dict(), status_code=201)


async def list_maintenance(request):
    items = []
    sev_map = {"LOW": FaultSeverity.LOW, "MEDIUM": FaultSeverity.MEDIUM, "HIGH": FaultSeverity.HIGH, "URGENT": FaultSeverity.URGENT}
    st_map = {"PENDING": MaintenanceStatus.PENDING, "ASSIGNED": MaintenanceStatus.ASSIGNED, "IN_PROGRESS": MaintenanceStatus.IN_PROGRESS, "RESOLVED": MaintenanceStatus.RESOLVED}
    for t in db.maintenance_tickets:
        items.append(MaintenanceTicketItem(
            ticket_code=t["code"],
            hub_name=t["hub_name"],
            device_type=t["device_type"],
            device_id=t.get("device_code", "DEV-01"),
            severity=sev_map.get(t.get("severity", "MEDIUM"), FaultSeverity.MEDIUM),
            status=st_map.get(t.get("status", "PENDING"), MaintenanceStatus.PENDING),
            reported_time=t.get("reported_time", "18/10/2026 · 09:15"),
            assigned_staff_id="STF-02",
            assigned_staff_name=t.get("assigned_to", "Nguyen Van B")
        ).dict())
    return JSONResponse(
        MaintenanceTicketList(total=len(items), items=items).dict()
    )


async def assign_maintenance(request):
    try:
        body = await request.json()
        req = MaintenanceAssignRequest(**body)
    except Exception:
        req = MaintenanceAssignRequest(
            ticket_code="TICK-802",
            technician_id="STF-02",
            technician_name="Nguyen Van B",
            priority=FaultSeverity.URGENT,
            operator_notes="Ưu tiên xử lý trước giờ cao điểm",
        )

    for item in db.maintenance_tickets:
        if item["code"] == req.ticket_code:
            item["assigned_to"] = req.technician_name
            item["severity"] = req.priority.value if hasattr(req.priority, "value") else str(req.priority)
            item["status"] = "ASSIGNED"
            return JSONResponse({
                "success": True,
                "message": f"Đã phân công {req.technician_name} xử lý phiếu {req.ticket_code}",
                "ticket": item,
            })

    return JSONResponse({"error": "Không tìm thấy mã phiếu bảo trì"}, status_code=404)


async def list_hubs_config(request):
    items = []
    for h in db.get_hubs():
        items.append(HubConfig(
            id=h["id"].upper(),
            hub_code=h.get("hub_code", h["id"].upper()),
            name=h["name"],
            parking_capacity=h.get("parking_capacity", 20),
            charger_capacity=h.get("charger_capacity", 4),
            max_power_kw=h.get("max_power_kw", 100.0),
            load_warning_threshold_pct=h.get("load_warning_threshold_pct", 85),
            status=HubOperationalStatus.ACTIVE if h.get("status") == "ACTIVE" else HubOperationalStatus.DEACTIVATED
        ).dict())
    return JSONResponse(
        HubManageList(total=len(items), items=items).dict()
    )


async def update_hub_config(request):
    hub_id = request.path_params.get("hub_id", "HUB-01").lower()
    try:
        body = await request.json()
        req = HubConfigUpdate(hub_id=hub_id, **body)
    except Exception:
        req = HubConfigUpdate(hub_id=hub_id)

    h = db.get_hub(hub_id) or db.get_hub(f"hub-{hub_id.split('-')[-1]}")
    if h:
        if req.name: h["name"] = req.name
        if req.parking_capacity: h["parking_capacity"] = req.parking_capacity
        if req.charger_capacity: h["charger_capacity"] = req.charger_capacity
        if req.max_power_kw: h["max_power_kw"] = req.max_power_kw
        if req.load_warning_threshold_pct: h["load_warning_threshold_pct"] = req.load_warning_threshold_pct
        if req.status: h["status"] = req.status.value if hasattr(req.status, "value") else req.status
        return JSONResponse({"success": True, "hub": h})

    return JSONResponse({"error": "Hub không tồn tại"}, status_code=404)


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

async def get_simulation_source_state(request):
    snapshots = [
        HubStateSnapshot(
            hub_id=f"HUB-0{i}",
            hub_code=f"HUB-0{i}",
            name=f"Hub 0{i} - {['Ga Metro A', 'ĐH Bách Khoa', 'KTX Khu B', 'ĐH Quốc Tế', 'KTX Khu A', 'ĐH KHTN', 'ĐH KHXH&NV', 'Thư viện Trung tâm'][i-1]}",
            total_parking_capacity=100,
            current_bikes=65 - i * 3,
            free_parking_slots=35 + i * 3,
            total_chargers=20,
            active_chargers=18 - (i % 3),
            base_power_kw=200.0,
            max_power_kw=1000.0,
        )
        for i in range(1, 9)
    ]
    resp = SimulationSourceState(
        source_type=SourceStateType.LIVE_STATE_A,
        source_label="Trạng thái mạng lưới hiện tại (A)",
        hub_snapshots=snapshots,
    )
    return JSONResponse(resp.dict())


async def validate_simulation_parameters(request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Check if manual data exceeds threshold to simulate EX-10-01
    hub_code = body.get("check_hub_code")
    if hub_code == "HUB-04" or body.get("trigger_invalid_error"):
        return JSONResponse(
            SimulationValidationResult(
                is_valid=False,
                error_code="EX-10-01",
                error_type="INVALID_INPUT",
                message="THAM SỐ KHÔNG HỢP LỆ",
                details="Hub 04 có số lượng xe vượt quá sức chứa tối đa của trạm (120/100 chỗ). Vui lòng điều chỉnh lại dữ liệu trước khi mô phỏng.",
            ).dict(),
            status_code=422,
        )

    return JSONResponse(
        SimulationValidationResult(
            is_valid=True,
            error_code=None,
            error_type=None,
            message="Dữ liệu đầu vào hợp lệ. Trạng thái mạng lưới sẵn sàng để chạy mô phỏng.",
        ).dict()
    )


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
