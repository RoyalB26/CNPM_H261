"""Tính cước thuê xe từ lúc nhận đến lúc trả, không tính thời gian giữ chỗ."""

from datetime import datetime
from decimal import Decimal, ROUND_CEILING


def rental_charge(ride: dict, ended_at: datetime, hourly_rate: int) -> dict:
    """Làm tròn lên phút và đồng; phiên cũ dùng số phút snapshot đã lưu.

    Từ chối mốc sai/mốc tương lai trước khi store thực hiện chuyển xe.
    """
    if type(hourly_rate) is not int or hourly_rate < 0:
        raise ValueError("Đơn giá thuê xe không hợp lệ")
    if ride.get("started_at") is not None:
        started_at = datetime.fromisoformat(ride["started_at"])
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("Thời điểm nhận xe phải có múi giờ")
        duration = ended_at - started_at
        if duration.total_seconds() < 0:
            raise ValueError("Thời điểm trả xe trước thời điểm nhận xe")
        microseconds = (duration.days * 86400 + duration.seconds) * 1_000_000 + duration.microseconds
        minutes = (microseconds + 60_000_000 - 1) // 60_000_000
        source = "started_at"
    else:
        minutes = ride.get("elapsed_minutes")
        if type(minutes) is not int or minutes < 0:
            raise ValueError("Phiên cũ thiếu thời lượng thuê hợp lệ")
        source = "legacy_elapsed_minutes"
    fee = int((Decimal(minutes) * hourly_rate / 60).to_integral_value(rounding=ROUND_CEILING))
    return {"elapsed_minutes": minutes, "hourly_rate": hourly_rate,
            "total_fee": fee, "billing_source": source}
