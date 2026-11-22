"""Kiểm tra biên hết hạn và việc hoàn xe chỉ diễn ra một lần."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.booking_expiry import booking_expired
from shared.memory_store import MockDatabaseStore
from user.bookings import expire_rental_bookings


class BookingExpiryTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.db.user['active_services']['ride'] = None
        self.booking = self.db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        self.deadline = datetime.fromisoformat(self.booking['expires_at'])

    def test_boundary_and_release_once(self):
        hub = self.db.get_hub('hub-02')
        reserved_count = hub['available_bikes']
        self.assertFalse(booking_expired(self.booking, self.deadline - timedelta(microseconds=1)))
        self.assertEqual(expire_rental_bookings(self.db, self.deadline), [self.booking['id']])
        self.assertEqual(self.booking['status'], 'Hết hạn')
        self.assertEqual(hub['available_bikes'], reserved_count + 1)
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(expire_rental_bookings(self.db, self.deadline), [])
        self.assertEqual(before, self.db.__dict__)

    def test_start_expired_rejected_without_mutation(self):
        self.booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.start_ride(self.booking['id'])['success'])
        self.assertEqual(before, self.db.__dict__)

    def test_active_ride_not_expired(self):
        self.assertTrue(self.db.start_ride(self.booking['id'])['success'])
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(expire_rental_bookings(self.db, self.deadline + timedelta(days=1)), [])
        self.assertEqual(before, self.db.__dict__)

    def test_maintenance_not_restored(self):
        bike = self.db.get_hub('hub-02')['bikes'][0]
        bike['status'] = 'Đang bảo trì'
        count = self.db.get_hub('hub-02')['available_bikes']
        expire_rental_bookings(self.db, self.deadline)
        self.assertEqual(bike['status'], 'Đang bảo trì')
        self.assertEqual(self.db.get_hub('hub-02')['available_bikes'], count)

    def test_bad_deadline_prevents_partial_cleanup(self):
        self.db.bookings.append({**copy.deepcopy(self.booking), 'id': 'EMH-BAD', 'expires_at': 'bad'})
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ValueError):
            expire_rental_bookings(self.db, self.deadline)
        self.assertEqual(before, self.db.__dict__)

    def test_seed_without_date_not_guessed(self):
        self.db.reset()
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(expire_rental_bookings(self.db, datetime.now(timezone.utc)), [])
        self.assertEqual(before, self.db.__dict__)

    def test_ambiguous_hold_prevents_partial_cleanup(self):
        other = self.db.create_booking({'plan_type': 'swap', 'hub_id': 'hub-02', 'battery_type': 'B48'})
        other['expires_at'] = self.booking['expires_at']
        duplicate = {**copy.deepcopy(self.booking), 'id': 'EMH-OTHER'}
        self.db.bookings.append(duplicate)
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ValueError):
            expire_rental_bookings(self.db, self.deadline)
        self.assertEqual(before, self.db.__dict__)
