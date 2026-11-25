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

  // Active bookings list (populated from Backend)
  bookings: [],

  // History bookings (populated from Backend)
  historyBookings: [],

  // Active in-progress service (populated from Backend)
  activeRide: null,

  activeParking: null,

  activeCharging: null,

  activeServices: {
    has_active: false,
    ride: null,
    parking: null,
    charging: null
  },

  // Incident reports (populated from Backend)
  incidents: [],

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
