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

from seed_loader import load_seed


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

    def get_user_profile(self):
        return self.user

    def get_user_vehicles(self):
        return self.user.get("vehicles", [])

    def get_bookings(self):
        return self.bookings

    def create_booking(self, payload: dict):
        new_id = f"EMH-{1020 + len(self.bookings) + 1}"
        hub = self.get_hub(payload.get("hub_id", "hub-01"))
        hub_name = hub["name"] if hub else "Hub Ga Metro ĐHQG"
        plan_type = payload.get("plan_type", "rental")

        if plan_type == "rental":
            if not hub:
                return {"error": "Hub không tồn tại"}

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
                or hub.get("available_bikes", 0) <= 0
            ):
                return {"error": "Xe không khả dụng hoặc đã được đặt"}

        # Reserve bike if rental
        if plan_type == "rental" and hub:
            dest_hub = payload.get("destination_hub_name", "Hub Đại học Bách khoa")
            resource_name = payload.get("resource_name", "XE-031 · Xe đạp điện")
            # Mark bike as reserved
            bike_id = resource_name.split(" · ")[0] if " · " in resource_name else "XE-031"
            for b in hub.get("bikes", []):
                if b["id"] == bike_id:
                    b["status"] = "Đã đặt chỗ"
                    break
            if hub["available_bikes"] > 0:
                hub["available_bikes"] -= 1

            booking_obj = {
                "id": new_id,
                "hub_id": hub["id"],
                "hub_name": hub_name,
                "plan_type": "rental",
                "resource_name": resource_name,
                "destination_hub_name": dest_hub,
                "hold_until": (datetime.now() + timedelta(minutes=10)).strftime("%H:%M"),
                "status": "Đã xác nhận",
                "created_at": datetime.now().strftime("%H:%M"),
                "price": 10000,
                "services": payload.get("services", [{"service_type": "rental", "detail": f"Thuê xe đạp điện {bike_id}", "price_est": 10000}])
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
        bk = next((b for b in self.bookings if b["id"] == booking_id), None)
        if not bk:
            return None
        if bk.get("status") != "Đã xác nhận":
            return {
                "error": "Booking đã hủy hoặc không còn hiệu lực"
            }
        bk["status"] = "Đã hủy"

        # Restore resources if rental
        if bk.get("plan_type") == "rental":
            hub = self.get_hub(bk.get("hub_id", "hub-01"))
            if hub:
                hub["available_bikes"] = min(len(hub.get("bikes", [])), hub["available_bikes"] + 1)
                bike_id = bk.get("resource_name", "").split(" · ")[0]
                for b in hub.get("bikes", []):
                    if b["id"] == bike_id:
                        b["status"] = "Sẵn sàng"
                        break
        return bk

    def start_ride(self, booking_id: str):
        booking = next(
            (b for b in self.bookings if b["id"] == booking_id),
            None
        )

        if not booking:
            return {"success": False, "error": "Booking không tồn tại"}

        if booking.get("plan_type") != "rental":
            return {"success": False, "error": "Không phải booking thuê xe"}

        if booking.get("status") != "Đã xác nhận":
            return {"success": False, "error": "Booking không còn hiệu lực"}

        if self.user["active_services"].get("ride"):
            return {"success": False, "error": "Bạn đang có chuyến đi khác"}

        hub = self.get_hub(booking["hub_id"])
        if not hub:
            return {"success": False, "error": "Hub không tồn tại"}

        vehicle_id = booking["resource_name"].split(" · ")[0].strip()

        bike = next(
            (b for b in hub["bikes"] if b["id"] == vehicle_id),
            None
        )

        if not bike or bike["status"] != "Đã đặt chỗ":
            return {"success": False, "error": "Xe không khả dụng"}

        # Xe rời Hub nguồn
        hub["bikes"].remove(bike)
        hub["available_parking"] = min(
            hub["parking_capacity"],
            hub["available_parking"] + 1
        )

        booking["status"] = "Đang sử dụng"

        trip = {
            "trip_id": f"TRIP-{datetime.now().strftime('%H%M%S')}",
            "vehicle_id": vehicle_id,
            "origin_hub": hub["name"],
            "destination_hub": booking.get("destination_hub_name"),
            "elapsed_minutes": 0,
            "battery_level": bike["battery_level"],
            "status": "Đang sử dụng"
        }

        self.user["active_services"]["ride"] = trip

        return {
            "success": True,
            "ride": trip
        }

    def return_vehicle(self, trip_id: str, return_hub_name: str):
        # Clear active ride
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

        vehicle_id = active_ride["vehicle_id"]

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

        if dest_hub.get("available_parking", 0) <= 0:
            return {
                "success": False,
                "error": "Hub đích không còn chỗ đỗ"
            }

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
                "hourly_rate": 10000
            }

        # Cập nhật xe tại Hub đích
        returned_bike["status"] = "Sẵn sàng"
        returned_bike["battery_level"] = active_ride.get(
            "battery_level", returned_bike.get("battery_level", 75)
        )

        dest_hub["bikes"].append(returned_bike)
        dest_hub["available_bikes"] += 1
        dest_hub["available_parking"] -= 1

        # Chỉ kết thúc chuyến đi sau khi cập nhật thành công
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
            "elapsed_minutes": 15,
            "total_fee": 10000
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
                and booking.get("plan_type") == "parking"
                and booking.get("status") in ("Đã xác nhận", "Đang sử dụng")
            ):
                occupied_slot_ids.add(
                    booking.get("resource_id")
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
        new_code = f"TICK-{800 + len(self.maintenance_tickets) + 1}"
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

    def resolve_maintenance(self, task_code: str, resolution_notes: str):
        ticket = next((t for t in self.maintenance_tickets if t["code"] == task_code), None)
        if ticket:
            ticket["status"] = "RESOLVED"
            ticket["resolution_notes"] = resolution_notes
            # If related to a hub port or bike, restore it
            if "S02" in ticket.get("device_code", ""):
                h = self.get_hub("hub-01")
                if h:
                    for p in h.get("ports", []):
                        if p["id"] == "S02":
                            p["is_available"] = True
                            p["status"] = "Sẵn sàng"
        return ticket

    def parking_checkin(self, payload: dict):
        ticket_code = f"PRK-{900 + len(self.parking_records) + 1}"
        hub_name = payload.get("hub_name", "Hub Ga Metro ĐHQG")
        hub = next((h for h in self.hubs if h["name"] == hub_name or h["id"] == payload.get("hub_id")), self.hubs[0])
        slot_id = payload.get("slot_id", f"P{len(self.parking_records)+1:02d}")

        record = {
            "ticket_code": ticket_code,
            "plate_number": payload.get("plate_number", "59-A1 999.99"),
            "vehicle_type": payload.get("vehicle_type", "Xe máy điện"),
            "hub_id": hub["id"],
            "hub_name": hub["name"],
            "slot_id": slot_id,
            "checkin_time": datetime.now().strftime("%d/%m/%Y · %H:%M"),
            "checkout_time": None,
            "duration_display": "0 phút",
            "parking_fee": 5000,
            "payment_status": "PENDING",
            "guard_id": "STF-02"
        }
        self.parking_records.insert(0, record)
        if hub["available_parking"] > 0:
            hub["available_parking"] -= 1
        return record

    def parking_checkout_confirm(self, ticket_code: str, payment_method: str):
        record = next((r for r in self.parking_records if r["ticket_code"] == ticket_code or r["plate_number"] == ticket_code), None)
        if record:
            record["checkout_time"] = datetime.now().strftime("%d/%m/%Y · %H:%M")
            record["payment_status"] = "PAID"
            record["payment_method"] = payment_method
            hub = self.get_hub(record["hub_id"])
            if hub:
                hub["available_parking"] += 1
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
