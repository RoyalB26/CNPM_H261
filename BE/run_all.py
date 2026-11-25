"""
Unified Mock Backend Runner
Smart E-Mobility Hub - ĐHQG-HCM

Runs all three backend subsystems (User, Operator, Staff)
unified under a single API Gateway on port 8000:
  - /api/v1/user/...      -> User Backend
  - /api/v1/operator/...  -> Operator Backend
  - /api/v1/staff/...     -> Staff & Security Guard Backend
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager, suppress
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
PROJECT_DIR = os.path.dirname(BASE_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from shared.middleware import SharedPersistenceMiddleware
from shared.database import storage
from shared.automation import run_operations_worker
from user.expiry_worker import expiry_interval, run_expiry_worker
# Import theo package để mỗi role dùng đúng schemas, không xóa module cache.
from BE.user import main as user_mod
from BE.operator import main as op_mod
from BE.staff import main as staff_mod

async def root_status(request):
    return JSONResponse({
        "system": "Smart E-Mobility Hub Mock API Gateway",
        "status": "ONLINE",
        "endpoints": {
            "user": "/api/v1/user",
            "operator": "/api/v1/operator",
            "staff": "/api/v1/staff"
        },
        "routes_count": len(user_mod.routes) + len(op_mod.routes) + len(staff_mod.routes),
    })

all_routes = [Route("/", root_status)] + user_mod.routes + op_mod.routes + staff_mod.routes

from starlette.exceptions import HTTPException
from shared.operations_api import http_error
from shared.authentication import AuthenticationMiddleware

middleware = [
    Middleware(SharedPersistenceMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(AuthenticationMiddleware)
]

@asynccontextmanager
async def lifespan(app):
    """Tạo khóa chung, khởi động quét hết hạn và thu hồi tác vụ khi tắt Gateway."""
    interval = expiry_interval(os.environ.get("BE_BOOKING_EXPIRY_INTERVAL_SECONDS", "5"))
    app.state.request_lock = asyncio.Lock()
    worker = asyncio.create_task(
        run_expiry_worker(storage, app.state.request_lock, interval),
        name="user-booking-expiry",
    )
    operations_worker = asyncio.create_task(
        run_operations_worker(storage, app.state.request_lock), name="operations",
    )
    app.state.operations_task = operations_worker
    app.state.expiry_task = worker
    try:
        yield
    finally:
        operations_worker.cancel()
        with suppress(asyncio.CancelledError):
            await operations_worker
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


app = Starlette(debug=True, routes=all_routes, middleware=middleware, lifespan=lifespan, exception_handlers={HTTPException: http_error})

if __name__ == "__main__":
    import uvicorn
    print("Starting Unified E-Mobility Hub Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("run_all:app", host="0.0.0.0", port=8000, reload=True)
