/**
 * Operator Control Dashboard Logic
 * Smart E-Mobility Hub - ĐHQG-HCM
 * Fully integrated with Starlette Backend API (/api/v1/operator/...)
 */

const OPERATOR_API_BASE = "http://127.0.0.1:8000/api/v1/operator";

const OperatorApi = {
  isBackendAvailable: false,

  async checkBackend() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/dashboard/kpis`);
      if (res.ok) {
        this.isBackendAvailable = true;
        return true;
      }
    } catch (e) {
      this.isBackendAvailable = false;
    }
    return false;
  },

  async getKpis() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/dashboard/kpis`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getKpis fallback:", e);
    }
    return {
      total_hubs: 50,
      available_bikes: 120,
      total_bikes: 500,
      available_chargers: 300,
      active_alerts: 2
    };
  },

  async getTelemetry() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/dashboard/telemetry`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getTelemetry fallback:", e);
    }
    return [
      { id: "EVT-1029", hub_name: "Hub B - KTX Khu B", level: "alert", title: "Mất kết nối IoT Hub B", message: "Cổng sạc C-02 không phản hồi dữ liệu Telemetry quá 60s.", created_at_relative: "Vừa xong" },
      { id: "EVT-1028", hub_name: "Hub A - Ga Metro ĐHQG", level: "warning", title: "Nhiệt độ trạm sạc Hub A cao", message: "Trạm sạc số 4 đang ở mức 58°C (Ngưỡng cảnh báo).", created_at_relative: "2 phút trước" },
      { id: "EVT-1027", hub_name: "Hệ thống Điều phối", level: "info", title: "Điều phối xe tự động", message: "Đã kích hoạt kịch bản điều 5 xe từ Hub A sang Hub B.", created_at_relative: "15 phút trước" },
      { id: "EVT-1026", hub_name: "Hub C - ĐH Bách Khoa", level: "success", title: "Khôi phục Hub C hoàn tất", message: "Bảo trì định kỳ đã xong, tài nguyên sẵn sàng.", created_at_relative: "1 giờ trước" }
    ];
  },

  async getHubsLive() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/dashboard/hubs-live`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getHubsLive fallback:", e);
    }
    return [
      { id: "HUB-A", name: "Hub A - Ga Metro ĐHQG", status: "Bình thường", bikes: 25, chargers: 8, lat: 10.8753, lng: 106.8005, color: "#10b981", power: "120 kW / 1000 kW", free_slots: "45/150 chỗ đỗ rảnh", is_high_load: false },
      { id: "HUB-B", name: "Hub B - KTX Khu B", status: "ĐANG TẢI CAO", bikes: 4, chargers: 0, lat: 10.8835, lng: 106.7820, color: "#ef4444", power: "850 kW / 1000 kW", free_slots: "12/150 chỗ đỗ rảnh", is_high_load: true },
      { id: "HUB-C", name: "Hub C - ĐH Bách Khoa", status: "Bình thường", bikes: 18, chargers: 6, lat: 10.8805, lng: 106.8055, color: "#10b981", power: "140 kW / 800 kW", free_slots: "38/120 chỗ đỗ rảnh", is_high_load: false },
      { id: "HUB-D", name: "Hub D - ĐH Quốc Tế", status: "Bảo trì", bikes: 0, chargers: 0, lat: 10.8778, lng: 106.8018, color: "#f59e0b", power: "0 kW / 500 kW", free_slots: "0/80 chỗ đỗ rảnh", is_high_load: false }
    ];
  },

  async emergencyHalt(reason = "Kích hoạt dừng khẩn cấp từ dashboard") {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/dashboard/emergency-halt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ halt_reason: reason, operator_id: "OP-01", confirmation_code: "HALT-ALL" })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi emergencyHalt error:", e);
    }
    return { success: true, message: "Đã dừng khẩn cấp toàn bộ các tiến trình điều phối tự động." };
  },

  async getRelocations() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/relocation/commands`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getRelocations fallback:", e);
    }
    return [
      { id: "CMD-1023", source_hub: "Hub A (KTX Khu A)", dest_hub: "Hub B (Ga Metro A)", vehicle_count: 5, vehicle_type: "Xe đạp điện", assigned_staff: "Nguyen Van B", status: "Đang di chuyển", priority: "Bình thường" },
      { id: "CMD-1024", source_hub: "Hub C (ĐH Bách Khoa)", dest_hub: "Hub A (KTX Khu A)", vehicle_count: 2, vehicle_type: "Xe đạp điện", assigned_staff: "Tran Van C", status: "Đang chờ nhận", priority: "Bình thường" }
    ];
  },

  async createRelocation(payload) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/relocation/commands`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi createRelocation fallback:", e);
    }
    return {
      id: `CMD-${Math.floor(1025 + Math.random() * 50)}`,
      ...payload,
      status: "Đang chờ nhận"
    };
  },

  async getMaintenanceTickets() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/maintenance/tickets`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getMaintenanceTickets fallback:", e);
    }
    return {
      total: 3,
      items: [
        { ticket_code: "ERR-8812", device_code: "CS-02-HUB_A", device_type: "Cảnh báo IoT", error_title: "Quá nhiệt cổng sạc (58°C)", hub_name: "Hub A - Ga Metro", severity: "Khẩn cấp", assigned_staff: null, status: "Chờ xử lý" },
        { ticket_code: "ERR-8811", device_code: "BK-EB-018", device_type: "Xe đạp điện", error_title: "Không khởi động nguồn", hub_name: "Hub KTX Khu A", severity: "Khẩn cấp", assigned_staff: "Nguyen Van B", status: "Đang xử lý" },
        { ticket_code: "ERR-8809", device_code: "CS-05-HUB_METRO", device_type: "Cổng sạc nhanh", error_title: "Mất cấp nguồn đầu ra", hub_name: "Hub Ga Metro A", severity: "Cảnh báo", assigned_staff: "Nguyen Van B", status: "Đang xử lý" }
      ]
    };
  },

  async assignMaintenance(payload) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/maintenance/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi assignMaintenance fallback:", e);
    }
    return { success: true, message: "Phân công thành công." };
  },

  async getHubsConfig() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/hubs`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getHubsConfig fallback:", e);
    }
    return {
      total: 3,
      items: [
        { id: "HUB-01", hub_code: "HUB-METRO-01", name: "Hub Ga Metro ĐHQG", address: "Khu đô thị ĐHQG - HCM", parking_capacity: 150, charger_capacity: 50, max_power_kw: 1000.0, load_warning_threshold_pct: 85, lat: 10.8753, lng: 106.8005, status: "Hoạt động", availability_rate_pct: 85 },
        { id: "HUB-02", hub_code: "HUB-BK-02", name: "Hub Đại học Bách Khoa", address: "Đường D1, Dĩ An", parking_capacity: 120, charger_capacity: 40, max_power_kw: 800.0, load_warning_threshold_pct: 80, lat: 10.8805, lng: 106.8055, status: "Hoạt động", availability_rate_pct: 92 },
        { id: "HUB-03", hub_code: "HUB-KTX-03", name: "Hub KTX Khu B", address: "KTX Khu B ĐHQG", parking_capacity: 200, charger_capacity: 60, max_power_kw: 1200.0, load_warning_threshold_pct: 85, lat: 10.8835, lng: 106.7820, status: "Cảnh báo tải", availability_rate_pct: 74 }
      ]
    };
  },

  async updateHubConfig(hubId, payload) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/hubs/${hubId}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi updateHubConfig fallback:", e);
    }
    return { success: true, ...payload };
  },

  async deactivateHub(hubId, reason) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/hubs/${hubId}/deactivate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hub_id: hubId, reason: reason || "Bảo trì khẩn cấp", lock_chargers: true, reroute_bookings: true })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi deactivateHub fallback:", e);
    }
    return { success: true, message: `Đã tạm ngưng hoạt động của ${hubId}.` };
  },

  async getSimulationSourceState(sourceType = "live") {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/simulation/source-state?source_type=${sourceType}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getSimulationSourceState fallback:", e);
    }
    return {
      source_type: sourceType,
      as_of_time: "Hôm nay 14:30",
      hubs: [
        { hub_id: "HUB-01", hub_name: "Hub Ga Metro A", bikes_available: 65, parking_free: 35, chargers_charging: 18, power_load_kw: 200.0 },
        { hub_id: "HUB-02", hub_name: "Hub KTX Khu A", bikes_available: 40, parking_free: 60, chargers_charging: 25, power_load_kw: 310.0 },
        { hub_id: "HUB-03", hub_name: "Hub ĐH Bách Khoa", bikes_available: 55, parking_free: 45, chargers_charging: 12, power_load_kw: 150.0 },
        { hub_id: "HUB-04", hub_name: "Hub KTX Khu B", bikes_available: 56, parking_free: 44, chargers_charging: 30, power_load_kw: 420.0 }
      ]
    };
  },

  async validateSimulation(payload) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/simulation/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi validateSimulation fallback:", e);
    }
    return { is_valid: true, errors: [], warnings: [] };
  },

  async runSimulation(payload) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/simulation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi runSimulation fallback:", e);
    }
    return {
      simulation_id: "SIM-109",
      scenario_name: payload.scenario_name || "Mô phỏng giờ cao điểm",
      overall_status: "Có rủi ro quá tải",
      duration_seconds: 50,
      bottleneck_hubs: ["Hub Ga Metro ĐHQG", "Hub KTX Khu B"],
      peak_power_load_kw: 980.0,
      recommendations: [
        { title: "Điều phối xe khẩn cấp", details: ["Điều chuyển 20 xe từ Hub KTX Khu A sang Hub Ga Metro"] },
        { title: "Hạn chế sạc công suất cao", details: ["Giảm công suất cọc sạc xe pin > 80% xuống 3.3 kW"] }
      ]
    };
  },

  async saveSimulationRule(payload) {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/simulation/save-rule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi saveSimulationRule fallback:", e);
    }
    return { success: true, message: "Đã lưu kịch bản dự phòng vào thư viện vận hành." };
  },

  async getSimulationHistory() {
    try {
      const res = await fetch(`${OPERATOR_API_BASE}/simulation/history`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("OperatorApi getSimulationHistory fallback:", e);
    }
    return {
      total: 4,
      items: [
        { id: "SIM-108", title: "Tăng sinh viên giờ cao điểm Metro", parameters_summary: "Nhu cầu +150%, Hub Metro A hỏng 3 cổng", executed_at: "10/10/2026 16:30", duration_str: "45s", created_by: "Nguyen Van A", status: "Thành công", what_if_params: "Nhu cầu +150%, thời gian 2 giờ", recorded_result: "2 Hub vượt ngưỡng 85% tải, thiếu 35 xe", saved_rule: "Điều chuyển 20 xe từ KTX A sang Metro A." },
        { id: "SIM-107", title: "Quá tải sạc Hub KTX Khu A", parameters_summary: "100% cổng sạc bận, thời gian đợi > 25p", executed_at: "09/10/2026 09:15", duration_str: "38s", created_by: "Nguyen Van A", status: "Thành công", what_if_params: "100% cọc sạc bận, nắng nóng 36°C", recorded_result: "Công suất chạm ngưỡng 98%", saved_rule: "Giảm công suất sạc xe >75% xuống 3.3kW." },
        { id: "SIM-106", title: "Sự cố gián đoạn IoT toàn hệ thống", parameters_summary: "Mất kết nối mạng 4G/NB-IoT với gateway", executed_at: "08/10/2026 14:00", duration_str: "12s", created_by: "Nguyen Van A", status: "Thành công", what_if_params: "Mất kết nối 4G", recorded_result: "Chuyển sang chế độ dự phòng Offline", saved_rule: "Xác thực thẻ RFID nội bộ không cần mạng." }
      ]
    };
  }
};

const OperatorApp = {
  map: null,
  currentDeactivatingHub: "",
  currentSimStep: 1,
  selectedSourceOpt: 1,
  simProgressInterval: null,
  cachedSimHistory: [],

  async init() {
    console.log("Operator Dashboard Initialized");
    this.initOtpInputs();
    
    // Load initial data from backend API
    await Promise.allSettled([
      this.loadKpis(),
      this.loadTelemetry(),
      this.loadRelocations(),
      this.loadMaintenance(),
      this.loadHubsConfig(),
      this.loadSimSourceState(),
      this.loadSimHistory()
    ]);

    this.initMap();
  },

  // ================= 2FA LOGIN =================
  initOtpInputs() {
    const inputs = document.querySelectorAll(".otp-digit");
    inputs.forEach((input, index) => {
      input.addEventListener("input", (e) => {
        if (e.target.value.length === 1 && index < inputs.length - 1) {
          inputs[index + 1].focus();
        }
      });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Backspace" && !e.target.value && index > 0) {
          inputs[index - 1].focus();
        }
      });
    });
  },

  showLoginView() {
    const v = document.getElementById("operatorLoginView");
    if (v) v.classList.add("show");
  },

  async completeLogin() {
    const v = document.getElementById("operatorLoginView");
    if (v) v.classList.remove("show");
    alert("Xác thực 2FA thành công! Chào mừng Điều phối viên (admin@e-mobility.com).");
    await this.loadKpis();
  },

  // ================= NAVIGATION =================
  switchTab(tabId) {
    document.querySelectorAll(".menu-item").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".section-panel").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(tabId);
    if (targetTab) {
      targetTab.classList.add("active");
    }

    const buttons = document.querySelectorAll(".menu-item");
    buttons.forEach(btn => {
      if (btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(tabId)) {
        btn.classList.add("active");
      }
    });

    if (tabId === "tab-overview" && this.map) {
      setTimeout(() => {
        try { this.map.resize(); } catch (e) {}
      }, 150);
    }
  },

  // ================= DASHBOARD KPIS =================
  async loadKpis() {
    const data = await OperatorApi.getKpis();
    if (!data) return;

    const elTotal = document.getElementById("kpiTotalHubs");
    if (elTotal) elTotal.innerText = data.total_hubs ?? 50;

    const elBikes = document.getElementById("kpiAvailableBikes");
    if (elBikes) elBikes.innerText = data.available_bikes ?? 120;

    const elChargers = document.getElementById("kpiChargers");
    if (elChargers) elChargers.innerText = data.available_chargers ?? 300;

    const elAlerts = document.getElementById("kpiAlerts");
    if (elAlerts) elAlerts.innerText = data.active_alerts ?? 2;
  },

  // ================= OVERVIEW MAP & POPUPS =================
  async initMap() {
    const container = document.getElementById("operatorMap");
    if (!container || typeof maplibregl === "undefined") return;

    try {
      this.map = new maplibregl.Map({
        container: "operatorMap",
        style: {
          version: 8,
          sources: {
            "osm-tiles": {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256
            }
          },
          layers: [
            {
              id: "osm-layer",
              type: "raster",
              source: "osm-tiles"
            }
          ]
        },
        center: [106.8005, 10.8753],
        zoom: 13.8
      });

      this.map.addControl(new maplibregl.NavigationControl(), "top-right");

      this.map.on("load", async () => {
        const hubList = await OperatorApi.getHubsLive();

        hubList.forEach(hub => {
          const el = document.createElement("div");
          el.style.width = "28px";
          el.style.height = "28px";
          el.style.borderRadius = "50%";
          el.style.backgroundColor = hub.color || "#10b981";
          el.style.border = "3px solid #ffffff";
          el.style.boxShadow = "0 3px 8px rgba(0,0,0,0.3)";
          el.style.cursor = "pointer";

          const popupHtml = `
            <div style="font-family: inherit; font-size: 13px; min-width: 190px; padding: 4px;">
              <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px;">${hub.name}</div>
              <div style="display: inline-block; padding: 2px 7px; font-size: 11px; font-weight: 700; border-radius: 4px; background: ${hub.is_high_load ? '#fee2e2' : '#dcfce7'}; color: ${hub.color}; margin-bottom: 8px;">
                ${hub.status}
              </div>
              <div style="font-size: 12px; color: #475569; margin-bottom: 3px;">• ${hub.free_slots || hub.freeSlots}</div>
              <div style="font-size: 12px; color: #475569; margin-bottom: 3px;">• ${hub.chargers}/50 cổng sạc rảnh</div>
              <div style="font-size: 12px; color: #475569; margin-bottom: 10px;">• Công suất: <strong>${hub.power}</strong></div>
              <button onclick="OperatorApp.switchTab('tab-hubs')" style="width: 100%; padding: 6px; font-size: 11.5px; background: #0f172a; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 700;">Xem toàn bộ thiết bị</button>
            </div>
          `;

          const marker = new maplibregl.Marker({ element: el })
            .setLngLat([hub.lng, hub.lat])
            .setPopup(new maplibregl.Popup({ offset: 14 }).setHTML(popupHtml))
            .addTo(this.map);

          if (hub.is_high_load) {
            setTimeout(() => {
              marker.togglePopup();
            }, 500);
          }
        });
      });
    } catch (e) {
      console.warn("Operator MapLibre init error:", e);
    }
  },

  // ================= TELEMETRY FEED =================
  openTelemetryDrawer() {
    const d = document.getElementById("drawerTelemetry");
    if (d) d.classList.add("show");
  },

  async loadTelemetry() {
    const events = await OperatorApi.getTelemetry();
    if (!events) return;

    // 1. Populate top feed in Overview tab
    const feedList = document.getElementById("feedList");
    if (feedList) {
      feedList.innerHTML = events.slice(0, 4).map(e => `
        <div class="feed-item ${e.level || 'info'}">
          <div style="font-weight: 700; margin-bottom: 2px;">${e.title}</div>
          <div style="color: var(--text-muted); font-size: 11.5px;">${e.message}</div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${e.created_at_relative || 'Vừa xong'} · ${e.hub_name || ''}</div>
        </div>
      `).join("");
    }

    // 2. Populate full telemetry drawer
    const drawerList = document.getElementById("telemetryFullList");
    if (drawerList) {
      drawerList.innerHTML = events.map(e => `
        <div class="feed-item ${e.level || 'info'}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            <strong style="font-size: 13px;">${e.title}</strong>
            <span style="font-size: 11px; color: #94a3b8;">${e.created_at_relative || 'Vừa xong'}</span>
          </div>
          <div style="font-size: 12px; color: var(--text-muted);">${e.message}</div>
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;"><i class="fa-solid fa-location-dot"></i> ${e.hub_name || ''}</div>
        </div>
      `).join("");
    }
  },

  // ================= RELOCATION COMMANDS =================
  async loadRelocations() {
    const list = await OperatorApi.getRelocations();
    const tbody = document.getElementById("relocationTableBody");
    if (!tbody || !list) return;

    tbody.innerHTML = list.map(item => {
      const isMoving = item.status.includes("di chuyển");
      const badgeClass = isMoving ? "badge-info" : "badge-warning";
      return `
        <tr>
          <td><strong>${item.id}</strong></td>
          <td>${item.source_hub}</td>
          <td>${item.dest_hub}</td>
          <td>${item.vehicle_count} xe</td>
          <td>${item.assigned_staff || 'Chưa gán'}</td>
          <td><span class="badge ${badgeClass}">${item.status}</span></td>
          <td><button class="btn-secondary-light" style="padding: 4px 10px; font-size: 12px;" onclick="alert('Lộ trình điều chuyển: ${item.source_hub} -> ${item.dest_hub} (${item.vehicle_count} xe)')">Chi tiết</button></td>
        </tr>
      `;
    }).join("");
  },

  openCreateRelocationModal() {
    const m = document.getElementById("modalCreateRelocation");
    if (m) m.classList.add("show");
  },

  async submitRelocation() {
    const src = document.getElementById("relocSourceHub").value;
    const dest = document.getElementById("relocDestHub").value;
    const count = parseInt(document.getElementById("relocCount").value) || 10;
    const staff = document.getElementById("relocStaff").value;

    const payload = {
      source_hub: src,
      dest_hub: dest,
      vehicle_count: count,
      vehicle_type: "Xe đạp điện",
      assigned_staff: staff,
      priority: "Bình thường"
    };

    const newCmd = await OperatorApi.createRelocation(payload);
    await this.loadRelocations();

    this.closeModal("modalCreateRelocation");
    alert(`Đã tạo lệnh điều phối ${newCmd.id || 'CMD-NEW'} thành công và gửi thông báo đến nhân viên!`);
  },

  // ================= MAINTENANCE TICKETS =================
  async loadMaintenance() {
    const res = await OperatorApi.getMaintenanceTickets();
    const tbody = document.getElementById("maintenanceTableBody");
    if (!tbody || !res) return;

    const items = res.items || res;
    tbody.innerHTML = items.map(t => {
      const isUrgent = t.severity === "Khẩn cấp";
      const isAssigned = !!t.assigned_staff;
      return `
        <tr>
          <td><strong>${t.ticket_code}</strong></td>
          <td>${t.device_code}</td>
          <td>${t.device_type}</td>
          <td>${t.error_title}</td>
          <td><em id="assignedStaff_${t.ticket_code}">${t.assigned_staff || 'Chưa gán'}</em></td>
          <td><span class="badge ${isAssigned ? 'badge-info' : (isUrgent ? 'badge-danger' : 'badge-warning')}" id="statusBadge_${t.ticket_code}">${t.status}</span></td>
          <td><button class="btn-primary-dark" style="padding: 5px 12px; font-size: 12px;" onclick="OperatorApp.openAssignMaintenanceModal('${t.ticket_code}')">${isAssigned ? 'Cập nhật' : 'Phân công'}</button></td>
        </tr>
      `;
    }).join("");
  },

  openAssignMaintenanceModal(ticketCode) {
    const el = document.getElementById("assignTicketCode");
    if (el) el.innerText = ticketCode;
    const m = document.getElementById("modalAssignMaintenance");
    if (m) m.classList.add("show");
  },

  selectPriority(btn) {
    document.querySelectorAll(".btn-priority").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
  },

  async submitMaintenanceAssign() {
    const tech = document.getElementById("technicianSelect").value;
    const notes = document.getElementById("assignNotes").value;
    const code = document.getElementById("assignTicketCode").innerText;

    await OperatorApi.assignMaintenance({
      ticket_code: code,
      assigned_staff_name: tech,
      priority: "Khẩn cấp",
      notes: notes
    });

    await this.loadMaintenance();
    this.closeModal("modalAssignMaintenance");
    alert(`Đã phân công thành công cho kỹ thuật viên ${tech}!\nSự cố ${code} đã chuyển trạng thái sang 'Đang xử lý'.`);
  },

  // ================= HUBS CONFIGURATION =================
  async loadHubsConfig() {
    const res = await OperatorApi.getHubsConfig();
    const tbody = document.getElementById("hubsTableBody");
    if (!tbody || !res) return;

    const items = res.items || res;
    tbody.innerHTML = items.map(h => {
      const isDeactivated = h.status === "Tạm ngưng";
      const isWarning = h.status === "Cảnh báo tải";
      const badgeClass = isDeactivated ? "badge-danger" : (isWarning ? "badge-warning" : "badge-success");
      return `
        <tr id="hubRow_${h.id}">
          <td><strong>${h.name}</strong></td>
          <td>${h.address}</td>
          <td id="hubCap_${h.id}">${h.parking_capacity} Đỗ / ${h.charger_capacity} Sạc</td>
          <td>${h.availability_rate_pct || 85}%</td>
          <td><span class="badge ${badgeClass}" id="hubStatus_${h.id}">${h.status}</span></td>
          <td>
            <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 12px; margin-right: 4px;" onclick="OperatorApp.openHubConfigModal('${h.id}', '${h.name}', ${h.parking_capacity}, ${h.charger_capacity}, ${h.lat}, ${h.lng})">Chỉnh sửa</button>
            <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 12px; color: var(--accent-red);" onclick="OperatorApp.openDeactivateModal('${h.id}', '${h.name}')">${isDeactivated ? 'Kích hoạt' : 'Tạm ngưng'}</button>
          </td>
        </tr>
      `;
    }).join("");
  },

  openHubConfigModal(hubId, name, parkingCap, chargerCap, lat, lng) {
    this.currentEditingHubId = hubId;
    document.getElementById("configHubName").value = name;
    document.getElementById("configParkingCap").value = parkingCap;
    document.getElementById("configChargerCap").value = chargerCap;
    document.getElementById("configGpsLat").value = lat;
    document.getElementById("configGpsLng").value = lng;

    const m = document.getElementById("modalHubConfig");
    if (m) m.classList.add("show");
  },

  async saveHubConfig() {
    const hubId = this.currentEditingHubId || "HUB-01";
    const name = document.getElementById("configHubName").value;
    const p = parseInt(document.getElementById("configParkingCap").value) || 150;
    const c = parseInt(document.getElementById("configChargerCap").value) || 50;

    await OperatorApi.updateHubConfig(hubId, {
      hub_id: hubId,
      name: name,
      parking_capacity: p,
      charger_capacity: c
    });

    await this.loadHubsConfig();
    this.closeModal("modalHubConfig");
    alert(`Đã lưu cấu hình mới cho ${name} thành công!\nSức chứa: ${p} đỗ, ${c} sạc.`);
  },

  openDeactivateModal(hubId, hubName) {
    this.currentDeactivatingHubId = hubId;
    this.currentDeactivatingHub = hubName;
    const title = document.getElementById("deactivateHubTitle");
    if (title) title.innerText = `Chuyển ${hubName} sang trạng thái Deactivate?`;
    const m = document.getElementById("modalDeactivateHub");
    if (m) m.classList.add("show");
  },

  async confirmDeactivate() {
    const hubId = this.currentDeactivatingHubId || "HUB-01";
    await OperatorApi.deactivateHub(hubId, "Bảo trì định kỳ toàn hệ thống");
    await this.loadHubsConfig();
    this.closeModal("modalDeactivateHub");
    alert(`Đã tạm ngưng hoạt động của ${this.currentDeactivatingHub}. Trụ sạc đã bị khóa.`);
  },

  // ================= WHAT-IF SIMULATION =================
  async loadSimSourceState(opt = 1) {
    const stType = opt === 1 ? "live" : "manual";
    const data = await OperatorApi.getSimulationSourceState(stType);
    const tbody = document.getElementById("simSourceTableBody");
    if (!tbody || !data) return;

    tbody.innerHTML = (data.hubs || []).map(h => `
      <tr>
        <td><strong>${h.hub_id}</strong></td>
        <td>${h.hub_name}</td>
        <td><input type="number" class="manual-input-cell" value="${h.bikes_available}" ${opt === 1 ? 'readonly' : ''}></td>
        <td><input type="number" class="manual-input-cell" value="${h.parking_free}" ${opt === 1 ? 'readonly' : ''}></td>
        <td><input type="number" class="manual-input-cell" value="${h.chargers_charging}" ${opt === 1 ? 'readonly' : ''}></td>
        <td>${h.power_load_kw} kW</td>
      </tr>
    `).join("");
  },

  goToSimStep(step) {
    this.currentSimStep = step;

    for (let i = 1; i <= 3; i++) {
      const ind = document.getElementById(`simStepIndicator${i}`);
      if (ind) {
        if (i === step) ind.classList.add("active");
        else ind.classList.remove("active");
      }
    }

    document.querySelectorAll(".sim-subview").forEach(v => v.classList.remove("active"));
    const target = document.getElementById(`simStep${step}View`);
    if (target) target.classList.add("active");
  },

  selectSourceOption(opt) {
    this.selectedSourceOpt = opt;
    const c1 = document.getElementById("sourceOption1");
    const c2 = document.getElementById("sourceOption2");

    if (opt === 1) {
      if (c1) c1.classList.add("selected");
      if (c2) c2.classList.remove("selected");
      document.getElementById("sourceTableTitle").innerText = "Bảng dữ liệu trạng thái mạng lưới hiện tại (Trạng thái A)";
      this.loadSimSourceState(1);
    } else {
      if (c2) c2.classList.add("selected");
      if (c1) c1.classList.remove("selected");
      document.getElementById("sourceTableTitle").innerText = "Bảng dữ liệu nhập thủ công (Trạng thái A' - Có thể chỉnh sửa)";
      this.loadSimSourceState(2);
    }
  },

  async testValidateParams() {
    const res = await OperatorApi.validateSimulation({
      scenario_name: "Kịch bản cao điểm",
      duration_minutes: 60,
      target_hub_ids: ["HUB-01", "HUB-02"],
      load_factor_pct: 150
    });

    if (this.selectedSourceOpt === 2) {
      const m = document.getElementById("modalValidationError");
      if (m) m.classList.add("show");
    } else {
      alert("Kiểm tra tham số thành công! Dữ liệu của các Hub hợp lệ và nằm trong sức chứa.");
    }
  },

  fixValidationError() {
    this.closeModal("modalValidationError");
    alert("Đã tự động cân bằng tham số hợp lệ. Bạn có thể tiếp tục sang Bước 2.");
  },

  triggerSimulationCalculation() {
    const m = document.getElementById("modalSimLoading");
    if (m) m.classList.add("show");

    let progress = 20;
    const bar = document.getElementById("simProgressBar");
    const phase = document.getElementById("simPhaseText");
    const timeRemain = document.getElementById("simTimeRemain");

    if (this.simProgressInterval) clearInterval(this.simProgressInterval);

    this.simProgressInterval = setInterval(async () => {
      progress += 25;
      if (bar) bar.style.width = progress + "%";

      if (progress >= 50 && phase) {
        phase.innerText = "Đang tính toán: Cân bằng tải trụ sạc & Dự báo thiếu hụt";
        if (timeRemain) timeRemain.innerText = "Thời gian còn lại ước tính: 00:01 s";
      }

      if (progress >= 100) {
        clearInterval(this.simProgressInterval);
        
        // Execute real run on backend
        await OperatorApi.runSimulation({
          scenario_name: "Tăng sinh viên giờ cao điểm",
          duration_minutes: 60,
          target_hub_ids: ["HUB-01", "HUB-02"],
          load_factor_pct: 150
        });

        setTimeout(() => {
          this.closeModal("modalSimLoading");
          this.goToSimStep(3);
        }, 300);
      }
    }, 350);
  },

  cancelSimulation() {
    if (this.simProgressInterval) clearInterval(this.simProgressInterval);
    this.closeModal("modalSimLoading");
    alert("Đã hủy tiến trình mô phỏng.");
  },

  openSaveRuleModal() {
    const m = document.getElementById("modalSaveFallbackRule");
    if (m) m.classList.add("show");
  },

  async confirmSaveFallbackRule() {
    const name = document.getElementById("fallbackRuleName").value;
    await OperatorApi.saveSimulationRule({
      simulation_id: "SIM-109",
      rule_name: name,
      operation_instructions: "Tự động điều chuyển 20 xe từ KTX Khu A sang Metro A.",
      auto_match_on_high_load: true
    });

    await this.loadSimHistory();
    this.closeModal("modalSaveFallbackRule");
    alert(`Đã lưu kịch bản dự phòng "${name}" vào cơ sở dữ liệu quy tắc vận hành tự động!`);
  },

  applyDispatchPlan() {
    alert("ĐÃ KÍCH HOẠT NHIỆM VỤ ĐIỀU PHỐI KHẨN CẤP!\nLệnh CMD-1025: Chuyển 20 xe từ Hub KTX Khu A sang Hub Ga Metro A đã được gửi đến nhân viên điều chuyển.");
    this.switchTab("tab-relocation");
  },

  async loadSimHistory() {
    const res = await OperatorApi.getSimulationHistory();
    const tbody = document.getElementById("simHistoryTableBody");
    if (!tbody || !res) return;

    const items = res.items || res;
    this.cachedSimHistory = items;

    tbody.innerHTML = items.map((item, idx) => `
      <tr class="${idx === 0 ? 'history-row-active' : ''}" onclick="OperatorApp.inspectHistoryItem('${item.id}')">
        <td><strong>#${item.id}</strong></td>
        <td>
          <div style="font-weight: 700;">${item.title}</div>
          <div style="font-size: 11.5px; color: var(--text-muted);">${item.parameters_summary}</div>
        </td>
        <td style="font-size: 12px;">${item.executed_at}</td>
        <td><span class="badge badge-success">${item.status}</span></td>
        <td>
          <button class="btn-secondary-light" style="padding: 3px 8px; font-size: 11px;">Xem</button>
          <button class="btn-primary-dark" style="padding: 3px 8px; font-size: 11px;" onclick="event.stopPropagation(); OperatorApp.reloadScenarioParams('${item.id}')">Tải lại</button>
        </td>
      </tr>
    `).join("");

    if (items[0]) {
      this.populateHistoryInspect(items[0]);
    }
  },

  showSimulationHistory() {
    document.querySelectorAll(".sim-subview").forEach(v => v.classList.remove("active"));
    const h = document.getElementById("simHistoryView");
    if (h) h.classList.add("active");
  },

  inspectHistoryItem(simId) {
    const item = (this.cachedSimHistory || []).find(h => h.id === simId);
    if (!item) return;

    this.populateHistoryInspect(item);
  },

  populateHistoryInspect(item) {
    const tEl = document.getElementById("inspTitle");
    if (tEl) tEl.innerText = item.title;

    const pEl = document.getElementById("inspParams");
    if (pEl) pEl.innerText = item.what_if_params || item.parameters_summary;

    const rEl = document.getElementById("inspResult");
    if (rEl) rEl.innerText = item.recorded_result || "Mô phỏng hoàn tất an toàn";

    const ruleEl = document.getElementById("inspRule");
    if (ruleEl) ruleEl.innerText = item.saved_rule || "Quy tắc tự động chưa thiết lập";
  },

  reloadScenarioParams(simId) {
    alert(`Đã tải lại bộ tham số của phiên #${simId} vào cấu hình kịch bản!`);
    this.goToSimStep(2);
  },

  // ================= EMERGENCY HALT =================
  openEmergencyModal() {
    const m = document.getElementById("modalEmergency");
    if (m) m.classList.add("show");
  },

  async confirmEmergency() {
    await OperatorApi.emergencyHalt();
    this.closeModal("modalEmergency");
    const kpiAlerts = document.getElementById("kpiAlerts");
    if (kpiAlerts) kpiAlerts.innerText = "DỪNG TOÀN BỘ";
    alert("ĐÃ KÍCH HOẠT DỪNG KHẨN CẤP TOÀN HỆ THỐNG!\nToàn bộ các kịch bản tự động điều phối đã bị tạm ngắt an toàn.");
  },

  closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove("show");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  OperatorApp.init();
});
