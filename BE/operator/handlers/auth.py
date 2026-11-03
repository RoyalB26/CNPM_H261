"""Các API đăng nhập và xác thực hai bước của Operator."""

import json
import copy


from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


from ..store import db
from ..schemas.auth import (
    OperatorLoginRequest,
    OperatorLoginResponse,
    OperatorAuthErrorResponse,
    Operator2FARequest,
    OperatorProfile,
    OperatorTokenResponse,
)


async def login(request: Request) -> JSONResponse:
    """Kiểm tra dữ liệu đăng nhập và trả yêu cầu 2FA của luồng giả lập."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        err_data = OperatorAuthErrorResponse(
            status_code="400",
            error=1,
            detail="JSON không hợp lệ",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        req = OperatorLoginRequest.model_validate(body)
    except ValidationError:
        # Không đưa mật khẩu trong dữ liệu lỗi Pydantic vào response.
        err_data = OperatorAuthErrorResponse(
            status_code="422",
            error=1,
            detail="Dữ liệu đăng nhập không hợp lệ",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    response_data = OperatorLoginResponse(
        success=True,
        requires_2fa=True,
        email=req.email,
        message="Vui lòng nhập mã xác thực 6 chữ số từ Google Authenticator hoặc Email.",
    )
    return JSONResponse(
        content=response_data.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )


async def verify_2fa(request: Request) -> JSONResponse:
    """Kiểm tra dữ liệu 2FA và trả token, hồ sơ của luồng giả lập."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        err_data = OperatorAuthErrorResponse(
            status_code="400",
            error=1,
            detail="JSON không hợp lệ",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        req = Operator2FARequest.model_validate(body)
    except ValidationError:
        # Không đưa mã OTP trong dữ liệu lỗi Pydantic vào response.
        err_data = OperatorAuthErrorResponse(
            status_code="422",
            error=1,
            detail="Dữ liệu xác thực hai bước không hợp lệ",
        )
        return JSONResponse(
            content=err_data.model_dump(mode="json"),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Sao chép mẫu để bổ sung dữ liệu request mà không sửa seed trong db.
    auth_data = copy.deepcopy(db.operator_mock["auth"])

    profile_data = auth_data["profile"]
    profile_data["email"] = req.email
    profile = OperatorProfile.model_validate(profile_data)

    token_data = auth_data["token"]
    token_data["operator"] = profile
    token_resp = OperatorTokenResponse.model_validate(token_data)


    
    return JSONResponse(
        content=token_resp.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )



routes = [
    Route("/api/v1/operator/auth/login", login, methods=["POST"]),
    Route("/api/v1/operator/auth/verify-2fa", verify_2fa, methods=["POST"]),

]