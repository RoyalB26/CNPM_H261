/**
 * API Service for End-User Mobile App
 * Connects to python backend (http://127.0.0.1:8000/api) or falls back to local AppState
 */
const API_BASE_URL = "http://127.0.0.1:8000/api";

const ApiService = {
  isBackendAvailable: false,

  _authHeaders(extra = {}) {
    const token = sessionStorage.getItem("user_access_token") || "";
    return token ? { ...extra, Authorization: "Bearer " + token } : { ...extra };
  },

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
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, password })
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(result.detail || result.error || "Sai tài khoản hoặc mật khẩu");
      }
      if (result.token) {
        sessionStorage.setItem("user_access_token", result.token);
      }
      return { success: true, ...result };
    }
    return { success: true, user: AppState.user };
  },

  async register(payload) {
    if (this.isBackendAvailable) {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(result.detail || result.error || "Đăng ký thất bại");
      }
      return result;
    }
    return { success: true };
  },

  async getProfile() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/user/profile`, { headers: this._authHeaders() });
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
          headers: this._authHeaders({ "Content-Type": "application/json" }),
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
        const res = await fetch(`${API_BASE_URL}/user/vehicles`, { headers: this._authHeaders() });
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
      const res = await fetch(`${API_BASE_URL}/hubs/suggest-route`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || `HTTP ${res.status}`);
      }
      return data;
    }
    return null;
  },

  async getHubs() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/hubs`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          return Array.isArray(data) ? data : (data && (data.items || data.hubs)) || [];
        }
      } catch (e) {
        console.warn("GetHubs API error:", e);
      }
    }
    return AppState.hubs;
  },

  async getHubDetail(hubId) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/hubs/${hubId}`, { headers: this._authHeaders() });
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
        const res = await fetch(`${API_BASE_URL}/bookings`, { headers: this._authHeaders() });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("GetBookings API error:", e);
      }
    }
    return AppState.bookings;
  },

  async createBooking(bookingPayload) {
    if (this.isBackendAvailable) {
      const res = await fetch(`${API_BASE_URL}/bookings`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(bookingPayload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.error || data.message || `HTTP ${res.status}`);
      }
      return data;
    }
    throw new Error("Chưa kết nối Backend, chưa thể xác nhận đặt chỗ.");
  },

  async startRide(bookingId) {
    if (!this.isBackendAvailable) {
      throw new Error("Backend chưa kết nối");
    }

    const res = await fetch(
      `${API_BASE_URL}/bookings/${encodeURIComponent(bookingId)}/start`,
      { method: "POST", headers: this._authHeaders() }
    );

    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.error || data.detail || "Không thể bắt đầu chuyến đi");
    }

    return data;
  },

  async cancelBooking(bookingId) {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/bookings/${bookingId}/cancel`, {
          method: "POST",
          headers: this._authHeaders()
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("CancelBooking API error:", e);
      }
    }
    return { success: true };
  },

  async getActiveServices() {
    // Trạng thái gửi xe phải do BE xác nhận, không dùng phiên cũ thay kết quả lỗi.
    if (!this.isBackendAvailable) {
      throw new Error("Chưa kết nối Backend. Vui lòng kiểm tra kết nối và thử lại.");
    }
    const res = await fetch(`${API_BASE_URL}/services/active`, { headers: this._authHeaders() });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new Error(data?.detail || data?.error || `Không tải được trạng thái dịch vụ (HTTP ${res.status}).`);
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("Backend trả trạng thái dịch vụ không hợp lệ.");
    }
    return data;
  },

  async returnVehicle(payload) {
    if (!this.isBackendAvailable) {
      throw new Error("Chưa kết nối Backend, chưa thể xác nhận trả xe.");
    }
    const res = await fetch(`${API_BASE_URL}/services/return-vehicle`, {
      method: "POST",
      headers: this._authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => null);
    if (!res.ok || data?.success !== true) {
      throw new Error(data?.error || data?.detail || "Backend chưa xác nhận trả xe thành công.");
    }
    return data;
  },

  async getIncidents() {
    if (this.isBackendAvailable) {
      try {
        const res = await fetch(`${API_BASE_URL}/incidents`, { headers: this._authHeaders() });
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
          headers: this._authHeaders({ "Content-Type": "application/json" }),
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

  async getInvoice(type = "rental", selectors = {}) {
    if (!this.isBackendAvailable) {
      throw new Error("Chưa kết nối Backend, chưa tải được hóa đơn.");
    }
    const params = new URLSearchParams({ type });
    Object.entries(selectors).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") params.set(key, value);
    });
    const res = await fetch(`${API_BASE_URL}/invoices/current?${params}`, { headers: this._authHeaders() });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new Error(data?.error || data?.detail || `Không tải được hóa đơn (HTTP ${res.status}).`);
    }
    return data;
  },

  async payInvoice(payload) {
    const response = await fetch(`${API_BASE_URL}/invoices/pay`, {
      method: "POST", headers: { "Content-Type": "application/json",
        Authorization: "Bearer " + (sessionStorage.getItem("user_access_token") || "") },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || result.detail || "Không tạo được phiên thanh toán");
    return result;
  },

  async completeSwap(bookingId) {
    const res = await fetch(`${API_BASE_URL}/bookings/${encodeURIComponent(bookingId)}/swap`, {
      method: "POST",
      headers: this._authHeaders()
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
    return data;
  },

  async startCharging(bookingId) {
    const res = await fetch(`${API_BASE_URL}/bookings/${encodeURIComponent(bookingId)}/charging/start`, {
      method: "POST",
      headers: this._authHeaders()
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
    return data;
  },

  async stopCharging(payload) {
    const res = await fetch(`${API_BASE_URL}/services/charging/stop`, {
      method: "POST",
      headers: this._authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
    return data;
  },

  async getChargingSchedules() {
    const res = await fetch(`${API_BASE_URL}/v1/user/charging/schedules`, {
      headers: this._authHeaders()
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return (data && data.items) || [];
  },

  async createChargingSchedule(payload) {
    const res = await fetch(`${API_BASE_URL}/v1/user/charging/schedules`, {
      method: "POST",
      headers: this._authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  },

  async actionChargingSchedule(scheduleId, action) {
    const res = await fetch(`${API_BASE_URL}/v1/user/charging/schedules/${encodeURIComponent(scheduleId)}/${encodeURIComponent(action)}`, {
      method: "POST",
      headers: this._authHeaders()
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  },

  async uploadIncidentPhoto(incidentId, file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE_URL}/v1/user/incidents/${encodeURIComponent(incidentId)}/photos`, {
      method: "POST",
      headers: this._authHeaders(),
      body: formData
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  },

  async fetchAttachmentBlobUrl(photoUrl) {
    const apiHost = (window.EMobilityConfig && window.EMobilityConfig.API_HOST) || "http://127.0.0.1:8000";
    const url = photoUrl.startsWith("http") ? photoUrl : `${apiHost}${photoUrl}`;
    const res = await fetch(url, { headers: this._authHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  async getNotifications() {
    const res = await fetch(`${API_BASE_URL}/v1/user/notifications`, {
      headers: this._authHeaders()
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return (data && data.items) || [];
  }

};

// Initialize backend connectivity check
ApiService.checkBackend();
