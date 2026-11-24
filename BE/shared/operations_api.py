"""API lịch sạc, quản trị tài nguyên, ảnh sự cố và thông báo."""
import base64
import io
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from .database import db, persist_change
from .charging_schedule import rows, reserve_schedule, reconcile_schedule, parse_time, utc_now
from .devices import COLLECTIONS, COUNTERS, get_device, set_device_state


class ScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    hub_id: str
    port_id: str | None = None
    plate_number: str = Field(min_length=1, pattern=r"\S")
    starts_at: str
    ends_at: str
    battery_pct: int = Field(ge=0, le=100)
    join_queue: bool = False


class HubCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hub_code: str = Field(min_length=1, pattern=r"\S")
    name: str = Field(min_length=1, pattern=r"\S")
    address: str = Field(min_length=1, pattern=r"\S")
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    parking_capacity: int = Field(ge=1, le=1000)
    charger_capacity: int = Field(ge=0, le=200)
    max_power_kw: float = Field(ge=10, allow_inf_nan=False)
    load_warning_threshold_pct: int = Field(default=85, ge=50, le=100)


class DeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["port", "slot", "bike", "battery"]
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1)
    power_kw: float = Field(default=7.4, gt=0, allow_inf_nan=False)
    rate_per_kwh: int = Field(default=3500, ge=0)
    hourly_rate: int = Field(default=2500, ge=0)
    battery_level: int = Field(default=100, ge=0, le=100)
    available_count: int = Field(default=1, ge=0, le=1000)
    swap_fee: int = Field(default=25000, ge=0)


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool


async def http_error(request, exc):
    """Lỗi nghiệp vụ trả JSON để client đọc được thông báo."""
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


async def read_model(request, model):
    try:
        body = await request.json()
    except (ValueError, UnicodeError):
        raise HTTPException(400, "JSON không hợp lệ")
    try:
        return model.model_validate(body)
    except ValidationError:
        raise HTTPException(422, "Dữ liệu không hợp lệ")


async def schedules(request):
    actor = request.state.account
    if request.method == "GET":
        return JSONResponse({"items": [r for r in rows(db)
            if actor["role"] == "operator" or r["user_id"] == actor["id"]]})
    payload = (await read_model(request, ScheduleRequest)).model_dump()
    from .parking_reservations import plate_key
    payload["plate_number"] = plate_key(payload["plate_number"])
    if not payload["plate_number"]:
        raise HTTPException(422, "Biển số không hợp lệ")
    def change(candidate):
        row = reserve_schedule(candidate, payload, actor["id"])
        return JSONResponse(row, status_code=201)
    return persist_change(change)


async def schedule_action(request):
    actor = request.state.account
    schedule_id = request.path_params["schedule_id"]
    action = request.path_params["action"]
    if action not in ("start", "cancel"):
        raise HTTPException(404, "Thao tác không tồn tại")
    def change(candidate):
        row = next((r for r in rows(candidate) if r["id"] == schedule_id and r["user_id"] == actor["id"]), None)
        if row is None:
            raise HTTPException(404, "Lịch không tồn tại")
        if action == "cancel":
            if row["status"] == "IN_SERVICE":
                raise HTTPException(409, "Cần kết thúc phiên sạc trước")
            if row["status"] not in ("RESERVED", "WAITING", "CANCELLED"):
                raise HTTPException(409, "Lịch đã kết thúc")
            row["status"] = "CANCELLED"
            reconcile_schedule(candidate)
            return JSONResponse(row)
        if row["status"] == "IN_SERVICE":
            return JSONResponse(row)
        if row["status"] != "RESERVED" or not parse_time(row["starts_at"]) <= utc_now() < parse_time(row["ends_at"]):
            raise HTTPException(409, "Lịch chưa đến giờ hoặc chưa có cổng")
        from user.charging import start_charging, ChargingError
        row["status"] = "ACTIVATING"
        booking = candidate.create_booking({
            "plan_type": "charging", "hub_id": row["hub_id"],
            "charging_port": row["port_id"], "personal_plate": row["plate_number"],
        })
        if "error" in booking:
            raise HTTPException(409, booking["error"])
        try:
            start_charging(candidate, booking["id"])
        except ChargingError as exc:
            raise HTTPException(exc.status_code, str(exc))
        row.update(status="IN_SERVICE", booking_id=booking["id"])
        return JSONResponse(row)
    return persist_change(change)


async def create_hub(request):
    payload = (await read_model(request, HubCreate)).model_dump()
    def change(candidate):
        if any(h["hub_code"].casefold() == payload["hub_code"].casefold()
               or h["name"].casefold() == payload["name"].casefold() for h in candidate.hubs):
            raise HTTPException(409, "Tên hoặc mã Hub đã tồn tại")
        hub = {**payload, "id": "hub-" + uuid4().hex, "status": "ACTIVE",
               "availability_rate_pct": 100, "available_bikes": 0,
               "available_parking": 0, "available_chargers": 0, "available_batteries": 0,
               "bikes": [], "ports": [], "slots": [], "batteries": [],
               "pricing": {"rental_bike_hourly": 10000, "parking_hourly": 2500,
                           "charging_kwh": 3500, "battery_swap_fee": 25000}}
        candidate.hubs.append(hub)
        return JSONResponse({"success": True, "hub": hub}, status_code=201)
    return persist_change(change)


async def devices(request):
    hub_id = request.path_params["hub_id"]
    hub = db.get_hub(hub_id)
    if hub is None:
        raise HTTPException(404, "Hub không tồn tại")
    if request.method == "GET":
        return JSONResponse({"items": [{**item, "id": item.get("id", item.get("battery_type")), "kind": kind}
            for kind, collection in COLLECTIONS.items() for item in hub.get(collection, [])]})
    payload = (await read_model(request, DeviceCreate)).model_dump()
    def change(candidate):
        target = candidate.get_hub(hub_id)
        kind = payload["kind"]
        collection = COLLECTIONS[kind]
        if any(d.get("id", d.get("battery_type")) == payload["id"] for h in candidate.hubs
               for d in h.get(collection, []) if kind == "bike" or h["id"] == hub_id):
            raise HTTPException(409, "Mã thiết bị đã tồn tại")
        capacity = target["charger_capacity"] if kind == "port" else target["parking_capacity"]
        if kind != "battery" and len(target.get(collection, [])) >= capacity:
            raise HTTPException(409, "Vượt sức chứa cấu hình của Hub")
        device = {k: v for k, v in payload.items() if k != "kind"}
        device.update(status="Sẵn sàng" if target["status"] == "ACTIVE" else "Không khả dụng",
                      is_available=target["status"] == "ACTIVE", disabled=False)
        if kind == "battery":
            device["battery_type"] = payload["id"]
        target.setdefault(collection, []).append(device)
        quantity = payload["available_count"] if kind == "battery" else 1
        target[COUNTERS[kind]] += quantity * int(target["status"] == "ACTIVE")
        reconcile_schedule(candidate)
        return JSONResponse({"success": True, "device": device}, status_code=201)
    return persist_change(change)


async def update_device(request):
    payload = await read_model(request, DeviceUpdate)
    if request.path_params["kind"] not in COLLECTIONS:
        raise HTTPException(422, "Loại thiết bị không hợp lệ")
    def change(candidate):
        device = set_device_state(candidate, request.path_params["hub_id"],
            request.path_params["kind"], request.path_params["device_id"], payload.enabled)
        return JSONResponse({"success": True, "device": device})
    return persist_change(change)


async def notifications(request):
    actor = request.state.account
    items = [n for n in db.operator_mock.get("notifications", [])
             if n["recipient"] in (actor["id"], actor["role"])]
    return JSONResponse({"items": items})


async def upload_photo(request):
    actor = request.state.account
    target_id = request.path_params["target_id"]
    limit = 2 * 1024 * 1024
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit + 65536:
            raise HTTPException(413, "Ảnh tối đa 2 MiB")
        chunks.append(chunk)
    content = b"".join(chunks)
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        request._body = content
        async with request.form(max_files=1, max_fields=0) as form:
            file = form.get("file")
            if file is None or not hasattr(file, "read"):
                raise HTTPException(422, "Cần file ảnh")
            content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, "Ảnh tối đa 2 MiB")
    try:
        with Image.open(io.BytesIO(content)) as picture:
            if picture.format not in ("JPEG", "PNG") or picture.width * picture.height > 20000000:
                raise ValueError()
            mime = "image/png" if picture.format == "PNG" else "image/jpeg"
            picture.verify()
        with Image.open(io.BytesIO(content)) as picture:
            picture.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Cần ảnh JPEG/PNG hợp lệ")
    attachment_id = "IMG-" + uuid4().hex
    role = actor["role"]
    url = f"/api/v1/{role}/attachments/{attachment_id}"
    def change(candidate):
        if role == "user":
            report = next((r for r in candidate.incidents if r["id"] == target_id
                           and r.get("user_id") == actor["id"]), None)
            if report is None:
                raise HTTPException(404, "Sự cố không tồn tại")
            ticket = next((t for t in candidate.maintenance_tickets
                           if t["code"] == report.get("maintenance_ticket_code")), None)
            report["photo_url"] = url
            report["image_attached"] = True
            report["attachment_id"] = attachment_id
        else:
            ticket = next((t for t in candidate.maintenance_tickets if t["code"] == target_id), None)
            if ticket is None:
                raise HTTPException(404, "Phiếu không tồn tại")
            if ticket.get("assigned_staff_id") != actor["id"]:
                raise HTTPException(403, "Phiếu chưa được phân công cho tài khoản này")
        if ticket is not None:
            ticket["photo_url"] = url
            ticket["attachment_id"] = attachment_id
        candidate.operator_mock.setdefault("attachments", {})[attachment_id] = {
            "owner_id": actor["id"], "ticket_code": ticket["code"] if ticket else None,
            "mime": mime, "data": base64.b64encode(content).decode(),
        }
        return JSONResponse({"id": attachment_id, "photo_url": url}, status_code=201)
    return persist_change(change)


async def read_photo(request):
    actor = request.state.account
    image = db.operator_mock.get("attachments", {}).get(request.path_params["attachment_id"])
    if image is None:
        raise HTTPException(404, "Ảnh không tồn tại")
    ticket = next((t for t in db.maintenance_tickets if t["code"] == image["ticket_code"]), {})
    if actor["role"] != "operator" and actor["id"] not in (image["owner_id"], ticket.get("user_id"), ticket.get("assigned_staff_id")):
        raise HTTPException(403, "Không có quyền đọc ảnh")
    return Response(base64.b64decode(image["data"]), media_type=image["mime"],
                    headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


user_routes = [
    Route("/api/v1/user/charging/schedules", schedules, methods=["GET", "POST"]),
    Route("/api/v1/user/charging/schedules/{schedule_id}/{action}", schedule_action, methods=["POST"]),
    Route("/api/v1/user/incidents/{target_id}/photos", upload_photo, methods=["POST"]),
]
operator_routes = [
    Route("/api/v1/operator/hubs", create_hub, methods=["POST"]),
    Route("/api/v1/operator/hubs/{hub_id}/devices", devices, methods=["GET", "POST"]),
    Route("/api/v1/operator/hubs/{hub_id}/devices/{kind}/{device_id}", update_device, methods=["PUT"]),
    Route("/api/v1/operator/charging/schedules", schedules, methods=["GET"]),
]
staff_routes = [Route("/api/v1/staff/maintenance/{target_id}/photos", upload_photo, methods=["POST"])]
for role, routes in (("user", user_routes), ("staff", staff_routes), ("operator", operator_routes)):
    routes.extend([
        Route(f"/api/v1/{role}/notifications", notifications, methods=["GET"]),
        Route(f"/api/v1/{role}/attachments/{{attachment_id}}", read_photo, methods=["GET"]),
    ])

class LoadUpdate(BaseModel):
    power_demand_kw: float = Field(ge=0, allow_inf_nan=False)


async def automation_runs(request):
    from .automation import scan_automation
    if request.method == "GET":
        return JSONResponse({"items": db.operator_mock.get("automation_runs", [])})
    def change(candidate):
        return JSONResponse({"items": scan_automation(candidate)})
    return persist_change(change)


async def update_load(request):
    payload = await read_model(request, LoadUpdate)
    def change(candidate):
        hub = candidate.get_hub(request.path_params["hub_id"])
        if hub is None:
            raise HTTPException(404, "Hub không tồn tại")
        hub["power_demand_kw"] = payload.power_demand_kw
        hub["power_measurement_source"] = "operator_input"
        return JSONResponse({"success": True, "hub_id": hub["id"]})
    return persist_change(change)


async def intervene_run(request):
    try:
        body = await request.json()
    except (ValueError, UnicodeError):
        raise HTTPException(400, "JSON không hợp lệ")
    action = body.get("action") if isinstance(body, dict) else None
    if action not in ("pause", "resume", "resolve"):
        raise HTTPException(422, "Cần action pause, resume hoặc resolve")
    def change(candidate):
        run = next((r for r in candidate.operator_mock.get("automation_runs", [])
                    if r["id"] == request.path_params["run_id"]), None)
        if run is None:
            raise HTTPException(404, "Phiên không tồn tại")
        if action == "resolve":
            run["status"] = "HANDLED"
        elif action == "pause":
            if run["status"] not in ("WAITING_OPERATOR", "PAUSED"):
                raise HTTPException(409, "Phiên đã hoàn tất")
            run["status"] = "PAUSED"
        else:
            if run["status"] not in ("PAUSED", "WAITING_OPERATOR"):
                raise HTTPException(409, "Phiên không chờ can thiệp")
            if candidate.operator_mock.get("emergency_halt"):
                raise HTTPException(409, "Hệ thống đang dừng khẩn cấp")
            from .automation import execute_actions
            rule_id = body.get("rule_id", run.get("rule_id"))
            rule = next((r for r in candidate.simulation_rules if r["id"] == rule_id and r.get("active")), None)
            if rule is None or not rule.get("actions"):
                raise HTTPException(409, "Cần quy tắc thực thi hợp lệ")
            if run.get("progress") and rule_id != run.get("rule_id"):
                raise HTTPException(409, "Phiên đã thực thi một phần, cần xử lý thủ công")
            run["rule_id"] = rule_id
            execute_actions(candidate, run, rule)
        return JSONResponse(run)
    return persist_change(change)


operator_routes.extend([
    Route("/api/v1/operator/automation/runs", automation_runs, methods=["GET"]),
    Route("/api/v1/operator/automation/scan", automation_runs, methods=["POST"]),
    Route("/api/v1/operator/automation/runs/{run_id}", intervene_run, methods=["PUT"]),
    Route("/api/v1/operator/hubs/{hub_id}/load", update_load, methods=["PUT"]),
])
