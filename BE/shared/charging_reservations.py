"""Giữ cổng sạc độc quyền trong bản demo, chưa phân lịch theo khung giờ."""

from .parking_reservations import plate_key


def charging_port_blocked(db, hub: dict, port_id: str, ignore_booking_id: str | None = None,
                          ignore_session_id: str | None = None) -> bool:
    """Xét phiên đang sạc, phiếu bảo trì và booking giữ cổng trong store chung."""
    active = db.user.get('active_services', {}).get('charging')
    if active and active.get('session_id') != ignore_session_id and active.get('port_id') == port_id:
        if not active.get('hub_id') or active['hub_id'] == hub['id']:
            return True
    if any(t.get('device_code') == port_id and t.get('hub_id') == hub['id']
           and t.get('status') in ('PENDING', 'ASSIGNED', 'IN_PROGRESS')
           for t in db.maintenance_tickets):
        return True
    return any(b.get('hub_id') == hub['id'] and b.get('plan_type') == 'charging'
               and b.get('id') != ignore_booking_id
               and b.get('status') in ('Đã xác nhận', 'Đang sử dụng')
               and (b.get('charging_port') or b.get('resource_id')) == port_id for b in db.bookings)


def select_charging_port(db, hub: dict, payload: dict) -> dict:
    """Trả cổng có thể giữ sau khi kiểm tra; chưa thay đổi dữ liệu."""
    if hub is None or hub.get('status') != 'ACTIVE':
        raise ValueError('Hub sạc không tồn tại hoặc không hoạt động')
    if not isinstance(payload.get('personal_plate'), str) or not payload['personal_plate'].strip():
        raise ValueError('Đặt cổng sạc cần biển số phương tiện cá nhân')
    if any(b.get('plan_type') == 'charging' and b.get('status') in ('Đã xác nhận', 'Đang sử dụng')
           and plate_key(b.get('personal_plate') or '') == plate_key(payload['personal_plate']) for b in db.bookings):
        raise ValueError('Phương tiện đang có booking sạc khác')
    if hub.get('available_chargers', 0) <= 0:
        raise ValueError('Hub không còn cổng sạc khả dụng')
    requested = payload.get('charging_port') or payload.get('resource_id')
    if payload.get('charging_port') and payload.get('resource_id') and payload['charging_port'] != payload['resource_id']:
        raise ValueError('Các mã cổng sạc không khớp nhau')
    ports = [p for p in hub.get('ports', [])
             if p.get('is_available') and p.get('status') == 'Sẵn sàng'
             and not p.get('reserved_by') and not charging_port_blocked(db, hub, p['id'])
             and (requested is None or p['id'] == requested)]
    if not ports:
        raise ValueError('Cổng sạc không khả dụng, đang sử dụng hoặc bảo trì')
    port = ports[0]
    if type(port.get('rate_per_kwh')) is not int or port['rate_per_kwh'] < 0:
        raise ValueError('Đơn giá điện không hợp lệ')
    return port


def release_charging_port(db, booking: dict) -> None:
    """Hoàn cổng của đúng booking, không bật lại cổng bảo trì hoặc đang sạc."""
    hub = db.get_hub(booking['hub_id'])
    port = next((p for p in hub.get('ports', []) if p['id'] == booking.get('charging_port')), None) if hub else None
    if port is None or port.get('reserved_by') != booking['id']:
        return
    port.pop('reserved_by')
    if port.get('status') != 'Đã đặt chỗ' or charging_port_blocked(db, hub, port['id']):
        return
    port['status'] = 'Sẵn sàng'
    port['is_available'] = True
    hub['available_chargers'] = min(hub['charger_capacity'], hub['available_chargers'] + 1)
