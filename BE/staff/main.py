"""
Mock Backend Service for Field Staff & Security Guard
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
    StaffRole,
    StaffLoginRequest,
    StaffProfile,
    StaffTokenResponse,
    BikeChecklistStatus,
    BikeChecklistItem,
    RelocationTaskDetail,
    BikeScanRequest,
    RelocationHandoverRequest,
    RelocationIncidentRequest,
    MaintenancePriority,
    ResolutionOutcome,
    MaintenanceTaskSummary,
    MaintenanceTaskDetail,
    DeviceVerifyRequest,
    MaintenanceResolveRequest,
    MaintenanceIncidentRequest,
    VehicleCheckInRequest,
    VehicleCheckInResponse,
    VehicleCheckOutResponse,
    ParkingTransactionItem,
    ShiftReconciliationSummary,
    ShiftCloseRequest,
)

# In-memory mock database for Staff operations
DB = {
    "staff_profile": StaffProfile(
        id="STF-02",
        full_name="Nguyen Van B",
        role=StaffRole.MAINTENANCE,
        shift_title="Ca chiều · 13:00 - 17:00",
        assigned_hub="Hub KTX Khu A",
        avatar_initials="MT",
        tasks_count=4,
    ),
    "relocation_task": RelocationTaskDetail(
        task_id="#102",
        title="Hướng dẫn di chuyển điều phối xe",
        source_hub_name="Hub KTX Khu A",
        target_hub_name="Hub Ga Metro A",
        vehicle_type="Xe đạp điện",
        total_bikes=20,
        in_transit_bikes=12,
        remaining_at_source=8,
        estimated_distance_km=2.5,
        estimated_duration_minutes=10,
        checklist=[
            BikeChecklistItem(bike_code="BK-EB-001", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-002", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-003", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-004", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-005", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-006", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-007", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-008", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-009", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-010", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-011", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-012", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-013", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-014", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-015", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-016", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-017", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-018", battery_pct=85, dock_number="02", status=BikeChecklistStatus.DONE),
            BikeChecklistItem(bike_code="BK-EB-019", battery_pct=85, dock_number="02", status=BikeChecklistStatus.WAITING),
            BikeChecklistItem(bike_code="BK-EB-020", battery_pct=85, dock_number="02", status=BikeChecklistStatus.WAITING),
        ],
    ),
    "maintenance_tasks": [
        MaintenanceTaskSummary(
            task_code="MT-102",
            priority=MaintenancePriority.URGENT,
            category_label="XE ĐẠP ĐIỆN · HƯ HỎNG",
            title="Xe BK-EB-018 không khởi động",
            hub_name="Hub KTX Khu A",
            created_at_label="Hôm nay, 14:25",
            due_label="Cần xử lý trong 35 phút",
            status="Mới tiếp nhận",
        ),
        MaintenanceTaskSummary(
            task_code="MT-098",
            priority=MaintenancePriority.WARNING,
            category_label="CỔNG SẠC · KHÔNG HOẠT ĐỘNG",
            title="Cổng sạc số 05 không nhận điện",
            hub_name="Hub Ga Metro A",
            created_at_label="Hôm nay, 13:50",
            due_label="Cần kiểm tra trong hôm nay",
            status="Mới tiếp nhận",
        ),
        MaintenanceTaskSummary(
            task_code="MT-091",
            priority=MaintenancePriority.NORMAL,
            category_label="TRẠM SẠC · BẢO DƯỠNG ĐỊNH KỲ",
            title="Nguồn điện trạm sạc cần bảo dưỡng",
            hub_name="Hub Trường BK",
            created_at_label="Hôm nay, 11:20",
            due_label="Định kỳ tuần",
            status="Mới tiếp nhận",
        ),
    ],
    "parking_shift": ShiftReconciliationSummary(
        shift_title="Ca chiều · 13:00 - 17:00",
        shift_date="22/10/2026",
        hub_name="Hub KTX Khu A",
        total_vehicles_served=48,
        total_cash_collected_vnd=1200000,
        transactions=[
            ParkingTransactionItem(seq_number="01", license_plate="59-B2 123.45", time_info="14:36 · 2 giờ 06 phút", amount_vnd=25000),
            ParkingTransactionItem(seq_number="02", license_plate="51-H1 678.90", time_info="14:22 · 1 giờ 48 phút", amount_vnd=25000),
            ParkingTransactionItem(seq_number="03", license_plate="59-C3 246.80", time_info="13:58 · 3 giờ 12 phút", amount_vnd=25000),
        ],
        is_closed=False,
    )
}


# ================= ROUTE HANDLERS =================

async def login(request):
    try:
        body = await request.json()
        req = StaffLoginRequest(**body)
    except Exception:
        req = StaffLoginRequest(username_or_phone="staff_b", password="password123")

    token_resp = StaffTokenResponse(
        access_token="mock-jwt-staff-session-token-4455",
        token_type="bearer",
        staff=DB["staff_profile"],
    )
    return JSONResponse(token_resp.dict())


async def get_profile(request):
    tasks_count = len([t for t in db.maintenance_tickets if t.get("status") in ["PENDING", "ASSIGNED", "IN_PROGRESS"]])
    profile = StaffProfile(
        id="STF-02",
        full_name="Nguyen Van B",
        role=StaffRole.MAINTENANCE,
        shift_title="Ca chiều · 13:00 - 17:00",
        assigned_hub="Hub KTX Khu B",
        avatar_initials="MT",
        tasks_count=tasks_count or 4,
    )
    return JSONResponse(profile.dict())


# Relocation Handlers
async def get_relocation_task(request):
    task_id = request.path_params.get("task_id", "#102")
    active_task = next((t for t in db.relocations if t.get("status") == "IN_PROGRESS"), db.relocations[0] if db.relocations else None)
    if not active_task:
        return JSONResponse({"error": "Không có lệnh điều phối"}, status_code=404)

    checklist = [
        BikeChecklistItem(
            bike_code=b["bike_id"],
            battery_pct=b["battery_pct"],
            status=BikeChecklistStatus.DONE if b["status"] == "VERIFIED" else BikeChecklistStatus.WAITING,
            scanned_at="Vừa quét" if b["status"] == "VERIFIED" else None,
        )
        for b in active_task.get("bikes", [])
    ]
    resp = RelocationTaskDetail(
        task_id=active_task["task_id"],
        title=active_task["title"],
        source_hub_name=active_task["source_hub_name"],
        target_hub_name=active_task["target_hub_name"],
        vehicle_type=active_task.get("vehicle_type", "Xe đạp điện"),
        total_bikes=active_task["total_bikes"],
        in_transit_bikes=active_task["in_transit_bikes"],
        remaining_at_source=active_task["remaining_at_source"],
        estimated_distance_km=active_task.get("estimated_distance_km", 2.5),
        source_contact=active_task.get("source_contact", "0901-234-567 (Hub Trưởng KTX B)"),
        target_contact=active_task.get("target_contact", "0908-765-432 (Trực ban Hub Ga Metro)"),
        status=active_task["status"],
        priority=active_task.get("priority", "HIGH"),
        checklist=checklist,
    )
    return JSONResponse(resp.dict())


async def scan_bike(request):
    try:
        body = await request.json()
        req = BikeScanRequest(**body)
    except Exception:
        req = BikeScanRequest(task_id="#102", qr_data="BK-0891")

    res = db.scan_bike_relocation(req.task_id, req.qr_data)
    task = res["task"]
    return JSONResponse({
        "success": True,
        "scanned_code": req.qr_data,
        "progress_done": res["verified_count"],
        "progress_total": task["total_bikes"],
        "message": f"Đã đối soát xe {req.qr_data} cọc sạc {req.target_dock_code}"
    })


async def handover_relocation(request):
    try:
        body = await request.json()
        req = RelocationHandoverRequest(**body)
    except Exception:
        req = RelocationHandoverRequest(task_id="#102", confirmed_by_staff_id="STF-02")

    res = db.handover_relocation(req.task_id)
    return JSONResponse({
        "success": True,
        "task_id": req.task_id,
        "status": "HANDOVER_COMPLETED",
        "message": "Hoàn tất bàn giao xe tại Hub! Hạ tầng đã cập nhật sẵn sàng đón khách.",
        "completed_at": datetime.utcnow().isoformat(),
    })


async def report_relocation_incident(request):
    try:
        body = await request.json()
        req = RelocationIncidentRequest(**body)
    except Exception:
        req = RelocationIncidentRequest(
            task_id="#102",
            incident_type="Xe bị thủng lốp",
            location_text="Đường nội bộ giữa Hub KTX Khu A và Hub Ga Metro A",
            description="Xe BK-EB-014 bị hỏng lốp",
        )

    db.create_maintenance_ticket({
        "title": f"Sự cố điều phối xe: {req.incident_type}",
        "hub_name": "Hub Ga Metro ĐHQG",
        "device_type": "Xe điều phối",
        "device_code": req.task_id,
        "description": f"{req.description} ({req.location_text})",
        "severity": "HIGH",
        "priority": "URGENT"
    })
    return JSONResponse({
        "success": True,
        "incident_id": f"INC-RELOC-{int(datetime.utcnow().timestamp())}",
        "message": "Đã gửi báo cáo sự cố thành công đến trung tâm điều hành!",
        "report": req.dict(),
    })


# Maintenance Handlers
async def get_maintenance_tasks(request):
    new_tasks = []
    in_progress = []
    completed = []
    for t in db.maintenance_tickets:
        summary = MaintenanceTaskSummary(
            task_code=t["code"],
            priority=MaintenancePriority.URGENT if t.get("severity") in ["HIGH", "URGENT"] else MaintenancePriority.NORMAL,
            category_label=f"{t['device_type'].upper()} · SỰ CỐ",
            title=t["title"],
            hub_name=t["hub_name"],
            reported_time=t.get("reported_time", "18/10/2026 · 09:15"),
            assigned_staff="Nguyen Van B",
            status_text="Chờ tiếp nhận" if t.get("status") == "PENDING" else ("Đang xử lý" if t.get("status") == "IN_PROGRESS" else "Đã hoàn tất"),
        )
        if t.get("status") in ["PENDING", "ASSIGNED"]:
            new_tasks.append(summary.dict())
        elif t.get("status") == "IN_PROGRESS":
            in_progress.append(summary.dict())
        else:
            completed.append(summary.dict())
    return JSONResponse({
        "new_tasks": new_tasks,
        "in_progress_tasks": in_progress,
        "completed_tasks": completed,
    })


async def get_maintenance_detail(request):
    task_code = request.path_params.get("task_code", "TICK-801")
    t = next((m for m in db.maintenance_tickets if m["code"] == task_code), db.maintenance_tickets[0])
    detail = MaintenanceTaskDetail(
        task_code=t["code"],
        priority=MaintenancePriority.URGENT if t.get("severity") in ["HIGH", "URGENT"] else MaintenancePriority.NORMAL,
        category_label=f"{t['device_type'].upper()} · HƯ HỎNG",
        title=t["title"],
        reported_by="Trung tâm điều hành / Khách hàng",
        device_code=t.get("device_code", "DEV-01"),
        exact_location=f"{t['hub_name']} · Khu vực kỹ thuật",
        reporter_notes=t.get("description", "Cần kiểm tra và khắc phục."),
        attachment_filename="anh-hien-trang-01.jpg",
        last_maintenance_info="Kiểm tra gần nhất · 12/10/2026 · NVKT Tran Minh A · Hoàn tất",
    )
    return JSONResponse(detail.dict())


async def verify_device(request):
    try:
        body = await request.json()
        req = DeviceVerifyRequest(**body)
    except Exception:
        req = DeviceVerifyRequest(task_code="TICK-801", scanned_qr_code="LOCK-019")

    return JSONResponse({
        "success": True,
        "device_code": req.scanned_qr_code,
        "location": "Hub KTX Khu B · Ô số 019",
        "verified": True,
        "message": f"Xác thực thành công! Đúng thiết bị {req.scanned_qr_code}",
    })


async def resolve_maintenance(request):
    try:
        body = await request.json()
        req = MaintenanceResolveRequest(**body)
    except Exception:
        req = MaintenanceResolveRequest(
            task_code="TICK-801",
            outcome=ResolutionOutcome.FIXED_ON_SITE,
            technical_notes="Đã sửa tại chỗ",
        )

    db.resolve_maintenance(req.task_code, req.technical_notes)
    return JSONResponse({
        "success": True,
        "task_code": req.task_code,
        "outcome": req.outcome.value if hasattr(req.outcome, "value") else str(req.outcome),
        "message": "Đã gửi kết quả bảo trì thành công! Thiết bị đã được mở khóa và đưa vào sử dụng.",
    })


async def report_maintenance_incident(request):
    try:
        body = await request.json()
        req = MaintenanceIncidentRequest(**body)
    except Exception:
        req = MaintenanceIncidentRequest(
            task_code="TICK-801",
            incident_type="Lỗi linh kiện thay thế",
            location_text="Hub KTX Khu B",
            description="Cần cấp thêm bộ bo mạch điều khiển mới",
        )

    return JSONResponse({
        "success": True,
        "incident_id": f"INC-MT-{int(datetime.utcnow().timestamp())}",
        "message": "Đã ghi nhận sự cố mới. Đội vận hành sẽ hỗ trợ kịp thời.",
        "report": req.dict(),
    })


# Security Guard / Hub Parking Handlers (Screens 11, 12, 13)
async def parking_checkin(request):
    try:
        body = await request.json()
        req = VehicleCheckInRequest(**body)
    except Exception:
        req = VehicleCheckInRequest(
            license_plate="59-X1 123.45",
            parking_bay="Dãy A",
            parking_slot="Ô số 018",
            hub_name="Hub Ga Metro ĐHQG",
        )

    rec = db.parking_checkin({
        "plate_number": req.license_plate,
        "hub_name": req.hub_name or "Hub Ga Metro ĐHQG",
        "slot_id": f"{req.parking_bay} · {req.parking_slot}"
    })
    resp = VehicleCheckInResponse(
        success=True,
        ticket_code=rec["ticket_code"],
        license_plate=rec["plate_number"],
        bay_slot=rec["slot_id"],
        checkin_time=rec["checkin_time"],
        status_message="Thông tin đã sẵn sàng · Kiểm tra lại trước khi xác nhận vào bãi.",
    )
    return JSONResponse(resp.dict())


async def parking_checkout_preview(request):
    plate = request.path_params.get("plate_or_ticket", "59-X1 123.45")
    rec = next((r for r in db.parking_records if r["plate_number"] == plate or r["ticket_code"] == plate), None)
    ticket_code = rec["ticket_code"] if rec else f"PRK-{int(datetime.utcnow().timestamp())%1000}"
    checkin_t = rec["checkin_time"] if rec else "18/10/2026 · 10:00"
    fee = rec["parking_fee"] if rec else 5000

    resp = VehicleCheckOutResponse(
        ticket_code=ticket_code,
        license_plate=plate,
        checkin_time=checkin_t,
        checkout_time=datetime.utcnow().strftime("%d/%m/%Y · %H:%M"),
        duration_str="2 giờ 06 phút",
        total_fee_vnd=fee,
        payment_method="Thanh toán bằng tiền mặt tại quầy",
        is_paid=False,
    )
    return JSONResponse(resp.dict())


async def parking_checkout_confirm(request):
    try:
        body = await request.json()
        ticket_code = body.get("ticket_code", "PRK-901")
        method = body.get("payment_method", "TIỀN MẶT")
    except Exception:
        ticket_code = "PRK-901"
        method = "TIỀN MẶT"
    db.parking_checkout_confirm(ticket_code, method)
    return JSONResponse({
        "success": True,
        "ticket_code": ticket_code,
        "paid_amount": 5000,
        "message": "Xác nhận đã thu 5.000 VNĐ tiền mặt thành công. Mở barrier cho xe ra.",
    })


async def get_shift_summary(request):
    records = db.parking_records
    cash = sum(r.get("parking_fee", 5000) for r in records if r.get("payment_method") == "TIỀN MẶT") or 65000
    tx_items = [
        ParkingTransactionItem(
            seq_number=f"{i+1:02d}",
            license_plate=r["plate_number"],
            time_info=f"{r['checkin_time']} · 45 phút",
            amount_vnd=r.get("parking_fee", 5000)
        )
        for i, r in enumerate(records[:5])
    ]
    summary = ShiftReconciliationSummary(
        shift_code="SHIFT-CA-CHIEU",
        guard_name="Nguyen Van B",
        hub_name="Hub Ga Metro ĐHQG",
        total_vehicles_served=len(records) + 40,
        total_cash_collected_vnd=cash,
        transactions=tx_items,
        is_closed=False,
    )
    return JSONResponse(summary.dict())


async def close_shift(request):
    try:
        body = await request.json()
        req = ShiftCloseRequest(**body)
    except Exception:
        req = ShiftCloseRequest(shift_code="SHIFT-CA-CHIEU", supervisor_pin="1234")

    return JSONResponse({
        "success": True,
        "shift_code": req.shift_code,
        "status": "SHIFT_CLOSED",
        "message": "Ca trực đã được kết toán và đóng thành công.",
        "closed_at": datetime.utcnow().isoformat(),
    })


# ================= APPLICATION SETUP =================

routes = [
    Route("/api/v1/staff/auth/login", login, methods=["POST"]),
    Route("/api/v1/staff/profile", get_profile, methods=["GET"]),
    Route("/api/v1/staff/relocation/task", get_relocation_task, methods=["GET"]),
    Route("/api/v1/staff/relocation/task/{task_id:path}", get_relocation_task, methods=["GET"]),
    Route("/api/v1/staff/relocation/scan-bike", scan_bike, methods=["POST"]),
    Route("/api/v1/staff/relocation/handover", handover_relocation, methods=["POST"]),
    Route("/api/v1/staff/relocation/incident", report_relocation_incident, methods=["POST"]),
    Route("/api/v1/staff/maintenance/tasks", get_maintenance_tasks, methods=["GET"]),
    Route("/api/v1/staff/maintenance/tasks/{task_code}", get_maintenance_detail, methods=["GET"]),
    Route("/api/v1/staff/maintenance/verify-device", verify_device, methods=["POST"]),
    Route("/api/v1/staff/maintenance/resolve", resolve_maintenance, methods=["POST"]),
    Route("/api/v1/staff/maintenance/incident", report_maintenance_incident, methods=["POST"]),
    Route("/api/v1/staff/parking/checkin", parking_checkin, methods=["POST"]),
    Route("/api/v1/staff/parking/checkout/{plate_or_ticket}", parking_checkout_preview, methods=["GET"]),
    Route("/api/v1/staff/parking/checkout/confirm", parking_checkout_confirm, methods=["POST"]),
    Route("/api/v1/staff/parking/shift-summary", get_shift_summary, methods=["GET"]),
    Route("/api/v1/staff/parking/shift-close", close_shift, methods=["POST"]),
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
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
