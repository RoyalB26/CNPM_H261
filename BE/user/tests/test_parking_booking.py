"""Kiểm tra giữ chỗ gửi xe và bàn giao cho bãi, không trừ tài nguyên hai lần."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from starlette.exceptions import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.bookings import expire_rental_bookings


class ParkingBookingTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.db.user['active_services']['parking'] = None
        self.payload = {'plan_type': 'parking', 'hub_id': 'hub-02', 'personal_plate': '59-A1 999.99', 'parking_slot': 'P11'}

    def test_reserve_cancel_and_no_double_release(self):
        hub = self.db.get_hub('hub-02')
        count = hub['available_parking']
        booking = self.db.create_booking(self.payload)
        self.assertEqual(booking['parking_slot'], 'P11')
        self.assertEqual(hub['available_parking'], count - 1)
        self.assertFalse(hub['slots'][0]['is_available'])
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(hub['available_parking'], count)
        before = copy.deepcopy(self.db.__dict__)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(before, self.db.__dict__)

    def test_checkin_checkout_uses_reservation_once(self):
        hub = self.db.get_hub('hub-02')
        count = hub['available_parking']
        booking = self.db.create_booking(self.payload)
        request = {'plate_number': self.payload['personal_plate'], 'hub_name': hub['name']}
        record = self.db.parking_checkin(request)
        self.assertEqual(record['slot_id'], 'P11')
        self.assertEqual(record['booking_id'], booking['id'])
        self.assertEqual(booking['status'], 'Đang sử dụng')
        self.assertEqual(hub['available_parking'], count - 1)
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(self.db.parking_checkin(request), record)
        self.assertEqual(before, self.db.__dict__)
        self.assertIn('error', self.db.cancel_booking(booking['id']))
        self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT')
        self.assertEqual(hub['available_parking'], count)
        self.assertTrue(hub['slots'][0]['is_available'])
        self.assertEqual(booking['status'], 'Hoàn thành')
        self.assertIsNone(self.db.user['active_services']['parking'])
        before = copy.deepcopy(self.db.__dict__)
        self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT')
        self.assertEqual(before, self.db.__dict__)

    def test_expiry_releases_slot_and_checkin_expired_rejected(self):
        booking = self.db.create_booking(self.payload)
        booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(HTTPException):
            self.db.parking_checkin({'plate_number': self.payload['personal_plate'], 'hub_name': 'Hub Đại học Bách khoa'})
        self.assertEqual(before, self.db.__dict__)
        self.assertEqual(expire_rental_bookings(self.db), [booking['id']])
        self.assertTrue(self.db.get_hub('hub-02')['slots'][0]['is_available'])

    def test_occupied_seed_and_relocation_holds_excluded(self):
        # P08 trong seed có vé đang mở dù is_available vẫn là true.
        invalid = {**self.payload, 'hub_id': 'hub-01', 'parking_slot': 'P08'}
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(invalid))
        self.assertEqual(before, self.db.__dict__)
        self.db.relocations.append({'target_hub_id': 'hub-02', 'status': 'PENDING', 'reserved_slot_ids': ['P11'], 'total_bikes': 1})
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)

    def test_full_inactive_unknown_slot_and_duplicate_plate(self):
        hub = self.db.get_hub('hub-02')
        for changes in [{'parking_slot': 'UNKNOWN'}, {'personal_plate': '59-X1 123.45'}, {'personal_plate': ''}]:
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking({**self.payload, **changes}))
            self.assertEqual(before, self.db.__dict__)
        for field, value in [('available_parking', 0), ('status', 'DEACTIVATED')]:
            old = hub[field]; hub[field] = value
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking(self.payload))
            self.assertEqual(before, self.db.__dict__)
            hub[field] = old
