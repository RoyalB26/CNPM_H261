"""Giữ import cũ; phần triển khai đã chuyển sang shared.persistence.json_store."""

from .persistence.json_store import (
    JsonStateStore,
    PersistenceError,
)

__all__ = ['JsonStateStore', 'PersistenceError']
