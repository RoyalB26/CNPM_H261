from pydantic import BaseModel, Field
from typing import Optional, List

class UserVehicleItem(BaseModel):
    id: str = Field(..., example="VEH-01")
    type: str = Field(..., example="Xe máy điện")
    plate_number: str = Field(..., example="59-X1 123.45")
    model: str = Field("VinFast Klara S", example="VinFast Klara S")
    battery_type: str = Field("B48", example="B48")

class UserLoginRequest(BaseModel):
    phone: str = Field(..., example="0912345678", description="Số điện thoại đăng nhập")
    password: str = Field(..., example="123456", description="Mật khẩu tài khoản")

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., example="Nguyễn Văn A", description="Họ và tên")
    phone: str = Field(..., example="0912345678", description="Số điện thoại")
    email: str = Field(..., example="abc123@hcmut.edu.vn", description="Email hợp lệ")
    password: str = Field(..., example="123456", description="Mật khẩu")
    confirm_password: str = Field(..., example="123456", description="Xác nhận mật khẩu")

class ForgotPasswordRequest(BaseModel):
    phone_or_email: str = Field(..., example="abc123@hcmut.edu.vn", description="SĐT hoặc Email đã đăng ký")

class UserProfileResponse(BaseModel):
    id: str = Field(..., example="USR-001")
    full_name: str = Field(..., example="Nguyễn Văn A")
    email: str = Field(..., example="abc123@hcmut.edu.vn")
    phone: str = Field(..., example="0123456789")
    avatar_url: Optional[str] = None
    default_payment_method: str = Field("E-Wallet", example="E-Wallet")
    role: str = Field("End-User", example="End-User")
    vehicles: List[UserVehicleItem] = []

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    default_payment_method: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
