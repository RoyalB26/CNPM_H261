"""Kiểm tra cước từ lúc đặt xe, biên làm tròn và đơn giá đã xác nhận."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.rental_pricing import rental_charge
from shared.memory_store import MockDatabaseStore


class RentalPricingTests(unittest.TestCase):
    def test_minute_rounding_and_cross_day(self):
        start = datetime(2026, 11, 21, 23, 50, tzinfo=timezone.utc)
        for seconds, minutes, fee in [(0, 0, 0), (1, 1, 167), (60, 1, 167),
                                      (61, 2, 334), (1800, 30, 5000),
                                      (3600, 60, 10000), (86400, 1440, 240000)]:
            with self.subTest(seconds=seconds):
                charge = rental_charge({'started_at': start.isoformat()}, start + timedelta(seconds=seconds), 10000)
                self.assertEqual((charge['elapsed_minutes'], charge['total_fee']), (minutes, fee))

    def test_invalid_clock_and_legacy_snapshot(self):
        now = datetime.now(timezone.utc)
        for value in ['invalid', '2026-01-01T00:00:00', (now + timedelta(minutes=1)).isoformat()]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                rental_charge({'started_at': value}, now, 10000)
        charge = rental_charge({'elapsed_minutes': 13}, now, 10000)
        self.assertEqual(charge['total_fee'], 2167)
        self.assertEqual(charge['billing_source'], 'legacy_elapsed_minutes')

    def test_snapshot_rate_and_invoice_match_return(self):
        db = MockDatabaseStore()
        db.user['active_services']['ride'] = None
        confirmed = datetime(2026, 11, 21, 8, 0, tzinfo=timezone.utc)
        with patch('shared.memory_store.datetime') as clock:
            clock.now.return_value = confirmed
            booking = db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        db.get_hub('hub-02')['pricing']['rental_bike_hourly'] = 20000
        start = confirmed + timedelta(minutes=8)
        with patch('shared.memory_store.datetime') as clock:
            clock.now.return_value = start
            ride = db.start_ride(booking['id'])['ride']
        db.get_hub('hub-02')['pricing']['rental_bike_hourly'] = 20000
        with patch('shared.memory_store.datetime') as clock:
            clock.now.return_value = confirmed + timedelta(minutes=30)
            result = db.return_vehicle(ride['trip_id'], 'Hub Đại học Quốc Tế')
        self.assertTrue(result['success'])
        self.assertEqual(result['elapsed_minutes'], 30)
        self.assertEqual(result['total_fee'], 5000)
        self.assertEqual(booking['rental_trip']['total_fee'], 5000)
        self.assertEqual(booking['rental_invoice']['total_amount'], 5000)
        self.assertEqual(ride['started_at'], start.isoformat())
        self.assertEqual(ride['billing_started_at'], confirmed.isoformat())
        self.assertEqual(booking['rental_trip']['billing_source'], 'billing_started_at')
        self.assertEqual(ride['hourly_rate'], 10000)

    def test_bad_booking_clock_does_not_move_bike(self):
        db = MockDatabaseStore()
        db.user['active_services']['ride'] = None
        booking = db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        for timestamp in ['bad', '2026-01-01T00:00:00', (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()]:
            booking['billing_started_at'] = timestamp
            before = copy.deepcopy(db.__dict__)
            self.assertFalse(db.start_ride(booking['id'])['success'])
            self.assertEqual(before, db.__dict__)

    def test_invalid_booking_price_does_not_reserve_bike(self):
        db = MockDatabaseStore()
        db.get_hub('hub-02')['pricing']['rental_bike_hourly'] = -1
        before = copy.deepcopy(db.__dict__)
        self.assertIn('error', db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'}))
        self.assertEqual(before, db.__dict__)

    def test_legacy_booking_keeps_receive_time_without_inventing_date(self):
        db = MockDatabaseStore()
        db.user['active_services']['ride'] = None
        booking = db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        booking.pop('billing_started_at'); booking.pop('rental_hourly_rate')
        ride = db.start_ride(booking['id'])['ride']
        self.assertNotIn('billing_started_at', ride)
        self.assertEqual(rental_charge(ride, datetime.fromisoformat(ride['started_at']) + timedelta(minutes=22), ride['hourly_rate'])['total_fee'], 3667)

    def test_invalid_start_does_not_move_vehicle(self):
        db = MockDatabaseStore()
        db.user['active_services']['ride'] = None
        booking = db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        ride = db.start_ride(booking['id'])['ride']
        ride['started_at'] = 'invalid'
        before = copy.deepcopy(db.__dict__)
        self.assertFalse(db.return_vehicle(ride['trip_id'], 'Hub Đại học Quốc Tế')['success'])
        self.assertEqual(before, db.__dict__)


if __name__ == '__main__':
    unittest.main()
