"""Ghép routes và tạo ứng dụng Starlette cho BE User.

Handler HTTP nằm trong user.handlers; nghiệp vụ và schema giữ ở các module
hiện có. Gateway chung vẫn được chạy bằng BE/run_all.py.
"""

import os
import sys

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Giữ cách chạy trực tiếp và cách Gateway nạp module như trước khi tách file.
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from shared.operations_api import user_routes as operation_routes, http_error
from user.payment_gateway import routes as payment_routes
from shared.authentication import AuthenticationMiddleware
from shared.middleware import SharedPersistenceMiddleware
from user.handlers.auth import (
    api_health,
    api_login,
    api_register,
    api_get_profile,
    api_update_profile,
    api_get_user_vehicles,
)
from user.handlers.hub import (
    api_list_hubs,
    api_get_hub,
    api_suggest_route,
)
from user.handlers.booking import (
    api_list_bookings,
    api_create_booking,
    api_expire_bookings,
    api_cancel_booking,
)
from user.handlers.service import (
    api_start_charging,
    api_stop_charging,
    api_complete_swap,
    api_active_services,
    api_start_ride,
    api_return_vehicle,
)
from user.handlers.incident import (api_list_incidents, api_create_incident)
from user.handlers.payment import (api_get_invoice, api_pay_invoice)

# Giữ nguyên URL, phương thức và thứ tự của hai nhóm alias.
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

routes.extend(payment_routes)
routes.extend(operation_routes)

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
