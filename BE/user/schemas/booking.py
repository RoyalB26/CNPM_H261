from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing import Annotated, List, Literal, Optional


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
        return self

class BookingResponse(BaseModel):
    """Bản ghi đặt trước theo cấu trúc hiện tại của store dùng chung."""

    id: str = Field(..., example="EMH-1024")
    hub_id: str = Field(..., examples=["hub-01"])
    plan_type: BookingPlanType = Field(..., examples=["personal"])
    hub_name: str = Field(..., example="Hub Ga Metro ĐHQG")
    destination_hub_name: Optional[str] = None
    personal_plate: Optional[str] = None
    resource_name: Optional[str] = None
    services: List[BookingServiceItem]
    status: str = Field(..., examples=["Đã xác nhận"])
    hold_until: str = Field(..., examples=["08:10"])
    created_at: str
    price: int = Field(..., ge=0, description="Giá do Backend xác định, đơn vị VNĐ")

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
