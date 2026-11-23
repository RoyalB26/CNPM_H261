"""Kiểm tra hồi quy đặt/nhận/hủy xe và tài nguyên dùng chung sau merge."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.memory_store import MockDatabaseStore


class RentalBookingTests(unittest.TestCase):
    """Mỗi ca dùng store riêng, không sửa seed hoặc runtime của nhóm."""

    def setUp(self):
        self.db = MockDatabaseStore()
        self.db.user["active_services"]["ride"] = None
        self.payload = {
            "plan_type": "rental", "hub_id": "hub-02", "resource_name": "XE-052",
        }

    def assert_rejected_without_changes(self):
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn("error", self.db.create_booking(self.payload))
        self.assertEqual(before, self.db.__dict__)

    def test_ids_are_unique_with_seed_and_nonstandard_ids(self):
        self.db.bookings.append({"id": "legacy"})
        for _ in range(5):
            result = self.db.create_booking({"plan_type": "swap", "hub_id": "hub-02", "battery_type": "B48"})
            self.assertNotIn("error", result)
        ids = [b["id"] for b in self.db.bookings]
        self.assertEqual(len(ids), len(set(ids)))

    def test_plain_bike_id_reserves_and_releases_correct_bike(self):
        hub = self.db.get_hub("hub-02")
        before_count = hub["available_bikes"]
        booking = self.db.create_booking(self.payload)
        self.assertEqual(hub["bikes"][0]["status"], "Đã đặt chỗ")
        self.assertEqual(hub["available_bikes"], before_count - 1)
        self.assert_rejected_without_changes()
        self.db.cancel_booking(booking["id"])
        self.assertEqual(hub["available_bikes"], before_count)
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn("error", self.db.cancel_booking(booking["id"]))
        self.assertEqual(before, self.db.__dict__)

    def test_inactive_hub_cannot_reserve_or_start(self):
        for status in ("DEACTIVATED", "MAINTENANCE"):
            with self.subTest(status=status):
                self.db.get_hub("hub-02")["status"] = status
                self.assert_rejected_without_changes()
        self.db.get_hub("hub-02")["status"] = "ACTIVE"
        booking = self.db.create_booking(self.payload)
        self.db.get_hub("hub-02")["status"] = "DEACTIVATED"
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.start_ride(booking["id"])["success"])
        self.assertEqual(before, self.db.__dict__)

    def test_relocation_and_maintenance_block_booking(self):
        self.db.relocations.append({"status": "PENDING", "bikes": [{"bike_id": "XE-052"}]})
        self.assert_rejected_without_changes()
        self.db.relocations.pop()
        self.db.maintenance_tickets.append({"status": "ASSIGNED", "device_code": "XE-052"})
        self.assert_rejected_without_changes()

    def test_active_ride_blocks_even_if_seed_says_ready(self):
        self.db.user["active_services"]["ride"] = {"vehicle_id": "XE-052"}
        self.assert_rejected_without_changes()

    def test_invalid_destination_rejected_before_reserving_bike(self):
        for destination in ({"destination_hub_id": "missing"},
                            {"destination_hub_name": "Hub không tồn tại"},
                            {"destination_hub_id": "hub-04", "destination_hub_name": "Tên sai"}):
            with self.subTest(destination=destination):
                self.payload = {"plan_type": "rental", "hub_id": "hub-02",
                                "resource_name": "XE-052", **destination}
                self.assert_rejected_without_changes()

    def test_closed_destination_rejected_before_reserving_bike(self):
        self.db.get_hub("hub-04")["status"] = "DEACTIVATED"
        self.payload["destination_hub_id"] = "hub-04"
        self.assert_rejected_without_changes()

    def test_destination_id_preserved_in_booking_and_ride(self):
        self.payload["destination_hub_id"] = "hub-04"
        booking = self.db.create_booking(self.payload)
        self.assertEqual(booking["destination_hub_id"], "hub-04")
        self.assertEqual(booking["destination_hub_name"], self.db.get_hub("hub-04")["name"])
        self.assertEqual(self.db.start_ride(booking["id"])["ride"]["destination_hub_id"], "hub-04")

    def test_cancel_does_not_restore_bike_under_maintenance(self):
        booking = self.db.create_booking(self.payload)
        hub = self.db.get_hub("hub-02")
        hub["bikes"][0]["status"] = "Đang bảo trì"
        before_count = hub["available_bikes"]
        self.db.cancel_booking(booking["id"])
        self.assertEqual(hub["available_bikes"], before_count)
        self.assertEqual(hub["bikes"][0]["status"], "Đang bảo trì")

    def test_start_rechecks_relocation(self):
        booking = self.db.create_booking(self.payload)
        self.db.relocations.append({"status": "IN_TRANSIT", "bikes": [{"bike_id": "XE-052"}]})
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.start_ride(booking["id"])["success"])
        self.assertEqual(before, self.db.__dict__)

    def test_seed_active_trip_cannot_cancel_even_if_booking_confirmed(self):
        self.db.reset()
        before = copy.deepcopy(self.db.__dict__)
        self.assertIn("error", self.db.cancel_booking("EMH-1024"))
        self.assertEqual(before, self.db.__dict__)
        self.assertTrue(self.db.return_vehicle("TRIP-8821", "Hub Đại học Quốc Tế")["success"])

    def test_duplicate_booking_ids_cannot_start_or_cancel(self):
        booking = self.db.create_booking(self.payload)
        self.db.bookings.append(copy.deepcopy(booking))
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.start_ride(booking["id"])["success"])
        self.assertIn("error", self.db.cancel_booking(booking["id"]))
        self.assertEqual(before, self.db.__dict__)

    def test_two_legacy_bookings_for_same_bike_cannot_release_each_other(self):
        booking = self.db.create_booking(self.payload)
        self.db.get_hub("hub-02")["bikes"][0].pop("reserved_by")
        duplicate = {**copy.deepcopy(booking), "id": "EMH-OTHER"}
        self.db.bookings.append(duplicate)
        before = copy.deepcopy(self.db.__dict__)
        for booking_id in (booking["id"], duplicate["id"]):
            self.assertFalse(self.db.start_ride(booking_id)["success"])
            self.assertIn("error", self.db.cancel_booking(booking_id))
        self.assertEqual(before, self.db.__dict__)

    def test_foreign_reservation_marker_blocks_start_and_cancel(self):
        booking = self.db.create_booking(self.payload)
        self.db.get_hub("hub-02")["bikes"][0]["reserved_by"] = "OTHER"
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.start_ride(booking["id"])["success"])
        self.assertIn("error", self.db.cancel_booking(booking["id"]))
        self.assertEqual(before, self.db.__dict__)

    def test_unique_legacy_hold_without_marker_can_start(self):
        booking = self.db.create_booking(self.payload)
        self.db.get_hub("hub-02")["bikes"][0].pop("reserved_by")
        self.assertTrue(self.db.start_ride(booking["id"])["success"])

    def test_cancel_removes_own_marker_and_bike_can_be_booked_again(self):
        booking = self.db.create_booking(self.payload)
        bike = self.db.get_hub("hub-02")["bikes"][0]
        self.assertEqual(bike["reserved_by"], booking["id"])
        self.db.cancel_booking(booking["id"])
        self.assertNotIn("reserved_by", bike)
        self.assertNotIn("error", self.db.create_booking(self.payload))

    def test_return_does_not_unlock_maintenance_or_relocation(self):
        for kind in ("maintenance", "relocation"):
            with self.subTest(kind=kind):
                self.setUp()
                booking = self.db.create_booking(self.payload)
                ride = self.db.start_ride(booking["id"])["ride"]
                if kind == "maintenance":
                    self.db.maintenance_tickets.append({"device_code": "XE-052", "status": "PENDING"})
                else:
                    self.db.relocations.append({"status": "IN_TRANSIT", "bikes": [{"bike_id": "XE-052"}]})
                hub = self.db.get_hub("hub-04")
                count = hub["available_bikes"]
                parking = hub["available_parking"]
                self.assertTrue(self.db.return_vehicle(ride["trip_id"], hub["name"])["success"])
                bike = next(b for b in hub["bikes"] if b["id"] == "XE-052")
                self.assertNotEqual(bike["status"], "Sẵn sàng")
                self.assertNotIn("reserved_by", bike)
                self.assertEqual(hub["available_bikes"], count)
                self.assertEqual(hub["available_parking"], parking - 1)
                self.assertEqual(booking["status"], "Hoàn thành")
                self.assertIn("rental_invoice", booking)
                self.assertIsNone(self.db.user["active_services"]["ride"])

    def test_return_completes_only_linked_booking_and_keeps_history(self):
        booking = self.db.create_booking(self.payload)
        ride = self.db.start_ride(booking["id"])["ride"]
        self.assertEqual(ride["booking_id"], booking["id"])
        self.assertIn("started_at", ride)
        other_before = copy.deepcopy(self.db.bookings[1:])
        result = self.db.return_vehicle(ride["trip_id"], "Hub Đại học Quốc Tế")
        self.assertTrue(result["success"])
        self.assertEqual(booking["status"], "Hoàn thành")
        self.assertEqual(booking["rental_trip"]["trip_id"], ride["trip_id"])
        self.assertIn("ended_at", booking["rental_trip"])
        self.assertEqual(booking["rental_trip"]["return_hub_id"], "hub-04")
        self.assertEqual(other_before, self.db.bookings[1:])
        self.assertIsNone(self.db.user["active_services"]["ride"])
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.return_vehicle(ride["trip_id"], "Hub Đại học Quốc Tế")["success"])
        self.assertEqual(before, self.db.__dict__)

    def test_failed_return_keeps_booking_and_active_trip(self):
        booking = self.db.create_booking(self.payload)
        ride = self.db.start_ride(booking["id"])["ride"]
        self.db.get_hub("hub-04")["available_parking"] = 0
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.return_vehicle(ride["trip_id"], "Hub Đại học Quốc Tế")["success"])
        self.assertEqual(before, self.db.__dict__)

    def test_destination_reserved_by_relocation_cannot_be_selected(self):
        hub = self.db.get_hub('hub-04')
        hub['available_parking'] = 1
        self.db.relocations.append({'target_hub_id': hub['id'], 'status': 'PENDING',
                                    'reserved_slot_ids': ['P31'], 'total_bikes': 1})
        self.payload['destination_hub_id'] = hub['id']
        self.assert_rejected_without_changes()

    def test_return_rechecks_incoming_holds_after_booking(self):
        for status in ('PENDING', 'IN_PROGRESS', 'IN_TRANSIT'):
            with self.subTest(status=status):
                self.setUp()
                booking = self.db.create_booking(self.payload)
                ride = self.db.start_ride(booking['id'])['ride']
                hub = self.db.get_hub('hub-04')
                hub['available_parking'] = 1
                self.db.relocations.append({'target_hub_id': hub['id'], 'status': status,
                                            'reserved_slot_ids': ['P31'], 'total_bikes': 1})
                before = copy.deepcopy(self.db.__dict__)
                self.assertFalse(self.db.return_vehicle(ride['trip_id'], hub['name'])['success'])
                self.assertEqual(before, self.db.__dict__)
                self.db.relocations[-1]['status'] = 'COMPLETED'
                self.assertTrue(self.db.return_vehicle(ride['trip_id'], hub['name'])['success'])

    def test_legacy_incoming_holds_without_slot_ids_block_return(self):
        booking = self.db.create_booking(self.payload)
        ride = self.db.start_ride(booking['id'])['ride']
        hub = self.db.get_hub('hub-04')
        hub['available_parking'] = 2
        self.db.relocations.append({'target_hub_id': hub['id'], 'status': 'IN_PROGRESS', 'total_bikes': 2})
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.return_vehicle(ride['trip_id'], hub['name'])['success'])
        self.assertEqual(before, self.db.__dict__)

    def test_parking_booking_already_deducted_is_not_deducted_twice(self):
        hub = self.db.get_hub('hub-04')
        hub['available_parking'] = 2
        held = self.db.create_booking({'plan_type': 'parking', 'hub_id': hub['id'],
                                      'personal_plate': '59-A1 888.88', 'parking_slot': 'P31'})
        self.assertNotIn('error', held)
        self.assertEqual(hub['available_parking'], 1)
        booking = self.db.create_booking({**self.payload, 'destination_hub_id': hub['id']})
        ride = self.db.start_ride(booking['id'])['ride']
        self.assertTrue(self.db.return_vehicle(ride['trip_id'], hub['name'])['success'])
        self.assertEqual(hub['available_parking'], 0)
        self.assertEqual(hub['slots'][0]['reserved_by'], held['id'])
        self.assertEqual(held['status'], 'Đã xác nhận')

    def test_sample_slot_list_does_not_replace_total_capacity(self):
        booking = self.db.create_booking(self.payload)
        ride = self.db.start_ride(booking['id'])['ride']
        hub = self.db.get_hub('hub-04')
        hub['slots'] = []
        count = hub['available_parking']
        self.assertTrue(self.db.return_vehicle(ride['trip_id'], hub['name'])['success'])
        self.assertEqual(hub['available_parking'], count - 1)

    def test_mismatched_booking_trip_or_status_prevents_return(self):
        for field, value in (('trip', 'TRIP-OTHER'), ('status', 'Đã xác nhận')):
            with self.subTest(field=field):
                self.setUp()
                booking = self.db.create_booking(self.payload)
                ride = self.db.start_ride(booking['id'])['ride']
                if field == 'trip':
                    booking['rental_trip']['trip_id'] = value
                else:
                    booking['status'] = value
                before = copy.deepcopy(self.db.__dict__)
                self.assertFalse(self.db.return_vehicle(ride['trip_id'], 'Hub Đại học Quốc Tế')['success'])
                self.assertEqual(before, self.db.__dict__)

    def test_vehicle_already_recorded_at_a_hub_cannot_be_silently_moved(self):
        booking = self.db.create_booking(self.payload)
        ride = self.db.start_ride(booking['id'])['ride']
        self.db.get_hub('hub-03')['bikes'].append({'id': ride['vehicle_id'], 'status': 'Sẵn sàng'})
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.return_vehicle(ride['trip_id'], 'Hub Đại học Quốc Tế')['success'])
        self.assertEqual(before, self.db.__dict__)

    def test_duplicate_legacy_vehicle_locations_are_rejected(self):
        self.db.reset()
        bike = next(b for b in self.db.get_hub('hub-01')['bikes'] if b['id'] == 'XE-024')
        self.db.get_hub('hub-03')['bikes'].append(copy.deepcopy(bike))
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.return_vehicle('TRIP-8821', 'Hub Đại học Quốc Tế')['success'])
        self.assertEqual(before, self.db.__dict__)

    def test_seed_trip_links_to_unique_legacy_booking(self):
        self.db.reset()
        self.assertTrue(self.db.return_vehicle("TRIP-8821", "Hub Đại học Quốc Tế")["success"])
        booking = next(b for b in self.db.bookings if b["id"] == "EMH-1024")
        self.assertEqual(booking["status"], "Hoàn thành")
        self.assertNotIn("started_at", booking["rental_trip"])

    def test_ambiguous_legacy_trip_is_rejected_without_changes(self):
        self.db.reset()
        duplicate = copy.deepcopy(self.db.bookings[0])
        duplicate["id"] = "EMH-OTHER"
        self.db.bookings.append(duplicate)
        before = copy.deepcopy(self.db.__dict__)
        self.assertFalse(self.db.return_vehicle("TRIP-8821", "Hub Đại học Quốc Tế")["success"])
        self.assertEqual(before, self.db.__dict__)


if __name__ == "__main__":
    unittest.main()
