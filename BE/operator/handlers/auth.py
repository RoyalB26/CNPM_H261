"""Các API đăng nhập và xác thực hai bước của Operator."""

import json

from pydantic import ValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

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

    profile = OperatorProfile(
        id="OP-001",
        full_name="Nhân viên 1",
        role="Nhân viên giám sát",
        email=req.email,
        shift="Ca chiều · 13:00 - 17:00",
        avatar_initials="OP",
    )
    token_resp = OperatorTokenResponse(
        access_token="mock-jwt-operator-session-token-99882",
        token_type="bearer",
        expires_in=28800,
        operator=profile,
    )
    return JSONResponse(
        content=token_resp.model_dump(mode="json"),
        status_code=status.HTTP_200_OK,
    )



routes = [
    Route("/api/v1/operator/auth/login", login, methods=["POST"]),
    Route("/api/v1/operator/auth/verify-2fa", verify_2fa, methods=["POST"]),

]