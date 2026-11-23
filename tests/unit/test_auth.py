"""Unit/API Test kiểm thử xác thực cho End-User, Operator (2FA) và Staff."""

import pytest
from starlette.testclient import TestClient

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
    assert body.get("success") is False


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
    assert login_res.status_code in (200, 201)

    otp_res = api_client.post(
        f"{OPERATOR_API}/auth/verify-2fa",
        json={"email": email, "otp_code": "123456"},
    )
    assert otp_res.status_code == 200
    assert any(key in otp_res.json() for key in ("access_token", "token", "operator"))


@pytest.mark.parametrize("role", ["relocation", "maintenance", "security"])
def test_staff_login_supports_all_three_roles(api_client: TestClient, role: str) -> None:
    """Kiểm thử đăng nhập nhân viên hiện trường với đầy đủ 3 vai trò."""
    response = api_client.post(
        f"{STAFF_API}/auth/login",
        json={"staff_id": "STF-01", "password": "password123", "role": role},
    )
    assert response.status_code == 200
    body = response.json()
    assert any(key in body for key in ("access_token", "token", "staff", "profile"))

@pytest.mark.nfr
@pytest.mark.xfail(
    reason="BUG-FE-03 (NFR05): Các route BE/operator chưa áp đặt middleware kiểm tra JWT token, role 'operator' và trạng thái xác thực 2FA",
    strict=True,
)
def test_nfr05_operator_api_enforces_rbac_and_2fa(api_client: TestClient) -> None:
    """NFR05 (API): Chặn request không token (401) và token role student (403) vào route Operator."""
    # 1. Không có token -> 401
    unauth_res = api_client.get(f"{OPERATOR_API}/dashboard/kpis")
    assert unauth_res.status_code == 401

    # 2. Đăng nhập bằng tài khoản sinh viên -> gọi API Operator phải trả 403
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