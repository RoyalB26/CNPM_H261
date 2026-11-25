"""Đăng nhập Operator bằng mật khẩu và TOTP, challenge dùng một lần."""
import json
import secrets
import time
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from shared.authentication import (
    ensure_accounts, find_account, password_matches, issue_session,
    challenges, totp,
)
from ..store import persist_change
from ..schemas.auth import OperatorLoginRequest, Operator2FARequest


def error(code, detail):
    return JSONResponse({"status_code": str(code), "error": 1, "detail": detail}, status_code=code)


async def parse(request, model):
    try:
        body = await request.json()
    except (ValueError, UnicodeError):
        return None, error(400, "JSON không hợp lệ")
    try:
        return model.model_validate(body), None
    except ValidationError:
        return None, error(422, "Dữ liệu xác thực không hợp lệ")


async def login(request: Request):
    req, failure = await parse(request, OperatorLoginRequest)
    if failure is not None:
        return failure
    failure = ensure_accounts()
    if failure is not None:
        return failure
    account = find_account(req.email, "operator")
    if account is None or not password_matches(req.password, account["password_hash"]):
        return error(401, "Sai tài khoản hoặc mật khẩu")
    now = time.time()
    for key in list(challenges):
        if challenges[key]["expires_at"] <= now:
            del challenges[key]
    challenge_id = secrets.token_urlsafe(32)
    challenges[challenge_id] = {
        "account_id": account["id"], "expires_at": now + 300, "attempts": 0,
    }
    return JSONResponse({
        "success": True, "requires_2fa": True, "email": account["email"],
        "challenge_id": challenge_id, "expires_in": 300,
        "message": "Nhập mã TOTP từ ứng dụng Authenticator.",
    })


async def verify_2fa(request: Request):
    req, failure = await parse(request, Operator2FARequest)
    if failure is not None:
        return failure
    challenge = challenges.get(req.challenge_id)
    account = find_account(req.email, "operator")
    if (not challenge or challenge["expires_at"] <= time.time()
            or challenge["attempts"] >= 5 or account is None
            or challenge["account_id"] != account["id"]):
        return error(401, "Yêu cầu 2FA không hợp lệ hoặc hết hạn")
    challenge["attempts"] += 1
    step = int(time.time() // 30)
    matched = next((s for s in (step - 1, step, step + 1)
                    if s > account["last_totp_step"]
                    and secrets.compare_digest(totp(account["totp_secret"], s), req.otp_code)), None)
    if matched is None:
        return error(401, "OTP không hợp lệ hoặc đã sử dụng")

    def change(candidate):
        target = next(a for a in candidate.operator_mock["accounts"] if a["id"] == account["id"])
        target["last_totp_step"] = matched

    failure = persist_change(change)
    if failure is not None:
        return failure
    challenges.pop(req.challenge_id, None)
    return JSONResponse({
        "access_token": issue_session(account), "token_type": "bearer",
        "expires_in": 28800, "operator": account["profile"],
    })


routes = [
    Route("/api/v1/operator/auth/login", login, methods=["POST"]),
    Route("/api/v1/operator/auth/verify-2fa", verify_2fa, methods=["POST"]),
]
