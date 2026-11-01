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



from datetime import timezone


class RelocationError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


class MockDatabaseStore:
    def __init__(self):
        self.reset()

    def reset(self):
        # 1. HUBS (Central hub inventory & live counters)
        self.hubs = [
            {
                "id": "hub-01",
                "hub_code": "HUB-01",
                "name": "Hub Ga Metro ĐHQG",
                "address": "Khu đô thị ĐHQG - HCM",
                "lat": 10.8753,
                "lng": 106.8005,
                "parking_capacity": 20,
                "charger_capacity": 4,
                "max_power_kw": 100.0,
                "load_warning_threshold_pct": 85,
                "status": "ACTIVE",
                "available_bikes": 3,
                "available_parking": 8,
                "available_chargers": 2,
                "available_batteries": 6,
                "availability_rate_pct": 92,
                "color": "#10b981",
                "pricing": {
                    "rental_bike_hourly": 10000,
                    "parking_hourly": 2500,
                    "charging_kwh": 3500,
                    "battery_swap_fee": 25000
                },
                "bikes": [
                    {"id": "XE-024", "name": "Xe đạp điện", "battery_level": 85, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "XE-031", "name": "Xe đạp điện", "battery_level": 92, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "XE-045", "name": "Xe đạp điện", "battery_level": 70, "status": "Sẵn sàng", "hourly_rate": 10000}
                ],
                "ports": [
                    {"id": "S01", "name": "Trụ sạc nhanh S01 (AC 7.4 kW)", "power_kw": 7.4, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3500, "time_slots": ["08:00 – 09:00", "09:00 – 10:00"]},
                    {"id": "S02", "name": "Trụ sạc nhanh S02 (AC 7.4 kW)", "power_kw": 7.4, "is_available": False, "status": "Đang bảo trì", "rate_per_kwh": 3500, "time_slots": []},
                    {"id": "S03", "name": "Trụ sạc nhanh S03 (AC 11 kW)", "power_kw": 11.0, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3500, "time_slots": ["10:00 – 11:00", "11:00 – 12:00"]},
                    {"id": "S04", "name": "Trụ sạc thường S04 (AC 3.3 kW)", "power_kw": 3.3, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3000, "time_slots": ["11:00 – 12:00", "14:00 – 15:00"]}
                ],
                "slots": [
                    {"id": "P01", "name": "Chỗ đỗ P01", "bay": "Khu A", "is_available": True, "hourly_rate": 2500},
                    {"id": "P02", "name": "Chỗ đỗ P02", "bay": "Khu A", "is_available": True, "hourly_rate": 2500},
                    {"id": "P03", "name": "Chỗ đỗ P03", "bay": "Khu A", "is_available": False, "hourly_rate": 2500},
                    {"id": "P04", "name": "Chỗ đỗ P04", "bay": "Khu B", "is_available": True, "hourly_rate": 2500},
                    {"id": "P05", "name": "Chỗ đỗ P05", "bay": "Khu B", "is_available": True, "hourly_rate": 2500},
                    {"id": "P06", "name": "Chỗ đỗ P06", "bay": "Khu B", "is_available": True, "hourly_rate": 2500},
                    {"id": "P07", "name": "Chỗ đỗ P07", "bay": "Khu B", "is_available": False, "hourly_rate": 2500},
                    {"id": "P08", "name": "Chỗ đỗ P08", "bay": "Khu B", "is_available": True, "hourly_rate": 2500}
                ],
                "batteries": [
                    {"battery_type": "B48", "name": "Pin Li-ion 48V-20Ah", "available_count": 4, "swap_fee": 25000},
                    {"battery_type": "LFP-72", "name": "Pin LFP 72V-30Ah", "available_count": 2, "swap_fee": 35000}
                ]
            },
            {
                "id": "hub-02",
                "hub_code": "HUB-02",
                "name": "Hub Đại học Bách khoa",
                "address": "Đường D3, Khu ĐHQG - HCM",
                "lat": 10.8805,
                "lng": 106.8055,
                "parking_capacity": 30,
                "charger_capacity": 6,
                "max_power_kw": 120.0,
                "load_warning_threshold_pct": 85,
                "status": "ACTIVE",
                "available_bikes": 8,
                "available_parking": 14,
                "available_chargers": 3,
                "available_batteries": 5,
                "availability_rate_pct": 88,
                "color": "#10b981",
                "pricing": {
                    "rental_bike_hourly": 10000,
                    "parking_hourly": 2500,
                    "charging_kwh": 3500,
                    "battery_swap_fee": 25000
                },
                "bikes": [
                    {"id": "XE-052", "name": "Xe đạp điện", "battery_level": 90, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "XE-061", "name": "Xe đạp điện", "battery_level": 88, "status": "Sẵn sàng", "hourly_rate": 10000}
                ],
                "ports": [
                    {"id": "S11", "name": "Trụ sạc nhanh S11 (AC 7.4 kW)", "power_kw": 7.4, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3500, "time_slots": ["08:00 – 09:00"]},
                    {"id": "S12", "name": "Trụ sạc AC 11 kW", "power_kw": 11.0, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3500, "time_slots": ["09:00 – 10:00"]}
                ],
                "slots": [
                    {"id": "P11", "name": "Chỗ đỗ P11", "bay": "Khu A", "is_available": True, "hourly_rate": 2500},
                    {"id": "P12", "name": "Chỗ đỗ P12", "bay": "Khu A", "is_available": True, "hourly_rate": 2500}
                ],
                "batteries": [
                    {"battery_type": "B48", "name": "Pin Li-ion 48V-20Ah", "available_count": 5, "swap_fee": 25000}
                ]
            },
            {
                "id": "hub-03",
                "hub_code": "HUB-03",
                "name": "Hub KTX Khu B",
                "address": "Khu B, ĐHQG - HCM",
                "lat": 10.8825,
                "lng": 106.7825,
                "parking_capacity": 40,
                "charger_capacity": 8,
                "max_power_kw": 150.0,
                "load_warning_threshold_pct": 80,
                "status": "ACTIVE",
                "available_bikes": 12,
                "available_parking": 20,
                "available_chargers": 4,
                "available_batteries": 10,
                "availability_rate_pct": 75,
                "color": "#10b981",
                "pricing": {
                    "rental_bike_hourly": 10000,
                    "parking_hourly": 2500,
                    "charging_kwh": 3500,
                    "battery_swap_fee": 25000
                },
                "bikes": [
                    {"id": "BK-0891", "name": "Xe đạp điện", "battery_level": 98, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "BK-0412", "name": "Xe đạp điện", "battery_level": 85, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "BK-0553", "name": "Xe đạp điện", "battery_level": 92, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "BK-0764", "name": "Xe đạp điện", "battery_level": 79, "status": "Sẵn sàng", "hourly_rate": 10000},
                    {"id": "BK-0125", "name": "Xe đạp điện", "battery_level": 88, "status": "Sẵn sàng", "hourly_rate": 10000}
                ],
                "ports": [
                    {"id": "S21", "name": "Trụ sạc AC 7.4 kW", "power_kw": 7.4, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3500, "time_slots": ["08:00 – 12:00"]}
                ],
                "slots": [
                    {"id": "P21", "name": "Chỗ đỗ P21", "bay": "Khu A", "is_available": True, "hourly_rate": 2500}
                ],
                "batteries": [
                    {"battery_type": "B48", "name": "Pin Li-ion 48V-20Ah", "available_count": 8, "swap_fee": 25000},
                    {"battery_type": "LFP-72", "name": "Pin LFP 72V-30Ah", "available_count": 2, "swap_fee": 35000}
                ]
            },
            {
                "id": "hub-04",
                "hub_code": "HUB-04",
                "name": "Hub Đại học Quốc Tế",
                "address": "Đường C1, Khu ĐHQG - HCM",
                "lat": 10.8775,
                "lng": 106.7975,
                "parking_capacity": 15,
                "charger_capacity": 2,
                "max_power_kw": 60.0,
                "load_warning_threshold_pct": 85,
                "status": "ACTIVE",
                "available_bikes": 4,
                "available_parking": 6,
                "available_chargers": 2,
                "available_batteries": 4,
                "availability_rate_pct": 95,
                "color": "#10b981",
                "pricing": {
                    "rental_bike_hourly": 10000,
                    "parking_hourly": 2500,
                    "charging_kwh": 3500,
                    "battery_swap_fee": 25000
                },
                "bikes": [
                    {"id": "XE-090", "name": "Xe đạp điện", "battery_level": 80, "status": "Sẵn sàng", "hourly_rate": 10000}
                ],
                "ports": [
                    {"id": "S31", "name": "Trụ sạc AC 3.3 kW", "power_kw": 3.3, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3000, "time_slots": []}
                ],
                "slots": [
                    {"id": "P31", "name": "Chỗ đỗ P31", "bay": "Khu A", "is_available": True, "hourly_rate": 2500}
                ],
                "batteries": [
                    {"battery_type": "B48", "name": "Pin Li-ion 48V-20Ah", "available_count": 4, "swap_fee": 25000}
                ]
            },
            {
                "id": "hub-05",
                "hub_code": "HUB-05",
                "name": "Hub Thư viện Trung tâm",
                "address": "Trung tâm ĐHQG - HCM",
                "lat": 10.8701,
                "lng": 106.8021,
                "parking_capacity": 25,
                "charger_capacity": 3,
                "max_power_kw": 80.0,
                "load_warning_threshold_pct": 85,
                "status": "ACTIVE",
                "available_bikes": 6,
                "available_parking": 10,
                "available_chargers": 2,
                "available_batteries": 3,
                "availability_rate_pct": 82,
                "color": "#10b981",
                "pricing": {
                    "rental_bike_hourly": 10000,
                    "parking_hourly": 2500,
                    "charging_kwh": 3500,
                    "battery_swap_fee": 25000
                },
                "bikes": [
                    {"id": "XE-101", "name": "Xe đạp điện", "battery_level": 84, "status": "Sẵn sàng", "hourly_rate": 10000}
                ],
                "ports": [
                    {"id": "S41", "name": "Trụ sạc AC 7.4 kW", "power_kw": 7.4, "is_available": True, "status": "Sẵn sàng", "rate_per_kwh": 3500, "time_slots": []}
                ],
                "slots": [
                    {"id": "P41", "name": "Chỗ đỗ P41", "bay": "Khu A", "is_available": True, "hourly_rate": 2500}
                ],
                "batteries": [
                    {"battery_type": "B48", "name": "Pin Li-ion 48V-20Ah", "available_count": 3, "swap_fee": 25000}
                ]
            }
        ]

        # 2. USER PROFILE & PERSONAL FLEET
        self.user = {
            "id": "USR-001",
            "full_name": "Nguyễn Văn A",
            "email": "abc123@hcmut.edu.vn",
            "phone": "0123456789",
            "avatar_url": None,
            "default_payment_method": "Ví điện tử",
            "role": "End-User",
            "vehicles": [
                {"id": "VEH-01", "type": "Xe máy điện", "plate_number": "59-X1 123.45", "model": "VinFast Klara S", "battery_type": "B48"},
                {"id": "VEH-02", "type": "Xe đạp điện", "plate_number": "59-MD 889.92", "model": "Pega Cap-A", "battery_type": "B48"},
                {"id": "VEH-03", "type": "Xe máy điện", "plate_number": "59-V1 456.78", "model": "VinFast Feliz Neo", "battery_type": "LFP-72"}
            ],
            "active_services": {
                "ride": {
                    "trip_id": "TRIP-8821",
                    "vehicle_id": "XE-024",
                    "origin_hub": "Hub Ga Metro ĐHQG",
                    "destination_hub": "Hub Đại học Bách khoa",
                    "elapsed_minutes": 13,
                    "battery_level": 78,
                    "status": "Đang sử dụng"
                },
                "parking": {
                    "ticket_id": "PRK-901",
                    "plate_number": "59-X1 123.45",
                    "hub_name": "Hub Ga Metro ĐHQG",
                    "slot_id": "P08",
                    "checkin_time": "10:00",
                    "elapsed_minutes": 45
                },
                "charging": {
                    "session_id": "CHG-302",
                    "port_id": "S03",
                    "power_consumed_kwh": 2.4,
                    "current_charge": 65,
                    "status": "Đang sạc"
                }
            }
        }

        # 3. BOOKINGS
        self.bookings = [
            {
                "id": "EMH-1024",
                "hub_id": "hub-01",
                "hub_name": "Hub Ga Metro ĐHQG",
                "plan_type": "rental",
                "resource_name": "XE-024 · Xe đạp điện",
                "destination_hub_name": "Hub Đại học Bách khoa",
                "hold_until": "10:15",
                "status": "Đã xác nhận",
                "created_at": "10:05",
                "price": 10000,
                "services": [{"service_type": "rental", "detail": "Thuê xe đạp điện XE-024 (Pin 85%)", "price_est": 10000}]
            },
            {
                "id": "EMH-1025",
                "hub_id": "hub-01",
                "hub_name": "Hub Ga Metro ĐHQG",
                "plan_type": "parking",
                "resource_name": "Chỗ đỗ P08",
                "personal_plate": "59-X1 123.45",
                "hold_until": "14:00",
                "status": "Đã xác nhận",
                "created_at": "09:30",
                "price": 5000,
                "services": [{"service_type": "parking", "detail": "Chỗ đỗ P08 · Xe máy điện 59-X1 123.45", "price_est": 5000}]
            }
        ]

        self.staff = [
            {
                "id": "STF-01",
                "full_name": "Nhân viên điều chuyển 1",
                "role": "RELOCATION",
            },
            {
                "id": "STF-02",
                "full_name": "Nguyen Van B",
                "role": "MAINTENANCE",
            },
        ]

        # 4. RELOCATION TASKS (Operator & Staff shared)
        self.relocations = [
            {
                "task_id": "#102",
                "title": "Hướng dẫn di chuyển điều phối xe",
                "source_hub_id": "hub-03",
                "source_hub_name": "Hub KTX Khu B",
                "target_hub_id": "hub-01",
                "target_hub_name": "Hub Ga Metro ĐHQG",
                "vehicle_type": "Xe đạp điện",
                "total_bikes": 5,
                "in_transit_bikes": 3,
                "remaining_at_source": 2,
                "estimated_distance_km": 2.5,
                "source_contact": "0901-234-567 (Hub Trưởng KTX B)",
                "target_contact": "0908-765-432 (Trực ban Hub Ga Metro)",
                "status": "IN_PROGRESS",
                "priority": "HIGH",
                "assigned_to": "STF-02 (Nguyen Van B)",
                "created_at": "2026-10-18T08:30:00",
                "bikes": [
                    {"bike_id": "BK-0891", "battery_pct": 98, "status": "VERIFIED"},
                    {"bike_id": "BK-0412", "battery_pct": 85, "status": "PENDING"},
                    {"bike_id": "BK-0553", "battery_pct": 92, "status": "VERIFIED"},
                    {"bike_id": "BK-0764", "battery_pct": 79, "status": "PENDING"},
                    {"bike_id": "BK-0125", "battery_pct": 88, "status": "VERIFIED"}
                ]
            },
            {
                "task_id": "#101",
                "title": "Điều phối xe giờ cao điểm sáng",
                "source_hub_id": "hub-04",
                "source_hub_name": "Hub Đại học Quốc Tế",
                "target_hub_id": "hub-05",
                "target_hub_name": "Hub Thư viện Trung tâm",
                "vehicle_type": "Xe đạp điện",
                "total_bikes": 4,
                "in_transit_bikes": 4,
                "remaining_at_source": 0,
                "estimated_distance_km": 1.2,
                "source_contact": "0903-111-222",
                "target_contact": "0903-333-444",
                "status": "COMPLETED",
                "priority": "NORMAL",
                "assigned_to": "STF-01",
                "created_at": "2026-10-18T07:00:00",
                "bikes": [
                    {"bike_id": "XE-090", "battery_pct": 80, "status": "VERIFIED"}
                ]
            }
        ]

        self.next_relocation_number = 103

        # 5. MAINTENANCE TICKETS (Operator, Staff, User Incident shared)
        self.maintenance_tickets = [
            {
                "code": "TICK-801",
                "title": "Sửa chốt khóa Smartlock xe XE-019",
                "hub_name": "Hub KTX Khu B",
                "hub_id": "hub-03",
                "device_type": "Smartlock xe đạp",
                "device_code": "LOCK-019",
                "device_title": "Khóa thông minh Smartlock XE-019",
                "reported_time": "18/10/2026 · 09:15",
                "severity": "MEDIUM",
                "priority": "NORMAL",
                "status": "ASSIGNED",
                "assigned_to": "STF-02 (Nguyen Van B)",
                "description": "Chốt khóa tự động không nhả khi người dùng quét mã mở khóa.",
                "guide_steps": [
                    "Sử dụng thiết bị cầm tay quét mã QR trên chốt khóa.",
                    "Kiểm tra nguồn pin dự phòng của khóa và tín hiệu BLE.",
                    "Nếu motor kẹt cơ học, dùng lục giác 4mm nới lỏng ốc định vị.",
                    "Nhập mã xác thực kỹ thuật viên và kiểm tra chu trình đóng/mở."
                ],
                "verified": False,
                "created_at": "2026-10-18T09:15:00"
            },
            {
                "code": "TICK-802",
                "title": "Kiểm tra chạm mạch trụ sạc nhanh S02",
                "hub_name": "Hub Ga Metro ĐHQG",
                "hub_id": "hub-01",
                "device_type": "Trụ sạc AC",
                "device_code": "S02",
                "device_title": "Trụ sạc nhanh S02 (AC 7.4 kW)",
                "reported_time": "18/10/2026 · 08:30",
                "severity": "HIGH",
                "priority": "URGENT",
                "status": "PENDING",
                "assigned_to": "Chưa phân công",
                "description": "Cảm biến nhiệt độ báo quá dòng, tạm thời ngắt kết nối an toàn.",
                "guide_steps": [
                    "Ngắt aptomat tổng cấp cho trụ S02.",
                    "Dùng đồng hồ VOM đo điện áp rò vỏ và trở kháng tiếp địa.",
                    "Kiểm tra tiếp điểm contactor và quạt làm mát biến tần."
                ],
                "verified": False,
                "created_at": "2026-10-18T08:30:00"
            },
            {
                "code": "TICK-803",
                "title": "Kẹt khay tủ pin thông minh ngăn số 4",
                "hub_name": "Hub Thư viện Trung tâm",
                "hub_id": "hub-05",
                "device_type": "Tủ đổi pin BSS",
                "device_code": "BSS-CAB-04",
                "device_title": "Ngăn tủ đổi pin BSS-04",
                "reported_time": "18/10/2026 · 10:10",
                "severity": "LOW",
                "priority": "NORMAL",
                "status": "IN_PROGRESS",
                "assigned_to": "STF-03",
                "description": "Motor đẩy pin phản hồi chậm khi mở cửa.",
                "guide_steps": [
                    "Bảo dưỡng thanh ray trượt và tra mỡ silicone.",
                    "Chạy chu trình hiệu chuẩn cửa tủ bằng app kỹ thuật."
                ],
                "verified": True,
                "created_at": "2026-10-18T10:10:00"
            }
        ]

        # 6. PARKING RECORDS (Staff Guard & User Personal Parking shared)
        self.parking_records = [
            {
                "ticket_code": "PRK-901",
                "plate_number": "59-X1 123.45",
                "vehicle_type": "Xe máy điện",
                "hub_id": "hub-01",
                "hub_name": "Hub Ga Metro ĐHQG",
                "slot_id": "P08",
                "checkin_time": "18/10/2026 · 10:00",
                "checkout_time": None,
                "duration_display": "45 phút",
                "parking_fee": 5000,
                "payment_status": "PENDING",
                "guard_id": "STF-02"
            },
            {
                "ticket_code": "PRK-902",
                "plate_number": "59-MD 889.92",
                "vehicle_type": "Xe đạp điện",
                "hub_id": "hub-03",
                "hub_name": "Hub KTX Khu B",
                "slot_id": "P03",
                "checkin_time": "18/10/2026 · 09:15",
                "checkout_time": None,
                "duration_display": "1 giờ 30 phút",
                "parking_fee": 5000,
                "payment_status": "PENDING",
                "guard_id": "STF-01"
            }
        ]

        # 7. INCIDENTS (User reported incidents)
        self.incidents = [
            {
                "id": "INC-2026-001",
                "title": "Chốt khóa phản hồi chậm",
                "category": "Khóa xe",
                "status": "Đang xử lý",
                "date": "18/10/2026 · 09:20",
                "hub_name": "Hub Ga Metro ĐHQG",
                "vehicle_id": "XE-024",
                "description": "Quét mã mở khóa xe XE-024 mất hơn 2 phút chốt mới bật ra.",
                "images": []
            }
        ]

        # 8. OPERATOR SIMULATIONS & RULES
        self.simulation_rules = [
            {"id": "RULE-01", "name": "Cân bằng tải giờ cao điểm sáng", "trigger": "Xe khả dụng < 20% tại Ga Metro", "action": "Điều động 15 xe từ KTX Khu B", "active": True},
            {"id": "RULE-02", "name": "Ngắt sạc chống quá tải trạm", "trigger": "Công suất trạm > 85 kW", "action": "Giảm dòng sạc trụ AC thường xuống 50%", "active": True}
        ]
        self.simulation_history = [
            {
                "run_id": "SIM-20261018-01",
                "name": "Mô phỏng giờ cao điểm sáng thứ 2 (07:00 - 09:00)",
                "created_at": "18/10/2026 · 08:00",
                "duration_minutes": 120,
                "scenario": "Peak Hours",
                "status": "COMPLETED",
                "summary": "Phát hiện thiếu hụt 18 xe tại Hub Ga Metro lúc 07:45. Tự động đề xuất lệnh điều phối từ KTX Khu B."
            }
        ]

        # 9. TELEMETRY EVENTS
        self.telemetry_events = [
            {"id": "TLM-101", "timestamp": "10:14:22", "hub_name": "Hub Ga Metro ĐHQG", "event_type": "RENTAL_START", "message": "Xe XE-024 đã được mở khóa bắt đầu chuyến đi.", "level": "INFO"},
            {"id": "TLM-102", "timestamp": "10:12:05", "hub_name": "Hub KTX Khu B", "event_type": "BATTERY_SWAP", "message": "Người dùng đổi pin B48 thành công tại khay số 2.", "level": "INFO"},
            {"id": "TLM-103", "timestamp": "10:08:41", "hub_name": "Hub Ga Metro ĐHQG", "event_type": "CHARGER_ALERT", "message": "Trụ sạc nhanh S02 quá nhiệt, tự động ngắt tải.", "level": "WARNING"},
            {"id": "TLM-104", "timestamp": "09:55:18", "hub_name": "Hub Đại học Bách khoa", "event_type": "RELOCATION_HANDOVER", "message": "Hoàn tất bàn giao 8 xe đạp điện từ Hub KTX A.", "level": "SUCCESS"}
        ]

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

    def return_vehicle(self, trip_id: str, return_hub_name: str):
        # Clear active ride
        active_ride = self.user["active_services"].get("ride")
        vehicle_id = active_ride["vehicle_id"] if active_ride else "XE-024"
        self.user["active_services"]["ride"] = None

        # Add bike to return hub
        dest_hub = next((h for h in self.hubs if h["name"] == return_hub_name), self.hubs[1])
        dest_hub["available_bikes"] += 1
        dest_hub["bikes"].append({
            "id": vehicle_id,
            "name": "Xe đạp điện",
            "battery_level": 75,
            "status": "Sẵn sàng",
            "hourly_rate": 10000
        })

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
