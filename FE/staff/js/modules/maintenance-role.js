/**
 * @fileoverview Module Nghiệp vụ Kỹ thuật viên Bảo trì (Maintenance Role).
 * @module Staff/Modules/MaintenanceRole
 */
(function (global) {
  "use strict";
  global.StaffModules = global.StaffModules || {};

  global.StaffModules.MaintenanceRole = {
  async loadMaintenanceTasks() {
    const data = await StaffApi.getMaintenanceTasks();
    const list = Array.isArray(data)
      ? data
      : [...((data && data.new_tasks) || []), ...((data && data.in_progress_tasks) || [])];
    const badge = document.getElementById("maintCountBadge");
    if (badge) badge.innerText = `${list.length} nhiệm vụ`;
    const container = document.getElementById("maintTasksContainer");
    if (!container || !list.length) return;

    container.innerHTML = list.map(t => {
      const pri = (t.priority || "THƯỜNG").toUpperCase();
      const tagClass = pri.includes("KHẨN") ? "badge-urgent-tag" : (pri.includes("CẢNH") ? "badge-warning-tag" : "badge-neutral-tag");
      return `
        <div class="staff-card" style="margin-bottom: 12px; padding: 14px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="${tagClass}">${pri}</span>
            <strong style="font-size: 13px;">${t.task_code}</strong>
          </div>
          <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; margin-bottom: 4px;">${t.category_label || "BẢO TRÌ"}</div>
          <h4 style="font-size: 15px; font-weight: 800; margin-bottom: 6px;">${t.title}</h4>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">${t.hub_name || ""}</div>
          <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 12px;">Tạo lúc: ${t.created_at_label || ""}</div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 10px;">
            <span style="font-size: 12px; color: var(--accent-red); font-weight: 700;">${t.due_label || t.status}</span>
            <button class="btn-staff-primary" style="width: auto; padding: 7px 14px; font-size: 12px;" onclick="StaffApp.openMaintenanceDetail('${t.task_code}')">XEM VÀ TIẾP NHẬN</button>
          </div>
        </div>
      `;
    }).join("");
  },

  async openMaintenanceDetail(taskCode) {
    this.currentMaintTaskCode = taskCode;
    const detail = await StaffApi.getMaintenanceDetail(taskCode);

    this.goToScreen("screen-maint-detail");
  },

  openMaintIncidentReport() {
    this.goToScreen("screen-maint-incident");
  },

  async submitMaintIncident() {
    await StaffApi.reportMaintIncident({
      incident_type: "Hư hỏng thiết bị",
      location_desc: "Hub KTX Khu A",
      description: "Ghi nhận sự cố mới từ kỹ thuật viên hiện trường",
      has_image: false
    });
    alert("Đã ghi nhận sự cố mới và báo cáo về hệ thống điều hành!");
    await this.loadMaintenanceTasks();
    this.goToScreen("screen-maint-list");
  },

  selectMaintOutcome(card, outcomeType) {
    document.querySelectorAll(".radio-card-select").forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    const radio = card.querySelector("input[type='radio']");
    if (radio) radio.checked = true;
  },

  async submitMaintResult() {
    const notes = document.getElementById("maintTechNotes") ? document.getElementById("maintTechNotes").value : "";
    await StaffApi.resolveMaintenance({
      task_code: this.currentMaintTaskCode || "MT-102",
      outcome: "FIXED_ON_SITE",
      technician_notes: notes
    });

    alert("GỬI KẾT QUẢ BẢO TRÌ THÀNH CÔNG!\nThiết bị đã được mở khóa và chuyển về trạng thái 'Sẵn sàng hoạt động'.");
    await this.loadMaintenanceTasks();
    this.goToScreen("screen-maint-list");
  },

  };
})(window);
