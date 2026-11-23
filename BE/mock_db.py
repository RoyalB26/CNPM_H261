"""Giữ tương thích import cho các backend đang sử dụng mock_db."""

from shared.memory_store import (
    MockDatabaseStore,
    RelocationError,
    db,
)

__all__ = [
    "MockDatabaseStore",
    "RelocationError",
    "db",
]