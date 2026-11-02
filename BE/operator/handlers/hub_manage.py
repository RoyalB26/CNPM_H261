
import json
from datetime import datetime, timezone
from typing import Any



from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..store import db
from ..schemas.hub_manage import (
    HubConfig,
    HubConfigUpdate,
    HubDeactivateRequest,
    HubManageList,
    HubOperationalStatus,
    HubConfigUpdateResponse,
    HubDeactivateResponse,
    HubErrorResponse,
)





# Xem danh sách -> list_hubs_config -> db.get_hubs()
#                                  -> hub_response cho từng Hub
#                                  -> HubManageList -> JSON HTTP 200

# Cập nhật     -> update_hub_config -> kiểm tra request -> db.get_hub()
#                                  -> kiểm tra cấu hình mới
#                                  -> hub_response -> HubConfigUpdateResponse
#                                  -> hub.update() -> JSON HTTP 200
#                                  -> hub_error_response nếu lỗi

# Tạm ngưng    -> deactivate_hub -> kiểm tra request -> db.get_hub()
#                               -> kiểm tra trạng thái hiện tại
#                               -> hub_response -> HubDeactivateResponse
#                               -> hub.update() -> JSON HTTP 200
#                               -> hub_error_response nếu lỗi


def hub_response(hub: dict[str, Any]) -> HubConfig:
    """Chuyển dữ liệu Hub trong store thành model response."""
    return HubConfig.model_validate({
        **hub,
        "status": HubOperationalStatus[hub["status"]],
    })


def hub_error_response(
    status_code: int,
    detail: str,
) -> JSONResponse:
    """Tạo response lỗi Hub theo cấu trúc thống nhất."""
    err_data = HubErrorResponse(
        status_code=str(status_code),
        error=1,
        detail=detail,
    )
    return JSONResponse(
        content=err_data.model_dump(mode="json"),
        status_code=status_code,
    )


async def list_hubs_config(request: Request) -> JSONResponse:
    """Trả danh sách cấu hình Hub theo HubManageList."""
    items = [hub_response(hub) for hub in db.get_hubs()]
    response_data = HubManageList(
        total=len(items),
        items=items,
    )
    return JSONResponse(
        content=response_data.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


async def update_hub_config(request: Request) -> JSONResponse:
    """Kiểm tra và cập nhật các trường cấu hình Hub được gửi."""
    hub_id = request.path_params["hub_id"].lower()

    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return hub_error_response(
            status.HTTP_400_BAD_REQUEST,
            "JSON không hợp lệ",
        )

    if not isinstance(body, dict):
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Body phải là một JSON object",
        )

    # Đường dẫn quyết định Hub cần cập nhật.
    if "hub_id" in body:
        body_hub_id = body["hub_id"]
        if (
            not isinstance(body_hub_id, str)
            or body_hub_id.lower() != hub_id
        ):
            return hub_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "hub_id trong body phải khớp với đường dẫn",
            )

    hub = db.get_hub(hub_id)
    if hub is None:
        return hub_error_response(
            status.HTTP_404_NOT_FOUND,
            "Hub không tồn tại",
        )

    try:
        req = HubConfigUpdate.model_validate({
            **body,
            "hub_id": hub_id,
        })
    except ValidationError:
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Dữ liệu cập nhật cấu hình Hub không hợp lệ",
        )

    changes = req.model_dump(
        mode="json",
        exclude_unset=True,
        exclude={"hub_id"},
    )

    if not changes:
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Chưa gửi trường cấu hình cần cập nhật",
        )

    if any(value is None for value in changes.values()):
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Các trường cập nhật không được nhận null",
        )

    # Store lưu mã trạng thái; response trả giá trị tiếng Việt.
    if "status" in changes:
        changes["status"] = req.status.name

    candidate = {**hub, **changes}

    try:
        response_data = HubConfigUpdateResponse(
            success=True,
            message="Đã cập nhật cấu hình Hub",
            hub=hub_response(candidate),
        )
    except ValidationError:
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Cấu hình mới vượt giới hạn cho phép",
        )

    # Chỉ ghi sau khi cấu hình và response đều hợp lệ.
    content = response_data.model_dump(mode="json")
    hub.update(changes)

    return JSONResponse(
        content=content,
        status_code=status.HTTP_200_OK,
    )


async def deactivate_hub(request: Request) -> JSONResponse:
    """Kiểm tra lý do và chuyển Hub sang trạng thái tạm ngưng."""
    hub_id = request.path_params["hub_id"].lower()

    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return hub_error_response(
            status.HTTP_400_BAD_REQUEST,
            "JSON không hợp lệ",
        )

    if not isinstance(body, dict):
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Body phải là một JSON object",
        )

    if "hub_id" in body:
        body_hub_id = body["hub_id"]
        if (
            not isinstance(body_hub_id, str)
            or body_hub_id.lower() != hub_id
        ):
            return hub_error_response(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "hub_id trong body phải khớp với đường dẫn",
            )

    try:
        req = HubDeactivateRequest.model_validate({
            **body,
            "hub_id": hub_id,
        })
    except ValidationError:
        return hub_error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Dữ liệu tạm ngưng Hub không hợp lệ; cần có lý do",
        )

    hub = db.get_hub(hub_id)
    if hub is None:
        return hub_error_response(
            status.HTTP_404_NOT_FOUND,
            "Hub không tồn tại",
        )

    # Giữ nguyên lý do và thời gian của lần tạm ngưng trước.
    if hub["status"] == "DEACTIVATED":
        return hub_error_response(
            status.HTTP_409_CONFLICT,
            "Hub đã tạm ngưng hoạt động",
        )

    reason = req.reason.strip()
    deactivated_at = datetime.now(timezone.utc).isoformat()

    # Ghi nhận yêu cầu; thao tác khóa và chuyển booking chưa thực hiện.
    pending_actions = []
    if req.lock_chargers:
        pending_actions.append("lock_chargers")
    if req.reroute_bookings:
        pending_actions.append("reroute_bookings")

    changes = {
        "status": "DEACTIVATED",
        "deactivation_reason": reason,
        "deactivated_at": deactivated_at,
        "deactivation_lock_chargers_requested": req.lock_chargers,
        "deactivation_reroute_bookings_requested": req.reroute_bookings,
    }
    candidate = {**hub, **changes}

    response_data = HubDeactivateResponse(
        success=True,
        message="Đã chuyển trạng thái Hub sang tạm ngưng",
        hub=hub_response(candidate),
        reason=reason,
        deactivated_at=deactivated_at,
        pending_actions=pending_actions,
    )

    content = response_data.model_dump(mode="json")
    hub.update(changes)

    return JSONResponse(
        content=content,
        status_code=status.HTTP_200_OK,
    )




routes = [
    Route("/api/v1/operator/hubs", list_hubs_config, methods=["GET"]),
    Route("/api/v1/operator/hubs/{hub_id}/config", update_hub_config, methods=["PUT"]),
    Route("/api/v1/operator/hubs/{hub_id}/deactivate", deactivate_hub, methods=["POST"]),
]