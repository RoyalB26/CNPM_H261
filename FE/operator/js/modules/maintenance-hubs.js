/**
 * @fileoverview Module Quản lý Bảo trì & Cấu hình Trạm Hub.
 * @module Operator/Modules/MaintenanceHubs
 */
(function (global) {
  "use strict";
  global.OperatorModules = global.OperatorModules || {};

  global.OperatorModules.MaintenanceHubs = {
    async loadMaintenance() {
      const tickets = await OperatorApi.getMaintenanceTickets();
      this.cachedTickets = tickets || [];
      const tbody = document.getElementById("maintenanceTableBody");
      if (!tbody || !tickets) return;

      tbody.innerHTML = tickets.map(t => {
        const isUrgent = t.priority === "urgent" || t.priority === "Khẩn cấp";
        const isAssigned = (t.status || "").toLowerCase().includes("đã phân công");
        const staffDisplay = t.assigned_staff_name && t.assigned_staff_name !== "Chưa gán"
          ? t.assigned_staff_name
          : "<em>Chưa gán</em>";
        return `
          <tr>
            <td><strong>${t.ticket_code}</strong></td>
            <td>${t.resource_code}</td>
            <td>${t.source || "Hệ thống"}</td>
            <td>${t.issue_type}</td>
            <td>${staffDisplay}</td>
            <td><span class="badge ${isAssigned ? 'badge-info' : (isUrgent ? 'badge-danger' : 'badge-warning')}">${t.status}</span></td>
            <td><button class="btn-primary-dark" style="padding: 5px 12px; font-size: 12px;" onclick="OperatorApp.openAssignMaintenanceModal('${t.ticket_code}')">${isAssigned ? 'Điều chỉnh NV' : 'Phân công'}</button></td>
          </tr>
        `;
      }).join("");
    },

    openAssignMaintenanceModal(ticketCode) {
      const codeEl = document.getElementById("assignTicketCode");
      if (codeEl) codeEl.innerText = ticketCode;
      const ticket = (this.cachedTickets || []).find(t => t.ticket_code === ticketCode);
      if (ticket) {
        const devEl = document.getElementById("assignDeviceHub");
        if (devEl) devEl.value = `${ticket.resource_code} · ${ticket.hub_name}`;
        const faultEl = document.getElementById("assignFaultCategory");
        if (faultEl) faultEl.value = ticket.issue_type;
      }
      const m = document.getElementById("modalAssignMaintenance");
      if (m) m.classList.add("show");
    },

    selectPriority(btn) {
      document.querySelectorAll(".btn-priority, .priority-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
    },

    async submitMaintenanceAssign() {
      const codeEl = document.getElementById("assignTicketCode");
      const code = codeEl ? (codeEl.value || codeEl.innerText || "").trim() : "";
      const techEl = document.getElementById("technicianSelect") || document.getElementById("assignTechSelect");
      const techId = techEl ? techEl.value : "STF-02";
      const techNameMap = { "STF-02": "Nguyen Van B", "STF-01": "Nhân viên điều chuyển 1" };
      const techName = techNameMap[techId] || (techEl && techEl.options[techEl.selectedIndex] ? techEl.options[techEl.selectedIndex].text.split(" (")[0] : "Nguyen Van B");
      const priBtn = document.querySelector(".btn-priority.active, .priority-btn.active");
      const rawPri = priBtn ? (priBtn.dataset.p || priBtn.innerText).trim() : "Khẩn cấp";
      const priorityMap = { "Khẩn cấp": "Khẩn cấp", "Cao": "Khẩn cấp", "Trung bình": "Cảnh báo", "Thấp": "Thường" };
      const priority = priorityMap[rawPri] || "Cảnh báo";
      const notesEl = document.getElementById("assignNotes");
      const notes = notesEl ? notesEl.value : "";

      try {
        await OperatorApi.assignMaintenance({
          ticket_code: code,
          technician_id: techId,
          technician_name: techName,
          priority: priority,
          operator_notes: notes
        });
        this.closeModal("modalAssignMaintenance");
        alert(`Đã phân công thành công cho kỹ thuật viên ${techName}!\nSự cố ${code} đã chuyển trạng thái.`);
        await this.loadMaintenance();
      } catch (err) {
        console.error("Lỗi phân công bảo trì:", err);
        alert("Không thể phân công bảo trì: " + (err.message || "Lỗi kết nối"));
      }
    },

    async loadHubsConfig() {
      const hubs = await OperatorApi.getHubsConfig();
      const tbody = document.getElementById("hubsTableBody") || document.getElementById("hubsConfigTableBody");
      if (!tbody || !hubs) return;

      tbody.innerHTML = hubs.map(h => {
        const isNormal = h.status === "Bình thường" || h.status === "Normal" || h.status === "Hoạt động";
        return `
          <tr>
            <td><strong>${h.hub_name}</strong></td>
            <td>${h.address || "Khu đô thị ĐHQG - HCM"}</td>
            <td>${h.parking_capacity} Đỗ / ${h.charger_capacity} Sạc</td>
            <td>${h.availability_rate_pct ?? 85}%</td>
            <td><span class="badge ${isNormal ? 'badge-success' : 'badge-danger'}">${h.status}</span></td>
            <td>
              <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11.5px; margin-right: 4px;" onclick="OperatorApp.openHubConfigModal('${h.hub_id}', '${h.hub_name}', ${h.parking_capacity}, ${h.charger_capacity}, ${h.lat}, ${h.lng})">Chỉnh sửa</button>
              <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11.5px; color: var(--accent-red);" onclick="OperatorApp.openDeactivateModal('${h.hub_id}', '${h.hub_name}')">Tạm ngưng</button>
            </td>
          </tr>
        `;
      }).join("");
    },

    openHubConfigModal(hubId, name, parkingCap, chargerCap, lat, lng) {
      // Hỗ trợ cả chữ ký 5 tham số từ HTML tĩnh lẫn 6 tham số từ bảng động
      if (typeof name === "number") {
        lng = lat;
        lat = chargerCap;
        chargerCap = parkingCap;
        parkingCap = name;
        name = hubId;
        hubId = "hub-01";
      }
      this.currentEditingHubId = hubId || "hub-01";
      const nameEl = document.getElementById("configHubName");
      if (nameEl) nameEl.value = name || "";
      const parkEl = document.getElementById("configParkingCap");
      if (parkEl) parkEl.value = parkingCap ?? 20;
      const chgEl = document.getElementById("configChargerCap");
      if (chgEl) chgEl.value = chargerCap ?? 4;
      const latEl = document.getElementById("configGpsLat");
      if (latEl) latEl.value = lat ?? 10.8753;
      const lngEl = document.getElementById("configGpsLng");
      if (lngEl) lngEl.value = lng ?? 106.8005;

      const m = document.getElementById("modalHubConfig");
      if (m) m.classList.add("show");
    },

    async saveHubConfig() {
      const id = this.currentEditingHubId || "hub-01";
      const nameEl = document.getElementById("configHubName");
      const name = nameEl ? nameEl.value : id;
      const p = parseInt(document.getElementById("configParkingCap").value, 10) || 20;
      const c = parseInt(document.getElementById("configChargerCap").value, 10) || 4;

      try {
        await OperatorApi.updateHubCapacity(id, p, c);
        this.closeModal("modalHubConfig");
        alert(`Đã lưu cấu hình mới cho ${name} thành công!\nSức chứa: ${p} đỗ, ${c} trụ sạc.`);
        await this.loadHubsConfig();
      } catch (err) {
        console.error("Lỗi lưu cấu hình Hub:", err);
        alert("Không thể lưu cấu hình Hub: " + (err.message || "Lỗi kết nối"));
      }
    },

    openDeactivateModal(hubId, hubName) {
      this.currentDeactivatingHubId = hubId;
      this.currentDeactivatingHub = hubName;
      const title = document.getElementById("deactivateHubTitle");
      if (title) title.innerText = `Chuyển ${hubName} sang trạng thái Deactivated?`;
      const m = document.getElementById("modalDeactivateHub");
      if (m) m.classList.add("show");
    },

    async confirmDeactivate() {
      await OperatorApi.deactivateHub(this.currentDeactivatingHubId || this.currentDeactivatingHub);
      this.closeModal("modalDeactivateHub");
      alert(`Đã tạm ngưng hoạt động của ${this.currentDeactivatingHub}. Trụ sạc và chỗ đỗ đã khóa trên ứng dụng người dùng.`);
      await this.loadHubsConfig();
      await this.loadKpis();
    }
  };
})(window);
