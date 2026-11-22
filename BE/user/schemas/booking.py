from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing import Annotated, List, Literal, Optional
from .payment import InvoiceResponse


BookingPlanType = Literal["rental", "personal", "swap", "parking", "charging", "battery_swap"]
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

class BookingServiceItem(BaseModel):
    """Thông tin một dịch vụ; giá ước tính không thay thế giá tính bởi Backend."""

    model_config = ConfigDict(strict=True)

    service_type: BookingPlanType = Field(..., examples=["parking"])
    detail: NonEmptyString = Field(..., examples=["Chỗ đỗ · 10:00 – 12:00"])
    resource_id: Optional[str] = Field(None, example="XE-024 hoặc S03")
    time_slot: Optional[str] = None
    price_est: int = Field(0, ge=0)

class CreateBookingRequest(BaseModel):
    """Dữ liệu tạo đặt trước, kiểm tra định dạng trước khi thay đổi tài nguyên."""

    model_config = ConfigDict(strict=True)

    plan_type: BookingPlanType = Field(..., examples=["personal"])
    hub_id: NonEmptyString = Field(..., examples=["hub-01"])
    destination_hub_id: Optional[str] = Field(None, example="hub-02", description="Chỉ dùng khi thuê xe")
    destination_hub_name: Optional[str] = Field(None, example="Hub Đại học Bách khoa")
    personal_plate: Optional[str] = Field(None, example="59-X1 123.45")
    resource_id: Optional[str] = None

    resource_name: Optional[NonEmptyString] = None
    selected_bike: Optional[str] = None
    parking_slot: Optional[str] = None
    charging_port: Optional[str] = None
    battery_type: Optional[str] = None
    battery_quantity: int = Field(1, gt=0)
    duration_hours: int = Field(2, gt=0)
    arrival_time: Optional[str] = None
    services: List[BookingServiceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rental_resource(self) -> "CreateBookingRequest":
        """Booking thuê xe cần tên tài nguyên mà store hiện dùng để xác định xe."""
        if self.plan_type == "rental" and self.resource_name is None:
            raise ValueError("Đặt thuê xe cần cung cấp resource_name")
        if self.plan_type == "rental":
            bike_id = self.resource_name.split(" · ")[0].strip()
            if any(value is not None and value != bike_id for value in (self.resource_id, self.selected_bike)):
                raise ValueError("Các mã xe không khớp nhau")
        if self.plan_type == "parking" and self.parking_slot and self.resource_id and self.parking_slot != self.resource_id:
            raise ValueError("Các mã chỗ đỗ không khớp nhau")
        if self.plan_type == "parking" and (not self.personal_plate or not self.personal_plate.strip()):
            raise ValueError("Đặt chỗ gửi xe cần biển số")
        if self.plan_type == "charging":
            if not self.personal_plate or not self.personal_plate.strip():
                raise ValueError("Đặt cổng sạc cần biển số")
            if self.arrival_time is not None or any(s.time_slot is not None for s in self.services):
                raise ValueError("Bản demo chỉ giữ cổng ngay, chưa hỗ trợ lịch theo khung giờ")
        return self

class RentalTripHistory(BaseModel):
    """Thông tin chuyến đi lưu trong booking, tương thích phiên seed thiếu mốc bắt đầu."""

    trip_id: str
    booking_id: str
    vehicle_id: str
    origin_hub: str
    destination_hub: Optional[str]
    destination_hub_id: Optional[str] = None
    elapsed_minutes: int = Field(..., ge=0)
    battery_level: int = Field(..., ge=0, le=100)
    status: Literal["Đang sử dụng", "Hoàn thành"]
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    return_hub_id: Optional[str] = None
    return_hub_name: Optional[str] = None
    hourly_rate: Optional[int] = Field(None, ge=0)
    total_fee: Optional[int] = Field(None, ge=0)
    billing_source: Optional[Literal["started_at", "legacy_elapsed_minutes"]] = None

class ChargingSessionHistory(BaseModel):
    """Thông tin phiên sạc đã lưu, gồm điện năng mô phỏng và đơn giá chốt."""

    session_id: str
    booking_id: Optional[str] = None
    port_id: str
    hub_id: Optional[str] = None
    hub_name: Optional[str] = None
    plate_number: Optional[str] = None
    power_consumed_kwh: float = Field(..., ge=0, allow_inf_nan=False)
    current_charge: int = Field(..., ge=0, le=100)
    status: str
    rate_per_kwh: Optional[int] = Field(None, ge=0)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    elapsed_minutes: Optional[int] = Field(None, ge=0)
    measurement_source: Optional[Literal["mock_input"]] = None

class BookingResponse(BaseModel):
    """Bản ghi đặt trước theo cấu trúc hiện tại của store dùng chung."""

    id: str = Field(..., example="EMH-1024")
    hub_id: str = Field(..., examples=["hub-01"])
    plan_type: BookingPlanType = Field(..., examples=["personal"])
    hub_name: str = Field(..., example="Hub Ga Metro ĐHQG")
    destination_hub_name: Optional[str] = None
    destination_hub_id: Optional[str] = None
    personal_plate: Optional[str] = None
    resource_name: Optional[str] = None
    services: List[BookingServiceItem]
    status: str = Field(..., examples=["Đã xác nhận"])
    hold_until: str = Field(..., examples=["08:10"])
    created_at: str
    price: int = Field(..., ge=0, description="Giá do Backend xác định, đơn vị VNĐ")
    rental_trip: Optional[RentalTripHistory] = None
    rental_invoice: Optional[InvoiceResponse] = None
    expires_at: Optional[str] = None
    expired_at: Optional[str] = None
    parking_slot: Optional[str] = None
    resource_id: Optional[str] = None
    battery_type: Optional[str] = None
    battery_quantity: Optional[int] = Field(None, gt=0)
    swap_unit_price: Optional[int] = Field(None, ge=0)
    completed_at: Optional[str] = None
    battery_swap_invoice: Optional[InvoiceResponse] = None
    charging_port: Optional[str] = None
    charging_rate_per_kwh: Optional[int] = Field(None, ge=0)
    charging_session: Optional[ChargingSessionHistory] = None
    charging_invoice: Optional[InvoiceResponse] = None

class CompleteSwapRequest(BaseModel):
    """Mã booking đổi pin lấy từ URL, không nhận giá hoặc số lượng mới."""

    model_config = ConfigDict(strict=True)
    booking_id: NonEmptyString

class CompleteSwapResponse(BaseModel):
    """Booking hoàn thành và hóa đơn tính theo pin đã giữ."""

    success: Literal[True] = True
    booking: BookingResponse
    invoice: InvoiceResponse

class ExpireBookingsResponse(BaseModel):
    """Kết quả xử lý booking thuê xe/gửi xe quá thời hạn nhận tài nguyên."""

    success: Literal[True] = True
    expired_booking_ids: list[str]
    expired_count: int = Field(..., ge=0)

class BookingErrorResponse(BaseModel):
    """Lỗi dữ liệu đầu vào hoặc xung đột trạng thái khi xử lý đặt trước."""

    success: Literal[False] = False
    error: str

class CancelBookingRequest(BaseModel):
    """Mã booking lấy từ URL; API hủy không yêu cầu body JSON."""

    model_config = ConfigDict(strict=True)

    booking_id: NonEmptyString = Field(..., examples=["EMH-1024"])

class CancelBookingResponse(BaseModel):
    """Kết quả hủy thành công kèm bản ghi booking đã cập nhật."""

    success: Literal[True] = True
    booking: BookingResponse

class CancelBookingNotFoundResponse(BaseModel):
    """Lỗi không tìm thấy booking, giữ cấu trúc phản hồi 404 hiện tại."""

    error: str
