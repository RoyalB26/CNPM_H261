from pydantic import BaseModel, Field
from typing import List, Optional

class TimeLog(BaseModel):
    label: str = Field(..., example="Đặt xe")
    time: str = Field(..., example="08:00")

class ActiveRideResponse(BaseModel):
    id: str = Field("ACT-01")
    vehicle_id: str = Field("XE-024")
    vehicle_name: str = Field("Xe đạp điện")
    battery_level: int = Field(78, description="Mức pin hiện tại %")
    origin_hub: str = Field("Hub Ga Metro ĐHQG")
    destination_hub: str = Field("ĐH Bách Khoa")
    elapsed_minutes: int = Field(13)
    status: str = Field("Đang sử dụng")
    logs: List[TimeLog] = [
        TimeLog(label="Đặt xe", time="08:00"),
        TimeLog(label="Nhận / bắt đầu", time="08:05"),
        TimeLog(label="Cập nhật gần nhất", time="08:18:02")
    ]

class ActiveParkingResponse(BaseModel):
    id: str = Field("PARK-01")
    plate_number: str = Field("59-X1 123.45")
    hub_name: str = Field("Hub Ga Metro ĐHQG")
    slot_id: str = Field("P-12")
    checkin_time: str = Field("09:15")
    elapsed_minutes: int = Field(45)
    status: str = Field("Đang đỗ")

class ActiveChargingResponse(BaseModel):
    id: str = Field("CHG-01")
    plate_number: str = Field("59-X1 123.45")
    hub_name: str = Field("Hub Ga Metro ĐHQG")
    port_id: str = Field("S03 (Trụ sạc nhanh)")
    current_charge: int = Field(65)
    target_charge: int = Field(100)
    power_consumed_kwh: float = Field(2.4)
    elapsed_minutes: int = Field(25)
    status: str = Field("Đang sạc")

class ReturnVehicleRequest(BaseModel):
    vehicle_id: str = Field(..., example="XE-024")
    hub_id: str = Field(..., example="hub-02")
    dock_id: Optional[str] = Field(None, example="DOCK-04")
    final_battery_level: Optional[int] = Field(75)

class ReturnVehicleResponse(BaseModel):
    success: bool = True
    message: str = "Xe đã được khóa chốt tại Hub thành công!"
    invoice_id: str = "INV-2026-901"
    hub_id: str = "hub-02"
    hub_name: str = "Hub Đại học Bách khoa"
    dock_assigned: str = "Cọc đỗ số 04"
