"""Kiểm tra chủ sở hữu dữ liệu, chưa coi đây là xác thực token/nhiều tài khoản."""

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.json_store import JsonStateStore
from shared.memory_store import MockDatabaseStore
from shared.seed_loader import load_seed, SeedLoadError
from user.bookings import expire_rental_bookings
from user.charging import ChargingError, start_charging
from user.incidents import create_report
from user.invoices import InvoiceNotFound, current_invoice
from user.payments import PaymentError, pay_invoice
from user.schemas.booking import CreateBookingRequest
from user.schemas.incident import CreateIncidentReportRequest
from user.schemas.payment import InvoiceQuery, PaymentSubmitRequest
from user.swaps import SwapError, complete_swap


class UserOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.owner = self.db.user['id']

    def make_booking(self, **payload):
        booking = self.db.create_booking(payload)
        self.assertNotIn('error', booking)
        return booking

    def test_legacy_ownership_is_added_only_in_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.json'
            seed = load_seed()
            for booking in seed['bookings']:
                booking.pop('user_id', None)
            for report in seed['incidents']:
                report.pop('user_id', None)
            path.write_text(json.dumps(seed), encoding='utf-8')
            before = path.read_bytes()
            loaded = load_seed(path)
            self.assertTrue(all(b['user_id'] == self.owner for b in loaded['bookings']))
            self.assertTrue(all(r['user_id'] == self.owner for r in loaded['incidents']))
            self.assertEqual(before, path.read_bytes())

    def test_explicit_owner_preserved_and_bad_nested_owner_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.json'
            seed = load_seed()
            seed['bookings'][0]['user_id'] = 'USR-OTHER'
            path.write_text(json.dumps(seed), encoding='utf-8')
            self.assertEqual(load_seed(path)['bookings'][0]['user_id'], 'USR-OTHER')
            seed['bookings'][0]['rental_trip'] = {'user_id': self.owner}
            path.write_text(json.dumps(seed), encoding='utf-8')
            with self.assertRaises(SeedLoadError):
                load_seed(path)

    def test_client_cannot_select_booking_or_report_owner(self):
        request = CreateBookingRequest.model_validate({
            'plan_type': 'swap', 'hub_id': 'hub-02', 'battery_type': 'B48', 'user_id': 'USR-OTHER',
        })
        booking = self.db.create_booking(request.model_dump(exclude_unset=True))
        self.assertEqual(booking['user_id'], self.owner)
        report = create_report(self.db, CreateIncidentReportRequest.model_validate({
            'resource_type': 'Phương tiện', 'resource_code': 'XE-052',
            'hub_name': 'Hub Đại học Bách khoa', 'incident_type': 'Lỗi khóa',
            'description': 'Không mở được khóa', 'user_id': 'USR-OTHER',
        }))
        self.assertEqual(report.user_id, self.owner)
        self.assertEqual(self.db.maintenance_tickets[0]['user_id'], self.owner)

    def test_foreign_booking_hidden_and_cannot_start_or_cancel(self):
        booking = self.make_booking(plan_type='rental', hub_id='hub-02', resource_name='XE-052')
        booking['user_id'] = 'USR-OTHER'
        before = copy.deepcopy(self.db.__dict__)
        self.assertNotIn(booking, self.db.get_bookings())
        self.assertIsNone(self.db.cancel_booking(booking['id']))
        self.assertEqual(self.db.start_ride(booking['id'])['error'], 'Booking không tồn tại')
        self.assertEqual(before, self.db.__dict__)

    def test_foreign_charging_and_swap_bookings_cannot_be_used(self):
        charging = self.make_booking(plan_type='charging', hub_id='hub-01',
                                     personal_plate='59-A1 999.99', charging_port='S01')
        swap = self.make_booking(plan_type='swap', hub_id='hub-02', battery_type='B48')
        charging['user_id'] = swap['user_id'] = 'USR-OTHER'
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError) as charging_error:
            start_charging(self.db, charging['id'])
        with self.assertRaises(SwapError) as swap_error:
            complete_swap(self.db, swap['id'])
        self.assertEqual(charging_error.exception.status_code, 404)
        self.assertEqual(swap_error.exception.status_code, 404)
        self.assertEqual(before, self.db.__dict__)

    def test_foreign_invoice_not_read_or_paid_even_with_known_id(self):
        booking = self.make_booking(plan_type='swap', hub_id='hub-02', battery_type='B48')
        complete_swap(self.db, booking['id'])
        invoice = booking['battery_swap_invoice']
        booking['user_id'] = invoice['user_id'] = 'USR-OTHER'
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(InvoiceNotFound):
            current_invoice(self.db, InvoiceQuery(type='swap', invoice_id=invoice['id']))
        with self.assertRaises(PaymentError) as error:
            pay_invoice(self.db, PaymentSubmitRequest(invoice_id=invoice['id'], method='wallet'))
        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(before, self.db.__dict__)

    def test_foreign_parking_invoice_same_plate_is_not_owned(self):
        plate = self.db.get_user_vehicles()[0]['plate_number']
        self.db.parking_records = [{
            'user_id': 'USR-OTHER', 'plate_number': plate, 'ticket_code': 'PRK-OTHER',
            'hub_name': 'Hub thử', 'slot_id': 'P01', 'parking_fee': 5000,
            'checkin_time': '2026-11-23T08:00:00+07:00', 'payment_status': 'PAID',
        }]
        with self.assertRaises(InvoiceNotFound):
            current_invoice(self.db, InvoiceQuery(type='parking', invoice_id='INV-PRK-OTHER'))

    def test_incident_list_filters_without_mutating_global_operator_data(self):
        foreign = {**copy.deepcopy(self.db.incidents[0]), 'id': 'INC-OTHER', 'user_id': 'USR-OTHER'}
        self.db.incidents.append(foreign)
        before = copy.deepcopy(self.db.__dict__)
        self.assertNotIn(foreign, self.db.get_user_incidents())
        self.assertIn(foreign, self.db.incidents)
        self.assertEqual(before, self.db.__dict__)

    def test_system_expiry_still_releases_other_owner_resources(self):
        booking = self.make_booking(plan_type='swap', hub_id='hub-02', battery_type='B48')
        booking['user_id'] = 'USR-OTHER'
        deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
        booking['expires_at'] = deadline.isoformat()
        stock = self.db.get_hub('hub-02')['available_batteries']
        self.assertEqual(expire_rental_bookings(self.db), [booking['id']])
        self.assertEqual(booking['status'], 'Hết hạn')
        self.assertEqual(self.db.get_hub('hub-02')['available_batteries'], stock + 1)
        self.assertEqual(booking['user_id'], 'USR-OTHER')

    def test_json_roundtrip_keeps_owner_and_foreign_records(self):
        booking = self.make_booking(plan_type='swap', hub_id='hub-02', battery_type='B48')
        booking['user_id'] = 'USR-OTHER'
        with tempfile.TemporaryDirectory() as directory:
            storage = JsonStateStore(self.db, Path(directory) / 'runtime.json')
            storage.commit(lambda candidate: None)
            other = MockDatabaseStore()
            reloaded = JsonStateStore(other, storage.path)
            reloaded.reload()
            self.assertEqual(storage.snapshot(), reloaded.snapshot())
            self.assertNotIn(booking['id'], [b['id'] for b in other.get_bookings()])
            self.assertIn(booking['id'], [b['id'] for b in other.bookings])


if __name__ == '__main__':
    unittest.main()
