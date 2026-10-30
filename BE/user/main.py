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
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Ensure parent directory is in sys.path to import mock_db
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from mock_db import db

# API Route Handlers
async def api_health(request):
    return JSONResponse({"status": "ok", "app": "Smart E-Mobility Hub Backend"})

async def api_login(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    return JSONResponse({
        "success": True,
        "token": "jwt-token-sample-mock-123456",
        "user": db.user
    })

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

async def api_get_profile(request):
    return JSONResponse(db.user)

async def api_update_profile(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    for k in ["full_name", "email", "phone", "default_payment_method"]:
        if k in data:
            db.user[k] = data[k]
    return JSONResponse({"success": True, "user": db.user})

async def api_get_user_vehicles(request):
    return JSONResponse(db.get_user_vehicles())

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

async def api_list_bookings(request):
    return JSONResponse(db.get_bookings())

async def api_create_booking(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    bk = db.create_booking(data)
    return JSONResponse(bk)

async def api_cancel_booking(request):
    booking_id = request.path_params.get("booking_id")
    bk = db.cancel_booking(booking_id)
    if bk:
        return JSONResponse({"success": True, "booking": bk})
    return JSONResponse({"error": "Booking not found"}, status_code=404)

async def api_active_services(request):
    return JSONResponse(db.user.get("active_services", {}))

async def api_return_vehicle(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if data.get("force_error") or data.get("simulate_error"):
        return JSONResponse({
            "success": False,
            "error": "Không thể hoàn tất trả xe: Vị trí xe ngoài bán kính Hub hoặc khóa chốt chưa đóng."
        }, status_code=400)
    
    trip_id = data.get("trip_id", "TRIP-8821")
    hub_name = data.get("hub_name", "Hub Đại học Bách khoa")
    res = db.return_vehicle(trip_id, hub_name)
    return JSONResponse(res)

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
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    print("Starting Smart E-Mobility Mock Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
