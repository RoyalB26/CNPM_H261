"""Kiểm thử A1–A3 qua Gateway, runtime tạm độc lập dữ liệu demo."""
import asyncio
import selectors
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

runtime = tempfile.TemporaryDirectory()
os.environ["BE_RUNTIME_PATH"] = str(Path(runtime.name) / "runtime.json")
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from starlette.testclient import TestClient
import run_all
from shared.authentication import accounts, challenges, sessions, totp
from shared.database import db, storage


class InProcessSelector(selectors.SelectSelector):
    def select(self, timeout=None):
        if not self.get_map():
            return []
        return super().select(timeout)


class InProcessLoop(asyncio.SelectorEventLoop):
    """ASGI in-process không mở socket trong môi trường test hạn chế mạng."""
    def __init__(self):
        super().__init__(InProcessSelector())

    def _make_self_pipe(self):
        pass

    def _close_self_pipe(self):
        pass

    def _write_to_self(self):
        pass


class AuthTests(unittest.TestCase):
    def setUp(self):
        storage.reset_to_seed()
        sessions.clear()
        challenges.clear()
        self.client = TestClient(run_all.app, backend_options={'loop_factory': InProcessLoop})

    def tearDown(self):
        self.client.close()

    def register(self, suffix="1"):
        return self.client.post("/api/auth/register", json={
            "full_name": "Test " + suffix, "email": f"user{suffix}@example.com",
            "phone": "090000000" + suffix, "password": "password123",
            "confirm_password": "password123",
        })

    def user_login(self, suffix="1"):
        response = self.client.post("/api/auth/login", json={
            "email": f"user{suffix}@example.com", "password": "password123",
        })
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": "Bearer " + response.json()["token"]}

    def operator_login(self):
        response = self.client.post("/api/v1/operator/auth/login", json={
            "email": db.operator_mock["auth"]["profile"].get("email", "admin@e-mobility.com"),
            "password": "operator123",
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_register_persist_login_and_duplicate(self):
        created = self.register()
        self.assertEqual(created.status_code, 201, created.text)
        self.assertNotIn("password", created.text)
        self.assertEqual(self.register().status_code, 409)
        storage.reload()
        headers = self.user_login()
        profile = self.client.get("/api/v1/user/profile", headers=headers)
        self.assertEqual(profile.json()["id"], created.json()["user"]["id"])
        self.assertEqual(profile.json()["vehicles"], [])

    def test_totp_rfc6238_vector(self):
        self.assertEqual(totp("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 1), "287082")

    def test_standalone_apps_protect_routes(self):
        for app, path in (
            (run_all.user_mod.app, "/api/v1/user/profile"),
            (run_all.op_mod.app, "/api/v1/operator/hubs"),
            (run_all.staff_mod.app, "/api/v1/staff/profile"),
        ):
            with TestClient(app, backend_options={"loop_factory": InProcessLoop}) as client:
                self.assertEqual(client.get(path).status_code, 401)

    def test_bad_inputs_and_wrong_password(self):
        self.assertEqual(self.client.post("/api/auth/register", content="{").status_code, 400)
        self.assertEqual(self.client.post("/api/auth/register", json={}).status_code, 422)
        self.assertEqual(self.client.post("/api/auth/login", json={
            "email": "missing@example.com", "password": "wrong",
        }).status_code, 401)

    def test_roles_expiry_and_user_isolation(self):
        self.register("1")
        self.register("2")
        one, two = self.user_login("1"), self.user_login("2")
        path = "/api/v1/user/profile"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get("/api/v1/operator/hubs", headers=one).status_code, 403)
        result = self.client.put(path, json={"full_name": "Changed"}, headers=one)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.get(path, headers=two).json()["full_name"], "Test 2")
        self.assertEqual(self.client.get("/api/v1/user/bookings", headers=two).json(), [])
        storage.reload()
        self.assertEqual(self.client.get(path, headers=one).json()["full_name"], "Changed")
        for session in sessions.values():
            session["expires_at"] = 0
        self.assertEqual(self.client.get(path, headers=one).status_code, 401)

    def test_2fa_requires_login_and_rejects_replay(self):
        challenge = self.operator_login()
        account = next(a for a in accounts() if a["role"] == "operator")
        payload = {"email": account["email"], "challenge_id": challenge["challenge_id"],
                   "otp_code": totp(account["totp_secret"])}
        missing = {**payload, "challenge_id": "missing"}
        self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=missing).status_code, 401)
        response = self.client.post("/api/v1/operator/auth/verify-2fa", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        self.assertEqual(self.client.get("/api/v1/operator/hubs", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/user/profile", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=payload).status_code, 401)
        again = self.operator_login()
        payload["challenge_id"] = again["challenge_id"]
        self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=payload).status_code, 401)

    def test_2fa_expiry_attempt_limit_wrong_password(self):
        self.assertEqual(self.client.post("/api/v1/operator/auth/login", json={
            "email": "admin@e-mobility.com", "password": "incorrect",
        }).status_code, 401)
        challenge = self.operator_login()
        payload = {"email": challenge["email"], "challenge_id": challenge["challenge_id"],
                   "otp_code": "abcdef"}
        self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=payload).status_code, 422)
        account = next(a for a in accounts() if a["role"] == "operator")
        valid = totp(account["totp_secret"])
        payload["otp_code"] = "000000" if valid != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=payload).status_code, 401)
        payload["otp_code"] = valid
        self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=payload).status_code, 401)
        challenge = self.operator_login()
        payload["challenge_id"] = challenge["challenge_id"]
        challenges[challenge["challenge_id"]]["expires_at"] = 0
        self.assertEqual(self.client.post("/api/v1/operator/auth/verify-2fa", json=payload).status_code, 401)

    def test_staff_credentials_and_cross_role(self):
        self.assertEqual(self.client.post("/api/v1/staff/auth/login", json={}).status_code, 422)
        response = self.client.post("/api/v1/staff/auth/login", json={
            "username_or_phone": "staff_b", "password": "staff123",
        })
        self.assertEqual(response.status_code, 200, response.text)
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        self.assertEqual(self.client.get("/api/v1/staff/profile", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/operator/hubs", headers=headers).status_code, 403)

    def test_failed_persistence_does_not_register(self):
        self.register()
        with self.assertLogs("shared.database", level="ERROR"), patch.object(storage, "_write", side_effect=__import__("shared.json_store", fromlist=["PersistenceError"]).PersistenceError("test")):
            self.assertEqual(self.register("2").status_code, 503)
        self.assertIsNone(next((a for a in accounts() if a.get("email") == "user2@example.com"), None))


if __name__ == "__main__":
    unittest.main()
