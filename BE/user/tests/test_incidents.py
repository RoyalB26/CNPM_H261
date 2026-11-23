"""Kiểm tra liên kết báo cáo–phiếu và đọc kết quả mà không ghi dữ liệu."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.incidents import create_report, report_view
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
