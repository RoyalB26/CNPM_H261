"""
Mock Backend Service for Operator Control Center
Smart E-Mobility Hub - ĐHQG-HCM
"""

import os
import sys





from starlette.applications import Starlette

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

# Ensure parent directory is in sys.path to import mock_db
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


PROJECT_DIR = os.path.dirname(PARENT_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from BE.operator.handlers.auth import routes as auth_routes
from BE.operator.handlers.dashboard import routes as dashboard_routes
from BE.operator.handlers.hub_manage import routes as hub_manage_routes
from BE.operator.handlers.maintenance import routes as maintenance_routes
from BE.operator.handlers.relocation import routes as relocation_routes
from BE.operator.handlers.simulation import routes as simulation_routes




from BE.operator.store import db, RelocationError




# ================= APPLICATION SETUP =================

routes = [
    *auth_routes,
    *dashboard_routes,
    *hub_manage_routes,
    *maintenance_routes,
    *relocation_routes,
    *simulation_routes,
]



middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
