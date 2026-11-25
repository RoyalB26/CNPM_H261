"""Giữ tương thích import cho các backend đang sử dụng mock_db."""

from shared.database import (
    MockDatabaseStore,
    RelocationError,
    db,
)

__all__ = [
    "MockDatabaseStore",
    "RelocationError",
    "db",
]