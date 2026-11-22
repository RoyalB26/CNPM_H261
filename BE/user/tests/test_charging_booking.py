"""Kiểm tra giữ cổng sạc ngay và hoàn tài nguyên, không mô phỏng lịch tối ưu."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.bookings import expire_rental_bookings


class ChargingBookingTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.payload = {'plan_type': 'charging', 'hub_id': 'hub-01', 'personal_plate': '59-A1 999.99', 'charging_port': 'S01'}

    def test_reserve_cancel_once(self):
        hub = self.db.get_hub('hub-01'); before_count = hub['available_chargers']
        booking = self.db.create_booking(self.payload)
        self.assertEqual(booking['charging_port'], 'S01')
        self.assertEqual(booking['charging_rate_per_kwh'], 3500)
        self.assertEqual(booking['price'], 0)
        self.assertEqual(hub['available_chargers'], before_count - 1)
        self.assertFalse(hub['ports'][0]['is_available'])
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking({**self.payload, 'personal_plate': 'OTHER'}))
        self.assertEqual(before, self.db.__dict__)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(hub['available_chargers'], before_count)
        self.assertTrue(hub['ports'][0]['is_available'])
        before = copy.deepcopy(self.db.__dict__)
        self.db.cancel_booking(booking['id'])
        self.assertEqual(before, self.db.__dict__)

    def test_seed_active_maintenance_unknown_and_mismatched_port(self):
        for change in [{'charging_port': 'S03'}, {'charging_port': 'S02'}, {'charging_port': 'UNKNOWN'},
                       {'resource_id': 'S04'}, {'personal_plate': None}]:
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking({**self.payload, **change}))
            self.assertEqual(before, self.db.__dict__)

    def test_expire_returns_port_once(self):
        booking = self.db.create_booking(self.payload)
        booking['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        self.assertEqual(expire_rental_bookings(self.db), [booking['id']])
        self.assertTrue(self.db.get_hub('hub-01')['ports'][0]['is_available'])
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(expire_rental_bookings(self.db), [])
        self.assertEqual(before, self.db.__dict__)

    def test_cancel_never_reactivates_maintenance_port(self):
        booking = self.db.create_booking(self.payload)
        hub = self.db.get_hub('hub-01'); reserved_count = hub['available_chargers']
        hub['ports'][0]['status'] = 'Đang bảo trì'
        self.db.cancel_booking(booking['id'])
        self.assertEqual(hub['ports'][0]['status'], 'Đang bảo trì')
        self.assertFalse(hub['ports'][0]['is_available'])
        self.assertEqual(hub['available_chargers'], reserved_count)

    def test_no_port_available_and_inactive_hub(self):
        hub = self.db.get_hub('hub-01')
        for field, value in [('available_chargers', 0), ('status', 'DEACTIVATED')]:
            original = hub[field]; hub[field] = value
            before = copy.deepcopy(self.db.__dict__)
            self.assertIn('error', self.db.create_booking(self.payload))
            self.assertEqual(before, self.db.__dict__)
            hub[field] = original

    def test_same_vehicle_cannot_hold_multiple_ports(self):
        self.db.create_booking(self.payload)
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking({**self.payload, 'charging_port': 'S04'}))
        self.assertEqual(before, self.db.__dict__)
