"""Kiểm tra và giữ pin đầy cho luồng đổi pin mô phỏng."""

from .parking_reservations import plate_key


def select_swap_battery(db, hub: dict, payload: dict) -> dict:
    """Chọn đúng loại pin và kiểm tra tồn kho trước khi thay đổi tài nguyên."""
    if hub is None or hub.get('status') != 'ACTIVE':
        raise ValueError('Hub đổi pin không tồn tại hoặc không hoạt động')
    quantity = payload.get('battery_quantity', 1)
    if type(quantity) is not int or quantity <= 0:
        raise ValueError('Số lượng pin phải là số nguyên dương')
    plate = payload.get('personal_plate') or ''
    vehicle = next((v for v in db.get_user_vehicles() if plate_key(v['plate_number']) == plate_key(plate)), None)
    battery_type = payload.get('battery_type') or (vehicle.get('battery_type') if vehicle else None)
    if not battery_type:
        raise ValueError('Cần cung cấp loại pin hoặc chọn phương tiện cá nhân đã lưu')
    if vehicle and vehicle.get('battery_type') != battery_type:
        raise ValueError('Loại pin không phù hợp với phương tiện')
    battery = next((b for b in hub.get('batteries', []) if b['battery_type'] == battery_type), None)
    if battery is None or not battery.get('is_available', True):
        raise ValueError('Loại pin không khả dụng tại Hub')
    if type(battery.get('available_count')) is not int or battery['available_count'] < quantity or hub.get('available_batteries', 0) < quantity:
        raise ValueError('Hub không đủ pin đầy khả dụng')
    if type(battery.get('swap_fee')) is not int or battery['swap_fee'] < 0:
        raise ValueError('Đơn giá đổi pin không hợp lệ')
    return battery


def release_swap_battery(db, booking: dict) -> None:
    """Hoàn pin đã giữ một lần; không hoàn pin của dịch vụ đã thực hiện."""
    if not booking.get('swap_reserved'):
        return
    hub = db.get_hub(booking['hub_id'])
    battery = next((b for b in hub.get('batteries', []) if b['battery_type'] == booking['battery_type']), None) if hub else None
    if battery is not None:
        battery['available_count'] += booking['battery_quantity']
        hub['available_batteries'] += booking['battery_quantity']
        booking['swap_reserved'] = False
