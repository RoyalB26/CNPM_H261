import os
from pathlib import Path
import sys
import tempfile
from typing import Iterator

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
BE_DIR = ROOT_DIR / "BE"

# Đặt runtime test ra file tạm TRƯỚC khi import BE/shared/database.py
_TEST_RUNTIME_FILE = Path(tempfile.gettempdir()) / f"cnpm_pytest_runtime_{os.getpid()}.json"
os.environ["BE_RUNTIME_PATH"] = str(_TEST_RUNTIME_FILE)

for path_str in (str(ROOT_DIR), str(BE_DIR)):
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import BE.mock_db as _shared_mock_db  # noqa: E402
from shared.authentication import challenges, sessions  # noqa: E402
from shared.database import storage  # noqa: E402

sys.modules["mock_db"] = _shared_mock_db
MockDatabaseStore = _shared_mock_db.MockDatabaseStore
db = _shared_mock_db.db


@pytest.fixture(autouse=True)
def reset_shared_mock_db() -> Iterator[MockDatabaseStore]:
    """Reset MockDatabaseStore, file runtime và phiên đăng nhập trước/sau mỗi test."""
    storage.reset_to_seed()
    sessions.clear()
    challenges.clear()
    yield db
    storage.reset_to_seed()
    sessions.clear()
    challenges.clear()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_runtime_file() -> Iterator[None]:
    """Xóa file runtime tạm sau khi kết thúc phiên pytest."""
    yield
    _TEST_RUNTIME_FILE.unlink(missing_ok=True)