"""Handler tra cứu Hub và gợi ý lộ trình cho User."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.database import db
from user.hubs import (
    hub_detail,
    search_hubs,
    suggest_route,
)
from user.schemas import SearchHubQuery, RouteSuggestionRequest


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
