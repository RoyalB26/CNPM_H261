"""Kiểm tra tồn kho pin, hoàn giữ và hóa đơn đổi pin theo số lượng."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.bookings import expire_rental_bookings
from user.swaps import complete_swap, SwapError
from user.payments import pay_invoice, PaymentError
from user.schemas.payment import PaymentSubmitRequest


class BatterySwapTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.payload = {'plan_type': 'swap', 'hub_id': 'hub-02', 'battery_type': 'B48', 'battery_quantity': 2}

    def test_reserve_cancel_and_expire_once(self):
        hub = self.db.get_hub('hub-02')
        battery = hub['batteries'][0]
        before_count = battery['available_count']
        booking = self.db.create_booking(self.payload)
        self.assertEqual(booking['price'], 50000)
        self.assertEqual(battery['available_count'], before_count - 2)
        self.assertEqual(hub['available_batteries'], before_count - 2)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(battery['available_count'], before_count)
        before = copy.deepcopy(self.db.__dict__)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(before, self.db.__dict__)
        booking = self.db.create_booking(self.payload)
        booking['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        self.assertEqual(expire_rental_bookings(self.db), [booking['id']])
        self.assertEqual(battery['available_count'], before_count)

    def test_complete_and_pay_without_double_consumption(self):
        booking = self.db.create_booking(self.payload)
        self.db.get_hub('hub-02')['batteries'][0]['swap_fee'] = 99999
        result = complete_swap(self.db, booking['id'])
        self.assertEqual(result.invoice.total_amount, 50000)
        self.assertEqual(self.db.get_hub('hub-02')['available_batteries'], 3)
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(SwapError):
            complete_swap(self.db, booking['id'])
        self.assertIn('error', self.db.cancel_booking(booking['id']))
        self.assertEqual(before, self.db.__dict__)
        payment = PaymentSubmitRequest(invoice_id=result.invoice.id, method='wallet', amount=50000)
        pay_invoice(self.db, payment)
        self.assertEqual(booking['battery_swap_invoice']['status'], 'paid')
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(PaymentError):
            pay_invoice(self.db, payment)
        self.assertEqual(before, self.db.__dict__)

    def test_invalid_stock_type_vehicle_and_hub_do_not_mutate(self):
        for changes in [{'battery_quantity': 6}, {'battery_quantity': 0}, {'battery_type': 'UNKNOWN'},
                        {'hub_id': 'UNKNOWN'}, {'personal_plate': '59-V1 456.78'}]:
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking({**self.payload, **changes}))
            self.assertEqual(before, self.db.__dict__)
        self.db.get_hub('hub-02')['status'] = 'DEACTIVATED'
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)

    def test_complete_expired_inactive_or_legacy_rejected(self):
        booking = self.db.create_booking(self.payload)
        booking['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(SwapError):
            complete_swap(self.db, booking['id'])
        self.assertEqual(before, self.db.__dict__)

    def test_alias_and_infer_type_from_personal_vehicle(self):
        booking = self.db.create_booking({'plan_type': 'battery_swap', 'hub_id': 'hub-02', 'personal_plate': '59-X1 123.45'})
        self.assertEqual(booking['battery_type'], 'B48')
        self.assertEqual(booking['battery_quantity'], 1)
        self.assertEqual(booking['price'], 25000)
