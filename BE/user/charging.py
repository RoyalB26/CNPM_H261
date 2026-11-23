"""Nhận/trả cổng sạc và tính phí điện năng mô phỏng, chưa tích hợp IoT."""

import copy
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
from uuid import uuid4

from shared.booking_expiry import booking_expired
from shared.charging_reservations import charging_port_blocked
from shared.memory_store import MockDatabaseStore
from .schemas.booking import BookingResponse
from .schemas.payment import InvoiceResponse
from .schemas.service import StartChargingResponse, StopChargingRequest, StopChargingResponse


class ChargingError(ValueError):
    """Lỗi nghiệp vụ; chưa thay đổi phiên hoặc tài nguyên khi phát sinh."""

    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def start_charging(db: MockDatabaseStore, booking_id: str) -> StartChargingResponse:
    """Dùng cổng đã giữ; không trừ số cổng khả dụng thêm lần nữa."""
    matches = [b for b in db.bookings if b['id'] == booking_id]
    if not matches:
        raise ChargingError('Booking không tồn tại', 404)
    if len(matches) != 1:
        raise ChargingError('Mã booking không duy nhất')
    booking = matches[0]
    if booking.get('plan_type') != 'charging' or booking.get('status') != 'Đã xác nhận':
        raise ChargingError('Booking không đủ điều kiện nhận cổng sạc')
    now = datetime.now(timezone.utc)
    try:
        expired = booking_expired(booking, now)
    except (ValueError, TypeError):
        raise ChargingError('Thời hạn booking không hợp lệ')
    if expired:
        raise ChargingError('Booking sạc đã hết hạn')
    if db.user.get('active_services', {}).get('charging'):
        raise ChargingError('Người dùng đang có phiên sạc khác')
    hub = db.get_hub(booking['hub_id'])
    port = next((p for p in hub.get('ports', []) if p['id'] == booking.get('charging_port')), None) if hub else None
    if hub is None or hub['status'] != 'ACTIVE' or port is None:
        raise ChargingError('Hub hoặc cổng sạc không hoạt động')
    if port.get('reserved_by') != booking_id or port.get('status') != 'Đã đặt chỗ' or charging_port_blocked(db, hub, port['id'], ignore_booking_id=booking_id):
        raise ChargingError('Cổng sạc không còn thuộc booking hoặc đang bảo trì')
    rate = booking.get('charging_rate_per_kwh')
    if type(rate) is not int or rate < 0:
        raise ChargingError('Booking thiếu đơn giá điện hợp lệ')
    session = {
        'session_id': f'CHG-{uuid4().hex}', 'booking_id': booking_id,
        'hub_id': hub['id'], 'hub_name': hub['name'], 'port_id': port['id'],
        'plate_number': booking.get('personal_plate'), 'started_at': now.isoformat(),
        'rate_per_kwh': rate, 'power_consumed_kwh': 0.0, 'current_charge': 0,
        'elapsed_minutes': 0, 'status': 'Đang sạc',
    }
    response = StartChargingResponse(charging=session)
    booking['status'] = 'Đang sử dụng'
    booking['charging_session'] = copy.deepcopy(session)
    port.pop('reserved_by')
    port['occupied_by'] = session['session_id']
    port['status'] = 'Đang sạc'
    db.user['active_services']['charging'] = session
    return response


def stop_charging(db: MockDatabaseStore, request: StopChargingRequest) -> StopChargingResponse:
    """Kết thúc phiên đã chọn, giữ lịch sử và hóa đơn; chỉ giải phóng cổng an toàn."""
    session = db.user.get('active_services', {}).get('charging')
    if not session or session.get('session_id') != request.session_id:
        raise ChargingError('Không có phiên sạc khớp mã yêu cầu')
    if request.power_consumed_kwh < session.get('power_consumed_kwh', 0):
        raise ChargingError('Điện năng tổng không được nhỏ hơn số đã ghi nhận')
    if request.final_charge is not None and request.final_charge < session.get('current_charge', 0):
        raise ChargingError('Mức pin sau sạc không được nhỏ hơn mức đã ghi nhận')
    hubs = [h for h in db.hubs if (session.get('hub_id') is None or h['id'] == session['hub_id'])
            and any(p['id'] == session['port_id'] for p in h.get('ports', []))]
    if len(hubs) != 1:
        raise ChargingError('Không xác định được Hub của phiên sạc')
    hub = hubs[0]
    port = next(p for p in hub['ports'] if p['id'] == session['port_id'])
    if port.get('reserved_by') or port.get('occupied_by') not in (None, request.session_id):
        raise ChargingError('Cổng sạc đang thuộc một phiên khác')
    legacy = session.get('booking_id') is None
    if legacy:
        # Seed chưa gắn booking: tạo lịch sử hoàn tất mới, không bịa thời điểm cắm sạc.
        booking = {
            'id': f'EMH-LEGACY-{uuid4().hex}', 'hub_id': hub['id'], 'hub_name': hub['name'],
            'plan_type': 'charging', 'resource_name': port['name'], 'charging_port': port['id'],
            'services': [], 'status': 'Hoàn thành', 'hold_until': '', 'created_at': '', 'price': 0,
        }
    else:
        matches = [b for b in db.bookings if b['id'] == session['booking_id']]
        if len(matches) != 1:
            raise ChargingError('Không xác định được booking của phiên sạc')
        booking = matches[0]
        if booking.get('status') != 'Đang sử dụng' or booking.get('plan_type') != 'charging' or booking.get('charging_port') != port['id'] or booking.get('hub_id') != hub['id']:
            raise ChargingError('Phiên sạc không khớp booking đang sử dụng')
    rate = session.get('rate_per_kwh', port.get('rate_per_kwh'))
    if type(rate) is not int or rate < 0:
        raise ChargingError('Đơn giá điện không hợp lệ')
    now = datetime.now(timezone.utc)
    history = {**copy.deepcopy(session), 'booking_id': booking['id'], 'hub_id': hub['id'],
               'hub_name': hub['name'], 'status': 'Hoàn thành', 'ended_at': now.isoformat(),
               'rate_per_kwh': rate, 'power_consumed_kwh': request.power_consumed_kwh,
               'measurement_source': 'mock_input'}
    if session.get('started_at') is not None:
        try:
            started = datetime.fromisoformat(session['started_at'])
            if started.tzinfo is None or started > now:
                raise ValueError('Mốc thời gian không hợp lệ')
            history['elapsed_minutes'] = math.ceil((now - started).total_seconds() / 60)
        except (ValueError, TypeError):
            raise ChargingError('Thời điểm bắt đầu sạc không hợp lệ')
    if request.final_charge is not None:
        history['current_charge'] = request.final_charge
    amount = int((Decimal(str(request.power_consumed_kwh)) * rate).to_integral_value(rounding=ROUND_CEILING))
    description = f"Điện năng {request.power_consumed_kwh} kWh × {rate}đ/kWh"
    invoice = InvoiceResponse(
        id=f'INV-{request.session_id}', service_type='charging', title='Hóa đơn dịch vụ sạc pin',
        reference_id=port['id'], items=[{'label': description, 'description': description, 'amount': amount}],
        total_amount=amount, payment_channel='online', status='unpaid', created_at=now.isoformat(),
    )
    updated = {**booking, 'status': 'Hoàn thành', 'price': amount, 'completed_at': now.isoformat(),
               'charging_rate_per_kwh': rate, 'charging_session': history,
               'charging_invoice': invoice.model_dump(mode='json', exclude_unset=True)}
    if legacy:
        updated['created_at'] = now.isoformat()
    BookingResponse.model_validate(updated)
    response = StopChargingResponse(booking_id=booking['id'], session_id=request.session_id,
                                    power_consumed_kwh=request.power_consumed_kwh, total_fee=amount, invoice=invoice)
    can_release = port.get('status') == 'Đang sạc' and not charging_port_blocked(
        db, hub, port['id'], ignore_booking_id=session.get('booking_id'), ignore_session_id=request.session_id)
    # Phiên seed có cờ is_available=true: không tăng lại bộ đếm đã tính cổng đó.
    was_unavailable = not port.get('is_available', False)
    booking.update(updated)
    if legacy:
        db.bookings.insert(0, booking)
        can_release = port.get('status') in ('Sẵn sàng', 'Đang sạc') and not charging_port_blocked(
            db, hub, port['id'], ignore_session_id=request.session_id)
    port.pop('occupied_by', None)
    if can_release:
        port.update(status='Sẵn sàng', is_available=True)
        if was_unavailable:
            hub['available_chargers'] = min(hub['charger_capacity'], hub['available_chargers'] + 1)
    elif port.get('status') == 'Đang sạc':
        port.update(status='Không khả dụng', is_available=False)
    db.user['active_services']['charging'] = None
    return response
