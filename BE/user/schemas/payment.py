from pydantic import BaseModel, Field
from typing import List, Optional

class InvoiceItem(BaseModel):
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

class PaymentSubmitRequest(BaseModel):
    invoice_id: str
    method: str = Field(..., example="wallet", description="'wallet' | 'bank_transfer' | 'cash_guard'")
    account_number: Optional[str] = None

class PaymentProcessResult(BaseModel):
    success: bool
    transaction_id: str
    status: str = Field(..., example="completed")
    message: str
