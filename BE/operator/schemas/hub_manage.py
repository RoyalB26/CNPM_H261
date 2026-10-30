"""
Operator Hub & Infrastructure Management Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class HubOperationalStatus(str, Enum):
    ACTIVE = "Hoạt động"
    WARNING = "Cảnh báo tải"
    MAINTENANCE = "Bảo trì"
    DEACTIVATED = "Tạm ngưng"


class HubConfig(BaseModel):
    id: str = Field(..., example="HUB-01")
    hub_code: str = Field(..., example="HUB-METRO-01")
    name: str = Field(..., example="Hub Ga Metro ĐHQG")
    address: str = Field(..., example="Khu đô thị ĐHQG - HCM")
    parking_capacity: int = Field(150, ge=1, le=1000)
    charger_capacity: int = Field(50, ge=0, le=200)
    max_power_kw: float = Field(1000.0, ge=10.0)
    load_warning_threshold_pct: int = Field(85, ge=50, le=100)
    lat: float = Field(..., example=10.8753)
    lng: float = Field(..., example=106.8005)
    status: HubOperationalStatus = Field(default=HubOperationalStatus.ACTIVE)
    availability_rate_pct: int = Field(85, ge=0, le=100)


class HubConfigUpdate(BaseModel):
    hub_id: str = Field(..., example="HUB-01")
    name: Optional[str] = None
    parking_capacity: Optional[int] = Field(None, ge=1)
    charger_capacity: Optional[int] = Field(None, ge=0)
    max_power_kw: Optional[float] = Field(None, ge=10.0)
    load_warning_threshold_pct: Optional[int] = Field(None, ge=50, le=100)
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: Optional[HubOperationalStatus] = None


class HubDeactivateRequest(BaseModel):
    hub_id: str = Field(..., example="HUB-01")
    reason: str = Field(..., example="Bảo trì toàn diện hệ thống trạm biến áp")
    lock_chargers: bool = True
    reroute_bookings: bool = True


class HubManageList(BaseModel):
    total: int
    items: List[HubConfig]
