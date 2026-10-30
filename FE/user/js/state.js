/**
 * State Management & Reactive Data Store for End-User Mobile App
 */
const AppState = {
  // Current user info
  user: {
    id: "USR-001",
    fullName: "Nguyễn Văn A",
    email: "abc123@hcmut.edu.vn",
    phone: "0123456789",
    paymentMethod: "Ví điện tử"
  },

  // Active bookings list
  bookings: [
    {
      id: "EMH-1023",
      planType: "rental",
      hubName: "Hub Ga Metro ĐHQG",
      destinationHubName: "Hub Đại học Bách khoa",
      resourceName: "XE-024 · Xe đạp điện",
      services: [{ service_type: "rental", detail: "Xe đạp điện XE-024 · Pin 85%", price_est: 10000 }],
      status: "Đã xác nhận",
      holdUntil: "08:10",
      createdAt: "18/10/2026 · từ 08:00",
      totalPrice: 10000
    },
    {
      id: "EMH-1024",
      planType: "personal",
      hubName: "Hub Ga Metro ĐHQG",
      personalPlate: "59-X1 123.45",
      services: [
        { service_type: "parking", detail: "Chỗ đỗ · 10:00 – 12:00", price_est: 5000 },
        { service_type: "charging", detail: "Sạc S03 · 10:00 – 11:00", price_est: 15000 }
      ],
      status: "Đã xác nhận",
      holdUntil: "10:15",
      createdAt: "18/10/2026 · từ 10:00",
      totalPrice: 20000
    }
  ],

  // History bookings
  historyBookings: [
    {
      id: "EMH-0988",
      planType: "rental",
      hubName: "Hub KTX Khu B",
      status: "Đã hoàn thành",
      createdAt: "15/10/2026",
      totalPrice: 15000
    },
    {
      id: "EMH-0950",
      planType: "personal",
      hubName: "Hub Ga Metro ĐHQG",
      status: "Đã hoàn thành",
      createdAt: "10/10/2026",
      totalPrice: 5000
    }
  ],

  // Active in-progress service
  activeRide: {
    id: "ACT-01",
    vehicleId: "XE-024",
    batteryLevel: 78,
    originHub: "Hub Ga Metro ĐHQG",
    destHub: "ĐH Bách Khoa",
    elapsedMinutes: 13,
    status: "Đang sử dụng",
    logs: [
      { label: "Đặt xe", time: "08:00" },
      { label: "Nhận / bắt đầu", time: "08:05" },
      { label: "Cập nhật gần nhất", time: "08:18:02" }
    ]
  },

  activeParking: {
    id: "PARK-01",
    plate: "59-X1 123.45",
    hubName: "Hub Ga Metro ĐHQG",
    slot: "P-12",
    checkin: "09:15",
    elapsedMinutes: 45
  },

  activeCharging: {
    id: "CHG-01",
    plate: "59-X1 123.45",
    hubName: "Hub Ga Metro ĐHQG",
    port: "S03",
    batteryPercent: 65,
    powerConsumed: 2.4,
    elapsedMinutes: 25
  },

  // Incident reports
  incidents: [
    {
      id: "INC-2026-089",
      resourceType: "Phương tiện",
      resourceCode: "XE-024",
      hubName: "Hub Ga Metro ĐHQG",
      incidentType: "Không mở được khóa",
      description: "Xe không mở được khóa sau khi xác nhận nhận xe.",
      createdAt: "10:35 · 18/10/2026",
      status: "Đang xử lý",
      operatorNote: "Đã tiếp nhận yêu cầu, kỹ thuật viên đang đến kiểm tra thiết bị."
    },
    {
      id: "INC-2026-042",
      resourceType: "Cổng sạc",
      resourceCode: "S02",
      hubName: "Hub KTX Khu B",
      incidentType: "Không vào điện",
      description: "Cắm cáp sạc nhưng đèn báo không sáng.",
      createdAt: "14:20 · 12/10/2026",
      status: "Đã giải quyết",
      operatorNote: "Đã reset cầu dao trạm sạc. Hoạt động bình thường."
    }
  ],

  // Current Booking Wizard State
  bookingDraft: {
    planType: "rental", // "rental" | "personal"
    hubId: "hub-01",
    hubName: "Hub Ga Metro ĐHQG",
    destinationHub: "Hub Đại học Bách khoa",
    selectedBike: "XE-024",
    bikeBattery: 85,
    parkingSelected: true,
    parkingSlot: "P-04",
    parkingTime: "10:00 – 12:00",
    chargingSelected: true,
    chargingPort: "S03",
    chargingTime: "10:00 – 11:00",
    swapSelected: false,
    swapBatteryType: "Pin 48V-20Ah",
    personalPlate: "59-X1 123.45"
  },

  // Current invoice being settled
  currentInvoice: {
    id: "INV-2026-901",
    type: "rental",
    title: "Hóa đơn thuê xe điện",
    amount: 15000,
    details: "Thời gian sử dụng: 45 phút",
    channel: "online" // "online" or "cash_guard"
  },

  // Mobility Hubs Network in DHQG
  hubs: [
    {
      id: "hub-01",
      name: "Hub Ga Metro ĐHQG",
      address: "Khu đô thị ĐHQG - HCM",
      lat: 10.8753,
      lng: 106.8005,
      available_bikes: 5,
      available_parking: 8,
      available_chargers: 2,
      available_batteries: 6
    },
    {
      id: "hub-02",
      name: "Hub Đại học Bách khoa",
      address: "Đường D1, Khu ĐHQG - Dĩ An",
      lat: 10.8805,
      lng: 106.8055,
      available_bikes: 4,
      available_parking: 12,
      available_chargers: 4,
      available_batteries: 8
    },
    {
      id: "hub-03",
      name: "Hub KTX Khu B",
      address: "Ký túc xá Khu B ĐHQG",
      lat: 10.8835,
      lng: 106.7820,
      available_bikes: 6,
      available_parking: 15,
      available_chargers: 3,
      available_batteries: 10
    },
    {
      id: "hub-04",
      name: "Hub Đại học Quốc Tế",
      address: "Đường số 6, Khu ĐHQG - Dĩ An",
      lat: 10.8778,
      lng: 106.8018,
      available_bikes: 3,
      available_parking: 6,
      available_chargers: 1,
      available_batteries: 4
    }
  ],

  // Active search filter
  searchCategory: "all" // "all" | "hub" | "school" | "dorm" | "amenity"
};
