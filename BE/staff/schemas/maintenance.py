"""
Staff Maintenance & Field Diagnostics Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class MaintenancePriority(str, Enum):
    URGENT = "KHẨN CẤP"
    WARNING = "CẢNH BÁO"
    NORMAL = "THƯỜNG"


class ResolutionOutcome(str, Enum):
    FIXED_ON_SITE = "Đã sửa tại chỗ"
    TRANSFER_TO_WORKSHOP = "Cần chuyển về xưởng"


class MaintenanceTaskSummary(BaseModel):
    task_code: str = Field(..., example="MT-102")
    priority: MaintenancePriority = Field(MaintenancePriority.URGENT)
    category_label: str = Field(..., example="XE ĐẠP ĐIỆN · HƯ HỎNG")
    title: str = Field(..., example="Xe BK-EB-018 không khởi động")
    hub_name: str = Field(..., example="Hub KTX Khu A")
    created_at_label: str = Field("Hôm nay, 14:25", example="Hôm nay, 14:25")
    due_label: str = Field("Cần xử lý trong 35 phút", example="Cần xử lý trong 35 phút")
    status: str = Field("Mới tiếp nhận", example="Mới tiếp nhận")


class MaintenanceTaskDetail(BaseModel):
    task_code: str = Field(..., example="MT-102")
    priority: MaintenancePriority = Field(MaintenancePriority.URGENT)
    category_label: str = Field(..., example="XE ĐẠP ĐIỆN · HƯ HỎNG")
    title: str = Field(..., example="Xe BK-EB-018 không khởi động")
    reported_by: str = Field("Nhân viên điều chuyển · 14:25 hôm nay", example="Nhân viên điều chuyển · 14:25 hôm nay")
    device_code: str = Field("BK-EB-018", example="BK-EB-018")
    exact_location: str = Field("Hub KTX Khu A · Khu đỗ xe · Dãy B · Ô số 018", example="Hub KTX Khu A · Khu đỗ xe · Dãy B · Ô số 018")
    reporter_notes: str = Field(
        "Xe không phản hồi khi bật nguồn. Đã thử cắm sạc nhưng đèn báo không sáng. Vui lòng kiểm tra pin và bộ điều khiển.",
        example="Xe không phản hồi khi bật nguồn."
    )
    attachment_filename: Optional[str] = Field("anh-hien-trang-01.jpg", example="anh-hien-trang-01.jpg")
    last_maintenance_info: str = Field("Kiểm tra pin và phanh · 12/10/2026 · NVKT Tran Minh A · Hoàn tất")


class DeviceVerifyRequest(BaseModel):
    task_code: str = Field(..., example="MT-102")
    scanned_qr_code: str = Field(..., example="BK-EB-018")
    confirmed_slot: str = Field("Ô số 018", example="Ô số 018")


class MaintenanceResolveRequest(BaseModel):
    task_code: str = Field(..., example="MT-102")
    outcome: ResolutionOutcome = Field(default=ResolutionOutcome.FIXED_ON_SITE)
    technical_notes: str = Field(
        ...,
        example="Đã kiểm tra tiếp xúc giắc cắm BMS pin, reset mạch sạc và chạy thử động cơ thành công."
    )
    photo_attachment_url: Optional[str] = None


class MaintenanceIncidentRequest(BaseModel):
    task_code: str = Field(..., example="MT-102")
    incident_type: str = Field(..., example="Xe hư hỏng giữa đường")
    location_text: str = Field(..., example="Đường nội bộ · Hub KTX Khu A")
    description: str = Field(..., max_length=300, example="Xe không lên nguồn sau khi đi qua đoạn ngập")
    photo_attachment_url: Optional[str] = None
