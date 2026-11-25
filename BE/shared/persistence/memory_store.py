"""
Unified In-Memory Mock Database Store
Smart E-Mobility Hub - ĐHQG-HCM

Provides a centralized shared mock database store (in Python list/dict structures)
connecting the User, Operator, and Staff subsystems.
All updates from any actor (User booking, Staff check-in, Operator relocation)
are reflected across all three systems in real time.
"""

from datetime import datetime, timedelta
import copy
from uuid import uuid4

from ..identity import current_user_id
from .seed_loader import load_seed
from ..rental_pricing import rental_charge
from ..booking_expiry import booking_expired
from ..parking_reservations import choose_parking_slot, release_parking_slot, plate_key, available_parking_capacity, parking_slot_blocked
from ..battery_reservations import select_swap_battery, release_swap_battery
from ..charging_reservations import select_charging_port, release_charging_port


from datetime import timezone


class RelocationError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


class MockDatabaseStore:
    def __init__(self):
        self.reset()



    def reset(self):
        """Nạp lại toàn bộ dữ liệu mẫu từ JSON vào store hiện có."""
        seed = load_seed()

        self.hubs = seed["hubs"]
        self.user = seed["user"]
        self.bookings = seed["bookings"]
        self.staff = seed["staff"]
        self.relocations = seed["relocations"]
        self.next_relocation_number = seed["next_relocation_number"]
        self.maintenance_tickets = seed["maintenance_tickets"]
        self.parking_records = seed["parking_records"]
        self.incidents = seed["incidents"]
        self.simulation_rules = seed["simulation_rules"]
        self.simulation_history = seed["simulation_history"]
        self.telemetry_events = seed["telemetry_events"]
        self.operator_mock = seed["operator_mock"]



    # ================= CRUD HELPERS =================
    def get_hubs(self):
        return self.hubs

    def get_hub(self, hub_id):
        return next((h for h in self.hubs if h["id"] == hub_id), None)

    @property
    def user(self):
        user_id = current_user_id.get()
        seed_user = self.__dict__["user"]
        if user_id is None or user_id == seed_user["id"]:
            return seed_user
        account = next(a for a in self.operator_mock.get("accounts", [])
                       if a["id"] == user_id and a["role"] == "user")
        return account["profile"]

    @user.setter
    def user(self, value):
        self.__dict__["user"] = value

    def get_user_profile(self):
        return self.user

    def get_user_vehicles(self):
        return self.user.get("vehicles", [])

    def get_bookings(self):
        """Danh sách cá nhân; kiểm tra tài nguyên/Operator dùng self.bookings toàn cục."""
        return [b for b in self.bookings if self.owns_user_record(b)]

    def owns_user_record(self, record: dict) -> bool:
        """Chủ được lấy từ hồ sơ Backend, không lấy user_id client tự gửi."""
        return record.get("user_id") == self.user["id"]

    def get_user_incidents(self):
        """Chỉ đọc báo cáo thuộc tài khoản hiện tại."""
        return [report for report in self.incidents if self.owns_user_record(report)]

    def _rental_bike_blocked(self, bike_id: str, *, ignore_active_ride: bool = False, ignore_maintenance: bool = False) -> bool:
        """Kiểm tra xe đang phục vụ chuyến đi, điều chuyển hoặc bảo trì."""
        profiles = [self.__dict__["user"]] + [
            a["profile"] for a in self.operator_mock.get("accounts", [])
            if a["role"] == "user" and a["id"] != self.__dict__["user"]["id"]
        ]
        active_ride = any(
            profile.get("active_services", {}).get("ride")
            and profile["active_services"]["ride"].get("vehicle_id") == bike_id
            for profile in profiles
        )
        return bool(
            (not ignore_active_ride and active_ride)
            or any(
                task.get("status") in ("PENDING", "IN_PROGRESS", "IN_TRANSIT")
                and any(b.get("bike_id") == bike_id for b in task.get("bikes", []))
                for task in self.relocations
            )
            or (not ignore_maintenance and any(
                ticket.get("status") in ("PENDING", "ASSIGNED", "IN_PROGRESS")
                and ticket.get("device_code") == bike_id
                for ticket in self.maintenance_tickets
            ))
        )

    def _rental_hold_owned(self, booking: dict, bike: dict | None) -> bool:
        """Chỉ nhận/hủy xe của một booking giữ chỗ duy nhất, kể cả runtime cũ.

        Booking mới lưu reserved_by trên xe; dữ liệu cũ thiếu trường này chỉ
        được chấp nhận khi không có booking xác nhận khác giữ cùng mã xe.
        """
        bike_id = booking.get("resource_name", "").split(" · ")[0].strip()
        holds = [b for b in self.bookings if b.get("plan_type") == "rental"
                 and b.get("status") == "Đã xác nhận"
                 and b.get("resource_name", "").split(" · ")[0].strip() == bike_id]
        return (len(holds) == 1 and holds[0]["id"] == booking["id"]
                and (bike is None or bike.get("reserved_by") in (None, booking["id"])))

    def create_booking(self, payload: dict) -> dict:
        """Giữ xe sau khi kiểm tra tài nguyên chung; sinh mã không trùng seed/runtime."""
        if payload.get('plan_type') not in ('rental', 'parking', 'charging', 'swap', 'battery_swap', 'personal'):
            return {'error': 'Gói dịch vụ chưa hỗ trợ giữ tài nguyên; hãy chọn từng dịch vụ riêng'}
        numbers = [
            int(b["id"][4:]) for b in self.bookings
            if b.get("id", "").startswith("EMH-") and b["id"][4:].isdigit()
        ]
        new_id = f"EMH-{max(numbers, default=1020) + 1}"
        hub = self.get_hub(payload.get("hub_id", "hub-01"))
        hub_name = hub["name"] if hub else "Hub Ga Metro ĐHQG"
        plan_type = payload.get("plan_type", "rental")
        confirmed_at = datetime.now(timezone.utc)
        expires_at = confirmed_at + timedelta(minutes=10 if plan_type == "rental" else 15)

        parking_slot = None
        swap_battery = None
        charging_port = None
        if plan_type == 'personal' and payload.get('resource_id') is not None:
            return {'error': 'Gói ghép cần mã chỗ đỗ và cổng sạc riêng'}
        if plan_type in ("charging", "personal"):
            try:
                charging_port = select_charging_port(self, hub, payload)
            except ValueError as exc:
                return {"error": str(exc)}
        if plan_type in ("swap", "battery_swap"):
            try:
                swap_battery = select_swap_battery(self, hub, payload)
            except ValueError as exc:
                return {"error": str(exc)}
        if plan_type in ("parking", "personal"):
            try:
                parking_slot = choose_parking_slot(self, hub, payload)
            except ValueError as exc:
                return {"error": str(exc)}
            rate = hub.get("pricing", {}).get("parking_hourly")
            if type(rate) is not int or rate < 0:
                return {"error": "Giá gửi xe không hợp lệ"}
            if sum(s['id'] == parking_slot['id'] for s in hub.get('slots', [])) != 1:
                return {'error': 'Mã chỗ đỗ bị trùng trong Hub'}

        if plan_type == "rental":
            if not hub:
                return {"error": "Hub không tồn tại"}
            if hub.get("status") != "ACTIVE":
                return {"error": "Hub nguồn không hoạt động"}
            rental_rate = hub.get("pricing", {}).get("rental_bike_hourly")
            if type(rental_rate) is not int or rental_rate < 0:
                return {"error": "Đơn giá thuê xe không hợp lệ"}

            destination_id = payload.get("destination_hub_id")
            destination_name = payload.get("destination_hub_name")
            if destination_id:
                destination = self.get_hub(destination_id)
            elif destination_name:
                destination = next((h for h in self.hubs if h["name"] == destination_name), None)
            else:
                destination = self.get_hub("hub-02") or hub
            if destination is None:
                return {"error": "Hub đích không tồn tại"}
            if destination_name and destination["name"] != destination_name:
                return {"error": "Mã và tên Hub đích không khớp"}
            if destination.get("status") != "ACTIVE":
                return {"error": "Hub đích không hoạt động"}
            if available_parking_capacity(self, destination) <= 0:
                return {"error": "Hub đích không còn chỗ đỗ khả dụng"}

            resource_name = payload.get("resource_name", "")
            bike_id = resource_name.split(" · ")[0].strip()

            bike = next(
                (b for b in hub.get("bikes", []) if b["id"] == bike_id),
                None
            )

            already_booked = any(
                b.get("hub_id") == hub["id"]
                and b.get("plan_type") == "rental"
                and b.get("resource_name", "").split(" · ")[0].strip() == bike_id
                and b.get("status") == "Đã xác nhận"
                for b in self.bookings
            )

            if (
                not bike
                or bike.get("status") != "Sẵn sàng"
                or already_booked
                or self._rental_bike_blocked(bike_id)
                or hub.get("available_bikes", 0) <= 0
            ):
                return {"error": "Xe không khả dụng hoặc đã được đặt"}

        # Reserve bike if rental
        if plan_type == "rental" and hub:
            dest_hub = destination["name"]
            resource_name = payload.get("resource_name", "XE-031 · Xe đạp điện")
            # Dùng cùng mã xe đã kiểm tra, kể cả khi client chỉ gửi mã xe.
            bike_id = resource_name.split(" · ")[0].strip()
            for b in hub.get("bikes", []):
                if b["id"] == bike_id:
                    b["status"] = "Đã đặt chỗ"
                    b["reserved_by"] = new_id
                    break
            if hub["available_bikes"] > 0:
                hub["available_bikes"] -= 1

            booking_obj = {
                "id": new_id,
                "hub_id": hub["id"],
                "hub_name": hub_name,
                "plan_type": "rental",
                "billing_started_at": confirmed_at.isoformat(),
                "rental_hourly_rate": rental_rate,
                "resource_name": resource_name,
                "destination_hub_name": dest_hub,
                "destination_hub_id": destination["id"],
                "hold_until": (datetime.now() + timedelta(minutes=10)).strftime("%H:%M"),
                "status": "Đã xác nhận",
                "created_at": datetime.now().strftime("%H:%M"),
                "price": rental_rate,
                "services": payload.get("services", [{"service_type": "rental", "detail": f"Thuê xe đạp điện {bike_id}", "price_est": rental_rate}])
            }
        else:
            booking_obj = {
                "id": new_id,
                "hub_id": payload.get("hub_id", "hub-01"),
                "hub_name": hub_name,
                "plan_type": plan_type,
                "resource_name": payload.get("resource_name", "Tài nguyên đã đặt"),
                "personal_plate": payload.get("personal_plate"),
                "destination_hub_name": payload.get("destination_hub_name"),
                "hold_until": (datetime.now() + timedelta(minutes=15)).strftime("%H:%M"),
                "status": "Đã xác nhận",
                "created_at": datetime.now().strftime("%H:%M"),
                "price": 10000,
                "services": payload.get("services", [])
            }

        booking_obj["user_id"] = self.user["id"]
        booking_obj["expires_at"] = expires_at.isoformat()
        if charging_port is not None:
            booking_obj.update(
                charging_port=charging_port["id"], resource_id=charging_port["id"],
                resource_name=charging_port["name"], price=0,
                charging_rate_per_kwh=charging_port["rate_per_kwh"],
            )
            charging_port["is_available"] = False
            charging_port["status"] = "Đã đặt chỗ"
            charging_port["reserved_by"] = new_id
            hub["available_chargers"] -= 1
        if swap_battery is not None:
            quantity = payload.get("battery_quantity", 1)
            booking_obj.update(
                battery_type=swap_battery["battery_type"], battery_quantity=quantity,
                swap_unit_price=swap_battery["swap_fee"], swap_reserved=True,
                resource_name=f"{quantity} pin {swap_battery['battery_type']}",
                price=quantity * swap_battery["swap_fee"],
            )
            swap_battery["available_count"] -= quantity
            hub["available_batteries"] -= quantity
        if parking_slot is not None:
            booking_obj.update(
                parking_slot=parking_slot["id"], resource_id=parking_slot["id"],
                resource_name=f"Chỗ đỗ {parking_slot['id']}",
                personal_plate=payload["personal_plate"].strip(),
                price=rate * payload.get("duration_hours", 2),
            )
            parking_slot["is_available"] = False
            parking_slot["reserved_by"] = new_id
            hub["available_parking"] -= 1
        if plan_type == 'personal':
            # Cả hai lựa chọn đã được kiểm tra trước mọi thao tác giữ tài nguyên.
            booking_obj.update(personal_bundle=True,
                               resource_name=f"Chỗ đỗ {parking_slot['id']} + Sạc {charging_port['id']}")
            booking_obj.pop('resource_id', None)
            booking_obj['services'] = [
                {'service_type': 'parking', 'resource_id': parking_slot['id'],
                 'detail': f"Chỗ đỗ {parking_slot['id']}", 'price_est': booking_obj['price']},
                {'service_type': 'charging', 'resource_id': charging_port['id'],
                 'detail': f"Cổng sạc {charging_port['id']} · tính theo kWh", 'price_est': 0},
            ]
        self.bookings.insert(0, booking_obj)
        self.telemetry_events.insert(0, {
            "id": f"TLM-{len(self.telemetry_events) + 100}",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "hub_name": hub_name,
            "event_type": "BOOKING_CREATED",
            "message": f"Đặt chỗ mới {new_id} ({plan_type}) đã được xác nhận.",
            "level": "INFO"
        })
        return booking_obj

    def cancel_booking(self, booking_id: str):
        """User chỉ được hủy booking thuộc tài khoản Backend hiện tại."""
        return self._cancel_booking(booking_id, user_only=True)

    def _cancel_booking(self, booking_id: str, *, user_only: bool):
        """Hủy một lần; chỉ hoàn số xe khi xe thực sự đang được giữ."""
        matches = [b for b in self.bookings if b["id"] == booking_id]
        if not matches:
            return None
        if len(matches) != 1:
            return {"error": "Mã booking bị trùng, không thể xác định đặt chỗ"}
        bk = matches[0]
        if user_only and not self.owns_user_record(bk):
            return None
        if bk.get("status") != "Đã xác nhận":
            return {
                "error": "Booking đã hủy hoặc không còn hiệu lực"
            }
        if bk.get("plan_type") == "rental":
            bike_id = bk.get("resource_name", "").split(" · ")[0].strip()
            ride = self.user.get("active_services", {}).get("ride")
            if ride and (ride.get("booking_id") == booking_id or ride.get("vehicle_id") == bike_id):
                return {"error": "Booking đang phục vụ chuyến đi, không thể hủy"}
            hub = self.get_hub(bk.get("hub_id"))
            bike = next((b for b in hub.get("bikes", []) if b["id"] == bike_id), None) if hub else None
            if not self._rental_hold_owned(bk, bike):
                return {"error": "Không xác định được booking đang giữ xe"}
        if bk.get('personal_bundle') and not self._personal_hold_owned(bk):
            return {'error': 'Không xác định được quyền giữ cả chỗ đỗ và cổng sạc'}
        bk["status"] = "Đã hủy"
        if bk.get("plan_type") in ("parking", "personal"):
            release_parking_slot(self, bk)
        if bk.get("plan_type") in ("swap", "battery_swap"):
            release_swap_battery(self, bk)
        if bk.get("plan_type") in ("charging", "personal"):
            release_charging_port(self, bk)

        # Restore resources if rental
        if bk.get("plan_type") == "rental":
            hub = self.get_hub(bk.get("hub_id", "hub-01"))
            if hub:
                bike_id = bk.get("resource_name", "").split(" · ")[0].strip()
                for b in hub.get("bikes", []):
                    if b["id"] == bike_id:
                        b.pop("reserved_by", None)
                        if b.get("status") == "Đã đặt chỗ" and not self._rental_bike_blocked(bike_id):
                            b["status"] = "Sẵn sàng"
                            hub["available_bikes"] += 1
                        break
        return bk

    def _personal_hold_owned(self, booking: dict) -> bool:
        """Gói chưa sử dụng phải còn giữ duy nhất cả hai tài nguyên."""
        hub = self.get_hub(booking.get('hub_id'))
        if hub is None:
            return False
        resources = [
            [s for s in hub.get('slots', []) if s['id'] == booking.get('parking_slot')],
            [p for p in hub.get('ports', []) if p['id'] == booking.get('charging_port')],
        ]
        return all(len(items) == 1 and items[0].get('reserved_by') == booking['id']
                   and not items[0].get('occupied_by') for items in resources)

    def start_ride(self, booking_id: str):
        """Nhận xe đã đặt khi Hub và tài nguyên vẫn đủ điều kiện phục vụ."""
        matches = [b for b in self.bookings if b["id"] == booking_id]
        if not matches:
            return {"success": False, "error": "Booking không tồn tại"}
        if len(matches) != 1:
            return {"success": False, "error": "Mã booking bị trùng, không thể xác định đặt chỗ"}
        booking = matches[0]
        if not self.owns_user_record(booking):
            return {"success": False, "error": "Booking không tồn tại"}

        if booking.get("plan_type") != "rental":
            return {"success": False, "error": "Không phải booking thuê xe"}

        if booking.get("status") != "Đã xác nhận":
            return {"success": False, "error": "Booking không còn hiệu lực"}

        try:
            if booking_expired(booking, datetime.now(timezone.utc)):
                return {"success": False, "error": "Booking đã quá thời hạn nhận xe"}
        except (ValueError, TypeError):
            return {"success": False, "error": "Thời hạn booking không hợp lệ"}

        if self.user["active_services"].get("ride"):
            return {"success": False, "error": "Bạn đang có chuyến đi khác"}

        hub = self.get_hub(booking["hub_id"])
        if not hub:
            return {"success": False, "error": "Hub không tồn tại"}
        if hub.get("status") != "ACTIVE":
            return {"success": False, "error": "Hub nguồn không hoạt động"}

        vehicle_id = booking["resource_name"].split(" · ")[0].strip()

        bike = next(
            (b for b in hub["bikes"] if b["id"] == vehicle_id),
            None
        )

        if not bike or bike["status"] != "Đã đặt chỗ" or self._rental_bike_blocked(vehicle_id):
            return {"success": False, "error": "Xe không khả dụng"}
        if not self._rental_hold_owned(booking, bike):
            return {"success": False, "error": "Không xác định được booking đang giữ xe"}

        hourly_rate = (booking.get("rental_hourly_rate") if booking.get("billing_started_at") is not None
                       else hub.get("pricing", {}).get("rental_bike_hourly"))
        if type(hourly_rate) is not int or hourly_rate < 0:
            return {"success": False, "error": "Đơn giá thuê xe không hợp lệ"}
        received_at = datetime.now(timezone.utc)
        billing = {"started_at": received_at.isoformat()}
        if booking.get("billing_started_at") is not None:
            billing["billing_started_at"] = booking["billing_started_at"]
        try:
            initial_charge = rental_charge(billing, received_at, hourly_rate)
        except (ValueError, TypeError):
            return {"success": False, "error": "Mốc tính phí booking không hợp lệ"}

        # Xe rời Hub nguồn
        hub["bikes"].remove(bike)
        hub["available_parking"] = min(
            hub["parking_capacity"],
            hub["available_parking"] + 1
        )

        booking["status"] = "Đang sử dụng"

        trip = {
            "user_id": self.user["id"],
            "trip_id": f"TRIP-{uuid4().hex}",
            "booking_id": booking_id,
            **billing,
            "hourly_rate": hourly_rate,
            "vehicle_id": vehicle_id,
            "origin_hub": hub["name"],
            "destination_hub": booking.get("destination_hub_name"),
            "destination_hub_id": booking.get("destination_hub_id"),
            "elapsed_minutes": initial_charge["elapsed_minutes"],
            "battery_level": bike["battery_level"],
            "status": "Đang sử dụng"
        }

        self.user["active_services"]["ride"] = trip
        booking["rental_trip"] = copy.deepcopy(trip)

        return {
            "success": True,
            "ride": trip
        }

    def return_vehicle(self, trip_id: str, return_hub_name: str):
        """Trả xe và lưu chuyến đi vào đúng booking trước khi xóa phiên hiện tại."""
        active_ride = self.user["active_services"].get("ride")

        if not active_ride:
            return {
                "success": False,
                "error": "Không có chuyến đi đang hoạt động"
            }

        if active_ride["trip_id"] != trip_id:
            return {
                "success": False,
                "error": "Mã chuyến đi không khớp"
            }

        if not self.owns_user_record(active_ride):
            return {"success": False, "error": "Chuyến đi không thuộc tài khoản hiện tại"}

        vehicle_id = active_ride["vehicle_id"]

        # Runtime mới liên kết trực tiếp; seed/runtime cũ chỉ nối khi có đúng
        # một booking thuê xe cùng mã xe, tránh hoàn thành nhầm bản ghi.
        booking_id = active_ride.get("booking_id")
        candidates = [
            booking for booking in self.bookings
            if booking.get("plan_type") == "rental"
            and booking.get("resource_name", "").split(" · ")[0].strip() == vehicle_id
            and (
                booking.get("id") == booking_id
                if booking_id is not None
                else booking.get("status") in ("Đã xác nhận", "Đang sử dụng")
            )
        ]
        if len(candidates) != 1 or candidates[0].get("status") not in ("Đã xác nhận", "Đang sử dụng"):
            return {"success": False, "error": "Không xác định được booking của chuyến đi"}
        booking = candidates[0]
        if not self.owns_user_record(booking):
            return {"success": False, "error": "Không xác định được booking của chuyến đi"}
        if booking_id is not None and (
            booking.get("status") != "Đang sử dụng"
            or (booking.get("rental_trip") or {}).get("trip_id") != trip_id
        ):
            return {"success": False, "error": "Trạng thái booking không khớp chuyến đi hiện tại"}

        existing_bikes = [b for h in self.hubs for b in h.get("bikes", []) if b["id"] == vehicle_id]
        if (booking_id is not None and existing_bikes) or len(existing_bikes) > 1:
            return {"success": False, "error": "Vị trí xe trong mạng lưới không khớp chuyến đi"}

        dest_hub = next(
            (h for h in self.hubs if h["name"] == return_hub_name),
            None
        )

        if dest_hub is None:
            return {
                "success": False,
                "error": "Hub đích không tồn tại"
            }

        if dest_hub.get("status") != "ACTIVE":
            return {
                "success": False,
                "error": "Hub đích không hoạt động"
            }

        if available_parking_capacity(self, dest_hub) <= 0:
            return {
                "success": False,
                "error": "Hub đích không còn chỗ đỗ"
            }

        ended_at = datetime.now(timezone.utc)
        origin_hub = self.get_hub(booking.get("hub_id"))
        hourly_rate = active_ride.get("hourly_rate")
        if hourly_rate is None and origin_hub is not None:
            # Tương thích seed/runtime cũ chưa chụp lại đơn giá khi nhận xe.
            hourly_rate = origin_hub.get("pricing", {}).get("rental_bike_hourly")
        try:
            charge = rental_charge(active_ride, ended_at, hourly_rate)
        except (ValueError, TypeError):
            return {"success": False, "error": "Thời gian hoặc đơn giá thuê xe không hợp lệ"}

        # Tìm và xóa xe khỏi Hub cũ, tránh trùng xe
        returned_bike = None

        for hub in self.hubs:
            for bike in hub.get("bikes", [])[:]:
                if bike["id"] == vehicle_id:
                    if returned_bike is None:
                        returned_bike = bike

                    hub["bikes"].remove(bike)

                    if bike["status"] == "Sẵn sàng":
                        hub["available_bikes"] = max(
                            0, hub["available_bikes"] - 1
                        )

        # Nếu xe không có trong danh sách Hub, tạo từ dữ liệu chuyến đi
        if returned_bike is None:
            returned_bike = {
                "id": vehicle_id,
                "name": "Xe đạp điện",
                "hourly_rate": hourly_rate
            }

        # Cập nhật xe tại Hub đích
        # Trả xe kết thúc chuyến nhưng không được tự gỡ khóa bảo trì/điều chuyển.
        blocked = self._rental_bike_blocked(vehicle_id, ignore_active_ride=True)
        maintenance = any(t.get("device_code") == vehicle_id
                          and t.get("status") in ("PENDING", "ASSIGNED", "IN_PROGRESS")
                          for t in self.maintenance_tickets)
        locked_status = returned_bike.get("status") in ("Đang bảo trì", "Bảo trì", "Không khả dụng")
        if blocked:
            returned_bike["status"] = "Đang bảo trì" if maintenance else "Không khả dụng"
        elif not locked_status:
            returned_bike["status"] = "Sẵn sàng"
        returned_bike.pop("reserved_by", None)
        returned_bike["battery_level"] = active_ride.get(
            "battery_level", returned_bike.get("battery_level", 75)
        )

        dest_hub["bikes"].append(returned_bike)
        if returned_bike["status"] == "Sẵn sàng":
            dest_hub["available_bikes"] += 1
        dest_hub["available_parking"] -= 1

        # Chỉ kết thúc chuyến đi sau khi cập nhật thành công
        booking["status"] = "Hoàn thành"
        booking["rental_trip"] = {
            **copy.deepcopy(active_ride),
            **charge,
            "booking_id": booking["id"],
            "status": "Hoàn thành",
            "ended_at": ended_at.isoformat(),
            "return_hub_id": dest_hub["id"],
            "return_hub_name": dest_hub["name"],
        }
        label = "Thời gian thuê từ khi đặt xe" if charge["billing_source"] == "billing_started_at" else "Thời gian sử dụng"
        description = f"{label}: {charge['elapsed_minutes']} phút"
        booking["rental_invoice"] = {
            "user_id": booking["user_id"],
            "id": f"INV-{trip_id}",
            "service_type": "rental",
            "title": "Hóa đơn thuê xe điện",
            "reference_id": vehicle_id,
            "items": [{"label": description, "description": description, "amount": charge["total_fee"]}],
            "total_amount": charge["total_fee"],
            "payment_channel": "online", "status": "unpaid",
            "created_at": ended_at.isoformat(),
        }
        self.user["active_services"]["ride"] = None

        self.telemetry_events.insert(0, {
            "id": f"TLM-{len(self.telemetry_events) + 100}",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "hub_name": dest_hub["name"],
            "event_type": "RENTAL_RETURN",
            "message": f"Xe {vehicle_id} đã được khóa an toàn và hoàn tất chuyến đi.",
            "level": "SUCCESS"
        })
        return {
            "success": True,
            "trip_id": trip_id,
            "vehicle_id": vehicle_id,
            "return_hub_name": return_hub_name,
            "elapsed_minutes": charge["elapsed_minutes"],
            "total_fee": charge["total_fee"]
        }

    def create_relocation_command(self, payload: dict):
        source = self.get_hub(payload["source_hub_id"])
        target = self.get_hub(payload["target_hub_id"])

        if source is None or target is None:
            raise RelocationError(404, "Không tìm thấy Hub nguồn hoặc Hub đích")

        if source["id"] == target["id"]:
            raise RelocationError(422, "Hub nguồn và Hub đích phải khác nhau")

        if source["status"] != "ACTIVE" or target["status"] != "ACTIVE":
            raise RelocationError(409, "Hub nguồn hoặc Hub đích không hoạt động")

        count = payload["bike_count"]
        if type(count) is not int or not 1 <= count <= 50:
            raise RelocationError(422, "Số xe phải là số nguyên từ 1 đến 50")

        staff = next(
            (
                person
                for person in self.staff
                if person["id"] == payload["assigned_staff_id"]
            ),
            None,
        )
        if staff is None:
            raise RelocationError(404, "Không tìm thấy nhân viên được giao")
        if staff["role"] != "RELOCATION":
            raise RelocationError(422, "Nhân viên không có vai trò điều chuyển")

        active_tasks = [
            task
            for task in self.relocations
            if task["status"] in ("PENDING", "IN_PROGRESS", "IN_TRANSIT")
        ]

        blocked_bike_ids = {
            entry["bike_id"]
            for task in active_tasks
            for entry in task["bikes"]
        }

        ride = self.user.get("active_services", {}).get("ride")
        if ride:
            blocked_bike_ids.add(ride["vehicle_id"])

        for booking in self.bookings:
            if (
                booking.get("plan_type") == "rental"
                and booking.get("status") in ("Đã xác nhận", "Đang sử dụng")
            ):
                bike_id = booking.get("resource_id")
                if not bike_id:
                    bike_id = booking.get("resource_name", "").split(" · ")[0]
                blocked_bike_ids.add(bike_id)

        blocked_bike_ids.update(
            ticket["device_code"]
            for ticket in self.maintenance_tickets
            if ticket["status"] in ("PENDING", "ASSIGNED", "IN_PROGRESS")
        )

        available_bikes = [
            bike
            for bike in source["bikes"]
            if bike["status"] == "Sẵn sàng"
            and bike["id"] not in blocked_bike_ids
        ]

        if len(available_bikes) < count:
            raise RelocationError(409, "Hub nguồn không đủ xe khả dụng")

        occupied_slot_ids = {
            record["slot_id"]
            for record in self.parking_records
            if record["hub_id"] == target["id"]
            and record.get("checkout_time") is None
        }

        for booking in self.bookings:
            if (
                booking.get("hub_id") == target["id"]
                and booking.get("plan_type") in ("parking", "personal")
                and booking.get("status") in ("Đã xác nhận", "Đang sử dụng")
            ):
                occupied_slot_ids.add(
                    booking.get("parking_slot") or booking.get("resource_id")
                    or booking.get("resource_name", "").split(" · ")[0]
                )

        incoming_tasks = [
            task
            for task in active_tasks
            if task["target_hub_id"] == target["id"]
        ]
        held_slot_ids = {
            slot_id
            for task in incoming_tasks
            for slot_id in task.get("reserved_slot_ids", [])
        }

        free_slots = [
            slot
            for slot in target["slots"]
            if slot["is_available"]
            and slot["id"] not in occupied_slot_ids
            and slot["id"] not in held_slot_ids
        ]

        # Lệnh seed cũ chưa lưu ID chỗ giữ: dành đủ số chỗ cho chúng.
        legacy_reserved_count = sum(
            task["total_bikes"]
            for task in incoming_tasks
            if not task.get("reserved_slot_ids")
        )
        free_slots = free_slots[legacy_reserved_count:]

        if len(free_slots) < count:
            raise RelocationError(409, "Hub đích không đủ chỗ trống")

        selected_bikes = available_bikes[:count]
        selected_slots = free_slots[:count]
        timestamp = datetime.now(timezone.utc).isoformat()
        priority = payload.get("priority", "Bình thường")
        if hasattr(priority, "value"):
            priority = priority.value

        task = {
            "task_id": f"CMD-{self.next_relocation_number}",
            "title": f"Điều chuyển {count} xe",
            "source_hub_id": source["id"],
            "source_hub_name": source["name"],
            "target_hub_id": target["id"],
            "target_hub_name": target["name"],
            "vehicle_type": "Xe đạp điện",
            "total_bikes": count,
            "in_transit_bikes": 0,
            "remaining_at_source": count,
            "status": "PENDING",
            "priority": priority,
            "notes": payload.get("notes"),
            "assigned_staff_id": staff["id"],
            "assigned_staff_name": staff["full_name"],
            "assigned_to": staff["id"],
            "created_at": timestamp,
            "updated_at": timestamp,
            "reserved_slot_ids": [slot["id"] for slot in selected_slots],
            "bikes": [
                {
                    "bike_id": bike["id"],
                    "battery_pct": bike["battery_level"],
                    "status": "PENDING",
                }
                for bike in selected_bikes
            ],
        }

        # Đây là chỗ duy nhất ghi vào store, sau toàn bộ kiểm tra.
        from ..notifications import notify
        notify(self, task["task_id"] + ":assigned", staff["id"],
               "Có nhiệm vụ điều chuyển mới", task["task_id"])
        self.relocations.insert(0, task)
        self.next_relocation_number += 1
        return task



    def scan_bike_relocation(self, task_id: str, bike_id: str):
        task = next((t for t in self.relocations if t["task_id"] == task_id or task_id in t["task_id"]), self.relocations[0])
        for b in task.get("bikes", []):
            if b["bike_id"] == bike_id:
                b["status"] = "VERIFIED"
                break
        verified_count = sum(1 for b in task.get("bikes", []) if b["status"] == "VERIFIED")
        task["in_transit_bikes"] = verified_count
        task["remaining_at_source"] = max(0, task["total_bikes"] - verified_count)
        return {"task": task, "verified_count": verified_count}

    def handover_relocation(self, task_id: str):
        task = next((t for t in self.relocations if t["task_id"] == task_id or task_id in t["task_id"]), self.relocations[0])
        task["status"] = "COMPLETED"
        task["in_transit_bikes"] = task["total_bikes"]
        task["remaining_at_source"] = 0

        # Transfer bike counts between hubs
        src = next((h for h in self.hubs if h["id"] == task.get("source_hub_id")), None)
        tgt = next((h for h in self.hubs if h["id"] == task.get("target_hub_id")), None)
        if src and src["available_bikes"] >= task["total_bikes"]:
            src["available_bikes"] -= task["total_bikes"]
        if tgt:
            tgt["available_bikes"] += task["total_bikes"]

        return {"task": task, "status": "COMPLETED"}

    def create_maintenance_ticket(self, payload: dict):
        numbers = [int(t["code"][5:]) for t in self.maintenance_tickets
                   if t.get("code", "").startswith("TICK-") and t["code"][5:].isdigit()]
        new_code = f"TICK-{max(numbers, default=800) + 1}"
        ticket = {
            "code": new_code,
            "title": payload.get("title", "Sự cố thiết bị mới"),
            "hub_name": payload.get("hub_name", "Hub Ga Metro ĐHQG"),
            "hub_id": payload.get("hub_id", "hub-01"),
            "device_type": payload.get("device_type", "Thiết bị"),
            "device_code": payload.get("device_code", "DEV-01"),
            "device_title": payload.get("title", "Thiết bị"),
            "reported_time": datetime.now().strftime("%d/%m/%Y · %H:%M"),
            "severity": payload.get("severity", "MEDIUM"),
            "priority": payload.get("priority", "NORMAL"),
            "status": "PENDING",
            "assigned_to": payload.get("assigned_to", "Chưa phân công"),
            "description": payload.get("description", "Sự cố được ghi nhận."),
            "guide_steps": ["Kiểm tra nguồn", "Xác thực thiết bị", "Tiến hành sửa chữa"],
            "verified": False,
            "created_at": datetime.now().isoformat()
        }
        self.maintenance_tickets.insert(0, ticket)
        return ticket

    def resolve_maintenance(self, task_code: str, resolution_notes: str,
                            outcome: str = "FIXED_ON_SITE", photo_url=None):
        from ..devices import resolve_ticket
        return resolve_ticket(self, task_code, resolution_notes, outcome, photo_url)

    def parking_checkin(self, payload: dict):
        """Dùng chỗ giữ của User khi có booking; giữ nhánh walk-in cũ của Staff."""
        from starlette.exceptions import HTTPException

        # Nhánh tương thích booking User mới: dùng đúng chỗ đã giữ, không trừ lần hai.
        hub = next((h for h in self.hubs if h["name"] == payload.get("hub_name") or h["id"] == payload.get("hub_id")), None)
        holds = [b for b in self.bookings if b.get("plan_type") in ("parking", "personal")
                     and b.get("status") == "Đã xác nhận" and hub and b.get("hub_id") == hub["id"]
                     and plate_key(b.get("personal_plate") or "") == plate_key(payload.get("plate_number", ""))
                     and b.get("parking_slot")]
        if len(holds) > 1:
            raise HTTPException(409, "Có nhiều booking gửi xe khớp biển số, chưa thể xác định chỗ giữ")
        held = holds[0] if holds else None
        opened = [r for r in self.parking_records if r.get('checkout_time') is None
                  and plate_key(r['plate_number']) == plate_key(payload.get('plate_number', ''))]
        if len(opened) > 1:
            raise HTTPException(409, "Biển số có nhiều vé đang mở")
        if opened and held is None:
            if hub is None or opened[0]['hub_id'] != hub['id']:
                raise HTTPException(409, "Biển số đang gửi xe tại Hub khác")
            return opened[0]
        if held is not None:
            if booking_expired(held, datetime.now(timezone.utc)) or hub.get("status") != "ACTIVE":
                raise HTTPException(409, "Booking gửi xe hết hạn hoặc Hub không hoạt động")
            slot = next((s for s in hub["slots"] if s["id"] == held["parking_slot"] and s.get("reserved_by") == held["id"]), None)
            if slot is None:
                raise HTTPException(409, "Chỗ giữ không còn khớp booking")
            if parking_slot_blocked(self, hub, slot):
                raise HTTPException(409, "Chỗ đỗ đang bảo trì hoặc không khả dụng")
            if held.get('personal_bundle'):
                from ..charging_reservations import charging_port_blocked
                ports = [p for p in hub.get('ports', []) if p['id'] == held.get('charging_port')]
                if (not self._personal_hold_owned(held) or len(ports) != 1
                    or ports[0].get('status') != 'Đã đặt chỗ'
                    or charging_port_blocked(self, hub, ports[0]['id'], ignore_booking_id=held['id'])):
                    raise HTTPException(409, 'Cổng sạc của gói ghép không còn khả dụng')
            if opened:
                raise HTTPException(409, "Biển số đang có vé gửi xe chưa kết thúc")
            if self.owns_user_record(held) and self.user.get("active_services", {}).get("parking"):
                raise HTTPException(409, "Người dùng đang có phiên gửi xe khác")
            if slot is not None:
                numbers = [int(r["ticket_code"][4:]) for r in self.parking_records
                           if r["ticket_code"].startswith("PRK-") and r["ticket_code"][4:].isdigit()]
                record = {
                    "user_id": held["user_id"],
                    "ticket_code": f"PRK-{max(numbers, default=900) + 1}",
                    "booking_id": held["id"], "plate_number": held["personal_plate"],
                    "vehicle_type": payload.get("vehicle_type", "Xe máy điện"),
                    "hub_id": hub["id"], "hub_name": hub["name"], "slot_id": slot["id"],
                    "checkin_time": datetime.now(timezone.utc).isoformat(), "checkout_time": None,
                    "duration_display": "0 phút", "parking_fee": 0, "parking_hourly_rate": slot.get("hourly_rate", hub.get("pricing", {}).get("parking_hourly")),
                    "payment_status": "PENDING", "guard_id": payload.get("guard_id", "STF-02"),
                }
                self.parking_records.insert(0, record)
                held["status"] = "Đang sử dụng"
                slot.pop("reserved_by")
                slot["occupied_by"] = record["ticket_code"]
                active_parking = {
                    "user_id": held["user_id"],
                    "ticket_id": record["ticket_code"], "plate_number": record["plate_number"],
                    "hub_name": hub["name"], "slot_id": slot["id"],
                    "checkin_time": record["checkin_time"], "elapsed_minutes": 0,
                }
                profiles = [self.__dict__["user"]] + [a["profile"] for a in
                    self.operator_mock.get("accounts", []) if a["role"] == "user"]
                for profile in profiles:
                    if profile["id"] == held["user_id"]:
                        profile.setdefault("active_services", {})["parking"] = active_parking
                return record
        if any(b.get("parking_slot") and b.get("status") in ("Đã xác nhận", "Đang sử dụng")
               and plate_key(b.get("personal_plate") or "") == plate_key(payload.get("plate_number", ""))
               for b in self.bookings):
            raise HTTPException(409, "Biển số đang có booking tại Hub khác hoặc đang gửi xe")
        if hub is None:
            raise HTTPException(404, "Hub không tồn tại")
        from ..parking_reservations import choose_parking_slot
        requested_slot = payload.get("slot_id", "").split(" · ")[-1].strip()
        try:
            slot = choose_parking_slot(self, hub, {
                "personal_plate": payload.get("plate_number"), "parking_slot": requested_slot or None,
            })
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        numbers = [int(r["ticket_code"][4:]) for r in self.parking_records
                   if r.get("ticket_code", "").startswith("PRK-") and r["ticket_code"][4:].isdigit()]
        ticket_code = f"PRK-{max(numbers, default=900) + 1}"
        slot_id = slot["id"]

        record = {
            "ticket_code": ticket_code,
            "plate_number": payload.get("plate_number", "59-A1 999.99"),
            "vehicle_type": payload.get("vehicle_type", "Xe máy điện"),
            "hub_id": hub["id"],
            "hub_name": hub["name"],
            "slot_id": slot_id,
            "checkin_time": datetime.now(timezone.utc).isoformat(),
            "checkout_time": None,
            "duration_display": "0 phút",
            "parking_fee": 0,
            "parking_hourly_rate": slot.get("hourly_rate", hub.get("pricing", {}).get("parking_hourly")),
            "payment_status": "PENDING",
            "guard_id": payload.get("guard_id", "STF-02")
        }
        self.parking_records.insert(0, record)
        slot.update(is_available=False, occupied_by=ticket_code)
        hub["available_parking"] -= 1
        return record

    def parking_checkout_confirm(self, ticket_code: str, payment_method: str, quote_token=None, cash_received=None):
        """Xác định duy nhất vé, kiểm tra liên kết rồi thu phí/hoàn chỗ một lần.

        Mã vé được ưu tiên. Nếu dùng biển số, chọn vé đang mở duy nhất thay
        vì vé lịch sử đầu tiên. Không tự chọn khi dữ liệu có nhiều vé khớp.
        """
        from starlette.exceptions import HTTPException

        if not isinstance(ticket_code, str) or not ticket_code.strip():
            raise HTTPException(422, "Cần cung cấp mã vé hoặc biển số")
        if not isinstance(payment_method, str) or not payment_method.strip():
            raise HTTPException(422, "Phương thức thu phí không hợp lệ")
        matches = [r for r in self.parking_records if r['ticket_code'] == ticket_code]
        if not matches:
            matches = [r for r in self.parking_records if plate_key(r['plate_number']) == plate_key(ticket_code)]
            opened = [r for r in matches if r.get('checkout_time') is None]
            if opened:
                matches = opened
        if not matches:
            raise HTTPException(404, "Không tìm thấy vé gửi xe")
        if len(matches) != 1:
            raise HTTPException(409, "Không xác định được vé duy nhất; cần kiểm tra mã vé")
        record = matches[0]
        if record.get('checkout_time') is not None:
            if record.get('payment_status') != 'PAID':
                raise HTTPException(409, "Vé đã kết thúc nhưng trạng thái thu phí không nhất quán")
            return record

        hub = self.get_hub(record['hub_id'])
        if hub is None:
            raise HTTPException(409, "Không xác định được Hub của vé gửi xe")
        count = hub.get('available_parking')
        capacity = hub.get('parking_capacity')
        if type(count) is not int or type(capacity) is not int or not 0 <= count < capacity:
            raise HTTPException(409, "Bộ đếm chỗ đỗ không hợp lệ")
        booking = None
        slot = None
        if record.get('booking_id'):
            bookings = [b for b in self.bookings if b['id'] == record['booking_id']]
            if len(bookings) != 1:
                raise HTTPException(409, "Không xác định được booking của vé gửi xe")
            booking = bookings[0]
            if (booking.get('plan_type') not in ('parking', 'personal') or booking.get('status') != 'Đang sử dụng'
                or booking.get('hub_id') != hub['id'] or booking.get('parking_slot') != record['slot_id']
                or plate_key(booking.get('personal_plate') or '') != plate_key(record['plate_number'])
                or record.get('user_id', booking.get('user_id')) != booking.get('user_id')):
                raise HTTPException(409, "Vé không khớp booking đang gửi xe")
            slots = [s for s in hub.get('slots', []) if s['id'] == record['slot_id']]
            if len(slots) != 1 or slots[0].get('occupied_by') != record['ticket_code'] or slots[0].get('reserved_by'):
                raise HTTPException(409, "Chỗ đỗ không còn khớp vé gửi xe")
            slot = slots[0]
            if booking.get('personal_bundle') and (booking.get('charging_session') or {}).get('status') != 'Hoàn thành':
                raise HTTPException(409, 'Cần kết thúc phiên sạc của gói ghép trước khi ra bãi')
        else:
            # Vé seed/walk-in cũ có thể chưa lưu trạng thái occupied_by.
            slot = next((s for s in hub.get('slots', []) if s['id'] == record['slot_id']), None)
            if slot and (slot.get('reserved_by') or slot.get('occupied_by') not in (None, record['ticket_code'])):
                raise HTTPException(409, "Chỗ đỗ đang thuộc vé hoặc booking khác")

        from ..parking_pricing import checkout_quote, verified_quote
        quote = verified_quote(self, record, quote_token) if quote_token else checkout_quote(self, record)
        if cash_received is not None and (type(cash_received) is not int or cash_received < quote["parking_fee"]):
            raise HTTPException(422, "Số tiền nhận chưa đủ hoặc không hợp lệ")
        record.update({key: quote[key] for key in (
            "parking_fee", "parking_hourly_rate", "elapsed_minutes", "billable_hours", "duration_display"
        )})
        blocked = slot is not None and parking_slot_blocked(self, hub, slot)
        checkout_time = quote["checkout_time"]
        record["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        # Chỉ ghi sau khi toàn bộ vé, booking và tài nguyên đã được đối chiếu.
        record.update(checkout_time=checkout_time, payment_status='PAID', payment_method=payment_method.strip())
        if booking is not None:
            booking.update(status='Hoàn thành', completed_at=checkout_time)
        if slot is not None:
            if slot.get('occupied_by') == record['ticket_code']:
                slot.pop('occupied_by')
            slot['is_available'] = not blocked
        if not blocked:
            hub['available_parking'] += 1
        profiles = [self.__dict__["user"]] + [a["profile"] for a in
            self.operator_mock.get("accounts", []) if a["role"] == "user"]
        for profile in profiles:
            active = profile.get("active_services", {}).get("parking")
            if active and active.get("ticket_id") == record["ticket_code"]:
                profile["active_services"]["parking"] = None
        return record

    def get_kpis(self):
        total_bikes = sum(len(h.get("bikes", [])) for h in self.hubs) + 40
        avail_bikes = sum(h.get("available_bikes", 0) for h in self.hubs)
        total_chargers = sum(len(h.get("ports", [])) for h in self.hubs) + 10
        avail_chargers = sum(h.get("available_chargers", 0) for h in self.hubs)
        total_parking = sum(h.get("parking_capacity", 20) for h in self.hubs)
        avail_parking = sum(h.get("available_parking", 0) for h in self.hubs)

        return {
            "total_hubs": len(self.hubs),
            "available_bikes": avail_bikes,
            "total_bikes": total_bikes,
            "active_rides": 1 if self.user["active_services"].get("ride") else 0,
            "available_chargers": avail_chargers,
            "total_chargers": total_chargers,
            "available_parking": avail_parking,
            "total_parking": total_parking,
            "relocations_in_progress": sum(1 for r in self.relocations if r["status"] == "IN_PROGRESS"),
            "open_maintenance_tickets": sum(1 for m in self.maintenance_tickets if m["status"] in ["PENDING", "ASSIGNED", "IN_PROGRESS"]),
            "system_health_pct": 98.5
        }


# Global Singleton Database Instance
db = MockDatabaseStore()
