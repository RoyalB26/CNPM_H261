"""Xử lý booking quá hạn theo yêu cầu demo, không ghi dữ liệu khi GET."""

from datetime import datetime, timezone

from shared.booking_expiry import booking_expired
from shared.memory_store import MockDatabaseStore


def expire_rental_bookings(db: MockDatabaseStore, now: datetime | None = None) -> list[str]:
    """Hết hạn booking đang giữ, hoàn xe/chỗ đỗ qua logic hủy dùng chung.

    Kiểm tra toàn bộ thời hạn trước khi sửa; không hết hạn chuyến đã nhận xe.
    """
    now = now if now is not None else datetime.now(timezone.utc)
    active = db.user.get("active_services", {}).get("ride")
    expired = []
    for booking in db.get_bookings():
        if booking.get("plan_type") not in ("rental", "parking", "swap", "battery_swap", "charging") or booking.get("status") != "Đã xác nhận":
            continue
        bike_id = booking.get("resource_name", "").split(" · ")[0].strip()
        if booking.get("plan_type") == "rental" and active and active.get("vehicle_id") == bike_id:
            continue
        if booking_expired(booking, now):
            expired.append(booking)
    ids = [booking["id"] for booking in expired]
    if any(sum(b["id"] == booking_id for b in db.bookings) != 1 for booking_id in ids):
        raise ValueError("Booking cũ có mã trùng, chưa thể xử lý hết hạn")
    # Kiểm tra mọi quyền giữ xe trước vòng sửa, tránh hết hạn một phần khi
    # runtime cũ có hai booking cùng giữ xe hoặc reserved_by không khớp.
    for booking in expired:
        if booking.get("plan_type") == "rental":
            hub = db.get_hub(booking.get("hub_id"))
            bike_id = booking.get("resource_name", "").split(" · ")[0].strip()
            bike = next((b for b in hub.get("bikes", []) if b["id"] == bike_id), None) if hub else None
            if not db._rental_hold_owned(booking, bike):
                raise ValueError("Không xác định được booking đang giữ xe, chưa thể xử lý hết hạn")
    for booking in expired:
        db.cancel_booking(booking["id"])
        booking["status"] = "Hết hạn"
        booking["expired_at"] = now.isoformat()
    return ids
