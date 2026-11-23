"""Kiểm tra phiên sạc, hóa đơn kWh và thao tác lặp trong môi trường mock."""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pydantic import ValidationError
from shared.memory_store import MockDatabaseStore
from user.charging import ChargingError, start_charging, stop_charging
from user.payments import PaymentError, pay_invoice
from user.schemas.service import StopChargingRequest
from user.schemas.payment import PaymentSubmitRequest


class ChargingSessionTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.db.user['active_services']['charging'] = None
        self.booking = self.db.create_booking({'plan_type': 'charging', 'hub_id': 'hub-01',
                                               'personal_plate': '59-A1 999.99', 'charging_port': 'S01'})

    def test_start_stop_pay_once_and_snapshot_rate(self):
        hub = self.db.get_hub('hub-01'); held_count = hub['available_chargers']
        session = start_charging(self.db, self.booking['id']).charging
        self.assertEqual(hub['available_chargers'], held_count)
        self.assertEqual(self.booking['status'], 'Đang sử dụng')
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError):
            start_charging(self.db, self.booking['id'])
        self.assertEqual(before, self.db.__dict__)
        hub['ports'][0]['rate_per_kwh'] = 99999
        result = stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=2.4, final_charge=80))
        self.assertEqual(result.total_fee, 8400)
        self.assertEqual(hub['available_chargers'], held_count + 1)
        self.assertTrue(hub['ports'][0]['is_available'])
        self.assertEqual(self.booking['status'], 'Hoàn thành')
        self.assertEqual(self.booking['charging_session']['measurement_source'], 'mock_input')
        self.assertIsNone(self.db.user['active_services']['charging'])
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError):
            stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=2.4))
        self.assertEqual(before, self.db.__dict__)
        payment = PaymentSubmitRequest(invoice_id=result.invoice.id, method='wallet', amount=8400)
        pay_invoice(self.db, payment)
        self.assertEqual(self.booking['charging_invoice']['status'], 'paid')
        with self.assertRaises(PaymentError):
            pay_invoice(self.db, payment)

    def test_invalid_energy_schema(self):
        for value in [-1, float('nan'), float('inf'), True, '2.4', None]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                StopChargingRequest(session_id='CHG-test', power_consumed_kwh=value)

    def test_payment_rejects_changed_final_energy_without_mutation(self):
        """Không thanh toán nếu lịch sử điện năng lệch hóa đơn đã chốt."""
        session = start_charging(self.db, self.booking['id']).charging
        result = stop_charging(self.db, StopChargingRequest(
            session_id=session.session_id, power_consumed_kwh=2.4))
        self.booking['charging_session']['power_consumed_kwh'] = 3
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(PaymentError) as error:
            pay_invoice(self.db, PaymentSubmitRequest(invoice_id=result.invoice.id, method='wallet'))
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(before, self.db.__dict__)

    def test_expired_or_maintenance_cannot_start(self):
        self.booking['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError):
            start_charging(self.db, self.booking['id'])
        self.assertEqual(before, self.db.__dict__)
        self.booking['expires_at'] = (datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
        self.db.get_hub('hub-01')['ports'][0]['status'] = 'Đang bảo trì'
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError):
            start_charging(self.db, self.booking['id'])
        self.assertEqual(before, self.db.__dict__)

    def test_wrong_session_or_reduced_energy_does_not_mutate(self):
        session = start_charging(self.db, self.booking['id']).charging
        self.db.user['active_services']['charging']['power_consumed_kwh'] = 1.5
        for session_id, energy in [('WRONG', 2.4), (session.session_id, 1.0)]:
            before = copy.deepcopy(self.db.__dict__)
            with self.assertRaises(ChargingError):
                stop_charging(self.db, StopChargingRequest(session_id=session_id, power_consumed_kwh=energy))
            self.assertEqual(before, self.db.__dict__)

    def test_stop_preserves_maintenance_lock(self):
        session = start_charging(self.db, self.booking['id']).charging
        hub = self.db.get_hub('hub-01'); count = hub['available_chargers']
        hub['ports'][0]['status'] = 'Đang bảo trì'
        stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=0.001))
        self.assertEqual(self.booking['charging_invoice']['total_amount'], 4)
        self.assertFalse(hub['ports'][0]['is_available'])
        self.assertEqual(hub['ports'][0]['status'], 'Đang bảo trì')
        self.assertEqual(hub['available_chargers'], count)

    def test_seed_session_can_finish_without_fabricated_start(self):
        self.db.reset(); original_count = self.db.get_hub('hub-01')['available_chargers']
        result = stop_charging(self.db, StopChargingRequest(session_id='CHG-302', power_consumed_kwh=2.4))
        self.assertEqual(result.total_fee, 8400)
        history = self.db.bookings[0]['charging_session']
        self.assertNotIn('started_at', history)
        self.assertEqual(self.db.get_hub('hub-01')['available_chargers'], original_count)

    def test_future_clock_rejected_before_state_changes(self):
        session = start_charging(self.db, self.booking['id']).charging
        self.db.user['active_services']['charging']['started_at'] = (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ChargingError):
            stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=2.4))
        self.assertEqual(before, self.db.__dict__)

    def test_inactive_hub_can_end_session_without_reopening_port(self):
        session = start_charging(self.db, self.booking['id']).charging
        hub = self.db.get_hub('hub-01')
        count = hub['available_chargers']
        hub['status'] = 'DEACTIVATED'
        result = stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=2.4))
        self.assertEqual(result.total_fee, 8400)
        self.assertIsNone(self.db.user['active_services']['charging'])
        self.assertEqual(self.booking['status'], 'Hoàn thành')
        self.assertFalse(hub['ports'][0]['is_available'])
        self.assertEqual(hub['ports'][0]['status'], 'Không khả dụng')
        self.assertEqual(hub['available_chargers'], count)

    def test_mismatched_session_rate_or_port_occupancy_cannot_finish(self):
        for fault in ('session', 'rate', 'missing_rate', 'occupancy', 'duplicate_port'):
            with self.subTest(fault=fault):
                self.setUp()
                session = start_charging(self.db, self.booking['id']).charging
                port = self.db.get_hub('hub-01')['ports'][0]
                if fault == 'session':
                    self.booking['charging_session']['session_id'] = 'CHG-OTHER'
                elif fault == 'rate':
                    self.db.user['active_services']['charging']['rate_per_kwh'] = 1
                elif fault == 'missing_rate':
                    self.db.user['active_services']['charging'].pop('rate_per_kwh')
                    self.booking.pop('charging_rate_per_kwh')
                elif fault == 'occupancy':
                    port.pop('occupied_by')
                else:
                    self.db.get_hub('hub-01')['ports'].append(copy.deepcopy(port))
                before = copy.deepcopy(self.db.__dict__)
                with self.assertRaises(ChargingError):
                    stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=2.4))
                self.assertEqual(before, self.db.__dict__)

    def test_zero_energy_creates_zero_invoice_and_can_be_paid_once(self):
        session = start_charging(self.db, self.booking['id']).charging
        result = stop_charging(self.db, StopChargingRequest(session_id=session.session_id, power_consumed_kwh=0))
        self.assertEqual(result.total_fee, 0)
        pay_invoice(self.db, PaymentSubmitRequest(invoice_id=result.invoice.id, method='wallet', amount=0))
        self.assertEqual(self.booking['charging_invoice']['status'], 'paid')

    def test_legacy_maintenance_flag_cannot_remain_available_on_stop(self):
        self.db.reset()
        port = next(p for p in self.db.get_hub('hub-01')['ports'] if p['id'] == 'S03')
        port.update(status='Đang bảo trì', is_available=True)
        stop_charging(self.db, StopChargingRequest(session_id='CHG-302', power_consumed_kwh=2.4))
        self.assertEqual(port['status'], 'Đang bảo trì')
        self.assertFalse(port['is_available'])
