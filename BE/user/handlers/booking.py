"""Handler tạo, liệt kê, hủy và xử lý hết hạn booking User."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.database import db, persist_change
from user.alternatives import booking_alternatives
from user.bookings import expire_rental_bookings
from user.schemas import (
    CreateBookingRequest,
    BookingResponse,
    BookingErrorResponse,
    CancelBookingRequest,
    CancelBookingResponse,
    CancelBookingNotFoundResponse,
    ExpireBookingsResponse,
)


async def api_list_bookings(request: Request) -> JSONResponse:
    """Trả danh sách booking mock sau khi kiểm tra từng bản ghi qua schema.

    Giữ thứ tự, trường null và các trường vắng mặt của dữ liệu hiện tại;
    trả mảng rỗng khi chưa có booking và không thay đổi store.
    """
    bookings: list[BookingResponse] = [
        BookingResponse.model_validate(booking) for booking in db.get_bookings()
    ]
    return JSONResponse([
        booking.model_dump(mode="json", exclude_unset=True) for booking in bookings
    ])


async def api_create_booking(request: Request) -> JSONResponse:
    """Kiểm tra request rồi tạo booking thông qua store dùng chung.

    Trả 400 nếu JSON lỗi, 422 nếu sai schema, 409 nếu tài nguyên không
    khả dụng; giữ mã 200 và cấu trúc bản ghi khi tạo thành công.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            BookingErrorResponse(error="Dữ liệu JSON không hợp lệ").model_dump(mode="json"),
            status_code=400
        )

    try:
        booking_request = CreateBookingRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(
            BookingErrorResponse(error="Dữ liệu đặt trước không hợp lệ").model_dump(mode="json"),
            status_code=422
        )

    # Chỉ truyền trường client đã gửi để giữ các giá trị mặc định của store.
    def change(candidate):
        bk = candidate.create_booking(booking_request.model_dump(mode="json", exclude_unset=True))

        if "error" in bk:
            return JSONResponse(
                BookingErrorResponse(success=False, error=bk["error"], alternatives=booking_alternatives(candidate, booking_request)).model_dump(mode="json", exclude_unset=True),
                status_code=409
            )

        response = BookingResponse.model_validate(bk)
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)


async def api_expire_bookings(request: Request) -> JSONResponse:
    """Xử lý hết hạn trên candidate rồi lưu runtime trước khi trả kết quả."""
    def change(candidate):
        try:
            ids = expire_rental_bookings(candidate)
        except (ValueError, TypeError):
            return JSONResponse(
                BookingErrorResponse(error="Dữ liệu booking cũ chưa đủ điều kiện xử lý hết hạn").model_dump(mode="json"),
                status_code=409
            )
        response = ExpireBookingsResponse(expired_booking_ids=ids, expired_count=len(ids))
        return JSONResponse(response.model_dump(mode="json"))

    return persist_change(change)


async def api_cancel_booking(request: Request) -> JSONResponse:
    """Kiểm tra mã trên URL rồi hủy booking qua store, không yêu cầu body.

    Trả 422 nếu mã rỗng hoặc sai kiểu, 404 nếu không tìm thấy, 409 nếu
    booking không còn hiệu lực; trả 200 kèm booking khi hủy thành công.
    """
    try:
        cancel_request = CancelBookingRequest.model_validate(request.path_params)
    except ValidationError:
        return JSONResponse(
            BookingErrorResponse(error="Mã booking không hợp lệ").model_dump(mode="json"),
            status_code=422
        )

    def change(candidate):
        bk = candidate.cancel_booking(cancel_request.booking_id)

        if bk is None:
            return JSONResponse(
                CancelBookingNotFoundResponse(error="Booking không tồn tại").model_dump(mode="json"),
                status_code=404
            )

        if "error" in bk:
            return JSONResponse(
                BookingErrorResponse(error=bk["error"]).model_dump(mode="json"),
                status_code=409
            )

        response = CancelBookingResponse(success=True, booking=BookingResponse.model_validate(bk))
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)
