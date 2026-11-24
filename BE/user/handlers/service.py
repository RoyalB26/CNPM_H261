"""Handler sử dụng dịch vụ thuê xe, sạc và đổi pin."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.database import db, persist_change
from user.swaps import SwapError, complete_swap
from user.charging import (
    ChargingError,
    start_charging,
    stop_charging,
)
from user.schemas import (
    BookingErrorResponse,
    StartRideRequest,
    StartRideResponse,
    ActiveServicesResponse,
    ReturnVehicleRequest,
    ReturnVehicleResponse,
    ReturnVehicleErrorResponse,
    CompleteSwapRequest,
    StartChargingRequest,
    StopChargingRequest,
)


async def api_start_charging(request: Request) -> JSONResponse:
    """Nhận cổng đã giữ theo booking trên URL, không yêu cầu body."""
    try:
        data = StartChargingRequest.model_validate(request.path_params)
    except ValidationError:
        return JSONResponse(BookingErrorResponse(error="Mã booking không hợp lệ").model_dump(mode="json"), status_code=422)
    def change(candidate):
        try:
            response = start_charging(candidate, data.booking_id)
        except ChargingError as exc:
            return JSONResponse(BookingErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)


async def api_stop_charging(request: Request) -> JSONResponse:
    """Kết thúc sạc bằng tổng kWh mô phỏng; Backend tính tiền theo đơn giá đã chốt."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(BookingErrorResponse(error="Dữ liệu JSON không hợp lệ").model_dump(mode="json"), status_code=400)
    try:
        data = StopChargingRequest.model_validate(body)
    except ValidationError:
        return JSONResponse(BookingErrorResponse(error="Dữ liệu kết thúc sạc không hợp lệ").model_dump(mode="json"), status_code=422)
    def change(candidate):
        try:
            response = stop_charging(candidate, data)
        except ChargingError as exc:
            return JSONResponse(BookingErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)


async def api_complete_swap(request: Request) -> JSONResponse:
    """Xác nhận đổi pin theo booking trên URL, không yêu cầu body."""
    try:
        data = CompleteSwapRequest.model_validate(request.path_params)
    except ValidationError:
        return JSONResponse(BookingErrorResponse(error="Mã booking không hợp lệ").model_dump(mode="json"), status_code=422)
    def change(candidate):
        try:
            response = complete_swap(candidate, data.booking_id)
        except SwapError as exc:
            return JSONResponse(BookingErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)


async def api_active_services(request: Request) -> JSONResponse:
    """Trả trạng thái dịch vụ qua schema, không thay đổi dữ liệu trong store.

    Giữ trường null và các trường chưa có như response hiện tại; không
    tự tạo phiên dịch vụ hoặc bổ sung dữ liệu mẫu khi không sử dụng.
    """
    response = ActiveServicesResponse.model_validate(db.user.get("active_services", {}))
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))


async def api_start_ride(request: Request) -> JSONResponse:
    """Kiểm tra mã trên URL rồi bắt đầu chuyến đi qua store dùng chung.

    Không yêu cầu body. Trả 422 nếu mã không hợp lệ, 404 nếu booking không
    tồn tại, 409 nếu chưa đủ điều kiện nhận xe; trả 200 kèm chuyến đi nếu
    thành công. Store chịu trách nhiệm cập nhật booking, xe và Hub nguồn.
    """
    try:
        start_request = StartRideRequest.model_validate(request.path_params)
    except ValidationError:
        return JSONResponse(
            BookingErrorResponse(error="Mã booking không hợp lệ").model_dump(mode="json"),
            status_code=422
        )

    def change(candidate):
        result = candidate.start_ride(start_request.booking_id)

        if not result["success"]:
            status_code = (
                404 if result["error"] == "Booking không tồn tại"
                else 409
            )
            return JSONResponse(
                BookingErrorResponse(error=result["error"]).model_dump(mode="json"),
                status_code=status_code
            )

        response = StartRideResponse.model_validate(result)
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)


async def api_return_vehicle(request: Request) -> JSONResponse:
    """Kiểm tra định danh rồi trả xe qua store, hỗ trợ cả request FE và cũ.

    Trả 400 nếu JSON lỗi hoặc mô phỏng lỗi; 422 nếu sai schema hoặc các
    định danh mâu thuẫn; 409 nếu không đủ điều kiện trả xe; 200 nếu thành
    công. Chỉ gọi hàm cập nhật store sau khi xe, chuyến và Hub đã khớp.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            ReturnVehicleErrorResponse(error="Dữ liệu JSON không hợp lệ").model_dump(mode="json"),
            status_code=400
        )

    try:
        return_request = ReturnVehicleRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(
            ReturnVehicleErrorResponse(error="Dữ liệu trả xe không hợp lệ").model_dump(mode="json"),
            status_code=422
        )

    if return_request.force_error or return_request.simulate_error:
        return JSONResponse(
            ReturnVehicleErrorResponse(
                error="Không thể hoàn tất trả xe: Vị trí xe ngoài bán kính Hub hoặc khóa chốt chưa đóng."
            ).model_dump(mode="json"),
            status_code=400
        )

    def change(candidate):
        active_ride = candidate.user.get("active_services", {}).get("ride")
        if not active_ride:
            return JSONResponse(
                ReturnVehicleErrorResponse(error="Không có chuyến đi đang hoạt động").model_dump(mode="json"),
                status_code=409
            )

        trip_matches = return_request.trip_id == active_ride["trip_id"]
        vehicle_matches = return_request.vehicle_id == active_ride["vehicle_id"]
        if return_request.trip_id is not None and return_request.vehicle_id is not None:
            # Một định danh khớp chuyến hiện tại nhưng định danh còn lại sai.
            if trip_matches != vehicle_matches:
                return JSONResponse(
                    ReturnVehicleErrorResponse(error="Mã chuyến đi và mã xe không khớp nhau").model_dump(mode="json"),
                    status_code=422
                )

        if return_request.trip_id is not None and not trip_matches:
            return JSONResponse(
                ReturnVehicleErrorResponse(error="Mã chuyến đi không khớp").model_dump(mode="json"),
                status_code=409
            )
        if return_request.vehicle_id is not None and not vehicle_matches:
            return JSONResponse(
                ReturnVehicleErrorResponse(error="Mã xe không khớp chuyến đi đang hoạt động").model_dump(mode="json"),
                status_code=409
            )

        hub_by_id = candidate.get_hub(return_request.hub_id) if return_request.hub_id is not None else None
        hub_by_name = next(
            (hub for hub in candidate.get_hubs() if hub["name"] == return_request.hub_name),
            None
        ) if return_request.hub_name is not None else None

        if (
            (return_request.hub_id is not None and hub_by_id is None)
            or (return_request.hub_name is not None and hub_by_name is None)
        ):
            return JSONResponse(
                ReturnVehicleErrorResponse(error="Hub đích không tồn tại").model_dump(mode="json"),
                status_code=409
            )
        if hub_by_id is not None and hub_by_name is not None and hub_by_id["id"] != hub_by_name["id"]:
            return JSONResponse(
                ReturnVehicleErrorResponse(error="hub_id và hub_name không khớp nhau").model_dump(mode="json"),
                status_code=422
            )

        # Dùng đúng chuyến đã đối chiếu và đúng Hub client yêu cầu, không fallback.
        return_hub = hub_by_id if hub_by_id is not None else hub_by_name
        res = candidate.return_vehicle(active_ride["trip_id"], return_hub["name"])

        if not res["success"]:
            return JSONResponse(
                ReturnVehicleErrorResponse(error=res["error"]).model_dump(mode="json"),
                status_code=409
            )

        response = ReturnVehicleResponse.model_validate(res)
        return JSONResponse(response.model_dump(mode="json"))

    return persist_change(change)
