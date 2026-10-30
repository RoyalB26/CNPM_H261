"""
Staff Relocation Workflow Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class BikeChecklistStatus(str, Enum):
    DONE = "Done"
    WAITING = "Waiting"


class BikeChecklistItem(BaseModel):
    bike_code: str = Field(..., example="BK-EB-001")
    battery_pct: int = Field(85, ge=0, le=100)
    dock_number: str = Field("02", example="02")
    status: BikeChecklistStatus = Field(default=BikeChecklistStatus.WAITING)
    scanned_at: Optional[str] = None


class RelocationTaskDetail(BaseModel):
    task_id: str = Field(..., example="#102")
    title: str = Field("Lộ trình điều chuyển", example="Lộ trình điều chuyển")
    source_hub_name: str = Field("Hub KTX Khu A", example="Hub KTX Khu A")
    target_hub_name: str = Field("Hub Ga Metro A", example="Hub Ga Metro A")
    vehicle_type: str = Field("Xe đạp điện", example="Xe đạp điện")
    total_bikes: int = Field(20, example=20)
    in_transit_bikes: int = Field(12, example=12)
    remaining_at_source: int = Field(8, example=8)
    estimated_distance_km: float = Field(2.5, example=2.5)
    estimated_duration_minutes: int = Field(10, example=10)
    source_contact: Optional[str] = Field("0901-234-567 (Hub Trưởng KTX B)")
    target_contact: Optional[str] = Field("0908-765-432 (Trực ban Hub Ga Metro)")
    status: Optional[str] = Field("IN_PROGRESS")
    priority: Optional[str] = Field("HIGH")
    checklist: List[BikeChecklistItem] = Field(default_factory=list)


class BikeScanRequest(BaseModel):
    task_id: str = Field(..., example="#102")
    qr_data: str = Field(..., example="BK-EB-001")
    target_dock_code: Optional[str] = Field("02", example="02")


class RelocationHandoverRequest(BaseModel):
    task_id: str = Field(..., example="#102")
    notes: Optional[str] = Field(None, example="Đã bàn giao đầy đủ 20 xe tại Ga Metro")
    confirmed_by_staff_id: str = Field(..., example="STF-02")


class RelocationIncidentRequest(BaseModel):
    task_id: str = Field(..., example="#102")
    incident_type: str = Field(..., example="Xe bị thủng lốp")
    location_text: str = Field(..., example="Đường nội bộ giữa Hub KTX Khu A và Hub Ga Metro A")
    description: str = Field(..., max_length=300, example="Xe BK-EB-014 bị hỏng lốp sau khi qua gờ giảm tốc")
    photo_attachment_url: Optional[str] = None
