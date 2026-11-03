
import json
from typing import Any


from pydantic import ValidationError, BaseModel
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..store import db, RelocationError, persist_change
from ..schemas.relocation import (
    RelocationCommandCreate,
    RelocationCommandItem,
    RelocationCommandList,
    RelocationStatus,
    RelocationPriority,
    RelocationResponse,
)





def relocation_response(task: dict[str, Any]) -> RelocationCommandItem:
    """Chuyển lệnh trong store thành model response điều chuyển."""
    status_map = {
        "PENDING": RelocationStatus.PENDING,
        "IN_PROGRESS": RelocationStatus.IN_TRANSIT,
        "IN_TRANSIT": RelocationStatus.IN_TRANSIT,
        "COMPLETED": RelocationStatus.COMPLETED,
        "CANCELLED": RelocationStatus.CANCELLED,
    }

    return RelocationCommandItem(
        id=task["task_id"],
        source_hub_name=task["source_hub_name"],
        target_hub_name=task["target_hub_name"],
        bike_count=task["total_bikes"],
        assigned_staff_name=(
            task.get("assigned_staff_name")
            or task.get("assigned_to")
            or "Chưa phân công"
        ),
        status=status_map[task["status"]],
        progress_current=task["in_transit_bikes"],
        progress_total=task["total_bikes"],
        created_at=task["created_at"],
        updated_at=task.get("updated_at") or task["created_at"],
        source_hub_id=task["source_hub_id"],
        target_hub_id=task["target_hub_id"],
        assigned_staff_id=task.get("assigned_staff_id"),
        bike_ids=[entry["bike_id"] for entry in task["bikes"]],
        reserved_slot_ids=task.get("reserved_slot_ids", []),
        priority=task["priority"],
        notes=task.get("notes"),
    )


async def list_relocations(request: Request) -> JSONResponse:
    """Trả danh sách lệnh điều chuyển theo RelocationCommandList."""
    items = [relocation_response(task) for task in db.relocations]
    response_data = RelocationCommandList(
        total=len(items),
        items=items,
    )

    return JSONResponse(
        content=response_data.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )







async def create_relocation(request: Request) -> JSONResponse:
    """Kiểm tra đầu vào và tạo lệnh điều chuyển.

    Trả về lệnh đã tạo với HTTP 201 khi thành công.
    Khi thất bại, trả thông báo lỗi theo RelocationResponse.
    """
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        err_data = RelocationResponse(
            status_code="400",
            error=1,
            detail="JSON không hợp lệ",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Chỉ nhận JSON object để kiểm tra các trường tạo lệnh.
    if not isinstance(body, dict):
        err_data = RelocationResponse(
            status_code="422",
            error=1,
            detail="Body phải là một JSON object",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        req = RelocationCommandCreate.model_validate(body)
    except ValidationError as exc:
        err_data = RelocationResponse(
            status_code="422",
            error=1,
            detail=f"Dữ liệu không hợp lệ: {exc}",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Store kiểm tra Hub, nhân viên, xe và chỗ đỗ trước khi tạo lệnh.
    


    def change(candidate):
        task = candidate.create_relocation_command(
            req.model_dump(mode="json"),
        )

        return JSONResponse(
            content=relocation_response(task).model_dump(mode="json"),
            status_code=status.HTTP_201_CREATED,
        )

    try:
        return persist_change(change)
    except RelocationError as exc:
        err_data = RelocationResponse(
            status_code=str(exc.status_code),
            error=1,
            detail=str(exc),
        )

        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=exc.status_code,
        )



routes = [
    Route("/api/v1/operator/relocation/commands", list_relocations, methods=["GET"]),
    Route("/api/v1/operator/relocation/commands", create_relocation, methods=["POST"]),
]