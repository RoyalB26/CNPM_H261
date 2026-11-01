"""
Operator Relocation Command Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator


class RelocationStatus(str, Enum):
    PENDING = "Đang chờ nhận"
    IN_TRANSIT = "Đang di chuyển"
    COMPLETED = "Hoàn thành"
    CANCELLED = "Đã hủy"


class RelocationPriority(str, Enum):
    NORMAL = "Bình thường"
    URGENT = "Khẩn cấp"


class RelocationCommandCreate(BaseModel):
    source_hub_id: str = Field(..., example="HUB-01")
    target_hub_id: str = Field(..., example="HUB-02")
    bike_count: int = Field(..., ge=1, le=50, example=5)
    assigned_staff_id: str = Field(..., example="STF-01")
    priority: RelocationPriority = Field(default=RelocationPriority.NORMAL)
    notes: Optional[str] = Field(None, example="Điều phối bù xe thiếu hụt giờ cao điểm")


class RelocationCommandItem(BaseModel):
    id: str = Field(..., example="CMD-1023")
    source_hub_name: str = Field(..., example="Hub A (KTX Khu A)")
    target_hub_name: str = Field(..., example="Hub B (Ga Metro A)")
    bike_count: int = Field(..., example=5)
    assigned_staff_name: str = Field(..., example="Nguyen Van B")
    status: RelocationStatus = Field(default=RelocationStatus.IN_TRANSIT)
    progress_current: int = Field(default=0, example=3)
    progress_total: int = Field(default=5, example=5)
    created_at: str = Field(..., example="2026-10-22 14:15")
    updated_at: str = Field(..., example="2026-10-22 14:28")


class RelocationCommandList(BaseModel):
    total: int
    items: List[RelocationCommandItem]
