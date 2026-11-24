"""Kiểm tra package, singleton và đường dẫn JSON trong tiến trình cô lập."""

import operator
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType


def run() -> None:
    """Import từ ngoài repository không xóa schemas khác hoặc tạo db thứ hai."""
    backend = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix='be-package-import-') as directory:
        runtime = Path(directory) / 'runtime.json'
        os.environ['BE_RUNTIME_PATH'] = str(runtime)
        os.environ['BE_BOOKING_EXPIRY_INTERVAL_SECONDS'] = '3600'
        sys.path.insert(0, str(backend))
        # Mô phỏng một package schemas không liên quan đã được tiến trình dùng.
        schemas = ModuleType('schemas')
        child = ModuleType('schemas.unrelated')
        sys.modules['schemas'] = schemas
        sys.modules['schemas.unrelated'] = child
        stdlib_operator = operator

        # Staff vẫn nạp độc lập được dù không chạy từ thư mục repository.
        direct_staff = runpy.run_path(str(backend / 'staff' / 'main.py'), run_name='staff_import_check')
        import run_all
        from shared import database, json_store, memory_store, seed_loader
        from shared.persistence import json_store as actual_json
        from shared.persistence import memory_store as actual_memory
        from shared.persistence import seed_loader as actual_seed
        import mock_db
        from BE.operator import store as operator_store
        from starlette.testclient import TestClient

        assert sys.modules['schemas'] is schemas
        assert sys.modules['schemas.unrelated'] is child
        assert sys.modules['operator'] is stdlib_operator
        assert all(name not in sys.modules for name in ('be_user_main', 'be_operator_main', 'be_staff_main'))
        assert run_all.user_mod.__name__ == 'BE.user.main'
        assert run_all.op_mod.__name__ == 'BE.operator.main'
        assert run_all.staff_mod.__name__ == 'BE.staff.main'
        assert memory_store.MockDatabaseStore is actual_memory.MockDatabaseStore is database.MockDatabaseStore
        assert json_store.JsonStateStore is actual_json.JsonStateStore
        assert json_store.PersistenceError is actual_json.PersistenceError
        assert seed_loader.load_seed is actual_seed.load_seed
        assert seed_loader.DEFAULT_SEED_PATH == backend / 'data' / 'mock_seed.json'
        assert database.DEFAULT_RUNTIME_PATH == backend / 'data' / 'runtime_db.json'
        assert database.storage.path == runtime.resolve()
        assert all(instance is database.db for instance in (
            actual_memory.db, memory_store.db, mock_db.db, operator_store.db,
            direct_staff['db'], run_all.staff_mod.db,
        ))
        assert operator_store.RelocationError is database.RelocationError is memory_store.RelocationError
        before = database.storage.snapshot()
        assert not runtime.exists()
        with TestClient(run_all.app) as client:
            root = client.get('/')
            assert root.status_code == 200
            assert root.json()['routes_count'] == sum(len(mod.routes) for mod in (
                run_all.user_mod, run_all.op_mod, run_all.staff_mod))
            for path in ('/api/v1/user/profile', '/api/v1/operator/hubs', '/api/v1/staff/profile'):
                response = client.get(path)
                assert response.status_code == 200, (path, response.text)
        assert before == database.storage.snapshot()
        assert not runtime.exists(), 'Chỉ import/GET không được ghi file runtime'


if __name__ == '__main__':
    run()
