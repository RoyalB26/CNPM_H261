"""Các ca BE hiện có và ca chờ theo đặc tả TC-O."""
import unittest
import test_auth
from test_auth import db, totp, accounts, storage


class OperatorCases(unittest.TestCase):
    setUp = test_auth.AuthTests.setUp
    tearDown = test_auth.AuthTests.tearDown
    operator_login = test_auth.AuthTests.operator_login

    def headers(self):
        challenge = self.operator_login()
        account = next(a for a in accounts() if a["role"] == "operator")
        response = self.client.post("/api/v1/operator/auth/verify-2fa", json={
            "email": account["email"], "challenge_id": challenge["challenge_id"],
            "otp_code": totp(account["totp_secret"]),
        })
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_TC_O05_hub_config_readback(self):
        headers = self.headers()
        hub = db.hubs[0]
        expected = hub["max_power_kw"] + 10
        response = self.client.put(f"/api/v1/operator/hubs/{hub['id']}/config",
            headers=headers, json={"hub_id": hub["id"], "max_power_kw": expected,
                                   "parking_capacity": hub["parking_capacity"] + 1,
                                   "status": "Cảnh báo tải"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["success"])
        self.assertTrue(response.json()["message"])
        storage.reload()
        response = self.client.get("/api/v1/operator/hubs", headers=headers)
        actual = next(h for h in response.json()["items"] if h["id"] == hub["id"])
        self.assertEqual(actual["max_power_kw"], expected)
        self.assertEqual(actual["parking_capacity"], hub["parking_capacity"] + 1)
        self.assertEqual(actual["status"], "Cảnh báo tải")

    def test_TCO03_ERR_no_destination_capacity(self):
        headers = self.headers()
        def change(candidate):
            target = candidate.hubs[1]
            target["available_parking"] = 0
            for slot in target.get("slots", []):
                slot["is_available"] = False
        storage.commit(change)
        before = storage.snapshot()
        response = self.client.post("/api/v1/operator/relocation/commands",
            headers=headers, json={
                "source_hub_id": db.hubs[0]["id"], "target_hub_id": db.hubs[1]["id"],
                "bike_count": 1, "assigned_staff_id": "STF-01",
            })
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(storage.snapshot(), before)

    @unittest.skip("E2E trình duyệt, phụ thuộc TC-O01 và nối FE")
    def test_TC_O02_what_if_dashboard(self):
        pass

    @unittest.skip("E2E trình duyệt chờ ghép FE; API/thông báo được test trong test_features")
    def test_TC_O03_dispatch_notification(self):
        pass

    @unittest.skip("E2E trình duyệt chờ ghép FE; API tạo phiếu/phân công đã có test")
    def test_TC_O04_maintenance_notification(self):
        pass
