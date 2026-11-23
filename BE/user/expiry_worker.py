"""Quét booking hết hạn trong Gateway một tiến trình, dùng chung khóa với HTTP."""

import asyncio
import copy
import logging
import math
from datetime import datetime

from shared.json_store import JsonStateStore
from .bookings import expire_rental_bookings


logger = logging.getLogger(__name__)


def expiry_interval(value: str = "5") -> float:
    """Đọc chu kỳ giây; từ chối cấu hình rỗng, không hữu hạn hoặc không dương."""
    interval = float(value)
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("BE_BOOKING_EXPIRY_INTERVAL_SECONDS phải là số giây dương, hữu hạn")
    return interval


async def sweep_expired_bookings(
    storage: JsonStateStore, request_lock: asyncio.Lock, now: datetime | None = None,
) -> list[str]:
    """Chuẩn bị trên bản sao; chỉ áp dụng RAM sau khi commit JSON thành công.

    Không ghi file khi không có booking quá hạn. Khóa phải là khóa đang được
    middleware dùng cho mọi request User/Operator/Staff trong cùng Gateway.
    """
    async with request_lock:
        candidate = copy.copy(storage.db)
        candidate.__dict__ = storage.snapshot()
        ids = expire_rental_bookings(candidate, now)
        if not ids:
            return []

        def change(next_state):
            next_state.__dict__.update(candidate.__dict__)

        storage.commit(change)
        return ids


async def run_expiry_worker(
    storage: JsonStateStore, request_lock: asyncio.Lock, interval_seconds: float,
) -> None:
    """Quét ngay khi chạy rồi định kỳ; lỗi một lượt được ghi log và thử lượt sau.

    Không nuốt CancelledError để Gateway có thể dừng worker khi shutdown.
    """
    if not math.isfinite(interval_seconds) or interval_seconds <= 0:
        raise ValueError("Chu kỳ quét hết hạn phải dương và hữu hạn")
    while True:
        try:
            ids = await sweep_expired_bookings(storage, request_lock)
            if ids:
                logger.info("Đã xử lý %d booking hết hạn", len(ids))
        except Exception:
            logger.exception("Quét booking hết hạn thất bại; sẽ thử lại ở lượt tiếp theo")
        await asyncio.sleep(interval_seconds)
