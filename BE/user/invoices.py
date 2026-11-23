"""Tra cứu hóa đơn từ booking hoặc vé gửi xe đã lưu, không tạo giao dịch khi GET."""

from datetime import datetime, timedelta, timezone

from shared.memory_store import MockDatabaseStore
from shared.parking_reservations import plate_key
from .schemas.payment import InvoiceQuery, InvoiceResponse


class InvoiceNotFound(ValueError):
    """Không có hóa đơn phù hợp bộ chọn của người dùng demo."""


class InvoiceConflict(ValueError):
    """Kết quả trùng mã; không tự chọn bản ghi đầu tiên để hiển thị."""


def invoice_time(value: str) -> datetime:
    """So sánh thời gian ISO mới và thời gian hiển thị Việt Nam của seed cũ."""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        moment = datetime.strptime(value, '%d/%m/%Y · %H:%M')
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone(timedelta(hours=7)))


def current_invoice(db: MockDatabaseStore, query: InvoiceQuery) -> InvoiceResponse:
    """Chọn hóa đơn đúng định danh hoặc mới nhất, không trả dữ liệu mẫu thay thế."""
    candidates = []
    if query.invoice_type == 'parking':
        # Bản demo một tài khoản: chỉ xem vé của xe cá nhân hoặc biển số đã đặt.
        plates = {plate_key(v['plate_number']) for v in db.get_user_vehicles()}
        plates.update(plate_key(b.get('personal_plate') or '') for b in db.get_bookings() if b.get('plan_type') in ('parking', 'personal'))
        for record in db.parking_records:
            if 'user_id' in record:
                if not db.owns_user_record(record):
                    continue
            elif record.get('booking_id'):
                linked = [b for b in db.bookings if b['id'] == record['booking_id']]
                if len(linked) != 1 or not db.owns_user_record(linked[0]):
                    continue
            elif plate_key(record['plate_number']) not in plates:
                continue
            if query.booking_id is not None and record.get('booking_id') != query.booking_id:
                continue
            description = f"Gửi xe tại {record['hub_name']} · {record['slot_id']}"
            invoice = {
                'user_id': db.user['id'],
                'id': f"INV-{record['ticket_code']}", 'service_type': 'parking',
                'title': 'Hóa đơn gửi xe cá nhân', 'reference_id': record['plate_number'],
                'items': [{'label': description, 'description': description, 'amount': record['parking_fee']}],
                'total_amount': record['parking_fee'], 'payment_channel': 'cash_guard',
                'status': 'paid' if record.get('payment_status') == 'PAID' else 'unpaid',
                'created_at': record['checkin_time'],
            }
            if query.invoice_id is None or invoice['id'] == query.invoice_id:
                candidates.append(invoice)
    else:
        key = {'rental': 'rental_invoice', 'charging': 'charging_invoice',
               'swap': 'battery_swap_invoice', 'battery_swap': 'battery_swap_invoice'}[query.invoice_type]
        for booking in db.get_bookings():
            invoice = booking.get(key)
            if not invoice:
                continue
            if not db.owns_user_record(invoice):
                continue
            if query.booking_id is not None and booking['id'] != query.booking_id:
                continue
            if query.trip_id is not None and (booking.get('rental_trip') or {}).get('trip_id') != query.trip_id:
                continue
            if query.session_id is not None and (booking.get('charging_session') or {}).get('session_id') != query.session_id:
                continue
            if query.invoice_id is None or invoice['id'] == query.invoice_id:
                candidates.append(invoice)
    if not candidates:
        raise InvoiceNotFound('Chưa có hóa đơn phù hợp yêu cầu')
    ids = [item['id'] for item in candidates]
    if len(ids) != len(set(ids)):
        raise InvoiceConflict('Mã hóa đơn bị trùng, chưa thể xác định hóa đơn duy nhất')
    return InvoiceResponse.model_validate(max(candidates, key=lambda i: invoice_time(i['created_at'])))
