"""Giữ import cũ; phần triển khai đã chuyển sang shared.persistence.seed_loader."""

from .persistence.seed_loader import (
    DEFAULT_SEED_PATH,
    SEED_TYPES,
    SeedLoadError,
    load_seed,
    reject_duplicate_keys,
    require_type,
)

__all__ = ['DEFAULT_SEED_PATH', 'SEED_TYPES', 'SeedLoadError', 'load_seed', 'reject_duplicate_keys', 'require_type']
