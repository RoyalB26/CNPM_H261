from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional
from .booking import NonEmptyString

class CreateIncidentReportRequest(BaseModel):
    """Báo cáo phải có định danh tài nguyên, Hub và mô tả không rỗng."""

    model_config = ConfigDict(strict=True)

    resource_type: NonEmptyString
    resource_code: NonEmptyString
    hub_name: NonEmptyString
    incident_type: NonEmptyString
    description: NonEmptyString
    image_attached: bool = Field(False)

class IncidentReportResponse(BaseModel):
    """Báo cáo chuẩn hóa; giữ các trường bổ sung của seed cũ khi đọc."""

    model_config = ConfigDict(extra="allow")
    id: str = Field(..., example="INC-2026-089")
    resource_type: str = Field(..., example="Phương tiện")
    resource_code: str = Field(..., example="XE-024")
    hub_name: str = Field(..., example="Hub Ga Metro ĐHQG")
    incident_type: str = Field(..., example="Không mở được khóa")
    description: str = Field(...)
    created_at: str = Field(..., example="10:35 · 18/10/2026")
    status: str = Field("Đang xử lý", example="Đang xử lý")
    operator_note: Optional[str] = Field("Đã tiếp nhận yêu cầu, kỹ thuật viên đang đến kiểm tra thiết bị.")
    maintenance_ticket_code: Optional[str] = None
    maintenance_status: Optional[str] = None

class IncidentErrorResponse(BaseModel):
    """Lỗi báo cáo, chưa tạo sự cố hoặc phiếu bảo trì."""

    success: Literal[False] = False
    error: str
