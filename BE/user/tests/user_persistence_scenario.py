"""Kiểm chứng ghi candidate trong tiến trình riêng, không mở runtime của nhóm."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


def run(mode: str) -> None:
    """User lưu được độc lập middleware, cả alias cũ và URL versioned."""
    with tempfile.TemporaryDirectory(prefix='be-user-write-contract-') as directory:
        os.environ['BE_RUNTIME_PATH'] = str(Path(directory) / 'runtime.json')
        os.environ['BE_BOOKING_EXPIRY_INTERVAL_SECONDS'] = '3600'
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from starlette.responses import JSONResponse
        from starlette.testclient import TestClient
        from shared.database import db, persist_change, storage
        from shared.json_store import PersistenceError
        if mode == 'gateway':
            from run_all import app
            prefix = '/api/v1/user'
            profile_path = prefix + '/profile'
        else:
            from user.main import app
            prefix = '/api'
            profile_path = '/api/user/profile'

        before = storage.snapshot()

        def rejected(candidate):
            candidate.user['full_name'] = 'Không được lưu'
            return JSONResponse({'error': 'Từ chối sau khi sửa candidate'}, status_code=409)

        with patch.object(storage, '_write') as write:
            assert persist_change(rejected).status_code == 409
            write.assert_not_called()
        assert before == storage.snapshot() and not storage.path.exists()

        def interrupted(candidate):
            candidate.hubs.clear()
            raise ValueError('Lỗi nghiệp vụ sau khi sửa candidate')

        try:
            persist_change(interrupted)
        except ValueError:
            pass
        else:
            raise AssertionError('Lỗi callback không được nuốt')
        assert before == storage.snapshot() and not storage.path.exists()

        with TestClient(app) as client:
            def disk():
                return storage.path.read_bytes() if storage.path.exists() else None

            def mutate(path, payload=None, method='POST'):
                """Mỗi loại thao tác đều thử lỗi ghi, rồi ghi thật đúng một lần."""
                url = path if path.startswith('/api/') else prefix + path
                kwargs = {'json': payload} if payload is not None else {}
                snapshot, saved = storage.snapshot(), disk()
                with patch.object(storage, '_write', side_effect=PersistenceError('Lỗi ghi mô phỏng')) as write:
                    response = client.request(method, url, **kwargs)
                    assert response.status_code == 503, (url, response.text)
                    assert write.call_count == 1
                assert snapshot == storage.snapshot() and saved == disk(), url
                actual_write = storage._write

                def checked_write(state):
                    # Bắt lỗi sửa db thật trước rồi mới hoàn nguyên/lưu qua middleware.
                    assert snapshot == storage.snapshot(), url
                    return actual_write(state)

                with patch.object(storage, '_write', side_effect=checked_write) as write:
                    response = client.request(method, url, **kwargs)
                    assert response.status_code == 200, (url, response.text)
                    assert write.call_count == 1, (url, write.call_count)
                assert snapshot != storage.snapshot(), url
                return response.json()

            mutate(profile_path, {'full_name': 'User kiểm thử candidate'}, method='PUT')
            snapshot, saved = storage.snapshot(), disk()
            with patch.object(storage, '_write') as write:
                assert client.put(profile_path, json={'full_name': 'User kiểm thử candidate'}).status_code == 200
                assert client.get(prefix + '/bookings').status_code == 200
                assert client.post(prefix + '/bookings/expire').status_code == 200
                assert client.post(prefix + '/bookings', json={'plan_type': 'rental', 'hub_id': 'missing',
                                                              'resource_name': 'missing'}).status_code == 409
                assert client.post(prefix + '/bookings', json={}).status_code == 422
                assert client.post(prefix + '/bookings/missing/start').status_code == 404
                write.assert_not_called()
            assert snapshot == storage.snapshot() and saved == disk()

            mutate('/services/return-vehicle', {'trip_id': 'TRIP-8821', 'hub_id': 'hub-04'})
            mutate('/services/charging/stop', {'session_id': 'CHG-302', 'power_consumed_kwh': 2.4})
            rental = {'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052',
                      'destination_hub_id': 'hub-04'}
            held = mutate('/bookings', rental)
            mutate(f"/bookings/{held['id']}/cancel")
            held = mutate('/bookings', rental)
            ride = mutate(f"/bookings/{held['id']}/start")['ride']
            mutate('/services/return-vehicle', {'trip_id': ride['trip_id'], 'hub_id': 'hub-04'})
            invoice = client.get(prefix + '/invoices/current', params={'type': 'rental', 'trip_id': ride['trip_id']}).json()
            mutate('/invoices/pay', {'invoice_id': invoice['id'], 'method': 'wallet'})
            held = mutate('/bookings', {'plan_type': 'charging', 'hub_id': 'hub-01',
                                        'personal_plate': '59-A1 999.99', 'charging_port': 'S01'})
            session = mutate(f"/bookings/{held['id']}/charging/start")['charging']
            mutate('/services/charging/stop', {'session_id': session['session_id'], 'power_consumed_kwh': 2.4})
            held = mutate('/bookings', {'plan_type': 'swap', 'hub_id': 'hub-02', 'battery_type': 'B48'})
            mutate(f"/bookings/{held['id']}/swap")
            mutate('/incidents', {'resource_type': 'Phương tiện', 'resource_code': 'XE-052',
                                  'hub_name': 'Hub Đại học Quốc Tế', 'incident_type': 'Lỗi khóa',
                                  'description': 'Kiểm thử ghi báo cáo và phiếu bảo trì cùng nhau'})
            held = mutate('/bookings', {'plan_type': 'parking', 'hub_id': 'hub-02', 'personal_plate': '59-A1 888.88'})

            def make_expired(candidate):
                booking = next(b for b in candidate.bookings if b['id'] == held['id'])
                booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()

            storage.commit(make_expired)
            expired = mutate('/bookings/expire')
            assert held['id'] in expired['expired_booking_ids']


if __name__ == '__main__':
    run(sys.argv[1])
