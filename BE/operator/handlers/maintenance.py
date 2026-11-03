
import json
from datetime import datetime
from typing import Any


from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..store import db, persist_change
from ..schemas.maintenance import (
    MaintenanceTicketItem,
    MaintenanceAssignRequest,
    MaintenanceCreateRequest,
    MaintenanceTicketList,
    MaintenanceAssignResponse,
    MaintenanceErrorResponse,
    FaultSeverity,
    MaintenanceStatus,
)





# Xem danh sách -> list_maintenance -> maintenance_response


# Phân công    -> assign_maintenance -> maintenance_response
#                                  -> maintenance_error_response if errorr

def maintenance_response(ticket: dict[str, Any], 
                         ) -> MaintenanceTicketItem:
    """Chuyển phiếu trong store thành model dùng cho danh sách và phân công."""
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

    staff_id = ticket.get("assigned_staff_id")

    # Hỗ trợ phiếu seed cũ lưu ID trong chuỗi assigned_to.
    if not staff_id:
        old_assignment = ticket.get("assigned_to") or ""
        candidate = old_assignment.split()[0] if old_assignment else ""
        if candidate.startswith("STF-"):
            staff_id = candidate

    staff = next(
        (person for person in db.staff if person["id"] == staff_id),
        None,
    )

    if staff:
        staff_name = staff["full_name"]
    else:
        staff_name = (
            ticket.get("assigned_staff_name")
            or ticket.get("assigned_to")
            or "Chưa gán"
        )

    return MaintenanceTicketItem(
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
        reported_at=ticket.get("reported_time") or ticket["created_at"],
        description=ticket.get("description"),
        photo_url=ticket.get("photo_url"),
    )


def maintenance_error_response(
    status_code: int,
    detail: str,
) -> JSONResponse:
    """Tạo response lỗi bảo trì theo cấu trúc thống nhất."""
    err_data = MaintenanceErrorResponse(
        status_code=str(status_code),
        error=1,
        detail=detail,
    )
    return JSONResponse(
        content=err_data.model_dump(mode="json"),
        status_code=status_code,
    )


async def list_maintenance(request: Request) -> JSONResponse:
    """Trả danh sách phiếu bảo trì theo MaintenanceTicketList."""
    items = [
        maintenance_response(ticket)
        for ticket in db.maintenance_tickets
    ]
    response_data = MaintenanceTicketList(
        total=len(items),
        items=items,
    )

    return JSONResponse(
        content=response_data.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


async def assign_maintenance(request: Request) -> JSONResponse:
    """Kiểm tra yêu cầu và phân công nhân viên cho phiếu bảo trì."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return maintenance_error_response(
            status.HTTP_400_BAD_REQUEST,
            "JSON không hợp lệ",
        )

    try:
        req = MaintenanceAssignRequest.model_validate(body)
    except ValidationError:
        return maintenance_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Dữ liệu phân công bảo trì không hợp lệ",
        )

    ticket = next(
        (
            item for item in db.maintenance_tickets
            if item["code"] == req.ticket_code
        ),
        None,
    )
    if ticket is None:
        return maintenance_error_response(
            status.HTTP_404_NOT_FOUND,
            "Không tìm thấy mã phiếu bảo trì",
        )

    technician = next(
        (
            person for person in db.staff
            if person["id"] == req.technician_id
        ),
        None,
    )
    if technician is None:
        return maintenance_error_response(
            status.HTTP_404_NOT_FOUND,
            "Không tìm thấy nhân viên",
        )

    if technician["role"] != "MAINTENANCE":
        return maintenance_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Nhân viên không có vai trò bảo trì",
        )

    if ticket["status"] not in ("PENDING", "ASSIGNED"):
        return maintenance_error_response(
            status.HTTP_409_CONFLICT,
            "Chỉ được giao phiếu đang chờ hoặc đã phân công",
        )

    severity_map = {
        FaultSeverity.LOW: "LOW",
        FaultSeverity.WARNING: "MEDIUM",
        FaultSeverity.URGENT: "URGENT",
    }

    # Chuẩn bị bản cập nhật; tên nhân viên lấy từ store.
    updated_ticket = {
        **ticket,
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
    }

    # Kiểm tra và serialize response trước khi thay đổi phiếu thật.
    response_data = MaintenanceAssignResponse(
        success=True,
        message=(
            f"Đã phân công {technician['full_name']} "
            f"xử lý phiếu {ticket['code']}"
        ),
        ticket=maintenance_response(updated_ticket),
    )
    content = response_data.model_dump(mode="json")

    def change(candidate):
        candidate_ticket = next(
            item
            for item in candidate.maintenance_tickets
            if item["code"] == req.ticket_code
        )
        candidate_ticket.update(updated_ticket)

        return JSONResponse(
            content=content,
            status_code=status.HTTP_200_OK,
        )

    return persist_change(change)

routes = [

    Route("/api/v1/operator/maintenance/tickets", list_maintenance, methods=["GET"]),
    Route("/api/v1/operator/maintenance/assign", assign_maintenance, methods=["POST"]),
]