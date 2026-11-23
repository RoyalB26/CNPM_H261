"""Kiểm tra API User không truy cập bản ghi mang chủ khác, runtime hoàn toàn tạm."""

import copy
import os
from pathlib import Path
import sys
import tempfile


def run():
    with tempfile.TemporaryDirectory(prefix='ownership-gateway-') as directory:
        os.environ['BE_RUNTIME_PATH'] = str(Path(directory) / 'runtime.json')
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from starlette.testclient import TestClient
        from run_all import app
        from shared.database import db, storage
        from user.swaps import complete_swap

        rental = db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        charging = db.create_booking({'plan_type': 'charging', 'hub_id': 'hub-01',
                                      'personal_plate': '59-A1 999.99', 'charging_port': 'S01'})
        swap = db.create_booking({'plan_type': 'swap', 'hub_id': 'hub-02', 'battery_type': 'B48'})
        complete_swap(db, swap['id'])
        for booking in (rental, charging, swap):
            booking['user_id'] = 'USR-OTHER'
        swap['battery_swap_invoice']['user_id'] = 'USR-OTHER'
        foreign_report = {**copy.deepcopy(db.incidents[0]), 'id': 'INC-OTHER', 'user_id': 'USR-OTHER'}
        db.incidents.append(foreign_report)
        storage.commit(lambda candidate: None)
        before = storage.snapshot()
        disk = storage.path.read_bytes()
        prefix = '/api/v1/user'
        with TestClient(app) as client:
            response = client.get(prefix + '/bookings')
            assert response.status_code == 200, response.text
            assert not {rental['id'], charging['id'], swap['id']} & {b['id'] for b in response.json()}
            response = client.get(prefix + '/incidents')
            assert response.status_code == 200, response.text
            assert 'INC-OTHER' not in {r['id'] for r in response.json()}
            for path in (f"/bookings/{rental['id']}/start", f"/bookings/{rental['id']}/cancel",
                         f"/bookings/{charging['id']}/charging/start", f"/bookings/{swap['id']}/swap"):
                response = client.post(prefix + path)
                assert response.status_code == 404, (path, response.text)
            invoice_id = swap['battery_swap_invoice']['id']
            response = client.get(prefix + '/invoices/current', params={'type': 'swap', 'invoice_id': invoice_id})
            assert response.status_code == 404, response.text
            response = client.post(prefix + '/invoices/pay', json={'invoice_id': invoice_id, 'method': 'wallet'})
            assert response.status_code == 404, response.text
            assert storage.snapshot() == before
            assert storage.path.read_bytes() == disk
        assert all(b in {row['id'] for row in db.bookings} for b in (rental['id'], charging['id'], swap['id']))


if __name__ == '__main__':
    run()
