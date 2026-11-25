"""Đầu mối truy cập db và lưu JSON chung cho toàn bộ BE."""

import logging
import os
from pathlib import Path

from starlette.responses import JSONResponse, Response

from .persistence.memory_store import MockDatabaseStore, RelocationError, db
from .persistence.json_store import JsonStateStore, PersistenceError


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


class _UncommittedResponse(Exception):
    """Dừng commit khi callback trả lỗi HTTP hoặc không thay đổi dữ liệu."""

    def __init__(self, result):
        self.result = result


def persist_change(change):
    """Callback đồng bộ chỉ sửa candidate; lưu JSON trước khi áp dụng RAM.

    Callback trả lỗi HTTP thì bỏ toàn bộ candidate. Không ghi file khi dữ
    liệu không đổi. Quy tắc này dùng được cho handler User và Operator.
    """
    def guarded_change(candidate):
        before = storage.snapshot()
        result = change(candidate)
        if (isinstance(result, Response) and result.status_code >= 400) or candidate.__dict__ == before:
            raise _UncommittedResponse(result)
        return result

    try:
        return storage.commit(guarded_change)
    except _UncommittedResponse as exc:
        return exc.result
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
    "RelocationError",
    "db",
    "storage",
    "persist_change",
]
