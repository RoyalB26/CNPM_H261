from pydantic import BaseModel, Field
from typing import List, Optional

class BikeInfo(BaseModel):
    id: str = Field(..., example="XE-024")
    name: str = Field(..., example="Xe đạp điện")
    battery_level: int = Field(..., example=85, description="Phần trăm pin")
    status: str = Field("ready", example="Sẵn sàng")
    hourly_rate: int = Field(10000, description="Giá thuê theo giờ (VNĐ)")

class ChargingPortInfo(BaseModel):
    id: str = Field(..., example="S01")
    name: str = Field(..., example="Trụ sạc nhanh S01")
    power_kw: float = Field(7.4, description="Công suất sạc (kW)")
    is_available: bool = Field(True)
    status: str = Field("Sẵn sàng", example="Sẵn sàng")
    rate_per_kwh: int = Field(3500, description="Đơn giá điện (VNĐ/kWh)")
    time_slots: List[str] = ["10:00 – 11:00", "11:00 – 12:00", "14:00 – 15:00"]

class ParkingSlotInfo(BaseModel):
    id: str = Field(..., example="P-01")
    name: str = Field(..., example="Chỗ đỗ P-01")
    bay: str = Field("Dãy A", example="Dãy A")
    is_available: bool = Field(True)
    hourly_rate: int = Field(2500, description="Giá gửi xe (VNĐ/giờ)")

class BatterySwapOption(BaseModel):
    battery_type: str = Field(..., example="B48")
    name: str = Field(..., example="Pin chuẩn 48V-20Ah (Lithium-ion)")
    available_count: int = Field(6, description="Số pin đầy có sẵn")
    swap_fee: int = Field(25000, description="Phí đổi pin (VNĐ/pin)")

class HubPricingPolicy(BaseModel):
    rental_bike_hourly: int = 10000
    parking_hourly: int = 2500
    charging_kwh: int = 3500
    battery_swap_fee: int = 25000

class HubSummary(BaseModel):
    id: str = Field(..., example="hub-01")
    name: str = Field(..., example="Hub Ga Metro ĐHQG")
    address: str = Field(..., example="Khu đô thị ĐHQG - HCM")
    lat: float = Field(..., example=10.8753)
    lng: float = Field(..., example=106.8005)
    available_bikes: int = Field(5, description="Số xe đạp điện khả dụng")
    available_parking: int = Field(8, description="Số chỗ đỗ còn trống")
    available_chargers: int = Field(2, description="Số cổng sạc khả dụng")
    available_batteries: int = Field(6, description="Số pin đầy có sẵn")

class HubDetailResponse(HubSummary):
    bikes: List[BikeInfo] = []
    ports: List[ChargingPortInfo] = []
    slots: List[ParkingSlotInfo] = []
    batteries: List[BatterySwapOption] = []
    pricing: HubPricingPolicy = HubPricingPolicy()
    parking_slots: int = 8
    charging_ports: int = 2
    battery_swaps: int = 6

class SearchHubQuery(BaseModel):
    keyword: Optional[str] = None
    vehicle_type: Optional[str] = "bike"
    destination: Optional[str] = None

class RouteSuggestionRequest(BaseModel):
    origin_name: Optional[str] = None
    origin_lat: float = Field(..., example=10.8753)
    origin_lng: float = Field(..., example=106.8005)
    dest_name: Optional[str] = None
    dest_lat: float = Field(..., example=10.8805)
    dest_lng: float = Field(..., example=106.8055)
    vehicle_type: str = Field("bike", example="bike")

class RouteSuggestionResponse(BaseModel):
    origin_hub: HubSummary
    destination_hub: HubSummary
    distance_km: float = Field(..., example=2.1)
    estimated_minutes: int = Field(..., example=8)
    recommended_bike: Optional[BikeInfo] = None
    message: str = Field("Đã tìm thấy lộ trình Hub tối ưu nhất")
