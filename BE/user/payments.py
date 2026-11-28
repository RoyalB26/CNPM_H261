"""Ghi nhận thanh toán thuê xe, đổi pin và sạc trong môi trường mock."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import math
from uuid import uuid4
from pydantic import ValidationError

from shared.memory_store import MockDatabaseStore
from shared.rental_pricing import rental_charge
from .schemas.payment import InvoiceResponse, PaymentProcessResult, PaymentSubmitRequest


class PaymentError(ValueError):
    """Lỗi nghiệp vụ kèm mã HTTP để handler trả đúng kết quả."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def validate_final_invoice(booking: dict, key: str, invoice: dict) -> None:
    """Đối chiếu hóa đơn với snapshot đã chốt, không lấy giá Hub hiện tại."""
    try:
        typed = InvoiceResponse.model_validate(invoice, strict=True)
        expected_type = {'rental_invoice': 'rental', 'charging_invoice': 'charging',
                         'battery_swap_invoice': 'battery_swap'}[key]
        if typed.service_type != expected_type or sum(item.amount for item in typed.items) != typed.total_amount:
            raise ValueError('Loại dịch vụ hoặc tổng các khoản phí không khớp')
        if any(invoice.get(field) is not None for field in ('transaction_id', 'paid_at', 'payment_method')):
            raise ValueError('Hóa đơn chưa thanh toán đã có metadata giao dịch')
        if key == 'rental_invoice':
            trip = booking['rental_trip']
            ended = datetime.fromisoformat(trip['ended_at'])
            if trip['status'] != 'Hoàn thành' or ended.tzinfo is None:
                raise ValueError('Chuyến đi chưa chốt hợp lệ')
            expected = rental_charge(trip, ended, trip['hourly_rate'])['total_fee']
            reference = trip['vehicle_id']
            if type(trip['total_fee']) is not int or trip['total_fee'] != expected:
                raise ValueError('Snapshot cước thuê không khớp')
        elif key == 'charging_invoice':
            session = booking['charging_session']
            energy, rate = session['power_consumed_kwh'], session['rate_per_kwh']
            if (session['status'] != 'Hoàn thành' or type(energy) not in (int, float)
                or not math.isfinite(energy) or energy < 0 or type(rate) is not int or rate < 0
                or rate != booking['charging_rate_per_kwh']):
                raise ValueError('Snapshot điện năng hoặc đơn giá không hợp lệ')
            expected = int((Decimal(str(energy)) * rate).to_integral_value(rounding=ROUND_CEILING))
            reference = booking['charging_port']
            if session['port_id'] != reference:
                raise ValueError('Cổng sạc trong lịch sử không khớp')
        else:
            quantity, rate = booking['battery_quantity'], booking['swap_unit_price']
            if type(quantity) is not int or quantity <= 0 or type(rate) is not int or rate < 0:
                raise ValueError('Snapshot số lượng pin hoặc đơn giá không hợp lệ')
            expected, reference = quantity * rate, booking['battery_type']
        if typed.reference_id != reference or typed.total_amount != expected:
            raise ValueError('Mã tham chiếu hoặc tổng tiền không khớp snapshot dịch vụ')
    except (ValidationError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise PaymentError('Hóa đơn không khớp kết quả dịch vụ đã chốt, chưa thể thanh toán', 409) from exc


def pay_invoice(db: MockDatabaseStore, payment: PaymentSubmitRequest, ip_address="127.0.0.1") -> PaymentProcessResult:
    """Demo ghi nhận tại store; luồng VNPAY vẫn chờ xác nhận tại IPN."""
    from .payment_gateway import create_payment, eligible_invoice, find_invoice
    if payment.simulate:
        booking, key, invoice = find_invoice(db, payment.invoice_id, db.user['id'])
        eligible_invoice(booking, key, invoice)
        # Không dùng mô phỏng để ghi đè giao dịch cổng thanh toán đang chờ.
        if invoice['status'] != 'unpaid':
            raise PaymentError('Hóa đơn đang chờ cổng thanh toán, chưa thể mô phỏng', 409)
        if payment.method == 'cash_guard':
            raise PaymentError('Thanh toán tại bảo vệ không thuộc mô phỏng online', 409)
        if payment.amount is not None and payment.amount != invoice['total_amount']:
            raise PaymentError('Số tiền không khớp hóa đơn', 409)
        reference = 'DEMO-' + uuid4().hex
        invoice.update(status='paid', transaction_id=reference,
                       paid_at=datetime.now(timezone.utc).isoformat(), payment_method=payment.method)
        return PaymentProcessResult(transaction_id=reference, status='completed',
                                    is_simulated=True, message='Thanh toán mô phỏng thành công, không trừ tiền thật')
    return create_payment(db, payment, ip_address)
