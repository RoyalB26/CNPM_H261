"""
Staff Authentication Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class StaffRole(str, Enum):
    RELOCATION = "Nhân viên điều phối"
    MAINTENANCE = "Nhân viên bảo trì"
    SECURITY_GUARD = "Bảo vệ Hub"


class StaffLoginRequest(BaseModel):
    username_or_phone: str = Field(..., example="staff_b")
    password: str = Field(..., min_length=6, example="staff123")


class StaffProfile(BaseModel):
    id: str = Field(..., example="STF-02")
    full_name: str = Field(..., example="Nguyen Van B")
    role: StaffRole = Field(StaffRole.MAINTENANCE)
    shift_title: str = Field("Ca chiều · 13:00 - 17:00", example="Ca chiều · 13:00 - 17:00")
    assigned_hub: str = Field("Hub KTX Khu A", example="Hub KTX Khu A")
    avatar_initials: str = Field("MT", example="MT")
    tasks_count: int = Field(4, example=4)


class StaffTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffProfile
