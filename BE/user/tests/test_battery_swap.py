"""Kiểm tra tồn kho pin, hoàn giữ và hóa đơn đổi pin theo số lượng."""

import copy
import os
from unittest.mock import patch
from integration_support import VNPAY_TEST_CONFIG
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
from user.hubs import hub_detail


class BatterySwapTests(unittest.TestCase):
    def setUp(self):
        config = patch.dict(os.environ, VNPAY_TEST_CONFIG)
        config.start()
        self.addCleanup(config.stop)
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
        pending = pay_invoice(self.db, payment)
        self.assertEqual(booking['battery_swap_invoice']['status'], 'pending')
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(pay_invoice(self.db, payment).transaction_id, pending.transaction_id)
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

    def test_payment_rejects_changed_final_quantity_without_mutation(self):
        """Hóa đơn đổi pin phải khớp số lượng và giá đã chốt khi đặt."""
        booking = self.db.create_booking(self.payload)
        result = complete_swap(self.db, booking['id'])
        booking['battery_quantity'] = 3
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(PaymentError) as error:
            pay_invoice(self.db, PaymentSubmitRequest(invoice_id=result.invoice.id, method='wallet'))
        self.assertEqual(error.exception.status_code, 409)
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

    def test_maintenance_blocks_reservation_and_completion_until_resolved(self):
        ticket = {'device_code': 'B48', 'hub_id': 'hub-02', 'status': 'PENDING'}
        self.db.maintenance_tickets.append(ticket)
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)
        ticket['status'] = 'RESOLVED'
        booking = self.db.create_booking(self.payload)
        ticket['status'] = 'IN_PROGRESS'
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(SwapError):
            complete_swap(self.db, booking['id'])
        self.assertEqual(before, self.db.__dict__)
        ticket['status'] = 'RESOLVED'
        self.assertEqual(complete_swap(self.db, booking['id']).invoice.total_amount, 50000)

    def test_cancel_restores_stock_without_unlocking_battery_group(self):
        hub = self.db.get_hub('hub-02')
        before_stock = hub['batteries'][0]['available_count']
        booking = self.db.create_booking(self.payload)
        hub['batteries'][0]['is_available'] = False
        self.db.cancel_booking(booking['id'])
        self.assertEqual(hub['batteries'][0]['available_count'], before_stock)
        self.assertFalse(hub['batteries'][0]['is_available'])
        snapshot = copy.deepcopy(self.db.__dict__)
        view = hub_detail(self.db, hub)
        self.assertEqual(view.available_batteries, 0)
        self.assertEqual(view.batteries[0].available_count, 0)
        self.assertEqual(snapshot, self.db.__dict__)

    def test_corrupted_reserved_quantity_or_price_rejected_without_mutation(self):
        booking = self.db.create_booking(self.payload)
        for quantity, price in ((-2, -25000), (True, 25000), (2, -1), (2, True)):
            booking.update(battery_quantity=quantity, swap_unit_price=price)
            before = copy.deepcopy(self.db.__dict__)
            with self.assertRaises(SwapError):
                complete_swap(self.db, booking['id'])
            self.assertEqual(before, self.db.__dict__)

    def test_duplicate_battery_types_are_not_silently_selected(self):
        hub = self.db.get_hub('hub-02')
        hub['batteries'].append(copy.deepcopy(hub['batteries'][0]))
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)

    def test_maintenance_at_other_hub_does_not_block_same_battery_type(self):
        self.db.maintenance_tickets.append({'device_code': 'B48', 'hub_id': 'hub-01', 'status': 'PENDING'})
        booking = self.db.create_booking(self.payload)
        self.assertNotIn('error', booking)
        self.assertEqual(complete_swap(self.db, booking['id']).invoice.total_amount, 50000)
