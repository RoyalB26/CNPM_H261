"""Liên kết báo cáo người dùng với phiếu bảo trì dùng chung."""

import copy
from datetime import datetime, timezone
from uuid import uuid4

from shared.memory_store import MockDatabaseStore
from .schemas.incident import CreateIncidentReportRequest, IncidentReportResponse


class IncidentError(ValueError):
    """Lỗi tài nguyên hoặc liên kết phiếu; không tạo dữ liệu thay thế."""

    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def resource_code(db: MockDatabaseStore, hub: dict, request: CreateIncidentReportRequest) -> str:
    """Đối chiếu mã theo loại; xe đang đi có thể chọn Hub tiếp nhận báo cáo."""
    kind = request.resource_type
    if kind == 'Phương tiện':
        codes = [b['id'] for b in hub.get('bikes', [])]
        ride = db.user.get('active_services', {}).get('ride')
        if ride and db.owns_user_record(ride):
            codes.append(ride['vehicle_id'])
    elif kind == 'Chỗ đỗ':
        codes = [slot['id'] for slot in hub.get('slots', [])]
    elif kind == 'Cổng sạc':
        codes = [port['id'] for port in hub.get('ports', [])]
    elif kind in ('Pin', 'Trạm pin'):
        codes = [code for battery in hub.get('batteries', [])
                 for code in (battery.get('id'), battery['battery_type']) if code]
    else:
        codes = [hub['id'], hub.get('hub_code', hub['id'])]
    matches = [code for code in codes if isinstance(code, str) and code.casefold() == request.resource_code.casefold()]
    if not matches:
        raise IncidentError('Mã tài nguyên không thuộc Hub hoặc phiên đang sử dụng', 404)
    return matches[0]


def create_report(db: MockDatabaseStore, request: CreateIncidentReportRequest) -> IncidentReportResponse:
    """Tạo báo cáo và phiếu đúng Hub sau khi chuẩn bị, kiểm tra toàn bộ dữ liệu."""
    hubs = [hub for hub in db.get_hubs() if hub['name'] == request.hub_name]
    if not hubs:
        raise IncidentError('Hub báo cáo không tồn tại', 404)
    if len(hubs) != 1:
        raise IncidentError('Tên Hub báo cáo không xác định duy nhất')
    hub = hubs[0]
    code = resource_code(db, hub, request)
    request = request.model_copy(update={'resource_code': code})
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
        user_id=db.user['id'],
        hub_id=hub['id'],
        id=f'INC-{uuid4().hex}', **request.model_dump(),
        created_at=datetime.now(timezone.utc).isoformat(), status='Đang xử lý',
        operator_note='Hệ thống đã nhận báo cáo và chuyển đến điều hành viên.',
        maintenance_ticket_code=ticket['code'], maintenance_status=ticket['status'],
    )
    ticket['incident_id'] = report.id
    ticket['user_id'] = db.user['id']
    from shared.notifications import notify
    notify(db, ticket["code"] + ":created", "operator", "User báo sự cố mới", ticket["code"])
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
    tickets = [t for t in db.maintenance_tickets if code and t['code'] == code]
    if len(tickets) > 1:
        raise IncidentError('Mã phiếu bảo trì bị trùng')
    ticket = tickets[0] if tickets else None
    if ticket is not None:
        if (ticket.get('incident_id', data['id']) != data['id']
            or (data.get('hub_id') and ticket.get('hub_id') != data['hub_id'])
            or ('user_id' in ticket and ticket['user_id'] != data.get('user_id'))):
            raise IncidentError('Phiếu bảo trì không khớp báo cáo đã lưu')
        status = ticket['status']
        data['maintenance_status'] = status
        data['status'] = 'Đã giải quyết' if status in ('RESOLVED', 'CLOSED') else 'Đang xử lý'
        note = ticket.get('resolution_notes') if status in ('RESOLVED', 'CLOSED') else ticket.get('operator_notes')
        if note:
            data['operator_note'] = note
    return IncidentReportResponse.model_validate(data)
