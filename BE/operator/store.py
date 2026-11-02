"""Đầu mối truy cập store dùng chung của backend Operator."""

from mock_db import db, RelocationError

__all__ = ["db", "RelocationError"]