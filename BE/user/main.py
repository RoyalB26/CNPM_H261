"""
Mock Backend Service for End-User Mobile Web
Smart E-Mobility Hub - ĐHQG-HCM
Provides standard REST API matching Pydantic schemas and serving mock data.
Uses Starlette & Uvicorn.
Synchronized with Central Mock Database (BE/mock_db.py).
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Ensure parent directory is in sys.path to import mock_db
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mock_db import db
from user.payments import PaymentError, pay_invoice
from user.incidents import IncidentError, create_report, report_view
from user.hubs import hub_detail, search_hubs, suggest_route
from user.alternatives import booking_alternatives
from user.bookings import expire_rental_bookings
from user.swaps import SwapError, complete_swap
from user.charging import ChargingError, start_charging, stop_charging
from user.invoices import InvoiceConflict, InvoiceNotFound, current_invoice
from user.schemas import (
    UserLoginRequest, UserLoginResponse, UserLoginErrorResponse, UserProfileResponse, UserVehicleItem,
    UpdateProfileRequest, UpdateProfileResponse, UpdateProfileErrorResponse,
    CreateBookingRequest, BookingResponse, BookingErrorResponse,
    CancelBookingRequest, CancelBookingResponse, CancelBookingNotFoundResponse,
    StartRideRequest, StartRideResponse, ActiveServicesResponse,
    ReturnVehicleRequest, ReturnVehicleResponse, ReturnVehicleErrorResponse, InvoiceResponse,
    PaymentSubmitRequest, PaymentErrorResponse, CreateIncidentReportRequest, IncidentErrorResponse,
    SearchHubQuery, RouteSuggestionRequest, HubDetailResponse, ExpireBookingsResponse, CompleteSwapRequest,
    StartChargingRequest, StopChargingRequest, InvoiceQuery
)

# API Route Handlers
async def api_health(request):
    return JSONResponse({"status": "ok", "app": "Smart E-Mobility Hub Backend"})

from shared.authentication import (
    ensure_accounts, find_account, issue_session, password_matches,
    password_hash, accounts,
)
from shared.database import persist_change
from uuid import uuid4
import re


async def api_login(request):
    try:
        data = await request.json()
    except (ValueError, UnicodeError):
        return JSONResponse({"detail": "JSON không hợp lệ"}, status_code=400)
    try:
        credentials = UserLoginRequest.model_validate(data)
    except ValidationError:
        return JSONResponse({"detail": "Thông tin đăng nhập không hợp lệ"}, status_code=422)
    failure = ensure_accounts()
    if failure is not None:
        return failure
    account = find_account(credentials.email or credentials.phone, "user")
    if account is None or not password_matches(credentials.password, account["password_hash"]):
        return JSONResponse({"detail": "Sai tài khoản hoặc mật khẩu"}, status_code=401)
    profile = db.__dict__["user"] if account["id"] == db.__dict__["user"]["id"] else account["profile"]
    return JSONResponse(UserLoginResponse(
        token=issue_session(account),
        user=UserProfileResponse.model_validate(profile),
    ).model_dump(mode="json"))


async def api_register(request):
    try:
        data = await request.json()
    except (ValueError, UnicodeError):
        return JSONResponse({"detail": "JSON không hợp lệ"}, status_code=400)
    required = ("full_name", "email", "phone", "password", "confirm_password")
    if not isinstance(data, dict) or any(
        not isinstance(data.get(k), str) or not data[k].strip() for k in required
    ):
        return JSONResponse({"detail": "Thiếu thông tin đăng ký"}, status_code=422)
    email = data["email"].strip().lower()
    phone = data["phone"].strip()
    if (not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or not re.fullmatch(r"\+?[0-9]{9,15}", phone)
            or len(data["password"]) < 8
            or data["password"] != data["confirm_password"]):
        return JSONResponse({"detail": "Email, số điện thoại hoặc mật khẩu không hợp lệ"}, status_code=422)
    failure = ensure_accounts()
    if failure is not None:
        return failure
    encoded = password_hash(data["password"])

    def change(candidate):
        if any(a.get("email") == email or a.get("phone") == phone for a in accounts(candidate)):
            return JSONResponse({"detail": "Email hoặc số điện thoại đã tồn tại"}, status_code=409)
        profile = UserProfileResponse(
            id="USR-" + uuid4().hex, full_name=data["full_name"].strip(),
            email=email, phone=phone, vehicles=[], active_services={},
        ).model_dump(mode="json")
        candidate.operator_mock["accounts"].append(dict(
            id=profile["id"], role="user", email=email, phone=phone,
            password_hash=encoded, profile=profile,
        ))
        return JSONResponse({"success": True, "message": "Đăng ký thành công", "user": profile}, status_code=201)

    return persist_change(change)


async def api_get_profile(request: Request) -> JSONResponse:
    """Trả hồ sơ người dùng mock sau khi kiểm tra qua schema.

    Giữ phương tiện cá nhân, dịch vụ hiện tại và trường null; không thêm
    giá trị mặc định cho trường vắng mặt và không thay đổi store.
    """
    response = UserProfileResponse.model_validate(db.get_user_profile())
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

async def api_update_profile(request: Request) -> JSONResponse:
    """Kiểm tra toàn bộ dữ liệu trước khi cập nhật các trường hồ sơ cho phép.

    Trả 400 nếu JSON lỗi, 422 nếu thiếu hoặc sai dữ liệu; trả 200 kèm hồ
    sơ khi thành công. Trường không được gửi giữ nguyên giá trị hiện tại.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            UpdateProfileErrorResponse(message="Dữ liệu JSON không hợp lệ").model_dump(mode="json"),
            status_code=400
        )

    try:
        profile_request = UpdateProfileRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(
            UpdateProfileErrorResponse(message="Dữ liệu cập nhật hồ sơ không hợp lệ").model_dump(mode="json"),
            status_code=422
        )

    changes = profile_request.model_dump(exclude_unset=True)
    if "email" in changes:
        changes["email"] = changes["email"].lower()
    if any(a["id"] != db.user["id"] and (
        ("email" in changes and a.get("email") == changes["email"])
        or ("phone" in changes and a.get("phone") == changes["phone"])
    ) for a in accounts()):
        return JSONResponse({"detail": "Email hoặc số điện thoại đã tồn tại"}, status_code=409)

    # Kiểm tra và tạo phản hồi trước khi ghi để tránh cập nhật dở dang.
    updated_user = UserProfileResponse.model_validate({**db.user, **changes})
    response = UpdateProfileResponse(success=True, user=updated_user)
    result = JSONResponse(response.model_dump(mode="json", exclude_unset=True))
    db.user.update(changes)
    for account in accounts():
        if account["id"] == db.user["id"]:
            account.update(email=db.user["email"], phone=db.user["phone"])
    return result

async def api_get_user_vehicles(request: Request) -> JSONResponse:
    """Trả danh sách phương tiện cá nhân sau khi kiểm tra từng xe qua schema.

    Giữ thứ tự và các trường đang có; trả mảng rỗng khi chưa có xe, không
    thêm giá trị mẫu cho trường vắng mặt và không thay đổi store.
    """
    vehicles: list[UserVehicleItem] = [
        UserVehicleItem.model_validate(vehicle) for vehicle in db.get_user_vehicles()
    ]
    return JSONResponse([
        vehicle.model_dump(mode="json", exclude_unset=True) for vehicle in vehicles
    ])

async def api_list_hubs(request: Request) -> JSONResponse:
    """Tìm Hub theo keyword, status, vehicle_type; giữ response dạng mảng."""
    try:
        query = SearchHubQuery.model_validate(dict(request.query_params))
    except ValidationError:
        return JSONResponse({"success": False, "error": "Bộ lọc Hub không hợp lệ"}, status_code=422)
    hubs = [hub_detail(db, hub) for hub in search_hubs(db, query)]
    return JSONResponse([hub.model_dump(mode="json", exclude_unset=True) for hub in hubs])

async def api_get_hub(request: Request) -> JSONResponse:
    """Đọc chi tiết Hub theo mã, bao gồm trạng thái và tài nguyên hiện tại."""
    hub = db.get_hub(request.path_params["hub_id"])
    if hub is None:
        return JSONResponse({"error": "Hub không tồn tại"}, status_code=404)
    response = hub_detail(db, hub)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

async def api_suggest_route(request: Request) -> JSONResponse:
    """Gợi ý Hub có xe/chỗ trả; từ chối tọa độ lỗi và thiếu tài nguyên."""
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse({"success": False, "error": "Dữ liệu JSON không hợp lệ"}, status_code=400)
    try:
        query = RouteSuggestionRequest.model_validate(data)
    except ValidationError:
        return JSONResponse({"success": False, "error": "Dữ liệu lộ trình không hợp lệ"}, status_code=422)
    try:
        response = await suggest_route(db, query)
    except ValueError:
        return JSONResponse({"success": False, "error": "Không có Hub lấy/trả xe khả dụng"}, status_code=409)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

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
    bk = db.create_booking(booking_request.model_dump(mode="json", exclude_unset=True))

    if "error" in bk:
        return JSONResponse(
            BookingErrorResponse(success=False, error=bk["error"], alternatives=booking_alternatives(db, booking_request)).model_dump(mode="json", exclude_unset=True),
            status_code=409
        )

    response = BookingResponse.model_validate(bk)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

async def api_start_charging(request: Request) -> JSONResponse:
    """Nhận cổng đã giữ theo booking trên URL, không yêu cầu body."""
    try:
        data = StartChargingRequest.model_validate(request.path_params)
    except ValidationError:
        return JSONResponse(BookingErrorResponse(error="Mã booking không hợp lệ").model_dump(mode="json"), status_code=422)
    try:
        response = start_charging(db, data.booking_id)
    except ChargingError as exc:
        return JSONResponse(BookingErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

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
    try:
        response = stop_charging(db, data)
    except ChargingError as exc:
        return JSONResponse(BookingErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

async def api_complete_swap(request: Request) -> JSONResponse:
    """Xác nhận đổi pin theo booking trên URL, không yêu cầu body."""
    try:
        data = CompleteSwapRequest.model_validate(request.path_params)
    except ValidationError:
        return JSONResponse(BookingErrorResponse(error="Mã booking không hợp lệ").model_dump(mode="json"), status_code=422)
    try:
        response = complete_swap(db, data.booking_id)
    except SwapError as exc:
        return JSONResponse(BookingErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

async def api_expire_bookings(request: Request) -> JSONResponse:
    """Xử lý hết hạn bằng POST cho demo; Gateway lưu kết quả xuống runtime."""
    try:
        ids = expire_rental_bookings(db)
    except (ValueError, TypeError):
        return JSONResponse(
            BookingErrorResponse(error="Dữ liệu booking cũ chưa đủ điều kiện xử lý hết hạn").model_dump(mode="json"),
            status_code=409
        )
    response = ExpireBookingsResponse(expired_booking_ids=ids, expired_count=len(ids))
    return JSONResponse(response.model_dump(mode="json"))

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

    bk = db.cancel_booking(cancel_request.booking_id)

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

    result = db.start_ride(start_request.booking_id)

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

    active_ride = db.user.get("active_services", {}).get("ride")
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

    hub_by_id = db.get_hub(return_request.hub_id) if return_request.hub_id is not None else None
    hub_by_name = next(
        (hub for hub in db.get_hubs() if hub["name"] == return_request.hub_name),
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
    res = db.return_vehicle(active_ride["trip_id"], return_hub["name"])

    if not res["success"]:
        return JSONResponse(
            ReturnVehicleErrorResponse(error=res["error"]).model_dump(mode="json"),
            status_code=409
        )

    response = ReturnVehicleResponse.model_validate(res)
    return JSONResponse(response.model_dump(mode="json"))

async def api_list_incidents(request: Request) -> JSONResponse:
    """Trả lịch sử báo cáo cùng trạng thái phiếu mới nhất, không ghi store."""
    try:
        reports = [report_view(db, report).model_dump(mode="json", exclude_unset=True)
                   for report in db.get_user_incidents()]
    except IncidentError as exc:
        return JSONResponse(IncidentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(reports)

async def api_create_incident(request: Request) -> JSONResponse:
    """Kiểm tra báo cáo rồi tạo phiếu đúng Hub; Gateway lưu hai bản ghi cùng nhau."""
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(IncidentErrorResponse(error="Dữ liệu JSON không hợp lệ").model_dump(mode="json"), status_code=400)
    try:
        report_request = CreateIncidentReportRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(IncidentErrorResponse(error="Dữ liệu báo cáo không hợp lệ").model_dump(mode="json"), status_code=422)
    try:
        response = create_report(db, report_request)
    except IncidentError as exc:
        return JSONResponse(IncidentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

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
    """Ghi nhận thanh toán thuê xe/đổi pin/sạc; Gateway lưu JSON trước khi trả thành công.

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
    try:
        response = pay_invoice(db, payment)
    except PaymentError as exc:
        return JSONResponse(PaymentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(response.model_dump(mode="json"))

# Routes support both /api/... and /api/v1/user/...
routes = [
    Route("/api/health", api_health, methods=["GET"]),
    Route("/api/auth/login", api_login, methods=["POST"]),
    Route("/api/auth/register", api_register, methods=["POST"]),
    Route("/api/user/profile", api_get_profile, methods=["GET"]),
    Route("/api/user/profile", api_update_profile, methods=["PUT"]),
    Route("/api/user/vehicles", api_get_user_vehicles, methods=["GET"]),
    Route("/api/hubs", api_list_hubs, methods=["GET"]),
    Route("/api/hubs/{hub_id}", api_get_hub, methods=["GET"]),
    Route("/api/hubs/suggest-route", api_suggest_route, methods=["POST"]),
    Route("/api/bookings", api_list_bookings, methods=["GET"]),
    Route("/api/bookings", api_create_booking, methods=["POST"]),
    Route("/api/bookings/expire", api_expire_bookings, methods=["POST"]),
    Route("/api/bookings/{booking_id}/swap", api_complete_swap, methods=["POST"]),
    Route("/api/bookings/{booking_id}/charging/start", api_start_charging, methods=["POST"]),
    Route("/api/services/charging/stop", api_stop_charging, methods=["POST"]),
    Route("/api/bookings/{booking_id}/cancel", api_cancel_booking, methods=["POST"]),
    Route("/api/services/active", api_active_services, methods=["GET"]),
    Route("/api/services/return-vehicle", api_return_vehicle, methods=["POST"]),
    Route("/api/incidents", api_list_incidents, methods=["GET"]),
    Route("/api/incidents", api_create_incident, methods=["POST"]),
    Route("/api/invoices/current", api_get_invoice, methods=["GET"]),
    Route("/api/invoices/pay", api_pay_invoice, methods=["POST"]),
    Route("/api/bookings/{booking_id}/start", api_start_ride, methods=["POST"]),

    # Prefixed aliases for api gateway
    Route("/api/v1/user/health", api_health, methods=["GET"]),
    Route("/api/v1/user/auth/login", api_login, methods=["POST"]),
    Route("/api/v1/user/auth/register", api_register, methods=["POST"]),
    Route("/api/v1/user/profile", api_get_profile, methods=["GET"]),
    Route("/api/v1/user/profile", api_update_profile, methods=["PUT"]),
    Route("/api/v1/user/vehicles", api_get_user_vehicles, methods=["GET"]),
    Route("/api/v1/user/hubs", api_list_hubs, methods=["GET"]),
    Route("/api/v1/user/hubs/{hub_id}", api_get_hub, methods=["GET"]),
    Route("/api/v1/user/hubs/suggest-route", api_suggest_route, methods=["POST"]),
    Route("/api/v1/user/bookings", api_list_bookings, methods=["GET"]),
    Route("/api/v1/user/bookings", api_create_booking, methods=["POST"]),
    Route("/api/v1/user/bookings/expire", api_expire_bookings, methods=["POST"]),
    Route("/api/v1/user/bookings/{booking_id}/swap", api_complete_swap, methods=["POST"]),
    Route("/api/v1/user/bookings/{booking_id}/charging/start", api_start_charging, methods=["POST"]),
    Route("/api/v1/user/services/charging/stop", api_stop_charging, methods=["POST"]),
    Route("/api/v1/user/bookings/{booking_id}/cancel", api_cancel_booking, methods=["POST"]),
    Route("/api/v1/user/services/active", api_active_services, methods=["GET"]),
    Route("/api/v1/user/services/return-vehicle", api_return_vehicle, methods=["POST"]),
    Route("/api/v1/user/incidents", api_list_incidents, methods=["GET"]),
    Route("/api/v1/user/incidents", api_create_incident, methods=["POST"]),
    Route("/api/v1/user/invoices/current", api_get_invoice, methods=["GET"]),
    Route("/api/v1/user/invoices/pay", api_pay_invoice, methods=["POST"]),
Route("/api/v1/user/bookings/{booking_id}/start", api_start_ride, methods=["POST"]),
]

from shared.operations_api import user_routes as operation_routes
routes.extend(operation_routes)

from starlette.exceptions import HTTPException
from shared.operations_api import http_error
from shared.authentication import AuthenticationMiddleware
from shared.middleware import SharedPersistenceMiddleware

middleware = [
    Middleware(SharedPersistenceMiddleware),
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    Middleware(AuthenticationMiddleware)
]

app = Starlette(debug=True, routes=routes, middleware=middleware, exception_handlers={HTTPException: http_error})

if __name__ == "__main__":
    import uvicorn
    print("Starting Smart E-Mobility Mock Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
