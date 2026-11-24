"""Giữ import cũ; phần triển khai đã chuyển sang shared.persistence.memory_store."""

from .persistence.memory_store import (
    MockDatabaseStore,
    RelocationError,
    db,
)

__all__ = ['MockDatabaseStore', 'RelocationError', 'db']
