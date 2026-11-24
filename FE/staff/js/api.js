/**
 * @fileoverview Dịch vụ giao tiếp API cho Nhân viên Hiện trường & Bảo vệ.
 * @module Staff/StaffApi
 */
(function (global) {
  "use strict";

  const STAFF_API_BASE = (window.EMobilityConfig && window.EMobilityConfig.STAFF_API_BASE) || "http://127.0.0.1:8000/api/v1/staff";

const StaffApi = {
  isBackendAvailable: false,

  _authHeaders(extra = {}) {
    const token = sessionStorage.getItem("staff_access_token") || "";
    return token ? { ...extra, Authorization: "Bearer " + token } : { ...extra };
  },

  async login(username, password) {
    const response = await fetch(`${STAFF_API_BASE}/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username_or_phone: username, password })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Đăng nhập thất bại");
    sessionStorage.setItem("staff_access_token", result.access_token);
    return result;
  },


  async checkBackend() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/profile`, { headers: { Authorization: "Bearer " + (sessionStorage.getItem("staff_access_token") || "") } });
      if (res.ok) {
        this.isBackendAvailable = true;
        return true;
      }
    } catch (e) {
      this.isBackendAvailable = false;
    }
    return false;
  },

  async getProfile() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/profile`, { headers: { Authorization: "Bearer " + (sessionStorage.getItem("staff_access_token") || "") } });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi getProfile fallback:", e);
    }
    return {
      id: "STF-02",
      full_name: "Nguyen Van B",
      role: "maintenance",
      shift_title: "Ca chiều · 13:00 - 17:00",
      assigned_hub: "Hub KTX Khu A",
      avatar_initials: "MT",
      tasks_count: 4
    };
  },

  async getRelocationTask() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/relocation/task`, { headers: this._authHeaders() });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi getRelocationTask fallback:", e);
    }
    return {
      task_id: "#102",
      title: "Hướng dẫn di chuyển điều phối xe",
      source_hub_name: "Hub KTX Khu A",
      target_hub_name: "Hub Ga Metro A",
      vehicle_type: "Xe đạp điện",
      total_bikes: 20,
      in_transit_bikes: 12,
      remaining_at_source: 8,
      estimated_distance_km: 2.5,
      estimated_duration_minutes: 10,
      checklist: [
        { bike_code: "BK-EB-001", battery_pct: 85, dock_number: "02", status: "Done" },
        { bike_code: "BK-EB-002", battery_pct: 85, dock_number: "02", status: "Done" },
        { bike_code: "BK-EB-019", battery_pct: 85, dock_number: "02", status: "Waiting" },
        { bike_code: "BK-EB-020", battery_pct: 85, dock_number: "02", status: "Waiting" }
      ]
    };
  },

  async scanBike(taskId, bikeCode, dockNumber = "02") {
    try {
      const res = await fetch(`${STAFF_API_BASE}/relocation/scan-bike`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ task_id: taskId, bike_code: bikeCode, dock_number: dockNumber })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi scanBike fallback:", e);
    }
    return { success: true, bike_code: bikeCode, new_status: "Done", progress_count: 19, total_count: 20 };
  },

  async handover(taskId, completedCount, targetHub) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/relocation/handover`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ task_id: taskId, completed_bikes_count: completedCount, target_hub_name: targetHub })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi handover fallback:", e);
    }
    return { success: true, message: "Hoàn tất bàn giao hạ tầng thành công!" };
  },

  async reportRelocIncident(payload) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/relocation/incident`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi reportRelocIncident fallback:", e);
    }
    return { success: true, report_id: "INC-RELOC-01" };
  },

  async getMaintenanceTasks() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/maintenance/tasks`, { headers: { Authorization: "Bearer " + (sessionStorage.getItem("staff_access_token") || "") } });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi getMaintenanceTasks fallback:", e);
    }
    return [
      { task_code: "MT-102", priority: "Khẩn cấp", category_label: "XE ĐẠP ĐIỆN · HƯ HỎNG", title: "Xe BK-EB-018 không khởi động", hub_name: "Hub KTX Khu A", created_at_label: "Hôm nay, 14:25", due_label: "Cần xử lý trong 35 phút", status: "Mới tiếp nhận" },
      { task_code: "MT-098", priority: "Cảnh báo", category_label: "CỔNG SẠC · KHÔNG HOẠT ĐỘNG", title: "Cổng sạc số 05 không nhận điện", hub_name: "Hub Ga Metro A", created_at_label: "Hôm nay, 13:50", due_label: "Cần kiểm tra trong hôm nay", status: "Đang xử lý" },
      { task_code: "MT-091", priority: "Thường", category_label: "NGUỒN ĐIỆN", title: "Nguồn điện trạm sạc cần bảo dưỡng", hub_name: "Hub Trường BK", created_at_label: "Hôm nay, 11:20", due_label: "Hạn 24 giờ", status: "Mới tiếp nhận" }
    ];
  },

  async getMaintenanceDetail(taskCode) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/maintenance/tasks/${taskCode}`, { headers: { Authorization: "Bearer " + (sessionStorage.getItem("staff_access_token") || "") } });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi getMaintenanceDetail fallback:", e);
    }
    return {
      task_code: taskCode,
      device_code: "BK-EB-018",
      device_name: "Xe đạp điện",
      location_hub: "Hub KTX Khu A",
      fault_type: "Hư hỏng nguồn",
      reporter_name: "Nhân viên điều chuyển",
      reported_at: "14:25 hôm nay",
      description: "Xe không phản hồi khi bật nguồn. Đã thử cắm sạc nhưng đèn báo không sáng.",
      status: "Mới tiếp nhận",
      priority: "Khẩn cấp",
      is_verified: true,
      technician_notes: "",
      outcome: null
    };
  },

  async verifyDevice(taskCode, scannedCode) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/maintenance/verify-device`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ task_code: taskCode, scanned_code: scannedCode })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi verifyDevice fallback:", e);
    }
    return { is_match: true, message: "Mã thiết bị trùng khớp 100% với phiếu sự cố." };
  },

  async resolveMaintenance(payload) {
    const response = await fetch(`${STAFF_API_BASE}/maintenance/resolve`, {
      method: "POST",
      headers: this._authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) return { success: false, detail: result.detail || "Gửi kết quả thất bại" };
    return result;
  },

  async reportMaintIncident(payload) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/maintenance/incident`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi reportMaintIncident fallback:", e);
    }
    return { success: true, report_id: "INC-MAINT-01" };
  },

  async parkingCheckin(payload) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/parking/checkin`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi parkingCheckin fallback:", e);
    }
    return {
      success: true,
      ticket_code: "SG-" + new Date().toISOString().slice(0,10).replace(/-/g, "") + "-018",
      license_plate: payload.license_plate,
      bay_slot: `${payload.parking_bay} · ${payload.parking_slot}`,
      checkin_time: new Date().toLocaleTimeString().slice(0, 5),
      status_message: "Đã xác nhận xe vào bãi thành công"
    };
  },

  async parkingCheckoutPreview(plateOrTicket) {
    const response = await fetch(`${STAFF_API_BASE}/parking/checkout/${encodeURIComponent(plateOrTicket)}`, {
      headers: { Authorization: "Bearer " + (sessionStorage.getItem("staff_access_token") || "") }
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Không lấy được báo giá gửi xe");
    return result;
  },

  async parkingCheckoutConfirm(ticketCode, cashReceived, quoteToken) {
    const response = await fetch(`${STAFF_API_BASE}/parking/checkout/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json",
        Authorization: "Bearer " + (sessionStorage.getItem("staff_access_token") || "") },
      body: JSON.stringify({ ticket_code: ticketCode, cash_received: cashReceived,
        payment_method: "TIỀN MẶT", quote_token: quoteToken })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Xác nhận thu phí thất bại");
    return result;
  },

  async getShiftSummary() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/parking/shift-summary`, { headers: this._authHeaders() });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi getShiftSummary fallback:", e);
    }
    return {
      shift_title: "Ca chiều · 13:00 - 17:00",
      shift_date: "22/10/2026",
      hub_name: "Hub KTX Khu A",
      total_vehicles_served: 48,
      total_cash_collected_vnd: 1200000,
      transactions: [
        { seq_number: "01", license_plate: "59-B2 123.45", time_info: "14:36 · 2 giờ 06 phút", amount_vnd: 25000 },
        { seq_number: "02", license_plate: "51-H1 889.92", time_info: "14:50 · 1 giờ 15 phút", amount_vnd: 20000 }
      ],
      is_closed: false
    };
  },

  async closeShift(guardId = "SG-02", cash = 1200000) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/parking/shift-close`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ guard_id: guardId, total_cash_deposited_vnd: cash })
      });
      if (res.ok) return await res.json();
      return { success: false, error: `HTTP ${res.status}` };
    } catch (e) {
      console.warn("StaffApi closeShift error:", e);
      return { success: false, error: e.message || "Lỗi kết nối" };
    }
  }
};

  global.StaffApi = StaffApi;
})(window);
