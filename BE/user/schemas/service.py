from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal, Optional

from .booking import NonEmptyString

class TimeLog(BaseModel):
    label: str = Field(..., example="Đặt xe")
    time: str = Field(..., example="08:00")

class StartRideRequest(BaseModel):
    """Mã booking lấy từ URL để nhận xe, không yêu cầu body JSON."""

    model_config = ConfigDict(strict=True)

    booking_id: NonEmptyString = Field(..., examples=["EMH-1024"])

class ActiveRideResponse(BaseModel):
    """Thông tin chuyến đi đang hoạt động theo dữ liệu thực tế của store."""

    model_config = ConfigDict(strict=True)

    trip_id: str = Field(..., min_length=1, examples=["TRIP-8821"])
    vehicle_id: str = Field(..., min_length=1, examples=["XE-024"])
    origin_hub: str = Field(..., min_length=1, examples=["Hub Ga Metro ĐHQG"])
    destination_hub: Optional[str] = Field(..., examples=["Hub Đại học Bách khoa"])
    elapsed_minutes: int = Field(..., ge=0)
    battery_level: int = Field(..., ge=0, le=100, description="Mức pin hiện tại, đơn vị %")
    status: Literal["Đang sử dụng"]

class StartRideResponse(BaseModel):
    """Kết quả nhận xe thành công kèm chuyến đi vừa được tạo."""

    success: Literal[True] = True
    ride: ActiveRideResponse

class ActiveParkingResponse(BaseModel):
    """Phiên gửi xe hiện tại, giữ mã vé và dữ liệu thực tế trong store."""

    model_config = ConfigDict(strict=True)

    ticket_id: str = Field(..., min_length=1, examples=["PRK-901"])
    plate_number: str = Field(..., min_length=1, examples=["59-X1 123.45"])
    hub_name: str = Field(..., min_length=1, examples=["Hub Ga Metro ĐHQG"])
    slot_id: str = Field(..., min_length=1, examples=["P08"])
    checkin_time: str = Field(..., min_length=1, examples=["10:00"])
    elapsed_minutes: int = Field(..., ge=0)

class ActiveChargingResponse(BaseModel):
    """Phiên sạc hiện tại; không tự thêm biển số, Hub hoặc thời gian mẫu."""

    model_config = ConfigDict(strict=True)

    session_id: str = Field(..., min_length=1, examples=["CHG-302"])
    port_id: str = Field(..., min_length=1, examples=["S03"])
    power_consumed_kwh: float = Field(..., ge=0, allow_inf_nan=False)
    current_charge: int = Field(..., ge=0, le=100, description="Mức sạc hiện tại, đơn vị %")
    status: str = Field(..., min_length=1, examples=["Đang sạc"])

class ActiveServicesResponse(BaseModel):
    """Các dịch vụ hiện tại; từng dịch vụ có thể vắng mặt hoặc bằng null."""

    model_config = ConfigDict(strict=True)

    ride: Optional[ActiveRideResponse] = None
    parking: Optional[ActiveParkingResponse] = None
    charging: Optional[ActiveChargingResponse] = None

class ReturnVehicleRequest(BaseModel):
    """Nhận mã xe/Hub từ FE hoặc mã chuyến/tên Hub từ request cũ."""

    model_config = ConfigDict(strict=True)

    vehicle_id: Optional[NonEmptyString] = Field(None, examples=["XE-031"])
    trip_id: Optional[NonEmptyString] = Field(None, examples=["TRIP-8821"])
    hub_id: Optional[NonEmptyString] = Field(None, examples=["hub-02"])
    hub_name: Optional[NonEmptyString] = Field(None, examples=["Hub Đại học Bách khoa"])
    force_error: bool = Field(False, description="Mô phỏng lỗi trả xe khi kiểm thử")
    simulate_error: bool = Field(False, description="Tên tương thích của cờ mô phỏng lỗi")

    @model_validator(mode="after")
    def validate_identifiers(self) -> "ReturnVehicleRequest":
        """Yêu cầu định danh xe/chuyến đi và Hub, không tự dùng dữ liệu seed."""
        if self.vehicle_id is None and self.trip_id is None:
            raise ValueError("Cần cung cấp vehicle_id hoặc trip_id")
        if self.hub_id is None and self.hub_name is None:
            raise ValueError("Cần cung cấp hub_id hoặc hub_name")
        return self

class ReturnVehicleResponse(BaseModel):
    """Kết quả trả xe thực tế của store, không tạo thêm hóa đơn hoặc cọc đỗ mẫu."""

    model_config = ConfigDict(strict=True)

    success: Literal[True] = True
    trip_id: NonEmptyString
    vehicle_id: NonEmptyString
    return_hub_name: NonEmptyString
    elapsed_minutes: int = Field(..., ge=0)
    total_fee: int = Field(..., ge=0, description="Phí dịch vụ do Backend xác định, đơn vị VNĐ")

class ReturnVehicleErrorResponse(BaseModel):
    """Lỗi đầu vào, định danh mâu thuẫn hoặc chưa đủ điều kiện trả xe."""

    success: Literal[False] = False
    error: str
