"""Gợi ý đặt lại từ tài nguyên thật; không đặt thay người dùng hoặc sửa store."""

import copy

from shared.memory_store import MockDatabaseStore
from shared.parking_reservations import choose_parking_slot
from shared.charging_reservations import select_charging_port
from shared.battery_reservations import select_swap_battery
from .hubs import available_bikes, distance, hub_detail
from .schemas.booking import BookingAlternative, CreateBookingRequest


def booking_alternatives(db: MockDatabaseStore, request: CreateBookingRequest) -> list[BookingAlternative]:
    """Giữ loại dịch vụ, biển số, số pin và Hub đích; chỉ đổi nơi/tài nguyên nhận.

    Kiểm tra bằng cùng hàm đặt chỗ trên bản sao để không gợi ý bỏ qua các
    booking toàn cục, bảo trì, điều chuyển hoặc ràng buộc của phương tiện.
    Mỗi Hub có tối đa một lựa chọn, ưu tiên Hub cũ rồi các Hub gần nó.
    """
    original = db.get_hub(request.hub_id)
    hubs = sorted(db.get_hubs(), key=lambda h: (
        distance(original['lat'], original['lng'], h['lat'], h['lng']) if original else 0,
        h['id'],
    ))
    results = []
    for hub in hubs:
        if hub.get('status') != 'ACTIVE':
            continue
        payload = request.model_dump(mode='json', exclude_unset=True)
        # Mã tài nguyên và mô tả cũ không được áp sang Hub khác.
        for field in ('resource_id', 'resource_name', 'selected_bike', 'parking_slot', 'charging_port', 'services'):
            payload.pop(field, None)
        payload['hub_id'] = hub['id']
        try:
            if request.plan_type == 'rental':
                bikes = available_bikes(db, hub)
                if not bikes:
                    continue
                payload['resource_name'] = bikes[0]['id']
            elif request.plan_type == 'personal':
                payload['parking_slot'] = choose_parking_slot(db, hub, payload)['id']
                payload['charging_port'] = select_charging_port(db, hub, payload)['id']
            elif request.plan_type == 'parking':
                payload['parking_slot'] = choose_parking_slot(db, hub, payload)['id']
            elif request.plan_type == 'charging':
                payload['charging_port'] = select_charging_port(db, hub, payload)['id']
            else:
                payload['battery_type'] = select_swap_battery(db, hub, payload)['battery_type']
        except ValueError:
            continue
        # Chỉ bản sao được giữ tài nguyên để kiểm chứng toàn bộ điều kiện.
        candidate = copy.deepcopy(db)
        if 'error' in candidate.create_booking(payload):
            continue
        results.append(BookingAlternative(hub=hub_detail(db, hub),
                                          request=CreateBookingRequest.model_validate(payload)))
        if len(results) == 3:
            break
    return results
