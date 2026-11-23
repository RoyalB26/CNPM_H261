"""Tra cứu và gợi ý Hub từ trạng thái tài nguyên dùng chung, không ghi store."""

import math
import unicodedata

from shared.memory_store import MockDatabaseStore
from shared.parking_reservations import available_parking_capacity
from shared.battery_reservations import available_swap_batteries, swap_battery_blocked
from .schemas.hub import HubDetailResponse, RouteSuggestionRequest, RouteSuggestionResponse, SearchHubQuery


def normalize(text: str) -> str:
    """Chuẩn hóa tìm kiếm tiếng Việt không dấu và không phân biệt hoa thường."""
    text = text.casefold().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))


def hub_detail(db: MockDatabaseStore, hub: dict) -> HubDetailResponse:
    """User xem chỗ còn có thể tiếp nhận xe, không gồm chỗ dành cho điều chuyển.

    Chỉ tạo response; không trừ lần nữa vào bộ đếm chung của Operator/Staff.
    """
    batteries = [{**b, 'available_count': 0} if swap_battery_blocked(db, hub, b) else b
                 for b in hub.get('batteries', [])]
    return HubDetailResponse.model_validate({**hub, 'available_parking': available_parking_capacity(db, hub),
        'available_batteries': available_swap_batteries(db, hub), 'batteries': batteries})


def available_bikes(db: MockDatabaseStore, hub: dict) -> list[dict]:
    """Loại xe đã đặt, đang đi, điều chuyển hoặc bảo trì khỏi gợi ý."""
    if hub.get('status') != 'ACTIVE' or hub.get('available_bikes', 0) <= 0:
        return []
    booked = {
        b.get('resource_name', '').split(' · ')[0].strip() for b in db.bookings
        if b.get('plan_type') == 'rental' and b.get('status') in ('Đã xác nhận', 'Đang sử dụng')
    }
    return [bike for bike in hub.get('bikes', []) if bike.get('status') == 'Sẵn sàng'
            and bike['id'] not in booked and not db._rental_bike_blocked(bike['id'])]


def search_hubs(db: MockDatabaseStore, query: SearchHubQuery) -> list[dict]:
    """Lọc tên/địa chỉ, trạng thái và tài nguyên phục vụ loại phương tiện."""
    keyword = normalize(query.keyword or '').strip()
    return [hub for hub in db.get_hubs()
            if (not keyword or keyword in normalize(hub['name'] + ' ' + hub['address']))
            and (query.status is None or hub['status'] == query.status)
            and (query.vehicle_type is None
                 or (query.vehicle_type == 'bike' and available_bikes(db, hub))
                 or (query.vehicle_type == 'personal' and hub['status'] == 'ACTIVE' and available_parking_capacity(db, hub) > 0))]


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách đường chim bay theo công thức Haversine, đơn vị km."""
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(math.radians(lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(math.sqrt(min(1, max(0, a))))


def suggest_route(db: MockDatabaseStore, query: RouteSuggestionRequest) -> RouteSuggestionResponse:
    """Chọn Hub khả dụng gần vị trí đi/đến; không phải định tuyến đường bộ."""
    origins = [(hub, available_bikes(db, hub)) for hub in db.get_hubs()]
    origins = [(hub, bikes) for hub, bikes in origins if bikes]
    destinations = [hub for hub in db.get_hubs() if hub['status'] == 'ACTIVE' and available_parking_capacity(db, hub) > 0]
    if not origins or not destinations:
        raise ValueError('Không có Hub lấy/trả xe khả dụng')
    origin, bikes = min(origins, key=lambda pair: distance(query.origin_lat, query.origin_lng, pair[0]['lat'], pair[0]['lng']))
    dest = min(destinations, key=lambda hub: distance(query.dest_lat, query.dest_lng, hub['lat'], hub['lng']))
    km = round(distance(origin['lat'], origin['lng'], dest['lat'], dest['lng']), 2)
    return RouteSuggestionResponse(
        origin_hub=hub_detail(db, origin), destination_hub=hub_detail(db, dest), distance_km=km,
        estimated_minutes=max(1, math.ceil(km/15*60)), recommended_bike=bikes[0],
        message='Gợi ý theo khoảng cách đường chim bay và tài nguyên hiện tại.',
    )
