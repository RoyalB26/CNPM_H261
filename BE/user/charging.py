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
    if not db.owns_user_record(booking):
        raise ChargingError('Booking không tồn tại', 404)
    personal = booking.get('plan_type') == 'personal' and booking.get('personal_bundle') is True
    expected_status = 'Đang sử dụng' if personal else 'Đã xác nhận'
    if booking.get('plan_type') not in ('charging', 'personal') or booking.get('status') != expected_status:
        raise ChargingError('Booking không đủ điều kiện nhận cổng sạc')
    if booking.get('plan_type') == 'personal' and not personal:
        raise ChargingError('Booking cũ chưa có quyền giữ cổng của gói ghép')
    if booking.get('charging_session'):
        raise ChargingError('Booking đã bắt đầu hoặc hoàn tất phiên sạc')
    if personal:
        tickets = [r for r in db.parking_records if r.get('booking_id') == booking_id
                   and r.get('checkout_time') is None]
        if (len(tickets) != 1 or tickets[0].get('hub_id') != booking['hub_id']
            or tickets[0].get('slot_id') != booking.get('parking_slot')
            or tickets[0].get('user_id') != booking.get('user_id')):
            raise ChargingError('Cần Staff xác nhận vào bãi đúng gói ghép trước khi sạc')
        parking_hub = db.get_hub(booking['hub_id'])
        slots = [s for s in parking_hub.get('slots', []) if s['id'] == booking.get('parking_slot')] if parking_hub else []
        if len(slots) != 1 or slots[0].get('occupied_by') != tickets[0]['ticket_code']:
            raise ChargingError('Chỗ đỗ không còn khớp vé của gói ghép')
    now = datetime.now(timezone.utc)
    try:
        expired = booking_expired(booking, now)
    except (ValueError, TypeError):
        raise ChargingError('Thời hạn booking không hợp lệ')
    if expired and not personal:
        raise ChargingError('Booking sạc đã hết hạn')
    if db.user.get('active_services', {}).get('charging'):
        raise ChargingError('Người dùng đang có phiên sạc khác')
    hub = db.get_hub(booking['hub_id'])
    ports = [p for p in hub.get('ports', []) if p['id'] == booking.get('charging_port')] if hub else []
    port = ports[0] if len(ports) == 1 else None
    if hub is None or hub['status'] != 'ACTIVE' or port is None:
        raise ChargingError('Hub hoặc cổng sạc không hoạt động')
    if port.get('occupied_by') or port.get('reserved_by') != booking_id or port.get('status') != 'Đã đặt chỗ' or charging_port_blocked(db, hub, port['id'], ignore_booking_id=booking_id):
        raise ChargingError('Cổng sạc không còn thuộc booking hoặc đang bảo trì')
    rate = booking.get('charging_rate_per_kwh')
    if type(rate) is not int or rate < 0:
        raise ChargingError('Booking thiếu đơn giá điện hợp lệ')
    session = {
        'user_id': db.user['id'],
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
    if not db.owns_user_record(session):
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
    ports = [p for p in hub['ports'] if p['id'] == session['port_id']]
    if len(ports) != 1:
        raise ChargingError('Mã cổng sạc bị trùng trong Hub')
    port = ports[0]
    if port.get('reserved_by') or port.get('occupied_by') not in (None, request.session_id):
        raise ChargingError('Cổng sạc đang thuộc một phiên khác')
    legacy = session.get('booking_id') is None
    if legacy:
        # Seed chưa gắn booking: tạo lịch sử hoàn tất mới, không bịa thời điểm cắm sạc.
        booking = {
            'user_id': db.user['id'],
            'id': f'EMH-LEGACY-{uuid4().hex}', 'hub_id': hub['id'], 'hub_name': hub['name'],
            'plan_type': 'charging', 'resource_name': port['name'], 'charging_port': port['id'],
            'services': [], 'status': 'Hoàn thành', 'hold_until': '', 'created_at': '', 'price': 0,
        }
    else:
        matches = [b for b in db.bookings if b['id'] == session['booking_id']]
        if len(matches) != 1:
            raise ChargingError('Không xác định được booking của phiên sạc')
        booking = matches[0]
        if not db.owns_user_record(booking):
            raise ChargingError('Không xác định được booking của phiên sạc')
        saved_session = booking.get('charging_session') or {}
        if (saved_session.get('session_id') != request.session_id
            or session.get('status') != 'Đang sạc'
            or port.get('occupied_by') != request.session_id
            or type(session.get('rate_per_kwh')) is not int
            or session.get('rate_per_kwh') != booking.get('charging_rate_per_kwh')
            or session.get('started_at') != saved_session.get('started_at')):
            raise ChargingError('Phiên sạc, đơn giá hoặc quyền chiếm cổng không khớp booking')
        if booking.get('status') != 'Đang sử dụng' or booking.get('plan_type') not in ('charging', 'personal') or booking.get('charging_port') != port['id'] or booking.get('hub_id') != hub['id']:
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
        user_id=db.user['id'],
        id=f'INV-{request.session_id}', service_type='charging', title='Hóa đơn dịch vụ sạc pin',
        reference_id=port['id'], items=[{'label': description, 'description': description, 'amount': amount}],
        total_amount=amount, payment_channel='online', status='unpaid', created_at=now.isoformat(),
    )
    updated = {**booking, 'status': 'Hoàn thành', 'price': amount, 'completed_at': now.isoformat(),
               'charging_rate_per_kwh': rate, 'charging_session': history,
               'charging_invoice': invoice.model_dump(mode='json', exclude_unset=True)}
    if booking.get('personal_bundle'):
        # Kết thúc sạc chỉ hoàn cổng; chỗ đỗ vẫn thuộc vé cho tới khi Staff cho ra bãi.
        updated['status'] = 'Đang sử dụng'
        updated['price'] = booking['price']
        updated.pop('completed_at', None)
    if legacy:
        updated['created_at'] = now.isoformat()
    BookingResponse.model_validate(updated)
    response = StopChargingResponse(booking_id=booking['id'], session_id=request.session_id,
                                    power_consumed_kwh=request.power_consumed_kwh, total_fee=amount, invoice=invoice)
    can_release = hub.get('status') == 'ACTIVE' and port.get('status') == 'Đang sạc' and not charging_port_blocked(
        db, hub, port['id'], ignore_booking_id=session.get('booking_id'), ignore_session_id=request.session_id)
    # Phiên seed có cờ is_available=true: không tăng lại bộ đếm đã tính cổng đó.
    was_unavailable = not port.get('is_available', False)
    booking.update(updated)
    if legacy:
        db.bookings.insert(0, booking)
        can_release = hub.get('status') == 'ACTIVE' and port.get('status') in ('Sẵn sàng', 'Đang sạc') and not charging_port_blocked(
            db, hub, port['id'], ignore_session_id=request.session_id)
    port.pop('occupied_by', None)
    if can_release:
        port.update(status='Sẵn sàng', is_available=True)
        if was_unavailable:
            hub['available_chargers'] = min(hub['charger_capacity'], hub['available_chargers'] + 1)
    else:
        port['is_available'] = False
        if port.get('status') in ('Đang sạc', 'Sẵn sàng'):
            port['status'] = 'Không khả dụng'
    db.user['active_services']['charging'] = None
    return response
