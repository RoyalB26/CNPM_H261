"""
Operator Authentication Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import Optional
from pydantic import BaseModel, Field


class OperatorLoginRequest(BaseModel):
    email: str = Field(..., example="admin@e-mobility.com")
    password: str = Field(..., min_length=6, example="operator123")

class OperatorLoginResponse(BaseModel):
    """Kết quả tiếp nhận đăng nhập và yêu cầu xác thực hai bước."""

    success: bool = Field(..., examples=[True])
    requires_2fa: bool = Field(..., examples=[True])
    email: str = Field(
        ...,
        examples=["admin@e-mobility.com"],
    )
    message: str = Field(
        ...,
        examples=["Vui lòng nhập mã xác thực 6 chữ số."],
    )


class OperatorAuthErrorResponse(BaseModel):
    """Thông báo lỗi của API đăng nhập và xác thực hai bước."""

    status_code: str = Field(..., examples=["400"])
    error: int = Field(..., examples=[1])
    detail: str = Field(
        ...,
        examples=["JSON không hợp lệ"],
    )

class Operator2FARequest(BaseModel):
    email: str = Field(..., example="admin@e-mobility.com")
    otp_code: str = Field(..., min_length=6, max_length=6, example="849201")
    remember_device: Optional[bool] = Field(default=True)


class OperatorProfile(BaseModel):
    id: str = Field(..., example="OP-001")
    full_name: str = Field(..., example="Nhân viên 1")
    role: str = Field(..., example="Nhân viên giám sát")
    email: str = Field(..., example="admin@e-mobility.com")
    shift: str = Field(..., example="Ca chiều · 13:00 - 17:00")
    avatar_initials: str = Field(default="OP")


class OperatorTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800
    operator: OperatorProfile
