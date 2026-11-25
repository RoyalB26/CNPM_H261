"""Handler tra cứu hóa đơn và thanh toán dịch vụ mô phỏng."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.database import db, persist_change
from user.payments import PaymentError, pay_invoice
from user.invoices import (
    InvoiceConflict,
    InvoiceNotFound,
    current_invoice,
)
from user.schemas import (
    PaymentSubmitRequest,
    PaymentErrorResponse,
    InvoiceQuery,
)


async def api_get_invoice(request: Request) -> JSONResponse:
    """Tra cứu hóa đơn từ dữ liệu đã lưu; sai bộ lọc trả 422, không có trả 404."""
    try:
        query = InvoiceQuery.model_validate(dict(request.query_params))
    except ValidationError:
        return JSONResponse(PaymentErrorResponse(error="Bộ lọc hóa đơn không hợp lệ").model_dump(mode="json"), status_code=422)
    try:
        response = current_invoice(db, query)
    except InvoiceNotFound as exc:
        return JSONResponse(PaymentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=404)
    except InvoiceConflict as exc:
        return JSONResponse(PaymentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=409)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))


async def api_pay_invoice(request: Request) -> JSONResponse:
    """Ghi nhận thanh toán thuê xe/đổi pin/sạc; lưu JSON trước khi trả thành công.

    Trả 400 khi JSON lỗi, 422 khi sai schema, 404 khi không có hóa đơn,
    409 khi xung đột nghiệp vụ. Thanh toán lặp không tạo giao dịch mới.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(PaymentErrorResponse(error="Dữ liệu JSON không hợp lệ").model_dump(mode="json"), status_code=400)
    try:
        payment = PaymentSubmitRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(PaymentErrorResponse(error="Dữ liệu thanh toán không hợp lệ").model_dump(mode="json"), status_code=422)
    def change(candidate):
        try:
            response = pay_invoice(candidate, payment, request.client.host if request.client else "127.0.0.1")
        except PaymentError as exc:
            return JSONResponse(PaymentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
        return JSONResponse(response.model_dump(mode="json"))

    return persist_change(change)
