/**
 * @fileoverview Module Vận hành Tự động, Lịch sạc & Thông báo Operator.
 * @module Operator/Modules/Automation
 */
(function (global) {
  "use strict";
  global.OperatorModules = global.OperatorModules || {};

  global.OperatorModules.Automation = {
    async loadAutomationTab() {
      await Promise.allSettled([
        this.loadAutomationRuns(),
        this.loadOperatorChargingSchedules()
      ]);
    },

    async loadAutomationRuns() {
      const tbody = document.getElementById("automationRunsTableBody");
      if (!tbody) return;
      try {
        const runs = await OperatorApi.getAutomationRuns();
        if (!runs.length) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">Chưa có phiên tự động nào.</td></tr>`;
          return;
        }
        tbody.innerHTML = runs.map(r => {
          const st = r.status || "WAITING_OPERATOR";
          const badge = st === "COMPLETED" || st === "HANDLED" ? "badge-success" : (st === "PAUSED" ? "badge-warning" : "badge-info");
          return `
            <tr>
              <td><strong>${r.id}</strong></td>
              <td>${r.hub_name || r.hub_id || "N/A"}</td>
              <td>${r.load_pct !== undefined ? r.load_pct + "%" : (r.power_demand_kw ? r.power_demand_kw + " kW" : "N/A")}</td>
              <td>${r.rule_id || r.rule_name || "Chưa khớp quy tắc"}</td>
              <td><span class="badge ${badge}">${st}</span></td>
              <td style="display: flex; gap: 6px; flex-wrap: wrap;">
                <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11px;" onclick="OperatorApp.interveneAutomation('${r.id}', 'pause')">Tạm dừng</button>
                <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11px;" onclick="OperatorApp.interveneAutomation('${r.id}', 'resume')">Tiếp tục</button>
                <button class="btn-primary-dark" style="padding: 4px 8px; font-size: 11px;" onclick="OperatorApp.interveneAutomation('${r.id}', 'resolve')">Đã xử lý</button>
              </td>
            </tr>
          `;
        }).join("");
      } catch (err) {
        console.warn("loadAutomationRuns error:", err);
      }
    },

    async triggerAutomationScan() {
      try {
        await OperatorApi.scanAutomation();
        await this.loadAutomationRuns();
        alert("Đã hoàn tất quét tải cao toàn mạng lưới.");
      } catch (err) {
        alert("Lỗi quét tải cao: " + (err.message || "Lỗi kết nối"));
      }
    },

    async interveneAutomation(runId, action) {
      try {
        await OperatorApi.interveneAutomationRun(runId, { action });
        await this.loadAutomationRuns();
      } catch (err) {
        alert("Không thể can thiệp phiên " + runId + ": " + (err.message || "Lỗi nghiệp vụ"));
      }
    },

    async submitHubLoadUpdate() {
      const hubId = document.getElementById("autoLoadHubSelect")?.value || "hub-01";
      const kw = parseFloat(document.getElementById("autoLoadPowerInput")?.value || "95");
      try {
        await OperatorApi.updateHubLoad(hubId, kw);
        await OperatorApi.scanAutomation();
        await this.loadAutomationRuns();
        alert(`Đã cập nhật công suất tải ${kw} kW cho ${hubId} và quét tự động.`);
      } catch (err) {
        alert("Lỗi cập nhật tải Hub: " + (err.message || "Lỗi kết nối"));
      }
    },

    async loadOperatorChargingSchedules() {
      const tbody = document.getElementById("operatorChargingSchedulesBody");
      if (!tbody) return;
      try {
        const items = await OperatorApi.getChargingSchedules();
        if (!items.length) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">Chưa có lịch sạc đặt trước nào.</td></tr>`;
          return;
        }
        tbody.innerHTML = items.map(s => `
          <tr>
            <td><strong>${s.id}</strong></td>
            <td>${s.hub_id} · ${s.port_id || "Auto"}</td>
            <td>${s.plate_number || "N/A"}</td>
            <td style="font-size: 12px;">${(s.starts_at || "").slice(11, 16)} - ${(s.ends_at || "").slice(11, 16)}</td>
            <td>${s.battery_pct ?? "--"}%</td>
            <td><span class="badge badge-info">${s.status}</span></td>
          </tr>
        `).join("");
      } catch (err) {
        console.warn("loadOperatorChargingSchedules error:", err);
      }
    },

    async loadOperatorNotifications() {
      try {
        const items = await OperatorApi.getNotifications();
        const badge = document.getElementById("operatorNotifBadge");
        if (badge) {
          badge.innerText = items.length;
          badge.style.display = items.length > 0 ? "inline-block" : "none";
        }
        return items;
      } catch (e) {
        return [];
      }
    },

    async openNotificationsModal() {
      const m = document.getElementById("modalOperatorNotifications");
      if (m) m.classList.add("show");
      const body = document.getElementById("operatorNotificationsBody");
      if (!body) return;
      const items = await this.loadOperatorNotifications();
      if (!items.length) {
        body.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Chưa có thông báo mới.</div>`;
        return;
      }
      body.innerHTML = items.map(n => `
        <div class="feed-item info" style="margin-bottom: 10px;">
          <div style="font-weight: 700; font-size: 13px;">${n.title || "Thông báo"}</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">${n.message || n.body || ""}</div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${n.created_at || ""}</div>
        </div>
      `).join("");
    }
  };
})(window);
