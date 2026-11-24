"""D1–D2 qua Gateway, chữ ký IPN mô phỏng và runtime tạm."""
import copy
import hashlib
import hmac
import os
import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse, parse_qs
from unittest.mock import patch
import test_auth
from shared.database import db, storage
from shared.parking_pricing import calculate_fee, parking_time
from shared.json_store import PersistenceError

VN = timezone(timedelta(hours=7))


class PaymentParkingTests(unittest.TestCase):
    tearDown = test_auth.AuthTests.tearDown
    register = test_auth.AuthTests.register
    user_login = test_auth.AuthTests.user_login

    def setUp(self):
        test_auth.AuthTests.setUp(self)
        self.register()
        self.user = self.user_login()
        self.user_id = self.client.get("/api/v1/user/profile", headers=self.user).json()["id"]
        response = self.client.post("/api/v1/staff/auth/login", json={
            "username_or_phone": "staff_b", "password": "staff123"})
        self.staff = {"Authorization": "Bearer " + response.json()["access_token"]}
        self.config = patch.dict(os.environ, {
            "VNPAY_TMN_CODE": "TESTMERCHANT", "VNPAY_HASH_SECRET": "test-only-secret",
            "VNPAY_RETURN_URL": "http://localhost:3000/payment-result",
        })
        self.config.start()
        self.addCleanup(self.config.stop)
        self.invoice()

    def invoice(self, suffix="1", amount=7000):
        now = datetime.now(timezone.utc).isoformat()
        def change(candidate):
            candidate.bookings.append({
                "id": "PAY-BOOK-" + suffix, "user_id": self.user_id,
                "plan_type": "charging", "status": "Hoàn thành", "hub_id": "hub-01",
                "charging_port": "S01", "charging_rate_per_kwh": 3500,
                "charging_session": {"status": "Hoàn thành", "port_id": "S01",
                    "power_consumed_kwh": amount / 3500, "rate_per_kwh": 3500},
                "charging_invoice": {
                    "id": "INV-TEST-" + suffix, "user_id": self.user_id, "service_type": "charging",
                    "title": "Charging", "reference_id": "S01", "created_at": now,
                    "items": [{"label": "Energy", "description": "Energy", "amount": amount}],
                    "total_amount": amount, "payment_channel": "online", "status": "unpaid",
                },
            })
        storage.commit(change)

    def pay(self, suffix="1", headers=None):
        return self.client.post("/api/v1/user/invoices/pay", headers=headers or self.user,
            json={"invoice_id": "INV-TEST-" + suffix, "method": "wallet"})

    def saved_invoice(self, suffix="1"):
        return next(b["charging_invoice"] for b in db.bookings if b["id"] == "PAY-BOOK-" + suffix)

    def callback(self, reference, **changes):
        data = {"vnp_TmnCode": "TESTMERCHANT", "vnp_TxnRef": reference,
                "vnp_Amount": "700000", "vnp_ResponseCode": "00", "vnp_TransactionStatus": "00",
                "vnp_TransactionNo": "123456", "vnp_PayDate": datetime.now(VN).strftime("%Y%m%d%H%M%S")}
        data.update(changes)
        encoded = urlencode(sorted(data.items()))
        data["vnp_SecureHash"] = hmac.new(b"test-only-secret", encoded.encode(), hashlib.sha512).hexdigest()
        return data

    def ipn(self, data):
        return self.client.get("/api/v1/payments/vnpay/ipn", params=data)

    def test_D1_payment_url_pending_and_idempotent_create(self):
        with patch.object(storage, "_write", wraps=storage._write) as write:
            response = self.pay()
            self.assertEqual(write.call_count, 1)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["status"], "pending")
        params = parse_qs(urlparse(data["payment_url"]).query)
        self.assertEqual(params["vnp_Amount"], ["700000"])
        self.assertEqual(params["vnp_TmnCode"], ["TESTMERCHANT"])
        self.assertEqual(self.saved_invoice()["status"], "pending")
        self.assertEqual(self.pay().json()["transaction_id"], data["transaction_id"])

    def test_D1_valid_ipn_duplicate_and_reload(self):
        reference = self.pay().json()["transaction_id"]
        params = self.callback(reference)
        self.assertEqual(self.ipn(params).json()["RspCode"], "00")
        storage.reload()
        self.assertEqual(self.saved_invoice()["status"], "paid")
        self.assertEqual(self.saved_invoice()["transaction_id"], "123456")
        self.assertEqual(self.ipn(params).json()["RspCode"], "02")
        messages = self.client.get("/api/v1/user/notifications", headers=self.user).json()["items"]
        self.assertEqual(sum(n["reference_id"] == "INV-TEST-1" for n in messages), 1)

    def test_D1_reject_signature_amount_merchant_and_unknown_reference(self):
        reference = self.pay().json()["transaction_id"]
        data = self.callback(reference)
        data["vnp_Amount"] = "100"
        self.assertEqual(self.ipn(data).json()["RspCode"], "97")
        self.assertEqual(self.ipn(self.callback(reference, vnp_Amount="100")).json()["RspCode"], "04")
        self.assertEqual(self.ipn(self.callback(reference, vnp_TmnCode="OTHER")).json()["RspCode"], "97")
        self.assertEqual(self.ipn(self.callback("missing")).json()["RspCode"], "01")
        self.assertEqual(self.saved_invoice()["status"], "pending")

    def test_D1_provider_transaction_cannot_pay_two_invoices(self):
        first = self.pay().json()["transaction_id"]
        self.invoice("2")
        second = self.pay("2").json()["transaction_id"]
        self.assertEqual(self.ipn(self.callback(first)).json()["RspCode"], "00")
        self.assertEqual(self.ipn(self.callback(second)).json()["RspCode"], "99")
        self.assertEqual(self.saved_invoice("2")["status"], "pending")

    def test_D1_failure_then_retry_and_late_ipn(self):
        reference = self.pay().json()["transaction_id"]
        self.assertEqual(self.ipn(self.callback(reference, vnp_ResponseCode="24", vnp_TransactionStatus="02")).json()["RspCode"], "00")
        self.assertEqual(self.saved_invoice()["status"], "unpaid")
        new_reference = self.pay().json()["transaction_id"]
        self.assertNotEqual(new_reference, reference)
        self.assertEqual(self.ipn(self.callback(new_reference)).json()["RspCode"], "00")

    def test_D1_persistence_failure_does_not_ack_success(self):
        reference = self.pay().json()["transaction_id"]
        with self.assertLogs("shared.database", level="ERROR"), patch.object(storage, "_write", side_effect=PersistenceError("test")):
            response = self.ipn(self.callback(reference))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.saved_invoice()["status"], "pending")
        self.assertEqual(self.ipn(self.callback(reference)).json()["RspCode"], "00")

    def test_D1_config_missing_and_user_ownership(self):
        with patch.dict(os.environ, {"VNPAY_HASH_SECRET": ""}):
            self.assertEqual(self.pay().status_code, 503)
        self.assertEqual(self.saved_invoice()["status"], "unpaid")
        self.register("2")
        self.assertEqual(self.pay(headers=self.user_login("2")).status_code, 404)

    def test_D1_expired_pending_requires_reconciliation(self):
        self.pay()
        def change(candidate):
            candidate.operator_mock["payment_intents"][0]["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        storage.commit(change)
        self.assertEqual(self.pay().status_code, 409)

    def test_D1_zero_invoice_and_duplicate_parameters(self):
        self.invoice("0", amount=0)
        response = self.pay("0")
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(self.saved_invoice("0")["status"], "paid")
        reference = self.pay().json()["transaction_id"]
        params = list(self.callback(reference).items()) + [("vnp_Amount", "100")]
        self.assertEqual(self.ipn(params).json()["RspCode"], "97")

    def record(self, minutes=61, rate=2500):
        now = datetime.now(timezone.utc)
        record = {"ticket_code": "PRK-TEST", "user_id": self.user_id, "plate_number": "59-TEST",
            "hub_id": "hub-01", "hub_name": "Hub Ga Metro ĐHQG", "slot_id": "P-TEST",
            "checkin_time": (now - timedelta(minutes=minutes)).isoformat(), "checkout_time": None,
            "parking_fee": 0, "parking_hourly_rate": rate, "duration_display": "0 phút",
            "payment_status": "PENDING", "guard_id": "STF-02"}
        def change(candidate):
            candidate.parking_records.append(record)
        storage.commit(change)
        return record

    def preview(self):
        return self.client.get("/api/v1/staff/parking/checkout/PRK-TEST", headers=self.staff)

    def test_D2_preview_confirm_invoice_same_and_retry_safe(self):
        self.record()
        preview = self.preview()
        self.assertEqual(preview.status_code, 200, preview.text)
        data = preview.json()
        self.assertEqual(data["total_fee_vnd"], 5000)
        before = db.get_hub("hub-01")["available_parking"]
        payload = {"ticket_code": "PRK-TEST", "quote_token": data["quote_token"], "cash_received": 5000}
        for _ in range(2):
            response = self.client.post("/api/v1/staff/parking/checkout/confirm", headers=self.staff, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["paid_amount"], 5000)
        self.assertEqual(db.get_hub("hub-01")["available_parking"], before + 1)
        invoice = self.client.get("/api/v1/user/invoices/current?type=parking&invoice_id=INV-PRK-TEST", headers=self.user)
        self.assertEqual(invoice.status_code, 200, invoice.text)
        self.assertEqual(invoice.json()["total_amount"], 5000)
        self.assertEqual(invoice.json()["status"], "paid")
        storage.reload()
        self.assertEqual(self.preview().json()["total_fee_vnd"], 5000)

    def test_D2_tampered_expired_quote_and_insufficient_cash(self):
        self.record()
        token = self.preview().json()["quote_token"]
        payload = {"ticket_code": "PRK-TEST", "quote_token": token, "cash_received": 1}
        self.assertEqual(self.client.post("/api/v1/staff/parking/checkout/confirm", headers=self.staff, json=payload).status_code, 422)
        payload.update(quote_token=token + "tampered", cash_received=10000)
        self.assertEqual(self.client.post("/api/v1/staff/parking/checkout/confirm", headers=self.staff, json=payload).status_code, 409)
        payload["quote_token"] = token
        future = datetime.now(timezone.utc) + timedelta(minutes=6)
        with patch("shared.parking_pricing.utc_now", return_value=future):
            self.assertEqual(self.client.post("/api/v1/staff/parking/checkout/confirm", headers=self.staff, json=payload).status_code, 409)
        self.assertIsNone(next(r for r in db.parking_records if r["ticket_code"] == "PRK-TEST")["checkout_time"])

    def test_D2_rounding_and_legacy_timezone(self):
        start = datetime(2026, 11, 24, tzinfo=VN)
        self.assertEqual(calculate_fee(start.isoformat(), (start + timedelta(hours=1)).isoformat(), 2500)["parking_fee"], 2500)
        self.assertEqual(calculate_fee(start.isoformat(), (start + timedelta(hours=1, seconds=1)).isoformat(), 2500)["parking_fee"], 5000)
        self.assertEqual(parking_time("24/11/2026 · 00:00"), start.astimezone(timezone.utc))
        self.assertEqual(self.client.get("/api/v1/staff/parking/checkout/missing", headers=self.staff).status_code, 404)

    def test_D2_legacy_record_and_hub_rate_change(self):
        self.record()
        def change(candidate):
            candidate.get_hub("hub-01")["pricing"]["parking_hourly"] = 99000
        storage.commit(change)
        self.assertEqual(self.preview().json()["total_fee_vnd"], 5000)
        def legacy(candidate):
            record = next(r for r in candidate.parking_records if r["ticket_code"] == "PRK-TEST")
            record.pop("parking_hourly_rate")
            candidate.get_hub("hub-01")["pricing"]["parking_hourly"] = 3000
        storage.commit(legacy)
        self.assertEqual(self.preview().json()["total_fee_vnd"], 6000)

    def test_D2_booking_checkin_checkout_full_api_flow(self):
        booked = self.client.post("/api/v1/user/bookings", headers=self.user, json={
            "plan_type": "parking", "hub_id": "hub-02", "parking_slot": "P11", "personal_plate": "59-NEW1"})
        self.assertEqual(booked.status_code, 200, booked.text)
        hub = db.get_hub("hub-02")
        checked = self.client.post("/api/v1/staff/parking/checkin", headers=self.staff, json={
            "license_plate": "59-NEW1", "hub_name": hub["name"], "parking_slot": "P11"})
        self.assertEqual(checked.status_code, 200, checked.text)
        ticket = checked.json()["ticket_code"]
        profile = self.client.get("/api/v1/user/profile", headers=self.user).json()
        self.assertEqual(profile["active_services"]["parking"]["ticket_id"], ticket)
        preview = self.client.get("/api/v1/staff/parking/checkout/" + ticket, headers=self.staff).json()
        response = self.client.post("/api/v1/staff/parking/checkout/confirm", headers=self.staff, json={
            "ticket_code": ticket, "quote_token": preview["quote_token"], "cash_received": preview["total_fee_vnd"]})
        self.assertEqual(response.status_code, 200, response.text)
        profile = self.client.get("/api/v1/user/profile", headers=self.user).json()
        self.assertIsNone(profile["active_services"]["parking"])
        invoice = self.client.get("/api/v1/user/invoices/current?type=parking&invoice_id=INV-" + ticket, headers=self.user)
        self.assertEqual(invoice.status_code, 200, invoice.text)
        self.assertEqual(invoice.json()["total_amount"], preview["total_fee_vnd"])

    def test_D2_walkin_captures_slot_rate_and_rejects_bad_checkin(self):
        hub = db.get_hub("hub-02")
        response = self.client.post("/api/v1/staff/parking/checkin", headers=self.staff, json={
            "license_plate": "59-WALKIN", "hub_name": hub["name"], "parking_slot": "P11"})
        self.assertEqual(response.status_code, 200, response.text)
        ticket = response.json()["ticket_code"]
        record = next(r for r in db.parking_records if r["ticket_code"] == ticket)
        self.assertEqual(record["guard_id"], "STF-02")
        self.assertTrue(record["checkin_time"].endswith("+00:00"))
        self.assertEqual(record["parking_hourly_rate"], next(s["hourly_rate"] for s in db.get_hub("hub-02")["slots"] if s["id"] == "P11"))
        self.assertEqual(self.client.post("/api/v1/staff/parking/checkin", headers=self.staff, json={}).status_code, 422)
