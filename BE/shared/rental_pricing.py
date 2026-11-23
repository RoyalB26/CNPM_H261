"""Tính cước từ lúc xác nhận đặt xe; giữ cách tính cũ cho phiên thiếu mốc mới."""

from datetime import datetime
from decimal import Decimal, ROUND_CEILING


def rental_charge(ride: dict, ended_at: datetime, hourly_rate: int) -> dict:
    """Làm tròn lên phút và đồng; phiên cũ dùng số phút snapshot đã lưu.

    Từ chối mốc sai/mốc tương lai trước khi store thực hiện chuyển xe.
    """
    if type(hourly_rate) is not int or hourly_rate < 0:
        raise ValueError("Đơn giá thuê xe không hợp lệ")
    source = "billing_started_at" if ride.get("billing_started_at") is not None else "started_at"
    if ride.get(source) is not None:
        started_at = datetime.fromisoformat(ride[source])
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("Thời điểm tính phí phải có múi giờ")
        if ride.get("started_at") is not None:
            received_at = datetime.fromisoformat(ride["started_at"])
            if received_at.tzinfo is None or not started_at <= received_at <= ended_at:
                raise ValueError("Thời điểm nhận xe không nằm trong khoảng thuê hợp lệ")
        duration = ended_at - started_at
        if duration.total_seconds() < 0:
            raise ValueError("Thời điểm trả xe trước thời điểm nhận xe")
        microseconds = (duration.days * 86400 + duration.seconds) * 1_000_000 + duration.microseconds
        minutes = (microseconds + 60_000_000 - 1) // 60_000_000
    else:
        minutes = ride.get("elapsed_minutes")
        if type(minutes) is not int or minutes < 0:
            raise ValueError("Phiên cũ thiếu thời lượng thuê hợp lệ")
        source = "legacy_elapsed_minutes"
    fee = int((Decimal(minutes) * hourly_rate / 60).to_integral_value(rounding=ROUND_CEILING))
    return {"elapsed_minutes": minutes, "hourly_rate": hourly_rate,
            "total_fee": fee, "billing_source": source}
