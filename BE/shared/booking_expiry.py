"""Đọc thời hạn booking; seed cũ chỉ có giờ hiển thị được giữ nguyên."""

from datetime import datetime


def booking_expired(booking: dict, now: datetime) -> bool:
    """Hết hạn tại đúng expires_at; không suy đoán ngày từ hold_until cũ."""
    value = booking.get("expires_at")
    if value is None:
        return False
    expires_at = datetime.fromisoformat(value)
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError("Thời hạn booking phải có múi giờ")
    return now >= expires_at
