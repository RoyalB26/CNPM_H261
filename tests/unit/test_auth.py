"""Unit/API Test kiểm thử xác thực cho End-User, Operator (2FA) và Staff."""

import pytest
from starlette.testclient import TestClient

from shared.authentication import accounts, totp
from shared.database import storage
from tests.unit.conftest import OPERATOR_API, STAFF_API, USER_API

pytestmark = pytest.mark.unit


def test_user_login_invalid_json_returns_400(api_client: TestClient) -> None:
    """Trường hợp thất bại: gửi body không phải JSON tới User login phải trả 400."""
    response = api_client.post(
        f"{USER_API}/auth/login",
        content="not-a-json-payload",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body.get("success") is False or bool(body.get("detail") or body.get("error"))


def test_user_login_valid_credentials_returns_token(api_client: TestClient) -> None:
    """Trường hợp thành công: User đăng nhập hợp lệ được cấp token và hồ sơ."""
    response = api_client.post(
        f"{USER_API}/auth/login",
        json={"email": "abc123@hcmut.edu.vn", "password": "123456"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("success", True) is True
    assert "token" in body
    assert body["user"]["id"] == "USR-001"


def test_operator_login_and_2fa_flow(api_client: TestClient) -> None:
    """Kiểm thử luồng đăng nhập Operator kết hợp bước xác thực OTP 2FA."""
    email = "admin@e-mobility.com"
    login_res = api_client.post(
        f"{OPERATOR_API}/auth/login",
        json={"email": email, "password": "operator123"},
    )
    assert login_res.status_code in (200, 201), login_res.text
    challenge_id = login_res.json()["challenge_id"]

    op_account = next(a for a in accounts() if a["role"] == "operator")
    otp_res = api_client.post(
        f"{OPERATOR_API}/auth/verify-2fa",
        json={
            "email": email,
            "challenge_id": challenge_id,
            "otp_code": totp(op_account["totp_secret"]),
        },
    )
    assert otp_res.status_code == 200, otp_res.text
    body = otp_res.json()
    assert "access_token" in body
    assert "operator" in body


@pytest.mark.parametrize(
    ("role", "username", "expected_role_label"),
    [
        ("relocation", "staff_01", "Nhân viên điều phối"),
        ("maintenance", "staff_b", "Nhân viên bảo trì"),
        ("security", "staff_03", "Bảo vệ Hub"),
    ],
)
def test_staff_login_supports_all_three_roles(
    api_client: TestClient,
    role: str,
    username: str,
    expected_role_label: str,
) -> None:
    """Kiểm thử đăng nhập nhân viên hiện trường với đầy đủ 3 vai trò."""
    if role == "security":
        def add_guard(candidate):
            candidate.staff.append(
                {
                    "id": "STF-03",
                    "full_name": "Bảo vệ Hub 1",
                    "role": "SECURITY_GUARD",
                }
            )

        storage.commit(add_guard)

    response = api_client.post(
        f"{STAFF_API}/auth/login",
        json={"username_or_phone": username, "password": "staff123"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    assert body["staff"]["role"] == expected_role_label


@pytest.mark.nfr
def test_nfr05_operator_api_enforces_rbac_and_2fa(api_client: TestClient) -> None:
    """NFR05 (API): Chặn request không token (401) và token role student (403) vào route Operator."""
    unauth_res = api_client.get(f"{OPERATOR_API}/dashboard/kpis")
    assert unauth_res.status_code == 401

    login_res = api_client.post(
        f"{USER_API}/auth/login",
        json={"email": "abc123@hcmut.edu.vn", "password": "123456"},
    )
    student_token = login_res.json()["token"]
    forbidden_res = api_client.get(
        f"{OPERATOR_API}/dashboard/kpis",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden_res.status_code == 403