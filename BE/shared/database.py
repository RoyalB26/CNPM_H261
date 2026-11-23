"""Đầu mối truy cập db và lưu JSON chung cho toàn bộ BE."""

import logging
import os
from pathlib import Path

from starlette.responses import JSONResponse

from .memory_store import MockDatabaseStore, db
from .json_store import JsonStateStore, PersistenceError


logger = logging.getLogger(__name__)

DEFAULT_RUNTIME_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "runtime_db.json"
)

runtime_path = os.environ.get(
    "BE_RUNTIME_PATH",
    str(DEFAULT_RUNTIME_PATH),
)

storage = JsonStateStore(db, runtime_path)
storage.reload()


def persist_change(change):
    """Chỉ trả thành công khi thay đổi đã được ghi xuống JSON."""
    try:
        return storage.commit(change)
    except PersistenceError:
        logger.exception("Không lưu được trạng thái backend")

        return JSONResponse(
            content={
                "status_code": "503",
                "error": 1,
                "error_code": "PERSISTENCE_UNAVAILABLE",
                "detail": (
                    "Không lưu được dữ liệu. "
                    "Thao tác chưa được áp dụng, vui lòng thử lại."
                ),
            },
            status_code=503,
        )


__all__ = [
    "MockDatabaseStore",
    "db",
    "storage",
    "persist_change",
]