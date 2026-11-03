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
import math
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
from user.schemas import (
    UserLoginRequest, UserLoginResponse, UserLoginErrorResponse, UserProfileResponse, UserVehicleItem,
    UpdateProfileRequest, UpdateProfileResponse, UpdateProfileErrorResponse,
    CreateBookingRequest, BookingResponse, BookingErrorResponse,
    CancelBookingRequest, CancelBookingResponse, CancelBookingNotFoundResponse,
    StartRideRequest, StartRideResponse, ActiveServicesResponse,
    ReturnVehicleRequest, ReturnVehicleResponse, ReturnVehicleErrorResponse
)

# API Route Handlers
async def api_health(request):
    return JSONResponse({"status": "ok", "app": "Smart E-Mobility Hub Backend"})

async def api_login(request: Request) -> JSONResponse:
    """Kiểm tra dữ liệu đăng nhập và xác thực tài khoản mock, không đổi store.

    Trả 400 nếu JSON lỗi, 422 nếu sai schema, 401 nếu sai tài khoản hoặc
    mật khẩu; trả 200 kèm token và hồ sơ khi đăng nhập thành công.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            UserLoginErrorResponse(message="Dữ liệu JSON không hợp lệ").model_dump(mode="json"),
            status_code=400
        )

    try:
        credentials = UserLoginRequest.model_validate(data)
    except ValidationError:
        # Không đính kèm dữ liệu lỗi vì có thể chứa mật khẩu người dùng.
        return JSONResponse(
            UserLoginErrorResponse(
                message="Cần cung cấp số điện thoại hoặc email và mật khẩu không rỗng, đúng kiểu dữ liệu"
            ).model_dump(mode="json"),
            status_code=422
        )

    valid_user = (
        (credentials.phone is not None and credentials.phone == db.user["phone"])
        or (credentials.email is not None and credentials.email == db.user["email"])
    )

    if not valid_user or credentials.password != "123456":
        return JSONResponse(
            UserLoginErrorResponse(message="Sai tài khoản hoặc mật khẩu").model_dump(mode="json"),
            status_code=401
        )

    response = UserLoginResponse(
        token="jwt-token-sample-mock-123456",
        user=UserProfileResponse.model_validate(db.user)
    )
    return JSONResponse(response.model_dump(mode="json"))

async def api_register(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    return JSONResponse({
        "success": True,
        "message": "Đăng ký tài khoản thành công",
        "user": {
            "id": "USR-002",
            "full_name": data.get("full_name", "Người dùng mới"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "role": "End-User"
        }
    })

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
    # Kiểm tra và tạo phản hồi trước khi ghi để tránh cập nhật dở dang.
    updated_user = UserProfileResponse.model_validate({**db.user, **changes})
    response = UpdateProfileResponse(success=True, user=updated_user)
    result = JSONResponse(response.model_dump(mode="json", exclude_unset=True))
    db.user.update(changes)
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

async def api_list_hubs(request):
    return JSONResponse(db.get_hubs())

async def api_get_hub(request):
    hub_id = request.path_params.get("hub_id")
    hub = db.get_hub(hub_id)
    if hub:
        return JSONResponse(hub)
    return JSONResponse({"error": "Hub not found"}, status_code=404)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def api_suggest_route(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    o_lat = float(data.get("origin_lat", 10.8753))
    o_lng = float(data.get("origin_lng", 106.8005))
    d_lat = float(data.get("dest_lat", 10.8805))
    d_lng = float(data.get("dest_lng", 106.8055))

    hubs = db.get_hubs()
    nearest_origin = min(
        hubs,
        key=lambda h: calculate_distance(o_lat, o_lng, h["lat"], h["lng"])
    )
    nearest_dest = min(
        [h for h in hubs if h["id"] != nearest_origin["id"]],
        key=lambda h: calculate_distance(d_lat, d_lng, h["lat"], h["lng"]),
        default=hubs[1] if len(hubs) > 1 else hubs[0]
    )

    dist = calculate_distance(nearest_origin["lat"], nearest_origin["lng"], nearest_dest["lat"], nearest_dest["lng"])
    dist_km = round(max(0.5, dist), 1)
    est_mins = max(5, int(dist_km / 15 * 60))

    bike = nearest_origin["bikes"][0] if nearest_origin.get("bikes") else None

    return JSONResponse({
        "origin_hub": nearest_origin,
        "destination_hub": nearest_dest,
        "distance_km": dist_km,
        "estimated_minutes": est_mins,
        "recommended_bike": bike,
        "message": f"Gợi ý tuyến đường từ {nearest_origin['name']} đến {nearest_dest['name']}."
    })

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
            BookingErrorResponse(error=bk["error"]).model_dump(mode="json"),
            status_code=409
        )

    response = BookingResponse.model_validate(bk)
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

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
    return JSONResponse(response.model_dump(mode="json"))

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

async def api_list_incidents(request):
    return JSONResponse(db.incidents)

async def api_create_incident(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    new_inc = {
        "id": f"INC-2026-0{len(db.incidents) + 90}",
        "resource_type": data.get("resource_type", "Phương tiện"),
        "resource_code": data.get("resource_code", "XE-024"),
        "hub_name": data.get("hub_name", "Hub Ga Metro ĐHQG"),
        "incident_type": data.get("incident_type", "Không mở được khóa"),
        "description": data.get("description", ""),
        "created_at": "Vừa xong",
        "status": "Đang xử lý",
        "operator_note": "Hệ thống đã nhận được báo cáo sự cố và chuyển đến điều hành viên."
    }
    db.incidents.insert(0, new_inc)
    # Auto create maintenance ticket for operator and staff
    db.create_maintenance_ticket({
        "title": f"Sự cố báo cáo từ người dùng: {new_inc['incident_type']} ({new_inc['resource_code']})",
        "hub_name": new_inc["hub_name"],
        "device_type": new_inc["resource_type"],
        "device_code": new_inc["resource_code"],
        "description": new_inc["description"] or "Báo cáo sự cố cần kiểm tra hiện trường.",
        "severity": "MEDIUM",
        "priority": "HIGH"
    })
    return JSONResponse(new_inc)

async def api_get_invoice(request):
    inv_type = request.query_params.get("type", "rental")
    if inv_type == "rental":
        return JSONResponse({
            "id": "INV-2026-901",
            "service_type": "rental",
            "title": "Hóa đơn thuê xe điện",
            "reference_id": "XE-031",
            "items": [
                {"label": "Thời gian sử dụng: 45 phút", "description": "Thời gian sử dụng: 45 phút", "amount": 10000},
                {"label": "Phụ phí trễ (nếu có)", "description": "Phụ phí trễ (nếu có)", "amount": 0}
            ],
            "total_amount": 10000,
            "payment_channel": "online",
            "status": "unpaid",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    elif inv_type == "charging":
        return JSONResponse({
            "id": "INV-2026-902",
            "service_type": "charging",
            "title": "Hóa đơn dịch vụ sạc pin",
            "reference_id": "Trụ S03 (2.4 kWh)",
            "items": [
                {"label": "Điện năng tiêu thụ (2.4 kWh x 3,500đ)", "description": "Điện năng tiêu thụ (2.4 kWh x 3,500đ)", "amount": 8400},
                {"label": "Phí chiếm trụ sau đầy", "description": "Phí chiếm trụ sau đầy", "amount": 0}
            ],
            "total_amount": 8400,
            "payment_channel": "online",
            "status": "unpaid",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    elif inv_type in ["swap", "battery_swap"]:
        return JSONResponse({
            "id": "INV-2026-903",
            "service_type": "battery_swap",
            "title": "Hóa đơn dịch vụ đổi pin",
            "reference_id": "Pin BAT-48V",
            "items": [
                {"label": "Đổi 1 pin tiêu chuẩn 48V-20Ah", "description": "Đổi 1 pin tiêu chuẩn 48V-20Ah", "amount": 25000}
            ],
            "total_amount": 25000,
            "payment_channel": "online",
            "status": "unpaid",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    else: # parking
        return JSONResponse({
            "id": "INV-2026-904",
            "service_type": "parking",
            "title": "Hóa đơn gửi xe cá nhân",
            "reference_id": "Biển số: 59-X1 123.45",
            "items": [
                {"label": "Thời gian gửi: 2 giờ (Chỗ P-08)", "description": "Thời gian gửi: 2 giờ (Chỗ P-08)", "amount": 5000}
            ],
            "total_amount": 5000,
            "payment_channel": "cash_guard",
            "status": "unpaid",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        })

async def api_pay_invoice(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    return JSONResponse({
        "success": True,
        "transaction_id": f"TXN-{int(datetime.now().timestamp())}",
        "status": "completed",
        "message": "Thanh toán thành công qua " + data.get("method", "Ví điện tử")
    })

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
    Route("/api/v1/user/bookings/{booking_id}/cancel", api_cancel_booking, methods=["POST"]),
    Route("/api/v1/user/services/active", api_active_services, methods=["GET"]),
    Route("/api/v1/user/services/return-vehicle", api_return_vehicle, methods=["POST"]),
    Route("/api/v1/user/incidents", api_list_incidents, methods=["GET"]),
    Route("/api/v1/user/incidents", api_create_incident, methods=["POST"]),
    Route("/api/v1/user/invoices/current", api_get_invoice, methods=["GET"]),
    Route("/api/v1/user/invoices/pay", api_pay_invoice, methods=["POST"]),
Route("/api/v1/user/bookings/{booking_id}/start", api_start_ride, methods=["POST"]),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    print("Starting Smart E-Mobility Mock Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
