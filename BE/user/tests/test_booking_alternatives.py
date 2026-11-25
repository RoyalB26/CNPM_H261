"""Kiểm tra gợi ý dùng đúng ràng buộc đặt chỗ và không tự giữ tài nguyên."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.alternatives import booking_alternatives
from user.schemas.booking import CreateBookingRequest


class BookingAlternativeTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()

    def suggestions(self, payload):
        """Mọi lựa chọn phải đặt được trên cùng snapshot và không sửa store thật."""
        before = copy.deepcopy(self.db.__dict__)
        result = booking_alternatives(self.db, CreateBookingRequest.model_validate(payload))
        self.assertLessEqual(len(result), 3)
        self.assertEqual(len({a.hub.id for a in result}), len(result))
        for alternative in result:
            candidate = copy.deepcopy(self.db)
            booking = candidate.create_booking(alternative.request.model_dump(mode='json', exclude_unset=True))
            self.assertNotIn('error', booking)
            self.assertEqual(booking['hub_id'], alternative.hub.id)
        self.assertEqual(before, self.db.__dict__)
        return result

    def test_rental_can_choose_another_bike_at_same_hub(self):
        result = self.suggestions({'plan_type': 'rental', 'hub_id': 'hub-02',
                                   'resource_name': 'XE-UNKNOWN', 'resource_id': 'XE-UNKNOWN',
                                   'selected_bike': 'XE-UNKNOWN', 'destination_hub_id': 'hub-04'})
        self.assertTrue(result)
        self.assertEqual(result[0].hub.id, 'hub-02')
        for alternative in result:
            self.assertNotEqual(alternative.request.resource_name, 'XE-024')
            self.assertEqual(alternative.request.destination_hub_id, 'hub-04')
            self.assertIsNone(alternative.request.selected_bike)

    def test_parking_replaces_requested_slot_but_preserves_plate_and_duration(self):
        result = self.suggestions({'plan_type': 'parking', 'hub_id': 'hub-02',
                                   'parking_slot': 'UNKNOWN', 'resource_id': 'UNKNOWN',
                                   'personal_plate': '59-A1 999.99', 'duration_hours': 3})
        self.assertTrue(result)
        for alternative in result:
            self.assertNotEqual(alternative.request.parking_slot, 'UNKNOWN')
            self.assertEqual(alternative.request.personal_plate, '59-A1 999.99')
            self.assertEqual(alternative.request.duration_hours, 3)

    def test_charging_skips_blocked_hub_and_maintenance_ports(self):
        self.db.get_hub('hub-02')['status'] = 'DEACTIVATED'
        self.db.maintenance_tickets.append({'hub_id': 'hub-01', 'device_code': 'S01', 'status': 'PENDING'})
        result = self.suggestions({'plan_type': 'charging', 'hub_id': 'hub-02',
                                   'charging_port': 'UNKNOWN', 'personal_plate': '59-A1 999.99'})
        self.assertTrue(result)
        self.assertNotIn('hub-02', [a.hub.id for a in result])
        self.assertNotIn(('hub-01', 'S01'), [(a.hub.id, a.request.charging_port) for a in result])

    def test_existing_plate_hold_is_not_bypassed_by_changing_hub(self):
        payload = {'plan_type': 'charging', 'hub_id': 'hub-01', 'personal_plate': '59-A1 999.99'}
        self.assertNotIn('error', self.db.create_booking(payload))
        self.assertEqual(self.suggestions(payload), [])

    def test_swap_preserves_type_and_quantity_without_fabricating_stock(self):
        result = self.suggestions({'plan_type': 'swap', 'hub_id': 'hub-02',
                                   'battery_type': 'B48', 'battery_quantity': 2})
        self.assertTrue(result)
        for alternative in result:
            self.assertEqual(alternative.request.battery_type, 'B48')
            self.assertEqual(alternative.request.battery_quantity, 2)
        self.assertEqual(self.suggestions({'plan_type': 'swap', 'hub_id': 'hub-02',
                                          'battery_type': 'B48', 'battery_quantity': 999}), [])

    def test_no_alternative_when_destination_cannot_accept_rental(self):
        self.db.get_hub('hub-04')['available_parking'] = 0
        result = self.suggestions({'plan_type': 'rental', 'hub_id': 'hub-02',
                                   'resource_name': 'XE-052', 'destination_hub_id': 'hub-04'})
        self.assertEqual(result, [])

    def test_empty_network_and_personal_bundle_require_actual_resources(self):
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn('error', self.db.create_booking({'plan_type': 'personal', 'hub_id': 'hub-02'}))
        self.assertEqual(before, self.db.__dict__)
        result = self.suggestions({'plan_type': 'personal', 'hub_id': 'hub-02',
                                   'personal_plate': '59-A1 999.99'})
        self.assertTrue(result)
        for alternative in result:
            self.assertTrue(alternative.request.parking_slot)
            self.assertTrue(alternative.request.charging_port)
        self.db.hubs = []
        self.assertEqual(self.suggestions({'plan_type': 'charging', 'hub_id': 'hub-02',
                                          'personal_plate': '59-A1 999.99'}), [])
