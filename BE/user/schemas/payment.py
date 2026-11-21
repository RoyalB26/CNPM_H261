from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Literal, Optional

class InvoiceItem(BaseModel):
    """Một khoản phí; nhãn hiển thị tương thích với FE hiện tại."""

    label: Optional[str] = None
    description: str = Field(..., example="Thời gian sử dụng: 45 phút")
    amount: int = Field(..., example=15000)

class InvoiceResponse(BaseModel):
    id: str = Field(..., example="INV-2026-901")
    service_type: str = Field(..., example="rental", description="'rental' | 'charging' | 'battery_swap' | 'parking'")
    title: str = Field(..., example="Hóa đơn thuê xe điện")
    reference_id: str = Field("XE-024")
    items: List[InvoiceItem] = []
    total_amount: int = Field(15000)
    payment_channel: str = Field("online", description="'online' (E-Wallet/Banking) hoặc 'cash_guard' (Bảo vệ)")
    status: str = Field("unpaid", description="'unpaid' | 'pending' | 'paid' | 'failed'")
    created_at: str = Field("18/10/2026 10:45")
    transaction_id: Optional[str] = None
    paid_at: Optional[str] = None
    payment_method: Optional[Literal["wallet", "bank_transfer"]] = None

class PaymentSubmitRequest(BaseModel):
    """Yêu cầu thanh toán; số tiền chính thức luôn lấy từ hóa đơn Backend."""

    model_config = ConfigDict(strict=True, str_strip_whitespace=True)

    invoice_id: str = Field(..., min_length=1)
    method: Literal["wallet", "bank_transfer", "cash_guard"]
    amount: Optional[int] = Field(None, ge=0)
    account_number: Optional[str] = None

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
    status: Literal["completed"] = "completed"
    message: str

class PaymentErrorResponse(BaseModel):
    """Lỗi thanh toán, chưa thay đổi trạng thái hóa đơn."""

    success: Literal[False] = False
    error: str
