from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal, Optional, List

class UserVehicleItem(BaseModel):
    id: str = Field(..., example="VEH-01")
    type: str = Field(..., example="Xe máy điện")
    plate_number: str = Field(..., example="59-X1 123.45")
    model: str = Field("VinFast Klara S", example="VinFast Klara S")
    battery_type: str = Field("B48", example="B48")

class UserLoginRequest(BaseModel):
    """Dữ liệu đăng nhập bằng số điện thoại hoặc email và mật khẩu."""

    phone: Optional[str] = Field(
        None, strict=True, examples=["0123456789"],
        description="Số điện thoại đăng nhập; bắt buộc nếu không có email"
    )
    email: Optional[str] = Field(
        None, strict=True, examples=["abc123@hcmut.edu.vn"],
        description="Email đăng nhập; bắt buộc nếu không có số điện thoại"
    )
    password: str = Field(
        ..., min_length=1, strict=True, repr=False,
        description="Mật khẩu tài khoản, không được để trống"
    )

    @field_validator("phone", "email")
    @classmethod
    def validate_identifier(cls, value: Optional[str]) -> Optional[str]:
        """Bỏ khoảng trắng hai đầu và từ chối thông tin đăng nhập rỗng."""
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Số điện thoại hoặc email không được để trống")
        return value

    @model_validator(mode="after")
    def validate_credentials(self) -> "UserLoginRequest":
        """Yêu cầu ít nhất một thông tin định danh để kiểm tra tài khoản."""
        if self.phone is None and self.email is None:
            raise ValueError("Cần cung cấp số điện thoại hoặc email")
        return self

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., example="Nguyễn Văn A", description="Họ và tên")
    phone: str = Field(..., example="0912345678", description="Số điện thoại")
    email: str = Field(..., example="abc123@hcmut.edu.vn", description="Email hợp lệ")
    password: str = Field(..., example="123456", description="Mật khẩu")
    confirm_password: str = Field(..., example="123456", description="Xác nhận mật khẩu")

class ForgotPasswordRequest(BaseModel):
    phone_or_email: str = Field(..., example="abc123@hcmut.edu.vn", description="SĐT hoặc Email đã đăng ký")

class UserProfileResponse(BaseModel):
    """Thông tin hồ sơ và trạng thái dịch vụ hiện tại của người dùng mock."""

    id: str = Field(..., example="USR-001")
    full_name: str = Field(..., example="Nguyễn Văn A")
    email: str = Field(..., example="abc123@hcmut.edu.vn")
    phone: str = Field(..., example="0123456789")
    avatar_url: Optional[str] = None
    default_payment_method: str = Field("E-Wallet", example="E-Wallet")
    role: str = Field("End-User", example="End-User")
    vehicles: List[UserVehicleItem] = []
    active_services: dict[str, dict[str, str | int | float | None] | None] = Field(
        default_factory=dict,
        description="Trạng thái từng dịch vụ; giá trị null khi không sử dụng"
    )

class UserLoginResponse(BaseModel):
    """Kết quả đăng nhập thành công, giữ cấu trúc phản hồi API hiện tại."""

    success: Literal[True] = True
    token: str
    user: UserProfileResponse

class UserLoginErrorResponse(BaseModel):
    """Lỗi dữ liệu hoặc xác thực, không trả lại mật khẩu trong phản hồi."""

    success: Literal[False] = False
    message: str

class UpdateProfileRequest(BaseModel):
    """Chỉ cập nhật các trường được gửi; không chấp nhận null hoặc trường lạ."""

    model_config = ConfigDict(strict=True, extra="forbid")

    full_name: Optional[str] = None
    email: Optional[str] = Field(
        None, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
        description="Email có phần tên và tên miền, không chứa khoảng trắng"
    )
    phone: Optional[str] = None
    default_payment_method: Optional[str] = None

    @field_validator("full_name", "email", "phone", "default_payment_method", mode="before")
    @classmethod
    def validate_profile_value(cls, value: object) -> str:
        """Trường được gửi phải là chuỗi không rỗng, bỏ khoảng trắng hai đầu."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Thông tin cập nhật phải là chuỗi không rỗng")
        return value.strip()

    @model_validator(mode="after")
    def validate_changes(self) -> "UpdateProfileRequest":
        """Yêu cầu ít nhất một trường hợp lệ để cập nhật hồ sơ."""
        if not self.model_fields_set:
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật")
        return self

class UpdateProfileResponse(BaseModel):
    """Kết quả cập nhật thành công kèm toàn bộ hồ sơ hiện tại."""

    success: Literal[True] = True
    user: UserProfileResponse

class UpdateProfileErrorResponse(BaseModel):
    """Lỗi JSON hoặc dữ liệu cập nhật, không thay đổi hồ sơ hiện tại."""

    success: Literal[False] = False
    message: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
