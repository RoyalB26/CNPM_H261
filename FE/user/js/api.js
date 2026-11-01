/**
 * API Service for End-User Mobile App
 * Connects to python backend (http://127.0.0.1:8000/api) or falls back to local AppState
 */
const API_BASE_URL = "http://127.0.0.1:8000/api";

const ApiService = {
  isBackendAvailable: false,

  async checkBackend() {
    try {
      const res = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
      if (res.ok) {
        this.isBackendAvailable = true;
        console.log("Mock Backend detected & active at " + API_BASE_URL);
        return true;
      }
    } catch (e) {
      this.isBackendAvailable = false;
      console.log("Mock Backend not running at " + API_BASE_URL + ", using local reactive store.");
      return false;
    }
    return false;
  },

  async login(phone, password) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, password })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("Login API error, fallback to local:", e);
      }
    }
    return { success: true, user: AppState.user };
  },

  async getProfile() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/user/profile`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetProfile API error:", e);
      }
    }
    return AppState.user;
  },

  async updateProfile(profileData) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/user/profile`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(profileData)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("UpdateProfile API error:", e);
      }
    }
    return { success: true, ...profileData };
  },

  async getUserVehicles() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/user/vehicles`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetUserVehicles API error:", e);
      }
    }
    return [
      { id: "VEH-01", type: "Xe máy điện", plate_number: "59-X1 123.45", model: "VinFast Klara S", battery_type: "B48" },
      { id: "VEH-02", type: "Xe đạp điện", plate_number: "59-MD 889.92", model: "Pega Cap-A", battery_type: "B48" },
      { id: "VEH-03", type: "Xe máy điện", plate_number: "59-V1 456.78", model: "VinFast Feliz Neo", battery_type: "LFP-72" }
    ];
  },

  async suggestRoute(payload) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/hubs/suggest-route`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("SuggestRoute API error:", e);
      }
    }
    return null;
  },

  async getHubs() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/hubs`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetHubs API error:", e);
      }
    }
    return AppState.hubs;
  },

  async getHubDetail(hubId) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/hubs/${hubId}`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetHubDetail API error:", e);
      }
    }
    return AppState.hubs.find(h => h.id === hubId) || AppState.hubs[0];
  },

  async getBookings() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/bookings`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetBookings API error:", e);
      }
    }
    return AppState.bookings;
  },

  async createBooking(bookingPayload) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/bookings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bookingPayload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("CreateBooking API error:", e);
      }
    }
    return {
      id: `EMH-${Math.floor(1000 + Math.random() * 9000)}`,
      ...bookingPayload,
      status: "Đã xác nhận",
      holdUntil: "15 phút kể từ hiện tại",
      createdAt: "Vừa xong"
    };
  },

  async startRide(bookingId) {
    if (!this.isBackendAvailable) {
      throw new Error("Backend chưa kết nối");
    }

    const res = await fetch(
      `${API_BASE_URL}/bookings/${encodeURIComponent(bookingId)}/start`,
      { method: "POST" }
    );

    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.error || "Không thể bắt đầu chuyến đi");
    }

    return data;
  },

  async cancelBooking(bookingId) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/bookings/${bookingId}/cancel`, {
          method: "POST"
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("CancelBooking API error:", e);
      }
    }
    return { success: true };
  },

  async getActiveServices() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/services/active`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetActiveServices API error:", e);
      }
    }
    return {
      has_active: true,
      ride: AppState.activeRide,
      parking: AppState.activeParking,
      charging: AppState.activeCharging
    };
  },

  async returnVehicle(payload) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/services/return-vehicle`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("ReturnVehicle API error:", e);
      }
    }
    return { success: true, message: "Xe đã được khóa chốt tại Hub thành công!" };
  },

  async getIncidents() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/incidents`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetIncidents API error:", e);
      }
    }
    return AppState.incidents;
  },

  async reportIncident(reportPayload) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/incidents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(reportPayload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("ReportIncident API error:", e);
      }
    }
    return {
      id: `INC-2026-0${Math.floor(100 + Math.random() * 900)}`,
      ...reportPayload,
      createdAt: "Vừa xong",
      status: "Đang xử lý",
      operatorNote: "Đã chuyển yêu cầu đến bộ phận kỹ thuật."
    };
  },

  async getInvoice(type = "rental") {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/invoices/current?type=${type}`);
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetInvoice API error:", e);
      }
    }
    return null;
  },

  async payInvoice(payload) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/invoices/pay`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("PayInvoice API error:", e);
      }
    }
    return { success: true, transaction_id: "TXN-88492019" };
  }
};

// Initialize backend connectivity check
ApiService.checkBackend();
