"""Chứng minh lifecycle Gateway tự quét và không chạy xen giữa request HTTP."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from integration_support import authorize_client, confirm_payment, VNPAY_TEST_CONFIG
from pathlib import Path
import sys
import tempfile
import time


def run():
    """Chỉ dùng runtime tạm, import Gateway sau khi đã đặt biến môi trường."""
    with tempfile.TemporaryDirectory(prefix='expiry-gateway-') as directory:
        runtime = Path(directory) / 'runtime.json'
        os.environ.update(VNPAY_TEST_CONFIG)
        os.environ['BE_RUNTIME_PATH'] = str(runtime)
        os.environ['BE_BOOKING_EXPIRY_INTERVAL_SECONDS'] = '0.005'
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient
        from run_all import app
        from shared.database import db, storage

        bike_count = db.get_hub('hub-02')['available_bikes']
        rental = db.create_booking({'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052'})
        rental['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        swap = db.create_booking({'plan_type': 'swap', 'hub_id': 'hub-02', 'battery_type': 'B48'})
        storage.commit(lambda candidate: None)

        async def blocking_request(request):
            # Chỉ route thử trong tiến trình con này: tạo hạn quá khứ trong
            # khi request đang giữ khóa để kiểm tra worker không chen vào RAM.
            assert app.state.request_lock.locked()
            booking = next(b for b in db.bookings if b['id'] == swap['id'])
            booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            await asyncio.sleep(0.03)
            assert booking['status'] == 'Đã xác nhận', 'Worker đã chạy xen giữa request'
            return JSONResponse({'lock_shared': True})

        app.router.routes.append(Route('/_test-expiry-lock', blocking_request))
        with TestClient(app) as client:
            authorize_client(client, db)
            worker = app.state.expiry_task
            assert not worker.done()

            def wait_expired(booking_id):
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    response = client.get('/api/v1/user/bookings')
                    assert response.status_code == 200, response.text
                    found = next(b for b in response.json() if b['id'] == booking_id)
                    if found['status'] == 'Hết hạn':
                        return found
                    time.sleep(0.005)
                raise AssertionError('Worker không tự xử lý booking quá hạn')

            wait_expired(rental['id'])
            assert db.get_hub('hub-02')['available_bikes'] == bike_count
            response = client.get('/_test-expiry-lock')
            assert response.status_code == 200, response.text
            wait_expired(swap['id'])
            response = client.post('/api/v1/user/bookings/expire')
            assert response.status_code == 200, response.text
            assert response.json()['expired_count'] == 0
            assert db.get_hub('hub-02')['available_bikes'] == bike_count
            saved = json.loads(runtime.read_text(encoding='utf-8'))
            for booking_id in (rental['id'], swap['id']):
                found = next(b for b in saved['bookings'] if b['id'] == booking_id)
                assert found['status'] == 'Hết hạn'
        assert worker.done() and worker.cancelled(), 'Worker chưa dừng sau shutdown'


if __name__ == '__main__':
    run()
