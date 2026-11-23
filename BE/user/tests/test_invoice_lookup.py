"""Kiểm tra truy vấn hóa đơn không lấy nhầm giao dịch hoặc thay đổi dữ liệu."""

import copy
from pathlib import Path
import sys
import unittest

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.invoices import InvoiceConflict, InvoiceNotFound, current_invoice, invoice_time
from user.schemas.payment import InvoiceQuery


class InvoiceLookupTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.assertTrue(self.db.return_vehicle("TRIP-8821", "Hub Đại học Quốc Tế")["success"])

    def test_matching_selectors_return_actual_invoice_without_mutation(self):
        before = copy.deepcopy(self.db.__dict__)
        invoice = current_invoice(self.db, InvoiceQuery(type="rental", trip_id="TRIP-8821"))
        self.assertEqual(invoice.id, self.db.bookings[0]["rental_invoice"]["id"])
        self.assertEqual(invoice.total_amount, self.db.bookings[0]["rental_invoice"]["total_amount"])
        self.assertEqual(before, self.db.__dict__)

    def test_each_selector_must_match(self):
        for selectors in ({"trip_id": "missing"}, {"booking_id": "missing"},
                          {"invoice_id": "missing"},
                          {"trip_id": "TRIP-8821", "booking_id": "missing"}):
            with self.subTest(selectors=selectors), self.assertRaises(InvoiceNotFound):
                current_invoice(self.db, InvoiceQuery(type="rental", **selectors))

    def test_invalid_type_or_irrelevant_filter_rejected(self):
        for values in ({"type": "unknown"}, {"type": "parking", "trip_id": "TRIP-8821"},
                       {"type": "rental", "session_id": "CHG-302"},
                       {"type": "rental", "booking_id": "  "}, {"typo": "rental"}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                InvoiceQuery.model_validate(values)

    def test_parking_invoice_comes_from_real_ticket(self):
        plate = self.db.get_user_vehicles()[0]["plate_number"]
        self.db.parking_records = [{
            "ticket_code": "PRK-TEST", "plate_number": plate,
            "hub_name": "Hub kiểm thử", "slot_id": "P01", "parking_fee": 7000,
            "payment_status": "PAID", "checkin_time": "2026-11-22T10:00:00+07:00",
        }]
        before = copy.deepcopy(self.db.__dict__)
        invoice = current_invoice(self.db, InvoiceQuery(type="parking"))
        self.assertEqual(invoice.id, "INV-PRK-TEST")
        self.assertEqual(invoice.total_amount, 7000)
        self.assertEqual(invoice.status, "paid")
        self.assertEqual(invoice.payment_channel, "cash_guard")
        self.assertEqual(before, self.db.__dict__)

    def test_unknown_plate_or_missing_invoice_has_no_fallback(self):
        self.db.parking_records = []
        with self.assertRaises(InvoiceNotFound):
            current_invoice(self.db, InvoiceQuery(type="parking"))
        with self.assertRaises(InvoiceNotFound):
            current_invoice(self.db, InvoiceQuery(type="charging"))

    def test_newest_invoice_uses_timestamp_not_list_order(self):
        older = copy.deepcopy(self.db.bookings[0])
        older["id"] = "OLD-BOOKING"
        older["rental_invoice"]["id"] = "OLD-INVOICE"
        older["rental_invoice"]["created_at"] = "2020-01-01T00:00:00+00:00"
        self.db.bookings.insert(0, older)
        self.assertNotEqual(current_invoice(self.db, InvoiceQuery()).id, "OLD-INVOICE")
        self.assertEqual(invoice_time("22/11/2026 · 10:00"),
                         invoice_time("2026-11-22T03:00:00+00:00"))

    def test_duplicate_invoice_id_not_silently_selected(self):
        self.db.bookings.append(copy.deepcopy(self.db.bookings[0]))
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(InvoiceConflict):
            current_invoice(self.db, InvoiceQuery(type='rental'))
        self.assertEqual(before, self.db.__dict__)


if __name__ == "__main__":
    unittest.main()
