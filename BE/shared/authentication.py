"""Tài khoản lưu cùng runtime, session opaque và TOTP RFC 6238."""
import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from urllib.parse import urlencode

from starlette.responses import JSONResponse
from .database import db, persist_change
from .identity import current_user_id

sessions = {}
challenges = {}
SESSION_SECONDS = 28800


def password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000)
    return f"pbkdf2_sha256$600000${salt}${digest.hex()}"


def password_matches(password, encoded):
    algorithm, rounds, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
    return algorithm == "pbkdf2_sha256" and hmac.compare_digest(actual.hex(), expected)


def accounts(store=db):
    return store.operator_mock.get("accounts", [])


def initialize_accounts(store):
    """Di trú runtime cũ một lần, giữ hồ sơ và dữ liệu dịch vụ seed."""
    if "accounts" in store.operator_mock:
        return
    profile = store.__dict__["user"]
    operator = dict(store.operator_mock["auth"]["profile"])
    operator.setdefault("email", "admin@e-mobility.com")
    store.operator_mock["accounts"] = [
        dict(id=profile["id"], role="user", email=profile["email"].lower(),
             phone=profile["phone"], password_hash=password_hash("123456"), profile=profile),
        dict(id=operator["id"], role="operator", email=operator["email"].lower(),
             password_hash=password_hash(os.environ.get("OPERATOR_PASSWORD", "operator123")),
             totp_secret=base64.b32encode(secrets.token_bytes(20)).decode(),
             last_totp_step=-1, profile=operator),
        dict(id="STF-02", role="staff", username="staff_b",
             password_hash=password_hash(os.environ.get("STAFF_PASSWORD", "staff123")),
             profile={}),
    ]

    add_staff_accounts(store)


def add_staff_accounts(store):
    existing = {a["id"] for a in accounts(store)}
    for person in store.staff:
        if person["id"] not in existing:
            store.operator_mock["accounts"].append(dict(
                id=person["id"], role="staff",
                username="staff_" + person["id"].split("-")[-1].lower(),
                password_hash=password_hash(os.environ.get("STAFF_PASSWORD", "staff123")),
                profile={},
            ))


def ensure_accounts():
    if "accounts" not in db.operator_mock:
        return persist_change(initialize_accounts)
    existing = {a["id"] for a in accounts()}
    if any(person["id"] not in existing for person in db.staff):
        return persist_change(add_staff_accounts)


def find_account(identifier, role):
    return next((a for a in accounts() if a["role"] == role and
                 identifier.strip().lower() in
                 (a.get("email"), a.get("phone"), a.get("username"))), None)


def issue_session(account):
    token = secrets.token_urlsafe(32)
    sessions[hashlib.sha256(token.encode()).hexdigest()] = {
        "id": account["id"], "role": account["role"],
        "expires_at": time.time() + SESSION_SECONDS,
    }
    return token


def totp(secret, step=None):
    counter = int(time.time() // 30) if step is None else step
    digest = hmac.new(base64.b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    return f"{(struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000:06d}"


def provisioning_uri(account):
    return "otpauth://totp/SmartHub:" + account["email"] + "?" + urlencode({
        "secret": account["totp_secret"], "issuer": "SmartHub",
        "algorithm": "SHA1", "digits": 6, "period": 30,
    })


class AuthenticationMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            return await self.app(scope, receive, send)
        path = scope["path"].rstrip("/")
        role = next((r for r in ("user", "operator", "staff")
                     if path.startswith(f"/api/v1/{r}/")), None)
        # Các alias /api/... của User cũng dùng cùng chính sách.
        if role is None and path.startswith("/api/"):
            role = "user"
        public = path.endswith("/auth/login") or path.endswith("/health")
        public = public or (role == "user" and path.endswith("/auth/register"))
        public = public or (role == "operator" and path.endswith("/auth/verify-2fa"))
        if not role or public:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin1")
        scheme, _, token = authorization.partition(" ")
        session = sessions.get(hashlib.sha256(token.encode()).hexdigest()) if scheme.lower() == "bearer" else None
        code = 401
        if session and session["expires_at"] > time.time():
            code = 403 if session["role"] != role else 200
        if code != 200:
            response = JSONResponse({"detail": "Phiên không hợp lệ" if code == 401 else "Không đủ quyền"}, status_code=code)
            return await response(scope, receive, send)
        scope["state"] = {**scope.get("state", {}), "account": session}
        context = current_user_id.set(session["id"] if role == "user" else None)
        try:
            await self.app(scope, receive, send)
        finally:
            current_user_id.reset(context)
