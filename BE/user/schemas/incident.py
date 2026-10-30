from pydantic import BaseModel, Field
from typing import Optional

class CreateIncidentReportRequest(BaseModel):
    resource_type: str = Field(..., example="Phương tiện", description="Phương tiện | Chỗ đỗ | Cổng sạc | Cơ sở hạ tầng")
    resource_code: str = Field(..., example="XE-024")
    hub_name: str = Field(..., example="Hub Ga Metro ĐHQG")
    incident_type: str = Field(..., example="Không mở được khóa")
    description: str = Field(..., example="Xe không mở được khóa sau khi xác nhận nhận xe.")
    image_attached: bool = Field(False)

class IncidentReportResponse(BaseModel):
    id: str = Field(..., example="INC-2026-089")
    resource_type: str = Field(..., example="Phương tiện")
    resource_code: str = Field(..., example="XE-024")
    hub_name: str = Field(..., example="Hub Ga Metro ĐHQG")
    incident_type: str = Field(..., example="Không mở được khóa")
    description: str = Field(...)
    created_at: str = Field(..., example="10:35 · 18/10/2026")
    status: str = Field("Đang xử lý", example="Đang xử lý")
    operator_note: Optional[str] = Field("Đã tiếp nhận yêu cầu, kỹ thuật viên đang đến kiểm tra thiết bị.")
