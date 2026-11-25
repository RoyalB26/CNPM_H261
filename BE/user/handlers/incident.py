"""Handler báo sự cố và đọc trạng thái phiếu bảo trì liên kết."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.database import db, persist_change
from user.incidents import (
    IncidentError,
    create_report,
    report_view,
)
from user.schemas import CreateIncidentReportRequest, IncidentErrorResponse


async def api_list_incidents(request: Request) -> JSONResponse:
    """Trả lịch sử báo cáo cùng trạng thái phiếu mới nhất, không ghi store."""
    try:
        reports = [report_view(db, report).model_dump(mode="json", exclude_unset=True)
                   for report in db.get_user_incidents()]
    except IncidentError as exc:
        return JSONResponse(IncidentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
    return JSONResponse(reports)


async def api_create_incident(request: Request) -> JSONResponse:
    """Kiểm tra và lưu báo cáo cùng phiếu đúng Hub trong một transaction."""
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(IncidentErrorResponse(error="Dữ liệu JSON không hợp lệ").model_dump(mode="json"), status_code=400)
    try:
        report_request = CreateIncidentReportRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(IncidentErrorResponse(error="Dữ liệu báo cáo không hợp lệ").model_dump(mode="json"), status_code=422)
    def change(candidate):
        try:
            response = create_report(candidate, report_request)
        except IncidentError as exc:
            return JSONResponse(IncidentErrorResponse(error=str(exc)).model_dump(mode="json"), status_code=exc.status_code)
        return JSONResponse(response.model_dump(mode="json", exclude_unset=True))

    return persist_change(change)
