from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import List, Literal, Optional

class InvoiceItem(BaseModel):
    """Một khoản phí; nhãn hiển thị tương thích với FE hiện tại."""

    label: Optional[str] = None
    description: str = Field(..., example="Thời gian sử dụng: 45 phút")
    amount: int = Field(..., ge=0, example=15000)

class InvoiceResponse(BaseModel):
    """Hóa đơn từ dữ liệu nghiệp vụ; không tự bổ sung mã, giá hoặc thời gian mẫu."""

    id: str = Field(..., example="INV-2026-901")
    user_id: Optional[str] = Field(None, min_length=1)
    service_type: Literal["rental", "charging", "battery_swap", "parking"]
    title: str = Field(..., example="Hóa đơn thuê xe điện")
    reference_id: str
    items: List[InvoiceItem] = Field(default_factory=list)
    total_amount: int = Field(..., ge=0)
    payment_channel: Literal["online", "cash_guard"]
    status: Literal["unpaid", "pending", "paid", "failed"]
    created_at: str
    transaction_id: Optional[str] = None
    paid_at: Optional[str] = None
    payment_method: Optional[Literal["wallet", "bank_transfer"]] = None

class InvoiceQuery(BaseModel):
    """Bộ chọn hóa đơn; từ chối loại dịch vụ hoặc bộ lọc không phù hợp."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    invoice_type: Literal["rental", "charging", "swap", "battery_swap", "parking"] = Field("rental", alias="type")
    booking_id: Optional[str] = Field(None, min_length=1)
    trip_id: Optional[str] = Field(None, min_length=1)
    session_id: Optional[str] = Field(None, min_length=1)
    invoice_id: Optional[str] = Field(None, min_length=1)

    @model_validator(mode="after")
    def validate_selectors(self) -> "InvoiceQuery":
        """Không bỏ qua nhầm trip/session khi client chọn sai loại hóa đơn."""
        if self.trip_id is not None and self.invoice_type != "rental":
            raise ValueError("trip_id chỉ dùng cho hóa đơn thuê xe")
        if self.session_id is not None and self.invoice_type != "charging":
            raise ValueError("session_id chỉ dùng cho hóa đơn sạc")
        return self

class PaymentSubmitRequest(BaseModel):
    """Yêu cầu thanh toán; số tiền chính thức luôn lấy từ hóa đơn Backend."""

    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    invoice_id: str = Field(..., min_length=1)
    method: Literal["wallet", "bank_transfer", "cash_guard"]
    amount: Optional[int] = Field(None, ge=0)
    account_number: Optional[str] = None
    simulate: bool = Field(False, description="Thanh toán demo, không trừ tiền thật")

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value: object) -> object:
        """Chấp nhận tên phương thức mà FE hiện tại đang gửi."""
        if isinstance(value, str):
            value = value.strip()
            return {"Ví điện tử": "wallet", "Thẻ ngân hàng": "bank_transfer"}.get(value, value)
        return value

class PaymentProcessResult(BaseModel):
    """Xác nhận giao dịch mô phỏng đã được ghi nhận trong store."""

    success: Literal[True] = True
    transaction_id: str
    status: Literal["completed", "pending"] = "completed"
    payment_url: Optional[str] = None
    expires_at: Optional[str] = None
    message: str
    is_simulated: bool = False

class PaymentErrorResponse(BaseModel):
    """Lỗi thanh toán, chưa thay đổi trạng thái hóa đơn."""

    success: Literal[False] = False
    error: str
