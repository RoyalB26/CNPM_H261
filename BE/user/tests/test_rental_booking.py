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
            self.db.create_booking({"plan_type": "parking", "hub_id": "hub-02"})
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
