from pathlib import Path
import sys
from typing import Iterator

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
BE_DIR = ROOT_DIR / "BE"

for path_str in (str(ROOT_DIR), str(BE_DIR)):
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import BE.mock_db as _shared_mock_db  # noqa: E402

sys.modules["mock_db"] = _shared_mock_db
MockDatabaseStore = _shared_mock_db.MockDatabaseStore
db = _shared_mock_db.db

@pytest.fixture(autouse=True)
def reset_shared_mock_db() -> Iterator[MockDatabaseStore]:
    """Reset MockDatabaseStore before and after test."""
    db.reset()
    yield db
    db.reset()