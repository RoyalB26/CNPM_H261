"""Định danh thiết bị theo Hub và loại, thay đổi khả dụng theo chênh lệch."""
from starlette.exceptions import HTTPException
from .charging_schedule import reconcile_schedule

COLLECTIONS = {"port": "ports", "slot": "slots", "bike": "bikes", "battery": "batteries"}
COUNTERS = {"port": "available_chargers", "slot": "available_parking", "bike": "available_bikes", "battery": "available_batteries"}
TYPE_LABELS = {"Cổng sạc": "port", "Chỗ đỗ": "slot", "Phương tiện": "bike", "Pin": "battery", "Trạm pin": "battery"}


def get_device(store, hub_id, kind, device_id):
    hub = store.get_hub(hub_id)
    if hub is None:
        raise HTTPException(404, "Hub không tồn tại")
    devices = hub.get(COLLECTIONS[kind], [])
    matches = [d for d in devices if d.get("id", d.get("battery_type")) == device_id]
    if len(matches) != 1:
        raise HTTPException(404, "Không xác định được đúng thiết bị trong Hub")
    return hub, matches[0]


def set_device_state(store, hub_id, kind, device_id, enabled, workshop=False, ignore_ticket=None):
    hub, device = get_device(store, hub_id, kind, device_id)
    if device.get("reserved_by") or device.get("occupied_by"):
        raise HTTPException(409, "Thiết bị đang được giữ hoặc đang sử dụng")
    if kind == "bike" and store._rental_bike_blocked(device_id, ignore_maintenance=True):
        # Phiếu đang được kết thúc được bỏ khỏi phép kiểm tra bằng caller.
        raise HTTPException(409, "Xe đang sử dụng, điều chuyển hoặc còn phiếu bảo trì")
    if kind == "slot" and (
        any(t.get("target_hub_id") == hub_id and t["status"] in ("PENDING", "IN_PROGRESS", "IN_TRANSIT")
            and (device_id in t.get("reserved_slot_ids", []) or not t.get("reserved_slot_ids"))
            for t in store.relocations)
        or any(r.get("hub_id") == hub_id and r.get("slot_id") == device_id
               and r.get("checkout_time") is None for r in store.parking_records)
    ):
        raise HTTPException(409, "Chỗ đỗ đang phục vụ hoặc được giữ cho điều chuyển")
    profiles = [store.__dict__["user"]] + [a["profile"] for a in
        store.operator_mock.get("accounts", []) if a["role"] == "user"]
    if kind == "port" and any(
        (session := profile.get("active_services", {}).get("charging"))
        and session.get("port_id") == device_id and session.get("hub_id", hub_id) == hub_id
        for profile in profiles
    ):
        raise HTTPException(409, "Cổng đang có phiên sạc")
    if enabled and any(t.get("hub_id") == hub_id and t.get("device_code") == device_id
                       and t["code"] != ignore_ticket
                       and t["status"] in ("PENDING", "ASSIGNED", "IN_PROGRESS")
                       for t in store.maintenance_tickets):
        raise HTTPException(409, "Thiết bị còn phiếu bảo trì đang xử lý")
    if kind == "battery":
        device.update(disabled=not enabled, is_available=enabled and hub["status"] == "ACTIVE",
                      workshop=workshop, status="Sẵn sàng" if enabled else "Không khả dụng")
        hub["available_batteries"] = sum(b["available_count"] for b in hub.get("batteries", [])
            if b.get("is_available", True) and not b.get("disabled", False))
        return device
    available_before = device.get("status") == "Sẵn sàng" if kind == "bike" else bool(device.get("is_available"))
    available_after = enabled and hub["status"] == "ACTIVE"
    device.update(disabled=not enabled, workshop=workshop,
                  status="Sẵn sàng" if available_after else ("Chuyển xưởng" if workshop else "Không khả dụng"))
    if kind != "bike":
        device["is_available"] = available_after
    counter = COUNTERS[kind]
    hub[counter] = max(0, hub.get(counter, 0) + int(available_after) - int(available_before))
    if kind == "port":
        reconcile_schedule(store)
    return device


def resolve_ticket(store, task_code, notes, outcome, photo_url=None):
    from .notifications import notify
    ticket = next((t for t in store.maintenance_tickets if t["code"] == task_code), None)
    if ticket is None:
        raise HTTPException(404, "Phiếu không tồn tại")
    if ticket["status"] in ("RESOLVED", "CLOSED"):
        if ticket.get("outcome") == outcome and ticket.get("resolution_notes") == notes:
            return ticket
        raise HTTPException(409, "Phiếu đã được kết thúc")
    kind = TYPE_LABELS.get(ticket.get("device_type"))
    if kind is None:
        matches = [k for k, collection in COLLECTIONS.items()
                   if any(d.get("id", d.get("battery_type")) == ticket["device_code"]
                          for h in store.hubs if h["id"] == ticket.get("hub_id")
                          for d in h.get(collection, []))]
        if len(matches) != 1:
            raise HTTPException(409, "Phiếu thiếu loại thiết bị hợp lệ")
        kind = matches[0]
    # Chuyển trạng thái trên candidate; lỗi tài nguyên sẽ hủy toàn bộ commit.
    ticket.update(status="RESOLVED", outcome=outcome, resolution_notes=notes)
    if photo_url:
        ticket["photo_url"] = photo_url
    set_device_state(store, ticket["hub_id"], kind, ticket["device_code"],
                     enabled=outcome == "FIXED_ON_SITE",
                     workshop=outcome == "TRANSFER_TO_WORKSHOP", ignore_ticket=task_code)
    recipients = {"operator", ticket.get("user_id"), ticket.get("assigned_staff_id")}
    for recipient in recipients - {None}:
        notify(store, task_code + ":resolved:" + recipient, recipient,
               "Phiếu bảo trì đã cập nhật kết quả " + outcome, task_code)
    return ticket
