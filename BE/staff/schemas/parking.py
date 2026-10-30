"""
Security Guard & Hub Personal Vehicle Parking Schemas
Smart E-Mobility Hub - ĐHQG-HCM (Screens 11, 12, 13)
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class VehicleCheckInRequest(BaseModel):
    license_plate: str = Field(..., example="59-B2 123.45")
    parking_bay: str = Field("Dãy A", example="Dãy A")
    parking_slot: str = Field("Ô số 018", example="Ô số 018")
    hub_name: str = Field("Hub KTX Khu A", example="Hub KTX Khu A")
    guard_id: str = Field("SG-02", example="SG-02")


class VehicleCheckInResponse(BaseModel):
    success: bool = True
    ticket_code: str = Field(..., example="SG-20261022-018")
    license_plate: str = Field(..., example="59-B2 123.45")
    bay_slot: str = Field(..., example="Dãy A · Ô số 018")
    checkin_time: str = Field(..., example="22/10/2026 · 14:36")
    status_message: str = Field("Thông tin đã sẵn sàng · Đã ghi nhận xe vào bãi")


class VehicleCheckOutLookup(BaseModel):
    ticket_code_or_plate: str = Field(..., example="59-B2 123.45")


class VehicleCheckOutResponse(BaseModel):
    ticket_code: str = Field("SG-20261022-018", example="SG-20261022-018")
    license_plate: str = Field("59-B2 123.45", example="59-B2 123.45")
    checkin_time: str = Field("22/10/2026 · 14:36", example="22/10/2026 · 14:36")
    checkout_time: str = Field("22/10/2026 · 16:42", example="22/10/2026 · 16:42")
    duration_str: str = Field("2 giờ 06 phút", example="2 giờ 06 phút")
    total_fee_vnd: int = Field(25000, example=25000)
    payment_method: str = Field("Tiền mặt tại quầy", example="Tiền mặt tại quầy")
    is_paid: bool = False


class ParkingTransactionItem(BaseModel):
    seq_number: str = Field(..., example="01")
    license_plate: str = Field(..., example="59-B2 123.45")
    time_info: str = Field(..., example="14:36 · 2 giờ 06 phút")
    amount_vnd: int = Field(25000, example=25000)


class ShiftReconciliationSummary(BaseModel):
    shift_title: str = Field("Ca chiều · 13:00 - 17:00", example="Ca chiều")
    shift_date: str = Field("22/10/2026", example="22/10/2026")
    hub_name: str = Field("Hub KTX Khu A", example="Hub KTX Khu A")
    total_vehicles_served: int = Field(48, example=48)
    total_cash_collected_vnd: int = Field(1200000, example=1200000)
    transactions: List[ParkingTransactionItem]
    is_closed: bool = False


class ShiftCloseRequest(BaseModel):
    guard_id: str = Field(..., example="SG-02")
    total_cash_deposited_vnd: int = Field(1200000, example=1200000)
    note: Optional[str] = Field("Đã bàn giao tiền mặt đầy đủ cho ca tối", example="Đã bàn giao tiền mặt")
