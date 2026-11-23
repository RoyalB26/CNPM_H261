"""Ghi nhận thanh toán thuê xe, đổi pin và sạc trong môi trường mock."""

from datetime import datetime, timezone
from uuid import uuid4

from shared.memory_store import MockDatabaseStore
from .schemas.payment import PaymentProcessResult, PaymentSubmitRequest


class PaymentError(ValueError):
    """Lỗi nghiệp vụ kèm mã HTTP để handler trả đúng kết quả."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


def pay_invoice(db: MockDatabaseStore, payment: PaymentSubmitRequest) -> PaymentProcessResult:
    """Kiểm tra toàn bộ điều kiện rồi ghi giao dịch một lần, không gọi cổng tiền thật."""
    matches = [(booking, booking[key]) for booking in db.get_bookings()
               for key in ("rental_invoice", "battery_swap_invoice", "charging_invoice")
               if (booking.get(key) or {}).get("id") == payment.invoice_id]
    if not matches:
        raise PaymentError("Không tìm thấy hóa đơn dịch vụ", 404)
    if len(matches) != 1:
        raise PaymentError("Mã hóa đơn không duy nhất", 409)
    booking, invoice = matches[0]
    if booking.get("status") != "Hoàn thành" or invoice.get("status") != "unpaid":
        raise PaymentError("Hóa đơn đã thanh toán hoặc chưa đủ điều kiện thanh toán", 409)
    if invoice.get("service_type") not in ("rental", "battery_swap", "charging") or invoice.get("payment_channel") != "online":
        raise PaymentError("Hóa đơn không hỗ trợ thanh toán trực tuyến", 409)
    if payment.method == "cash_guard":
        raise PaymentError("Dịch vụ này chỉ hỗ trợ ví điện tử hoặc chuyển khoản", 409)
    if payment.amount is not None and payment.amount != invoice["total_amount"]:
        raise PaymentError("Số tiền không khớp hóa đơn", 409)

    transaction_id = f"TXN-{uuid4().hex}"
    result = PaymentProcessResult(transaction_id=transaction_id, message="Thanh toán mô phỏng thành công")
    invoice.update(status="paid", transaction_id=transaction_id,
                   paid_at=datetime.now(timezone.utc).isoformat(), payment_method=payment.method)
    return result
