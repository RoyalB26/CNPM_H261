"""Liên kết báo cáo người dùng với phiếu bảo trì dùng chung."""

import copy
from datetime import datetime, timezone
from uuid import uuid4

from shared.memory_store import MockDatabaseStore
from .schemas.incident import CreateIncidentReportRequest, IncidentReportResponse


def create_report(db: MockDatabaseStore, request: CreateIncidentReportRequest) -> IncidentReportResponse:
    """Tạo báo cáo và phiếu đúng Hub sau khi chuẩn bị, kiểm tra toàn bộ dữ liệu."""
    hub = next((hub for hub in db.get_hubs() if hub['name'] == request.hub_name), None)
    if hub is None:
        raise ValueError('Hub báo cáo không tồn tại')
    # Chuẩn bị phiếu trên bản sao; chưa thêm vào store thật nếu dữ liệu lỗi.
    candidate = copy.copy(db)
    candidate.maintenance_tickets = list(db.maintenance_tickets)
    ticket = candidate.create_maintenance_ticket({
        'title': f'Sự cố người dùng: {request.incident_type} ({request.resource_code})',
        'hub_id': hub['id'], 'hub_name': hub['name'],
        'device_type': request.resource_type, 'device_code': request.resource_code,
        'description': request.description, 'severity': 'MEDIUM', 'priority': 'HIGH',
    })
    numbers = [int(t['code'][5:]) for t in db.maintenance_tickets
               if t.get('code', '').startswith('TICK-') and t['code'][5:].isdigit()]
    ticket['code'] = f'TICK-{max(numbers, default=800) + 1}'
    ticket['source'] = 'Người dùng'
    report = IncidentReportResponse(
        id=f'INC-{uuid4().hex}', **request.model_dump(),
        created_at=datetime.now(timezone.utc).isoformat(), status='Đang xử lý',
        operator_note='Hệ thống đã nhận báo cáo và chuyển đến điều hành viên.',
        maintenance_ticket_code=ticket['code'], maintenance_status=ticket['status'],
    )
    ticket['incident_id'] = report.id
    db.maintenance_tickets.insert(0, ticket)
    db.incidents.insert(0, report.model_dump(mode='json', exclude_unset=True))
    return report


def report_view(db: MockDatabaseStore, stored: dict) -> IncidentReportResponse:
    """Đọc trạng thái mới nhất của phiếu; không sửa báo cáo khi GET."""
    data = copy.deepcopy(stored)
    # Seed cũ chưa có cấu trúc response mới, chuyển đổi trên bản sao.
    data.setdefault('resource_type', 'Phương tiện' if data.get('vehicle_id') else 'Thiết bị')
    data.setdefault('resource_code', data.get('vehicle_id', 'Không rõ'))
    data.setdefault('incident_type', data.get('title') or data.get('category', 'Sự cố'))
    data.setdefault('created_at', data.get('date', 'Không rõ'))
    code = data.get('maintenance_ticket_code')
    ticket = next((t for t in db.maintenance_tickets if code and t['code'] == code), None)
    if ticket is not None:
        status = ticket['status']
        data['maintenance_status'] = status
        data['status'] = 'Đã giải quyết' if status in ('RESOLVED', 'CLOSED') else 'Đang xử lý'
        note = ticket.get('resolution_notes') if status in ('RESOLVED', 'CLOSED') else ticket.get('operator_notes')
        if note:
            data['operator_note'] = note
    return IncidentReportResponse.model_validate(data)
