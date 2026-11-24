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
import importlib.util
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

from shared.middleware import SharedPersistenceMiddleware
from shared.database import storage
from user.expiry_worker import expiry_interval, run_expiry_worker



def load_backend_submodule(subfolder, module_name):
    folder_path = os.path.join(BASE_DIR, subfolder)
    for k in list(sys.modules.keys()):
        if k == "schemas" or k.startswith("schemas."):
            del sys.modules[k]
    if folder_path in sys.path:
        sys.path.remove(folder_path)
    sys.path.insert(0, folder_path)
    
    spec = importlib.util.spec_from_file_location(module_name, os.path.join(folder_path, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

user_mod = load_backend_submodule("user", "be_user_main")
op_mod = load_backend_submodule("operator", "be_operator_main")
staff_mod = load_backend_submodule("staff", "be_staff_main")

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

from shared.authentication import AuthenticationMiddleware

middleware = [
    Middleware(AuthenticationMiddleware),
    Middleware(SharedPersistenceMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
    app.state.expiry_task = worker
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


app = Starlette(debug=True, routes=all_routes, middleware=middleware, lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn
    print("Starting Unified E-Mobility Hub Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("run_all:app", host="0.0.0.0", port=8000, reload=True)
