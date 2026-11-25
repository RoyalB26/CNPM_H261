"""Kiểm tra gói đỗ xe + sạc: giữ đồng thời, bàn giao và hoàn từng tài nguyên."""

import copy
import os
from unittest.mock import patch
from integration_support import VNPAY_TEST_CONFIG
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

from pydantic import ValidationError
from starlette.exceptions import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.bookings import expire_rental_bookings
from user.charging import ChargingError, start_charging, stop_charging
from user.payments import pay_invoice
from user.schemas.booking import CreateBookingRequest, BookingResponse
from user.schemas.payment import PaymentSubmitRequest, InvoiceQuery
from user.schemas.service import StopChargingRequest
from user.invoices import current_invoice


class PersonalBookingTests(unittest.TestCase):
    def setUp(self):
        config = patch.dict(os.environ, VNPAY_TEST_CONFIG)
        config.start()
        self.addCleanup(config.stop)
        self.db = MockDatabaseStore()
        self.db.user['active_services'].update(parking=None, charging=None)
        self.hub = self.db.get_hub('hub-02')
        self.payload = {'plan_type': 'personal', 'hub_id': 'hub-02', 'personal_plate': '59-A1 999.99'}
        self.counts = self.hub['available_parking'], self.hub['available_chargers']

    def hold(self):
        booking = self.db.create_booking(self.payload)
        self.assertNotIn('error', booking)
        BookingResponse.model_validate(booking)
        return booking

    def checkin(self):
        return self.db.parking_checkin({'plate_number': self.payload['personal_plate'],
                                       'hub_name': self.hub['name']})

    def test_hold_cancel_both_once_and_block_individual_double_booking(self):
        booking = self.hold()
        self.assertEqual((self.hub['available_parking'], self.hub['available_chargers']),
                         (self.counts[0] - 1, self.counts[1] - 1))
        self.assertEqual([s['service_type'] for s in booking['services']], ['parking', 'charging'])
        for plan in ('parking', 'charging', 'personal'):
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking({**self.payload, 'plan_type': plan}))
            self.assertEqual(before, self.db.__dict__)
        self.assertNotIn('error', self.db.cancel_booking(booking['id']))
        self.assertEqual((self.hub['available_parking'], self.hub['available_chargers']), self.counts)
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.cancel_booking(booking['id']))
        self.assertEqual(before, self.db.__dict__)

    def test_unavailable_either_side_never_reserves_other_side(self):
        for changes in ({'available_parking': 0}, {'available_chargers': 0}):
            with self.subTest(changes=changes):
                candidate = copy.deepcopy(self.db)
                candidate.get_hub('hub-02').update(changes)
                before = copy.deepcopy(candidate.__dict__)
                self.assertIn('error', candidate.create_booking(self.payload))
                self.assertEqual(before, candidate.__dict__)
        for resource in ({'parking_slot': 'UNKNOWN'}, {'charging_port': 'UNKNOWN'}):
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking({**self.payload, **resource}))
            self.assertEqual(before, self.db.__dict__)

    def test_expiry_releases_both_once(self):
        booking = self.hold()
        booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.assertEqual(expire_rental_bookings(self.db), [booking['id']])
        self.assertEqual((self.hub['available_parking'], self.hub['available_chargers']), self.counts)
        self.assertEqual(expire_rental_bookings(self.db), [])

    def test_checkin_charge_pay_checkout_preserves_separate_fees_and_counters(self):
        booking = self.hold()
        parking_price = booking['price']
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError):
            start_charging(self.db, booking['id'])
        self.assertEqual(before, self.db.__dict__)
        record = self.checkin()
        self.assertEqual(record['parking_fee'], 0)
        self.assertGreater(record['parking_hourly_rate'], 0)
        self.assertEqual(self.hub['available_parking'], self.counts[0] - 1)
        self.assertIn('error', self.db.cancel_booking(booking['id']))
        # Nhận tài nguyên trước hạn thì được tiếp tục dùng sau thời hạn giữ chỗ.
        booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.assertEqual(expire_rental_bookings(self.db), [])
        session = start_charging(self.db, booking['id']).charging
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(HTTPException):
            self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT')
        self.assertEqual(before, self.db.__dict__)
        result = stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=2.4))
        self.assertEqual(booking['status'], 'Đang sử dụng')
        self.assertEqual(booking['price'], parking_price)
        self.assertEqual(self.hub['available_chargers'], self.counts[1])
        self.assertEqual(self.hub['available_parking'], self.counts[0] - 1)
        invoice = current_invoice(self.db, InvoiceQuery(type='charging', booking_id=booking['id']))
        pay_invoice(self.db, PaymentSubmitRequest(invoice_id=invoice.id, method='wallet'))
        self.assertEqual(booking['charging_invoice']['status'], 'pending')
        with self.assertRaises(ChargingError):
            start_charging(self.db, booking['id'])
        self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT')
        self.assertEqual(booking['status'], 'Hoàn thành')
        self.assertEqual((self.hub['available_parking'], self.hub['available_chargers']), self.counts)
        self.assertEqual(current_invoice(self.db, InvoiceQuery(type='parking', booking_id=booking['id'])).total_amount,
                         record['parking_fee'])
        before = copy.deepcopy(self.db.__dict__)
        self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT')
        self.assertEqual(before, self.db.__dict__)

    def test_maintenance_port_blocks_checkin_but_cancel_releases_parking(self):
        booking = self.hold()
        self.db.maintenance_tickets.append({'hub_id': self.hub['id'], 'device_code': booking['charging_port'],
                                            'status': 'PENDING'})
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(HTTPException):
            self.checkin()
        self.assertEqual(before, self.db.__dict__)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(self.hub['available_parking'], self.counts[0])
        self.assertEqual(self.hub['available_chargers'], self.counts[1] - 1)

    def test_lost_hold_rejects_cancel_without_releasing_other_resource(self):
        booking = self.hold()
        port = next(p for p in self.hub['ports'] if p['id'] == booking['charging_port'])
        port['reserved_by'] = 'OTHER'
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.cancel_booking(booking['id']))
        self.assertEqual(before, self.db.__dict__)

    def test_schema_requires_plate_and_separate_resource_identifiers(self):
        for changes in ({'personal_plate': None}, {'personal_plate': ' '}, {'resource_id': 'P11'},
                        {'arrival_time': '12:00'}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                CreateBookingRequest.model_validate({**self.payload, **changes})
