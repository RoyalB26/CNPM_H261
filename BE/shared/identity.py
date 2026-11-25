"""Danh tính tài khoản hiện hành, độc lập giữa các request."""
from contextvars import ContextVar

current_user_id = ContextVar("current_user_id", default=None)
