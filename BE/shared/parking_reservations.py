"""Chọn và hoàn chỗ giữ xe cá nhân, xét vé bãi và lệnh điều chuyển chung."""


def plate_key(value: str) -> str:
    """So khớp biển số không phân biệt khoảng trắng, dấu chấm hoặc gạch nối."""
    return ''.join(c for c in value.upper() if c.isalnum())


def slot_id(booking: dict) -> str:
    """Đọc mã chỗ mới hoặc chuỗi hiển thị của booking seed cũ."""
    return booking.get('parking_slot') or booking.get('resource_id') or booking.get('resource_name', '').removeprefix('Chỗ đỗ ').split(' · ')[0].strip()


def choose_parking_slot(db, hub: dict, payload: dict) -> dict:
    """Kiểm tra toàn bộ ràng buộc trước khi trả chỗ có thể giữ, không ghi store."""
    plate = payload.get('personal_plate')
    if not isinstance(plate, str) or not plate_key(plate):
        raise ValueError('Cần cung cấp biển số phương tiện cá nhân')
    if hub is None or hub.get('status') != 'ACTIVE':
        raise ValueError('Hub gửi xe không tồn tại hoặc không hoạt động')
    if hub.get('available_parking', 0) <= 0:
        raise ValueError('Hub không còn chỗ đỗ')
    live_bookings = [b for b in db.bookings if b.get('plan_type') in ('parking', 'personal')
                     and b.get('status') in ('Đã xác nhận', 'Đang sử dụng')]
    live_records = [r for r in db.parking_records if r.get('checkout_time') is None]
    if any(plate_key(b.get('personal_plate') or '') == plate_key(plate) for b in live_bookings) or any(
        plate_key(r['plate_number']) == plate_key(plate) for r in live_records
    ):
        raise ValueError('Biển số đang có đặt chỗ hoặc đang gửi xe')
    occupied = {slot_id(b) for b in live_bookings if b.get('hub_id') == hub['id']}
    occupied.update(r['slot_id'] for r in live_records if r['hub_id'] == hub['id'])
    tasks = [t for t in db.relocations if t.get('target_hub_id') == hub['id']
             and t.get('status') in ('PENDING', 'IN_PROGRESS', 'IN_TRANSIT')]
    occupied.update(s for t in tasks for s in t.get('reserved_slot_ids', []))
    free = [s for s in hub.get('slots', []) if s.get('is_available') and s['id'] not in occupied]
    legacy_holds = sum(t['total_bikes'] for t in tasks if not t.get('reserved_slot_ids'))
    free = free[legacy_holds:]
    requested = payload.get('parking_slot') or payload.get('resource_id')
    if requested:
        free = [s for s in free if s['id'] == requested]
    if not free:
        raise ValueError('Chỗ đỗ không khả dụng hoặc đang được giữ')
    return free[0]


def release_parking_slot(db, booking: dict) -> None:
    """Chỉ hoàn chỗ do booking này giữ và chưa có xe vào, tối đa một lần."""
    hub = db.get_hub(booking['hub_id'])
    slot = next((s for s in hub.get('slots', []) if s['id'] == slot_id(booking)), None) if hub else None
    if slot is None or slot.get('reserved_by') != booking['id']:
        return
    occupied = any(r['hub_id'] == hub['id'] and r['slot_id'] == slot['id'] and r.get('checkout_time') is None
                   for r in db.parking_records)
    slot.pop('reserved_by')
    if not occupied:
        slot['is_available'] = True
        hub['available_parking'] = min(hub['parking_capacity'], hub['available_parking'] + 1)
