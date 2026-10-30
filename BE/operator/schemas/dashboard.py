"""
Operator Dashboard & Realtime Telemetry Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    ALERT = "ALERT"
    EMERGENCY = "EMERGENCY"


class KPISummary(BaseModel):
    total_hubs: int = Field(50, description="Tổng số Hub trong hệ thống")
    available_bikes: int = Field(120, description="Xe đang rảnh")
    total_bikes: int = Field(500, description="Tổng số xe trong mạng lưới")
    available_chargers: int = Field(300, description="Số cổng sạc khả dụng")
    active_alerts: int = Field(2, description="Số cảnh báo hệ thống cần xử lý")


class TelemetryEvent(BaseModel):
    id: str = Field(..., example="EVT-1029")
    hub_id: str = Field(..., example="HUB-B")
    hub_name: str = Field(..., example="Hub B - KTX Khu B")
    level: AlertLevel = Field(AlertLevel.ALERT)
    title: str = Field(..., example="Mất kết nối IoT Hub B")
    message: str = Field(..., example="Cổng sạc C-02 không phản hồi dữ liệu Telemetry quá 60s.")
    created_at_relative: str = Field("Vừa xong", example="Vừa xong")
    timestamp_iso: str = Field(..., example="2026-10-22T14:35:00Z")


class HubLiveStatus(BaseModel):
    hub_id: str
    hub_code: str
    name: str
    status_label: str
    is_high_load: bool = False
    parking_free: int
    parking_total: int
    chargers_free: int
    chargers_total: int
    current_power_kw: float
    max_power_kw: float
    lat: float
    lng: float
    color_code: str = "#10b981"
    available_bikes: Optional[int] = 0


class EmergencyHaltRequest(BaseModel):
    reason: str = Field(..., example="Sự cố lưới điện diện rộng ĐHQG")
    operator_id: str = Field(..., example="OP-001")
    confirmation_token: str = Field(..., example="HALT_ALL_CONFIRM")


class EmergencyHaltResponse(BaseModel):
    success: bool
    status: str = "EMERGENCY_HALT_ACTIVATED"
    message: str
    affected_hubs: int
    timestamp_iso: str
