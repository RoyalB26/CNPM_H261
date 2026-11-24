/**
 * @fileoverview Dịch vụ giao tiếp API máy chủ cho Bảng điều khiển Operator.
 * @module Operator/OperatorApi
 */
(function (global) {
  "use strict";

  const OPERATOR_API_BASE = (window.EMobilityConfig && window.EMobilityConfig.OPERATOR_API_BASE) || "http://127.0.0.1:8000/api/v1/operator";

  const OperatorApi = {
    isBackendAvailable: false,

    _authHeaders(extra = {}) {
      const token = sessionStorage.getItem("operator_access_token") || "";
      return token ? { ...extra, Authorization: "Bearer " + token } : { ...extra };
    },

    async login(email, password) {
      const res = await fetch(`${OPERATOR_API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || "Sai tài khoản hoặc mật khẩu");
      }
      return data;
    },

    async verify2fa(email, challenge_id, otp_code) {
      const res = await fetch(`${OPERATOR_API_BASE}/auth/verify-2fa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, challenge_id, otp_code })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || "Mã OTP không hợp lệ");
      }
      if (data.access_token) {
        sessionStorage.setItem("operator_access_token", data.access_token);
      }
      return data;
    },

    async checkBackend() {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/dashboard/kpis`, { headers: this._authHeaders() });
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
        const res = await fetch(`${OPERATOR_API_BASE}/dashboard/kpis`, { headers: this._authHeaders() });
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
        const res = await fetch(`${OPERATOR_API_BASE}/dashboard/telemetry`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          return Array.isArray(data) ? data : (data && (data.items || data.events)) || [];
        }
      } catch (e) {
        console.warn("OperatorApi getTelemetry fallback:", e);
      }
      return [
        { level: "alert", title: "Mất kết nối IoT Hub B", message: "Cổng sạc C-02 không phản hồi dữ liệu Telemetry quá 60s.", created_at_relative: "Vừa xong", hub_name: "Hub B - KTX Khu B" },
        { level: "warning", title: "Nhiệt độ trạm sạc Hub A cao", message: "Trạm sạc số 4 đang ở mức 58°C (Ngưỡng cảnh báo).", created_at_relative: "2 phút trước", hub_name: "Hub A - Ga Metro" },
        { level: "info", title: "Điều phối xe tự động", message: "Đã kích hoạt kịch bản điều 5 xe từ Hub A sang Hub B.", created_at_relative: "15 phút trước", hub_name: "Hệ thống" },
        { level: "success", title: "Khôi phục Hub C hoàn tất", message: "Bảo trì định kỳ đã xong, tài nguyên sẵn sàng.", created_at_relative: "1 giờ trước", hub_name: "Hub C - ĐH Bách Khoa" }
      ];
    },

    async getHubsLive() {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/dashboard/hubs-live`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : (data && (data.items || data.hubs)) || [];
          return items.map(h => ({
            ...h,
            id: h.hub_id || h.id,
            status: h.status_label || h.status || "Bình thường",
            color: h.color_code || h.color || "#10b981",
            chargers: h.chargers_free ?? h.chargers ?? 0,
            chargers_total: h.chargers_total ?? 50,
            free_slots: h.free_slots || `${h.parking_free ?? 0}/${h.parking_total ?? 0} chỗ đỗ rảnh`,
            power: h.power || `${h.current_power_kw ?? 0} kW / ${h.max_power_kw ?? 100} kW`
          }));
        }
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
          headers: this._authHeaders({ "Content-Type": "application/json" }),
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
        const res = await fetch(`${OPERATOR_API_BASE}/relocation/commands`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          return Array.isArray(data) ? data : (data && (data.items || data.commands)) || [];
        }
      } catch (e) {
        console.warn("OperatorApi getRelocations fallback:", e);
      }
      return [
        { id: "CMD-1023", source_hub: "Hub A (KTX Khu A)", dest_hub: "Hub B (Ga Metro A)", vehicle_count: 5, vehicle_type: "Xe đạp điện", assigned_staff: "Nguyen Van B", status: "Đang di chuyển", priority: "Bình thường" },
        { id: "CMD-1024", source_hub: "Hub C (ĐH Bách Khoa)", dest_hub: "Hub A (KTX Khu A)", vehicle_count: 2, vehicle_type: "Xe đạp điện", assigned_staff: "Tran Van C", status: "Đang chờ nhận", priority: "Bình thường" }
      ];
    },

    async createRelocation(payload) {
      const res = await fetch(`${OPERATOR_API_BASE}/relocation/commands`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || `HTTP ${res.status}`);
      }
      return data;
    },

    async getMaintenanceTickets() {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/maintenance/tickets`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : (data && (data.items || data.tickets)) || [];
          return items.map(t => ({
            ticket_code: t.ticket_code || t.id,
            resource_code: t.device_code || t.resource_code || "N/A",
            source: t.source || "Hệ thống",
            issue_type: t.fault_category || t.issue_type || "Bảo trì",
            priority: t.severity || t.priority || "Thường",
            hub_name: t.hub_name || "N/A",
            assigned_staff_id: t.assigned_staff_id || null,
            assigned_staff_name: t.assigned_staff_name || "Chưa gán",
            status: t.status || "Chờ xử lý"
          }));
        }
      } catch (e) {
        console.warn("OperatorApi getMaintenanceTickets fallback:", e);
      }
      return [
        { ticket_code: "TICK-801", resource_code: "LOCK-019", issue_type: "Sửa chốt khóa Smartlock", priority: "Khẩn cấp", hub_name: "Hub KTX Khu B", status: "Đã phân công" },
        { ticket_code: "TICK-802", resource_code: "S02", issue_type: "Chạm mạch trụ sạc nhanh", priority: "Khẩn cấp", hub_name: "Hub Ga Metro ĐHQG", status: "Chờ xử lý" },
        { ticket_code: "TICK-803", resource_code: "BSS-CAB-04", issue_type: "Kẹt khay tủ pin", priority: "Bình thường", hub_name: "Hub Thư viện Trung tâm", status: "Đang xử lý" }
      ];
    },

    async assignMaintenance(payload) {
      const res = await fetch(`${OPERATOR_API_BASE}/maintenance/assign`, {
        method: "POST",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || `HTTP ${res.status}`);
      }
      return data;
    },

    async getHubsConfig() {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/hubs`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : (data && data.items) || [];
          return items.map(h => ({
            hub_id: h.id || h.hub_id,
            hub_name: h.name || h.hub_name,
            address: h.address || "Khu đô thị ĐHQG - HCM",
            parking_capacity: h.parking_capacity,
            charger_capacity: h.charger_capacity,
            availability_rate_pct: h.availability_rate_pct ?? 85,
            lat: h.lat,
            lng: h.lng,
            status: h.status
          }));
        }
      } catch (e) {
        console.warn("OperatorApi getHubsConfig fallback:", e);
      }
      return [
        { hub_id: "hub-01", hub_name: "Hub Ga Metro ĐHQG", address: "Khu đô thị ĐHQG - HCM", parking_capacity: 20, charger_capacity: 4, availability_rate_pct: 92, lat: 10.8753, lng: 106.8005, status: "Hoạt động" },
        { hub_id: "hub-02", hub_name: "Hub Đại học Bách khoa", address: "Đường D1, Khu ĐHQG", parking_capacity: 30, charger_capacity: 6, availability_rate_pct: 88, lat: 10.8805, lng: 106.8055, status: "Hoạt động" }
      ];
    },

    async updateHubCapacity(hubId, parkingCap, chargerCap) {
      const res = await fetch(`${OPERATOR_API_BASE}/hubs/${hubId}/config`, {
        method: "PUT",
        headers: this._authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ hub_id: hubId, parking_capacity: parkingCap, charger_capacity: chargerCap })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || `HTTP ${res.status}`);
      }
      return data;
    },

    async deactivateHub(hubId, reason = "Tạm ngưng vận hành từ bảng điều khiển Operator") {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/hubs/${hubId}/deactivate`, {
          method: "POST",
          headers: this._authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({
            hub_id: hubId,
            reason,
            lock_chargers: true,
            reroute_bookings: true
          })
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("OperatorApi deactivateHub fallback:", e);
      }
      return { success: true };
    },

    async getSimStateSource() {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/simulation/source-state`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data)
            ? data
            : (data && (data.hub_snapshots || data.items || data.hubs)) || [];
          return items.map(h => ({
            hub_id: h.hub_id,
            hub_name: h.name || h.hub_name || h.hub_code,
            available_bikes: h.current_bikes ?? h.available_bikes ?? 0,
            total_bikes: h.total_parking_capacity ?? h.total_bikes ?? 0,
            free_parking: h.free_parking_slots ?? h.free_parking ?? 0,
            total_parking: h.total_parking_capacity ?? h.total_parking ?? 0,
            active_chargers: h.active_chargers ?? 0,
            total_chargers: h.total_chargers ?? 0,
            power_usage: h.power_usage || `${h.base_power_kw ?? 0} / ${h.max_power_kw ?? 100} kW`,
            status: h.status || "Bình thường"
          }));
        }
      } catch (e) {
        console.warn("OperatorApi getSimStateSource fallback:", e);
      }
      return [
        { hub_name: "Hub Ga Metro A", available_bikes: 25, total_bikes: 40, free_parking: 15, total_parking: 30, active_chargers: 4, total_chargers: 8, power_usage: "60 kW", status: "Bình thường" },
        { hub_name: "Hub KTX Khu A", available_bikes: 12, total_bikes: 30, free_parking: 20, total_parking: 25, active_chargers: 6, total_chargers: 6, power_usage: "90 kW", status: "Bình thường" }
      ];
    },

    async runSimulation(params) {
      const payload = params && params.config ? params : {
        source_type: "LIVE_A",
        config: {
          scenario_name: (params && params.scenario_name) || "Nhu cầu sạc tăng cao",
          scenario_type: (params && params.scenario_type) || "Nhu cầu sạc tăng đột biến",
          demand_increase_pct: Number((params && params.demand_increase_pct) ?? 50),
          duration_minutes: Number((params && params.duration_minutes) ?? 60),
          start_time: (params && params.start_time) || "18:00"
        }
      };
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/simulation/run`, {
          method: "POST",
          headers: this._authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify(payload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("OperatorApi runSimulation fallback:", e);
      }
      return { success: true, simulation_id: "SIM-LOCAL-01", message: "Mô phỏng hoàn tất." };
    },

    async getSimHistory() {
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/simulation/history`, { headers: this._authHeaders() });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : (data && data.items) || [];
          return items.map(item => ({
            ...item,
            sim_id: item.sim_id || item.id,
            created_at: item.executed_at || item.created_at || "",
            scenario_name: item.scenario_name || item.title || "Kịch bản mô phỏng",
            peak_power_kw: item.peak_power_kw ?? (item.result && item.result.peak_power_kw) ?? 185,
            impacted_hubs: item.impacted_hubs ?? 2
          }));
        }
      } catch (e) {
        console.warn("OperatorApi getSimHistory fallback:", e);
      }
      return [
        { sim_id: "SIM-2026-001", created_at: "18/10/2026", scenario_name: "Mưa lớn giờ tan tầm", status: "Thành công", peak_power_kw: 185, impacted_hubs: 2 }
      ];
    },

    async saveFallbackRule(rule) {
      const payload = {
        simulation_id: rule.simulation_id || "SIM-20261018-01",
        rule_name: rule.rule_name || rule.name || "Kịch bản dự phòng",
        operation_instructions: rule.operation_instructions || rule.condition || "Điều chuyển xe khi tải cao",
        auto_match_on_high_load: rule.auto_match_on_high_load !== undefined ? Boolean(rule.auto_match_on_high_load) : true
      };
      try {
        const res = await fetch(`${OPERATOR_API_BASE}/simulation/save-rule`, {
          method: "POST",
          headers: this._authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify(payload)
        });
        if (res.ok) return await res.json();
      } catch (e) {
        console.warn("OperatorApi saveFallbackRule fallback:", e);
      }
      return { success: true };
    }
  };

  global.OperatorApi = OperatorApi;
})(window);
