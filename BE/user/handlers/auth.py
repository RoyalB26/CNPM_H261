"""Handler kiểm tra hoạt động, đăng nhập và quản lý hồ sơ User."""

import json
import re
from uuid import uuid4
from shared.authentication import (
    ensure_accounts, find_account, issue_session, password_matches, password_hash, accounts,
)
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
    """Xác thực tài khoản và trả session, khởi tạo tài khoản seed nếu cần."""
    try:
        data = await request.json()
    except (ValueError, UnicodeError):
        return JSONResponse({"detail": "JSON không hợp lệ"}, status_code=400)
    try:
        credentials = UserLoginRequest.model_validate(data)
    except ValidationError:
        return JSONResponse({"detail": "Thông tin đăng nhập không hợp lệ"}, status_code=422)
    failure = ensure_accounts()
    if failure is not None:
        return failure
    account = find_account(credentials.email or credentials.phone, "user")
    if account is None or not password_matches(credentials.password, account["password_hash"]):
        return JSONResponse({"detail": "Sai tài khoản hoặc mật khẩu"}, status_code=401)
    profile = db.__dict__["user"] if account["id"] == db.__dict__["user"]["id"] else account["profile"]
    return JSONResponse(UserLoginResponse(
        token=issue_session(account),
        user=UserProfileResponse.model_validate(profile),
    ).model_dump(mode="json"))


async def api_register(request: Request) -> JSONResponse:
    """Lưu tài khoản mới với mật khẩu băm, từ chối email/số điện thoại trùng."""
    try:
        data = await request.json()
    except (ValueError, UnicodeError):
        return JSONResponse({"detail": "JSON không hợp lệ"}, status_code=400)
    required = ("full_name", "email", "phone", "password", "confirm_password")
    if not isinstance(data, dict) or any(
        not isinstance(data.get(k), str) or not data[k].strip() for k in required
    ):
        return JSONResponse({"detail": "Thiếu thông tin đăng ký"}, status_code=422)
    email = data["email"].strip().lower()
    phone = data["phone"].strip()
    if (not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or not re.fullmatch(r"\+?[0-9]{9,15}", phone)
            or len(data["password"]) < 8
            or data["password"] != data["confirm_password"]):
        return JSONResponse({"detail": "Email, số điện thoại hoặc mật khẩu không hợp lệ"}, status_code=422)
    failure = ensure_accounts()
    if failure is not None:
        return failure
    encoded = password_hash(data["password"])

    def change(candidate):
        if any(a.get("email") == email or a.get("phone") == phone for a in accounts(candidate)):
            return JSONResponse({"detail": "Email hoặc số điện thoại đã tồn tại"}, status_code=409)
        profile = UserProfileResponse(
            id="USR-" + uuid4().hex, full_name=data["full_name"].strip(),
            email=email, phone=phone, vehicles=[], active_services={},
        ).model_dump(mode="json")
        candidate.operator_mock["accounts"].append(dict(
            id=profile["id"], role="user", email=email, phone=phone,
            password_hash=encoded, profile=profile,
        ))
        return JSONResponse({"success": True, "message": "Đăng ký thành công", "user": profile}, status_code=201)

    return persist_change(change)


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
        if 'email' in changes:
            changes['email'] = changes['email'].lower()
        if any(account['id'] != candidate.user['id'] and (
            ('email' in changes and account.get('email') == changes['email'])
            or ('phone' in changes and account.get('phone') == changes['phone'])
        ) for account in accounts(candidate)):
            return JSONResponse({'detail': 'Email hoặc số điện thoại đã tồn tại'}, status_code=409)
        # Kiểm tra và tạo phản hồi trước khi ghi để tránh cập nhật dở dang.
        updated_user = UserProfileResponse.model_validate({**candidate.user, **changes})
        response = UpdateProfileResponse(success=True, user=updated_user)
        result = JSONResponse(response.model_dump(mode="json", exclude_unset=True))
        candidate.user.update(changes)
        for account in accounts(candidate):
            if account['id'] == candidate.user['id']:
                account.update(email=candidate.user['email'], phone=candidate.user['phone'])
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
