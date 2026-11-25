"""Kiểm tra auth mới đi qua handler/candidate đã tách, chỉ dùng runtime tạm."""

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


def run():
    with tempfile.TemporaryDirectory(prefix='be-user-merged-auth-') as directory:
        os.environ['BE_RUNTIME_PATH'] = str(Path(directory) / 'runtime.json')
        os.environ['BE_BOOKING_EXPIRY_INTERVAL_SECONDS'] = '3600'
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from run_all import app
        from shared.database import db, storage
        from shared.json_store import PersistenceError
        from starlette.testclient import TestClient

        seed_profile = copy.deepcopy(db.__dict__['user'])
        with TestClient(app) as client:
            profiles = []
            for index in (1, 2):
                response = client.post('/api/auth/register', json={
                    'full_name': f'Người kiểm thử {index}', 'email': f'merge{index}@example.com',
                    'phone': f'090000000{index}', 'password': 'password123', 'confirm_password': 'password123'})
                assert response.status_code == 201, response.text
                profiles.append(response.json()['user'])
            logged = client.post('/api/auth/login', json={'email': 'merge1@example.com', 'password': 'password123'})
            assert logged.status_code == 200, logged.text
            headers = {'Authorization': 'Bearer ' + logged.json()['token']}
            held = client.post('/api/v1/user/bookings', headers=headers, json={
                'plan_type': 'rental', 'hub_id': 'hub-02', 'resource_name': 'XE-052', 'destination_hub_id': 'hub-04'})
            assert held.status_code == 200, held.text
            assert held.json()['user_id'] == profiles[0]['id']
            # Snapshot ghi JSON phải giữ hồ sơ seed, không thay bằng User hiện tại.
            saved = json.loads(storage.path.read_text(encoding='utf-8'))
            assert saved['user'] == seed_profile == db.__dict__['user']

            updated = client.put('/api/v1/user/profile', headers=headers, json={'email': 'NewMerge@Example.com'})
            assert updated.status_code == 200, updated.text
            assert updated.json()['user']['email'] == 'newmerge@example.com'
            assert client.post('/api/auth/login', json={'email': 'newmerge@example.com', 'password': 'password123'}).status_code == 200
            assert client.post('/api/auth/login', json={'email': 'merge1@example.com', 'password': 'password123'}).status_code == 401

            before, disk = storage.snapshot(), storage.path.read_bytes()
            collision = client.put('/api/v1/user/profile', headers=headers, json={'phone': profiles[1]['phone']})
            assert collision.status_code == 409, collision.text
            assert before == storage.snapshot() and disk == storage.path.read_bytes()
            with patch.object(storage, '_write', side_effect=PersistenceError('Lỗi ghi hồ sơ mới')):
                failed = client.put('/api/v1/user/profile', headers=headers, json={'phone': '0900999999'})
                assert failed.status_code == 503, failed.text
            assert before == storage.snapshot() and disk == storage.path.read_bytes()
            storage.reload()
            loaded = client.get('/api/v1/user/profile', headers=headers)
            assert loaded.status_code == 200, loaded.text
            assert loaded.json()['id'] == profiles[0]['id'] and loaded.json()['email'] == 'newmerge@example.com'
            assert db.__dict__['user'] == seed_profile


if __name__ == '__main__':
    run()
