"""Kiểm tra liên kết báo cáo–phiếu và đọc kết quả mà không ghi dữ liệu."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.incidents import IncidentError, create_report, report_view
from pydantic import ValidationError
from user.schemas.incident import CreateIncidentReportRequest


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.payload = dict(resource_type='Phương tiện', resource_code='XE-052',
                            hub_name='Hub Đại học Bách khoa', incident_type='Lỗi khóa', description='Không mở được khóa')

    def test_correct_hub_and_status_projection(self):
        report = create_report(self.db, CreateIncidentReportRequest(**self.payload))
        ticket = self.db.maintenance_tickets[0]
        self.assertEqual(ticket['hub_id'], 'hub-02')
        self.assertEqual(ticket['code'], report.maintenance_ticket_code)
        ticket.update(status='ASSIGNED', operator_notes='Đã phân công kỹ thuật viên')
        self.assertEqual(report_view(self.db, self.db.incidents[0]).operator_note, ticket['operator_notes'])
        self.db.resolve_maintenance(ticket['code'], 'Đã sửa khóa')
        before = copy.deepcopy(self.db.__dict__)
        result = report_view(self.db, self.db.incidents[0])
        self.assertEqual(result.status, 'Đã giải quyết')
        self.assertEqual(result.operator_note, 'Đã sửa khóa')
        self.assertEqual(before, self.db.__dict__)

    def test_unknown_hub_does_not_create_records(self):
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(ValueError):
            create_report(self.db, CreateIncidentReportRequest(**{**self.payload, 'hub_name': 'UNKNOWN'}))
        self.assertEqual(before, self.db.__dict__)

    def test_legacy_seed_read_does_not_mutate(self):
        before = copy.deepcopy(self.db.__dict__)
        result = report_view(self.db, self.db.incidents[0])
        self.assertEqual(result.resource_code, 'XE-024')
        self.assertEqual(before, self.db.__dict__)

    def test_unknown_wrong_hub_or_wrong_type_resource_not_created(self):
        for changes in ({'resource_code': 'UNKNOWN'}, {'hub_name': 'Hub Đại học Quốc Tế'},
                        {'resource_type': 'Cổng sạc', 'resource_code': 'XE-052'}):
            with self.subTest(changes=changes):
                before = copy.deepcopy(self.db.__dict__)
                with self.assertRaises(IncidentError) as error:
                    create_report(self.db, CreateIncidentReportRequest(**{**self.payload, **changes}))
                self.assertEqual(error.exception.status_code, 404)
                self.assertEqual(before, self.db.__dict__)

    def test_resource_code_is_normalized_to_known_identifier(self):
        report = create_report(self.db, CreateIncidentReportRequest(**{**self.payload, 'resource_code': 'xe-052'}))
        self.assertEqual(report.resource_code, 'XE-052')
        self.assertEqual(report.hub_id, 'hub-02')
        self.assertEqual(self.db.maintenance_tickets[0]['device_code'], 'XE-052')

    def test_all_supported_resource_types_use_hub_catalog(self):
        for kind, code in (('Chỗ đỗ', 'P11'), ('Cổng sạc', 'S05'), ('Pin', 'B48'),
                           ('Trạm pin', 'B48'), ('Cơ sở hạ tầng', 'HUB-02')):
            with self.subTest(kind=kind):
                if kind == 'Cổng sạc':
                    code = self.db.get_hub('hub-02')['ports'][0]['id']
                report = create_report(self.db, CreateIncidentReportRequest(**{
                    **self.payload, 'resource_type': kind, 'resource_code': code}))
                self.assertEqual(report.hub_id, 'hub-02')

    def test_active_vehicle_can_be_reported_at_receiving_hub(self):
        self.db.user['active_services']['ride'] = None
        booking = self.db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        self.db.start_ride(booking['id'])
        report = create_report(self.db, CreateIncidentReportRequest(**{
            **self.payload, 'hub_name': 'Hub Đại học Quốc Tế'}))
        self.assertEqual(report.hub_id, 'hub-04')

    def test_fake_image_attachment_and_unsupported_type_rejected_by_schema(self):
        for changes in ({'image_attached': True}, {'resource_type': 'UNKNOWN'}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                CreateIncidentReportRequest(**{**self.payload, **changes})

    def test_duplicate_or_mismatched_ticket_does_not_project_wrong_status(self):
        report = create_report(self.db, CreateIncidentReportRequest(**self.payload))
        ticket = self.db.maintenance_tickets[0]
        self.db.maintenance_tickets.append(copy.deepcopy(ticket))
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(IncidentError):
            report_view(self.db, self.db.incidents[0])
        self.assertEqual(before, self.db.__dict__)
        self.db.maintenance_tickets.pop()
        ticket['incident_id'] = 'INC-OTHER'
        before = copy.deepcopy(self.db.__dict__)
        with self.assertRaises(IncidentError):
            report_view(self.db, self.db.incidents[0])
        self.assertEqual(before, self.db.__dict__)
