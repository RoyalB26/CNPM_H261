from pydantic import BaseModel, Field
from typing import List, Optional

class BookingServiceItem(BaseModel):
    service_type: str = Field(..., example="parking", description="'rental' | 'parking' | 'charging' | 'battery_swap' | 'swap'")
    detail: str = Field(..., example="Chỗ đỗ · 10:00 – 12:00")
    resource_id: Optional[str] = Field(None, example="XE-024 hoặc S03")
    time_slot: Optional[str] = Field("10:00 – 12:00")
    price_est: int = Field(5000)

class CreateBookingRequest(BaseModel):
    plan_type: str = Field(..., example="personal", description="'rental' | 'personal' | 'swap' | 'parking' | 'charging'")
    hub_id: str = Field(..., example="hub-01")
    destination_hub_id: Optional[str] = Field(None, example="hub-02", description="Chỉ dùng khi thuê xe")
    destination_hub_name: Optional[str] = Field(None, example="Hub Đại học Bách khoa")
    personal_plate: Optional[str] = Field(None, example="59-X1 123.45")
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    selected_bike: Optional[str] = None
    parking_slot: Optional[str] = None
    charging_port: Optional[str] = None
    battery_type: Optional[str] = None
    battery_quantity: Optional[int] = 1
    duration_hours: Optional[int] = 2
    arrival_time: Optional[str] = None
    services: List[BookingServiceItem] = []

class BookingResponse(BaseModel):
    id: str = Field(..., example="EMH-1024")
    plan_type: str = Field(..., example="personal")
    hub_name: str = Field(..., example="Hub Ga Metro ĐHQG")
    destination_hub_name: Optional[str] = None
    personal_plate: Optional[str] = None
    resource_name: Optional[str] = None
    services: List[BookingServiceItem] = []
    status: str = Field("confirmed", example="Đã xác nhận")
    hold_until: str = Field("08:10", example="08:10")
    created_at: str = Field("18/10/2026 · từ 10:00")
    total_price: int = Field(15000)

class CancelBookingRequest(BaseModel):
    booking_id: str
    reason: Optional[str] = "Thay đổi kế hoạch"
