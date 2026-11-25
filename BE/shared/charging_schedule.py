"""Lịch sạc [bắt đầu, kết thúc), hàng đợi ưu tiên pin thấp và FIFO."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from starlette.exceptions import HTTPException
from .notifications import notify


def utc_now():
    return datetime.now(timezone.utc)


def parse_time(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise HTTPException(422, "Thời gian phải là ISO 8601 có múi giờ")


def overlaps(start, end, other_start, other_end):
    return start < other_end and other_start < end


def rows(store):
    return store.operator_mock.get("charging_schedule", [])


def scheduled_blocked(store, hub_id, port_id, start=None, end=None):
    start = start or utc_now()
    end = end or start + timedelta(minutes=15)
    return any(row["status"] == "RESERVED" and row["hub_id"] == hub_id
               and row.get("port_id") == port_id
               and overlaps(start, end, parse_time(row["starts_at"]), parse_time(row["ends_at"]))
               for row in rows(store))


def usable_port(store, hub, port):
    from .charging_reservations import charging_port_blocked
    return (hub["status"] == "ACTIVE" and not port.get("disabled")
            and port.get("is_available") and port.get("status") == "Sẵn sàng"
            and not port.get("reserved_by") and not port.get("occupied_by")
            and not charging_port_blocked(store, hub, port["id"], check_schedule=False))


def choose_port(store, row):
    hub = store.get_hub(row["hub_id"])
    if hub is None:
        return None
    return next((p for p in hub.get("ports", []) if usable_port(store, hub, p)
                 and (row.get("requested_port_id") is None or p["id"] == row["requested_port_id"])
                 and not scheduled_blocked(store, hub["id"], p["id"],
                     parse_time(row["starts_at"]), parse_time(row["ends_at"]))), None)


def reconcile_schedule(store, now=None):
    now = now or utc_now()
    for row in rows(store):
        if row["status"] in ("RESERVED", "WAITING") and parse_time(row["ends_at"]) <= now:
            row["status"] = "MISSED"
            notify(store, row["id"] + ":missed", row["user_id"], "Lịch sạc đã hết giờ", row["id"])
        if row["status"] == "IN_SERVICE":
            booking = next((b for b in store.bookings if b["id"] == row.get("booking_id")), {})
            if (booking.get("charging_session") or {}).get("status") == "Hoàn thành":
                row["status"] = "COMPLETED"
        if row["status"] == "RESERVED":
            hub = store.get_hub(row["hub_id"])
            port = next((p for p in hub.get("ports", []) if p["id"] == row["port_id"]), None) if hub else None
            if port is None or not usable_port(store, hub, port):
                row.update(status="WAITING", port_id=None)
                notify(store, row["id"] + ":rescheduled:" + str(row.get("revision", 0)),
                       row["user_id"], "Cổng thay đổi trạng thái, lịch chuyển về hàng đợi", row["id"])
                row["revision"] = row.get("revision", 0) + 1
    waiting = sorted((r for r in rows(store) if r["status"] == "WAITING"),
                     key=lambda r: (r["battery_pct"], r["created_at"], r["id"]))
    for row in waiting:
        port = choose_port(store, row)
        if port is not None:
            row.update(port_id=port["id"], status="RESERVED")
            key = row["id"] + ":ready:" + str(row.get("revision", 0))
            notify(store, key, row["user_id"], "Đã có cổng sạc phù hợp với lịch đặt", row["id"])


def reserve_schedule(store, payload, user_id):
    start, end = parse_time(payload["starts_at"]), parse_time(payload["ends_at"])
    if start < utc_now() or end <= start or end - start > timedelta(hours=12):
        raise HTTPException(422, "Lịch phải trong tương lai, kết thúc sau bắt đầu, tối đa 12 giờ")
    hub = store.get_hub(payload["hub_id"])
    if hub is None:
        raise HTTPException(404, "Hub không tồn tại")
    if hub["status"] != "ACTIVE":
        raise HTTPException(409, "Hub không hoạt động")
    port_id = payload.get("port_id")
    if port_id and not any(p["id"] == port_id for p in hub.get("ports", [])):
        raise HTTPException(404, "Cổng không thuộc Hub")
    from .parking_reservations import plate_key
    for old in rows(store):
        if old["status"] in ("RESERVED", "WAITING", "IN_SERVICE") and (
                old["user_id"] == user_id or plate_key(old["plate_number"]) == plate_key(payload["plate_number"])):
            if overlaps(start, end, parse_time(old["starts_at"]), parse_time(old["ends_at"])):
                raise HTTPException(409, "Tài khoản hoặc xe đã có lịch giao nhau")
    reconcile_schedule(store)
    row = {**payload, "id": "SCH-" + uuid4().hex, "user_id": user_id,
           "requested_port_id": port_id, "port_id": None, "status": "WAITING",
           "starts_at": start.isoformat(), "ends_at": end.isoformat(),
           "created_at": utc_now().isoformat(), "revision": 0}
    port = choose_port(store, row)
    if port is None and not payload.get("join_queue", False):
        raise HTTPException(409, "Không có cổng trống trong khung giờ")
    store.operator_mock.setdefault("charging_schedule", []).append(row)
    reconcile_schedule(store)
    return row
