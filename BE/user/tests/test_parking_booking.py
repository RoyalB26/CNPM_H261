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

    def checkin_booking(self):
        booking = self.db.create_booking(self.payload)
        self.assertNotIn('error', booking)
        record = self.db.parking_checkin({'plate_number': self.payload['personal_plate'],
                                         'hub_name': 'Hub Đại học Bách khoa'})
        return booking, record

    def assert_no_change_error(self, action, status=409):
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(HTTPException) as caught:
            action()
        self.assertEqual(caught.exception.status_code, status)
        self.assertEqual(before, self.db.__dict__)

    def test_legacy_checkin_and_checkout_repeated_do_not_change_counters(self):
        before = copy.deepcopy(self.db.__dict__)
        record = self.db.parking_checkin({'plate_number': '59X112345', 'hub_name': 'Hub Ga Metro ĐHQG'})
        self.assertEqual(record['ticket_code'], 'PRK-901')
        self.assertEqual(before, self.db.__dict__)
        self.db.parking_checkout_confirm('PRK-901', 'TIỀN MẶT')
        after = copy.deepcopy(self.db.__dict__)
        self.db.parking_checkout_confirm('PRK-901', 'TIỀN MẶT')
        self.assertEqual(after, self.db.__dict__)

    def test_checkout_by_plate_selects_open_visit_over_old_history(self):
        booking, record = self.checkin_booking()
        old = {**copy.deepcopy(record), 'ticket_code': 'PRK-OLD', 'checkout_time': '2026-01-01T00:00:00+00:00',
               'payment_status': 'PAID'}
        self.db.parking_records.insert(0, old)
        result = self.db.parking_checkout_confirm('59A199999', 'TIỀN MẶT')
        self.assertIs(result, record)
        self.assertEqual(booking['status'], 'Hoàn thành')
        self.assertEqual(old['checkout_time'], '2026-01-01T00:00:00+00:00')

    def test_duplicate_ticket_codes_and_open_plates_rejected(self):
        _, record = self.checkin_booking()
        duplicate = copy.deepcopy(record)
        self.db.parking_records.append(duplicate)
        self.assert_no_change_error(lambda: self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT'))
        duplicate['ticket_code'] = 'PRK-OTHER'
        self.assert_no_change_error(lambda: self.db.parking_checkout_confirm(record['plate_number'], 'TIỀN MẶT'))
        self.assert_no_change_error(lambda: self.db.parking_checkin({
            'plate_number': record['plate_number'], 'hub_name': record['hub_name']}))

    def test_unknown_ticket_rejected_without_marking_anything_paid(self):
        self.assert_no_change_error(lambda: self.db.parking_checkout_confirm('UNKNOWN', 'TIỀN MẶT'), 404)

    def test_corrupted_booking_or_slot_prevents_partial_checkout(self):
        booking, record = self.checkin_booking()
        slot = self.db.get_hub('hub-02')['slots'][0]
        for key, value in [('status', 'Đã hủy'), ('hub_id', 'hub-04'), ('user_id', 'USR-OTHER')]:
            original = booking[key]
            booking[key] = value
            self.assert_no_change_error(lambda: self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT'))
            booking[key] = original
        slot['occupied_by'] = 'PRK-OTHER'
        self.assert_no_change_error(lambda: self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT'))

    def test_counter_over_capacity_rejected_without_partial_checkout(self):
        _, record = self.checkin_booking()
        hub = self.db.get_hub('hub-02')
        hub['available_parking'] = hub['parking_capacity']
        self.assert_no_change_error(lambda: self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT'))

    def test_maintenance_blocks_reserve_and_checkin(self):
        ticket = {'device_code': 'P11', 'hub_id': 'hub-02', 'status': 'PENDING'}
        self.db.maintenance_tickets.append(ticket)
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)
        self.db.maintenance_tickets.remove(ticket)
        self.db.create_booking(self.payload)
        self.db.maintenance_tickets.append(ticket)
        self.assert_no_change_error(lambda: self.db.parking_checkin({
            'plate_number': self.payload['personal_plate'], 'hub_name': 'Hub Đại học Bách khoa'}))

    def test_cancel_does_not_reopen_maintenance_slot(self):
        booking = self.db.create_booking(self.payload)
        hub = self.db.get_hub('hub-02')
        count = hub['available_parking']
        self.db.maintenance_tickets.append({'device_code': 'P11', 'hub_id': 'hub-02', 'status': 'ASSIGNED'})
        self.assertNotIn('error', self.db.cancel_booking(booking['id']))
        self.assertFalse(hub['slots'][0]['is_available'])
        self.assertNotIn('reserved_by', hub['slots'][0])
        self.assertEqual(hub['available_parking'], count)

    def test_checkout_keeps_maintenance_slot_unavailable(self):
        booking, record = self.checkin_booking()
        hub = self.db.get_hub('hub-02')
        count = hub['available_parking']
        self.db.maintenance_tickets.append({'device_code': 'P11', 'hub_id': 'hub-02', 'status': 'IN_PROGRESS'})
        self.db.parking_checkout_confirm(record['ticket_code'], 'TIỀN MẶT')
        self.assertEqual(booking['status'], 'Hoàn thành')
        self.assertEqual(record['payment_status'], 'PAID')
        self.assertFalse(hub['slots'][0]['is_available'])
        self.assertNotIn('occupied_by', hub['slots'][0])
        self.assertEqual(hub['available_parking'], count)
        self.assertIsNone(self.db.user['active_services']['parking'])

    def test_checkin_cannot_create_another_visit_at_different_hub(self):
        self.assert_no_change_error(lambda: self.db.parking_checkin({
            'plate_number': '59-X1 123.45', 'hub_name': 'Hub Đại học Bách khoa'}))

    def test_same_slot_code_at_other_hub_does_not_block(self):
        self.db.maintenance_tickets.append({'device_code': 'P11', 'hub_id': 'hub-04', 'status': 'PENDING'})
        self.assertNotIn('error', self.db.create_booking(self.payload))

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
