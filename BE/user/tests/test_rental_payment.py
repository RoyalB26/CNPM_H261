"""Kiểm tra thanh toán một lần và bảo vệ số tiền hóa đơn thuê xe."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.payments import PaymentError, pay_invoice
from user.schemas.payment import PaymentSubmitRequest


class RentalPaymentTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        result = self.db.return_vehicle("TRIP-8821", "Hub Đại học Quốc Tế")
        self.assertTrue(result['success'])
        self.invoice = self.db.bookings[0]['rental_invoice']

    def test_paid_state_and_repeat_rejected(self):
        request = PaymentSubmitRequest(invoice_id=self.invoice['id'], method='Ví điện tử')
        result = pay_invoice(self.db, request)
        self.assertEqual(self.invoice['status'], 'paid')
        self.assertEqual(self.invoice['transaction_id'], result.transaction_id)
        self.assertEqual(self.invoice['payment_method'], 'wallet')
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(PaymentError):
            pay_invoice(self.db, request)
        self.assertEqual(before, self.db.__dict__)

    def test_wrong_amount_cash_and_unknown_invoice_do_not_mutate(self):
        for overrides in [{'amount': 1}, {'method': 'cash_guard'}, {'invoice_id': 'UNKNOWN'}]:
            request = PaymentSubmitRequest.model_validate({'invoice_id': self.invoice['id'], 'method': 'bank_transfer', **overrides})
            before = copy.deepcopy(self.db.__dict__)
            with self.assertRaises(PaymentError):
                pay_invoice(self.db, request)
            self.assertEqual(before, self.db.__dict__)

    def test_duplicate_invoice_rejected(self):
        self.db.bookings.append(copy.deepcopy(self.db.bookings[0]))
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(PaymentError):
            pay_invoice(self.db, PaymentSubmitRequest(invoice_id=self.invoice['id'], method='wallet'))
        self.assertEqual(before, self.db.__dict__)

    def test_invoice_type_reference_total_or_items_mismatch_not_paid(self):
        original = copy.deepcopy(self.invoice)
        for changes in ({'service_type': 'charging'}, {'reference_id': 'XE-OTHER'},
                        {'total_amount': self.invoice['total_amount'] + 1},
                        {'items': [{'description': 'Sai khoản phí', 'amount': 1}]},
                        {'total_amount': '2167'}, {'transaction_id': 'TXN-ALREADY-CREATED'}):
            with self.subTest(changes=changes):
                self.invoice.clear(); self.invoice.update(copy.deepcopy(original)); self.invoice.update(changes)
                before = copy.deepcopy(self.db.__dict__)
                with self.assertRaises(PaymentError) as error:
                    pay_invoice(self.db, PaymentSubmitRequest(invoice_id=self.invoice['id'], method='wallet'))
                self.assertEqual(error.exception.status_code, 409)
                self.assertEqual(before, self.db.__dict__)

    def test_changed_final_trip_fee_prevents_payment(self):
        self.db.bookings[0]['rental_trip']['total_fee'] += 1
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(PaymentError):
            pay_invoice(self.db, PaymentSubmitRequest(invoice_id=self.invoice['id'], method='wallet'))
        self.assertEqual(before, self.db.__dict__)

    def test_changed_current_hub_price_does_not_reprice_final_invoice(self):
        self.db.get_hub('hub-01')['pricing']['rental_bike_hourly'] = 999999
        result = pay_invoice(self.db, PaymentSubmitRequest(invoice_id=self.invoice['id'], method='wallet'))
        self.assertTrue(result.success)
        self.assertEqual(self.invoice['status'], 'paid')
