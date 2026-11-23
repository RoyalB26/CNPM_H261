"""
Operator Maintenance Management Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class FaultSeverity(str, Enum):
    LOW = "Thường"
    WARNING = "Cảnh báo"
    URGENT = "Khẩn cấp"


class MaintenanceStatus(str, Enum):
    PENDING = "Chờ xử lý"
    ASSIGNED = "Đã phân công"
    IN_PROGRESS = "Đang xử lý"
    RESOLVED = "Đã xử lý"
    CLOSED = "Đã đóng"


class MaintenanceTicketItem(BaseModel):
    id: str = Field(..., example="TKT-001")
    ticket_code: str = Field(..., example="ERR-8812")
    device_code: str = Field(..., example="CS-02-HUB_A")
    hub_name: str = Field(..., example="Hub KTX Khu A")
    source: str = Field(..., example="Cảnh báo IoT")
    fault_category: str = Field(..., example="Quá nhiệt cổng sạc")
    severity: FaultSeverity = Field(default=FaultSeverity.URGENT)
    assigned_staff_id: Optional[str] = None
    assigned_staff_name: Optional[str] = Field("Chưa gán", example="Le Van D")
    status: MaintenanceStatus = Field(default=MaintenanceStatus.PENDING)
    reported_at: str = Field(..., example="2026-10-22 14:25")
    description: Optional[str] = Field(None, example="Trạm sạc số 4 đang ở mức 58°C")
    photo_url: Optional[str] = None


class MaintenanceAssignRequest(BaseModel):
    ticket_code: str = Field(..., example="ERR-8812")
    technician_id: str = Field(..., example="TECH-04")
    technician_name: str = Field(..., example="Le Van D")
    priority: FaultSeverity = Field(default=FaultSeverity.URGENT)
    operator_notes: Optional[str] = Field(None, example="Ưu tiên xử lý trước giờ cao điểm 16:30")


class MaintenanceCreateRequest(BaseModel):
    device_code: str = Field(..., example="XE-024")
    hub_name: str = Field(..., example="Hub Đại học Bách Khoa")
    source: str = Field(..., example="Operator thủ công")
    fault_category: str = Field(..., example="Không mở được khóa")
    severity: FaultSeverity = Field(default=FaultSeverity.WARNING)
    description: str = Field(..., example="Khóa xe không phản hồi Bluetooth")
    assigned_staff_id: Optional[str] = None


class MaintenanceTicketList(BaseModel):
    total: int
    items: List[MaintenanceTicketItem]



class MaintenanceAssignResponse(BaseModel):
    """Kết quả phân công + thông tin phiếu bảo trì sau update."""

    success: bool = Field(..., examples=[True])
    message: str = Field(
        ...,
        examples=["Đã phân công Nguyen Van B xử lý phiếu TICK-802"],
    )
    ticket: MaintenanceTicketItem


class MaintenanceErrorResponse(BaseModel):
    """Thông báo lỗi của API bảo trì."""

    status_code: str = Field(..., examples=["422"])
    error: int = Field(..., examples=[1])
    detail: str = Field(
        ...,
        examples=["Dữ liệu phân công bảo trì không hợp lệ"],
    )