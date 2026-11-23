"""Xác nhận đổi pin mô phỏng và tạo hóa đơn theo đơn giá đã giữ."""

from datetime import datetime, timezone
from shared.booking_expiry import booking_expired
from shared.memory_store import MockDatabaseStore
from .schemas.booking import BookingResponse, CompleteSwapResponse
from .schemas.payment import InvoiceResponse


class SwapError(ValueError):
    """Lỗi nghiệp vụ đổi pin trước khi sửa dữ liệu."""

    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def complete_swap(db: MockDatabaseStore, booking_id: str) -> CompleteSwapResponse:
    """Tiêu thụ pin đã giữ một lần; không trừ tồn kho lần thứ hai."""
    matches = [b for b in db.get_bookings() if b['id'] == booking_id]
    if not matches:
        raise SwapError('Booking không tồn tại', 404)
    if len(matches) != 1:
        raise SwapError('Mã booking không duy nhất')
    booking = matches[0]
    if booking.get('plan_type') not in ('swap', 'battery_swap') or booking.get('status') != 'Đã xác nhận' or not booking.get('swap_reserved'):
        raise SwapError('Booking không còn pin được giữ để đổi')
    now = datetime.now(timezone.utc)
    try:
        expired = booking_expired(booking, now)
    except (ValueError, TypeError):
        raise SwapError('Thời hạn booking không hợp lệ')
    if expired:
        raise SwapError('Booking đổi pin đã hết hạn')
    hub = db.get_hub(booking['hub_id'])
    battery = next((b for b in hub.get('batteries', []) if b['battery_type'] == booking['battery_type']), None) if hub else None
    if hub is None or hub.get('status') != 'ACTIVE' or battery is None or not battery.get('is_available', True):
        raise SwapError('Hub hoặc loại pin không còn hoạt động')
    quantity, unit_price = booking['battery_quantity'], booking['swap_unit_price']
    amount = quantity * unit_price
    description = f"Đổi {quantity} pin {booking['battery_type']}"
    invoice = InvoiceResponse(
        id=f'INV-SWAP-{booking_id}', service_type='battery_swap', title='Hóa đơn đổi pin',
        reference_id=booking['battery_type'], items=[{'label': description, 'description': description, 'amount': amount}],
        total_amount=amount, payment_channel='online', status='unpaid', created_at=now.isoformat(),
    )
    updated = {**booking, 'status': 'Hoàn thành', 'completed_at': now.isoformat(),
               'battery_swap_invoice': invoice.model_dump(mode='json', exclude_unset=True)}
    response = CompleteSwapResponse(booking=BookingResponse.model_validate(updated), invoice=invoice)
    # Toàn bộ response đã hợp lệ mới cập nhật; tồn kho đã trừ lúc đặt trước.
    booking.update(updated)
    booking['swap_reserved'] = False
    return response
