"""Handler kiểm tra hoạt động, đăng nhập và quản lý hồ sơ User."""

import json
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from shared.database import db, persist_change
from user.schemas import (
    UserLoginRequest,
    UserLoginResponse,
    UserLoginErrorResponse,
    UserProfileResponse,
    UserVehicleItem,
    UpdateProfileRequest,
    UpdateProfileResponse,
    UpdateProfileErrorResponse,
)


async def api_health(request):
    return JSONResponse({"status": "ok", "app": "Smart E-Mobility Hub Backend"})


async def api_login(request: Request) -> JSONResponse:
    """Kiểm tra dữ liệu đăng nhập và xác thực tài khoản mock, không đổi store.

    Trả 400 nếu JSON lỗi, 422 nếu sai schema, 401 nếu sai tài khoản hoặc
    mật khẩu; trả 200 kèm token và hồ sơ khi đăng nhập thành công.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            UserLoginErrorResponse(message="Dữ liệu JSON không hợp lệ").model_dump(mode="json"),
            status_code=400
        )

    try:
        credentials = UserLoginRequest.model_validate(data)
    except ValidationError:
        # Không đính kèm dữ liệu lỗi vì có thể chứa mật khẩu người dùng.
        return JSONResponse(
            UserLoginErrorResponse(
                message="Cần cung cấp số điện thoại hoặc email và mật khẩu không rỗng, đúng kiểu dữ liệu"
            ).model_dump(mode="json"),
            status_code=422
        )

    valid_user = (
        (credentials.phone is not None and credentials.phone == db.user["phone"])
        or (credentials.email is not None and credentials.email == db.user["email"])
    )

    if not valid_user or credentials.password != "123456":
        return JSONResponse(
            UserLoginErrorResponse(message="Sai tài khoản hoặc mật khẩu").model_dump(mode="json"),
            status_code=401
        )

    response = UserLoginResponse(
        token="jwt-token-sample-mock-123456",
        user=UserProfileResponse.model_validate(db.user)
    )
    return JSONResponse(response.model_dump(mode="json"))


async def api_register(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    return JSONResponse({
        "success": True,
        "message": "Đăng ký tài khoản thành công",
        "user": {
            "id": "USR-002",
            "full_name": data.get("full_name", "Người dùng mới"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "role": "End-User"
        }
    })


async def api_get_profile(request: Request) -> JSONResponse:
    """Trả hồ sơ người dùng mock sau khi kiểm tra qua schema.

    Giữ phương tiện cá nhân, dịch vụ hiện tại và trường null; không thêm
    giá trị mặc định cho trường vắng mặt và không thay đổi store.
    """
    response = UserProfileResponse.model_validate(db.get_user_profile())
    return JSONResponse(response.model_dump(mode="json", exclude_unset=True))


async def api_update_profile(request: Request) -> JSONResponse:
    """Kiểm tra toàn bộ dữ liệu trước khi cập nhật các trường hồ sơ cho phép.

    Trả 400 nếu JSON lỗi, 422 nếu thiếu hoặc sai dữ liệu; trả 200 kèm hồ
    sơ khi thành công. Trường không được gửi giữ nguyên giá trị hiện tại.
    """
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            UpdateProfileErrorResponse(message="Dữ liệu JSON không hợp lệ").model_dump(mode="json"),
            status_code=400
        )

    try:
        profile_request = UpdateProfileRequest.model_validate(data)
    except ValidationError:
        return JSONResponse(
            UpdateProfileErrorResponse(message="Dữ liệu cập nhật hồ sơ không hợp lệ").model_dump(mode="json"),
            status_code=422
        )

    def change(candidate):
        changes = profile_request.model_dump(exclude_unset=True)
        # Kiểm tra và tạo phản hồi trước khi ghi để tránh cập nhật dở dang.
        updated_user = UserProfileResponse.model_validate({**candidate.user, **changes})
        response = UpdateProfileResponse(success=True, user=updated_user)
        result = JSONResponse(response.model_dump(mode="json", exclude_unset=True))
        candidate.user.update(changes)
        return result

    return persist_change(change)


async def api_get_user_vehicles(request: Request) -> JSONResponse:
    """Trả danh sách phương tiện cá nhân sau khi kiểm tra từng xe qua schema.

    Giữ thứ tự và các trường đang có; trả mảng rỗng khi chưa có xe, không
    thêm giá trị mẫu cho trường vắng mặt và không thay đổi store.
    """
    vehicles: list[UserVehicleItem] = [
        UserVehicleItem.model_validate(vehicle) for vehicle in db.get_user_vehicles()
    ]
    return JSONResponse([
        vehicle.model_dump(mode="json", exclude_unset=True) for vehicle in vehicles
    ])
