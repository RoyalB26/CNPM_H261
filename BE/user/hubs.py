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
    """User xem số xe và danh sách xe cùng có thể đặt, cùng chỗ còn tiếp nhận.

    Chỉ tạo response; không sửa danh sách/bộ đếm chung của Operator/Staff.
    """
    bikes = available_bikes(db, hub)
    batteries = [{**b, 'available_count': 0} if swap_battery_blocked(db, hub, b) else b
                 for b in hub.get('batteries', [])]
    return HubDetailResponse.model_validate({**hub, 'available_bikes': len(bikes), 'bikes': bikes,
        'available_parking': available_parking_capacity(db, hub),
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


async def suggest_route(db: MockDatabaseStore, query: RouteSuggestionRequest) -> RouteSuggestionResponse:
    """Xếp hạng ứng viên theo tuyến OSRM qua tọa độ đi, Hub và tọa độ đến."""
    import asyncio
    import os
    import httpx
    from shared.charging_reservations import charging_port_blocked

    destinations = [h for h in db.hubs if h["status"] == "ACTIVE"
                    and available_parking_capacity(db, h) > 0]
    if query.vehicle_type == "personal" and query.service == "charging":
        destinations = [h for h in destinations if any(
            p.get("is_available") and not charging_port_blocked(db, h, p["id"])
            for p in h.get("ports", [])
        )]
    destinations = sorted(destinations, key=lambda h: distance(
        query.dest_lat, query.dest_lng, h["lat"], h["lng"]))[:3]
    origins = sorted(
        [(h, available_bikes(db, h)) for h in db.hubs if available_bikes(db, h)],
        key=lambda item: distance(query.origin_lat, query.origin_lng, item[0]["lat"], item[0]["lng"]),
    )[:3] if query.vehicle_type == "bike" else [(None, [])]
    if not destinations or not origins:
        raise ValueError("Không có Hub phù hợp tài nguyên yêu cầu")
    base = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
    profile = os.environ.get("OSRM_PROFILE", "driving")

    async with httpx.AsyncClient(timeout=8) as client:
        async def candidate(origin, bikes, target):
            coordinates = [(query.origin_lng, query.origin_lat)]
            if origin:
                coordinates.append((origin["lng"], origin["lat"]))
            coordinates.extend([(target["lng"], target["lat"]), (query.dest_lng, query.dest_lat)])
            points = ";".join(f"{lng},{lat}" for lng, lat in coordinates)
            try:
                response = await client.get(f"{base}/route/v1/{profile}/{points}",
                    params={"overview": "full", "geometries": "geojson"})
                response.raise_for_status()
                data = response.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    return None
                route = data["routes"][0]
                if route["distance"] < 0 or route["duration"] < 0 or route["geometry"].get("type") != "LineString":
                    return None
                return origin, bikes, target, route
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                return None

        options = await asyncio.gather(*(candidate(h, bikes, dest)
            for h, bikes in origins for dest in destinations if h is None or h["id"] != dest["id"]))
    options = [item for item in options if item is not None]
    if not options:
        from starlette.exceptions import HTTPException
        raise HTTPException(503, "Dịch vụ OSRM chưa trả được tuyến đường bộ")
    origin, bikes, dest, route = min(options, key=lambda item: item[3]["duration"])
    return RouteSuggestionResponse(
        origin_hub=hub_detail(db, origin or dest), destination_hub=hub_detail(db, dest),
        distance_km=round(route["distance"] / 1000, 3),
        estimated_minutes=max(1, math.ceil(route["duration"] / 60)),
        recommended_bike=bikes[0] if bikes else None,
        routing_provider="OSRM", routing_profile=profile, geometry=route["geometry"],
        message="Tuyến OSRM qua Hub, xếp theo thời gian đường bộ trong các Hub ứng viên.",
    )
