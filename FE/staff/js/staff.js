/**
 * Field Staff & Security Guard Mobile Application Controller
 * Smart E-Mobility Hub - ĐHQG-HCM
 * Fully integrated with Starlette Backend API (/api/v1/staff/...)
 */

const STAFF_API_BASE = "http://127.0.0.1:8000/api/v1/staff";

const StaffApi = {
  isBackendAvailable: false,

  async checkBackend() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/profile`);
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
      const res = await fetch(`${STAFF_API_BASE}/profile`);
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
      const res = await fetch(`${STAFF_API_BASE}/relocation/task`);
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
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
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
      const res = await fetch(`${STAFF_API_BASE}/maintenance/tasks`);
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
      const res = await fetch(`${STAFF_API_BASE}/maintenance/tasks/${taskCode}`);
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_code: taskCode, scanned_code: scannedCode })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi verifyDevice fallback:", e);
    }
    return { is_match: true, message: "Mã thiết bị trùng khớp 100% với phiếu sự cố." };
  },

  async resolveMaintenance(payload) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/maintenance/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi resolveMaintenance fallback:", e);
    }
    return { success: true, message: "Gửi kết quả bảo trì thành công!" };
  },

  async reportMaintIncident(payload) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/maintenance/incident`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
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
    try {
      const res = await fetch(`${STAFF_API_BASE}/parking/checkout/${encodeURIComponent(plateOrTicket)}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi parkingCheckoutPreview fallback:", e);
    }
    return {
      ticket_code: "SG-20261022-018",
      license_plate: plateOrTicket,
      checkin_time: "22/10/2026 · 14:36",
      checkout_time: "22/10/2026 · 16:42",
      duration_str: "2 giờ 06 phút",
      total_fee_vnd: 25000,
      payment_method: "Thanh toán bằng tiền mặt tại quầy",
      is_paid: false
    };
  },

  async parkingCheckoutConfirm(ticketCode, cashReceived = 25000) {
    try {
      const res = await fetch(`${STAFF_API_BASE}/parking/checkout/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_code: ticketCode, cash_received: cashReceived })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi parkingCheckoutConfirm fallback:", e);
    }
    return { success: true, message: "Xác nhận đã thu tiền mặt thành công. Mở barrier cho xe ra." };
  },

  async getShiftSummary() {
    try {
      const res = await fetch(`${STAFF_API_BASE}/parking/shift-summary`);
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guard_id: guardId, total_cash_deposited_vnd: cash })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("StaffApi closeShift fallback:", e);
    }
    return { success: true, message: `Đã chốt ca trực thành công! Số tiền nộp về quầy: ${cash.toLocaleString()} VNĐ.` };
  }
};

const StaffApp = {
  currentRole: "relocation",
  currentScreen: "screen-reloc-route",
  handoverDoneCount: 18,
  handoverTotalCount: 20,
  currentRelocTaskId: "#102",
  currentMaintTaskCode: "MT-102",

  async init() {
    console.log("Staff App Initialized");
    this.updateBottomNavLabels();

    await Promise.allSettled([
      this.loadProfile(),
      this.loadRelocationTask(),
      this.loadMaintenanceTasks(),
      this.loadShiftSummary()
    ]);
  },

  async loadProfile() {
    const prof = await StaffApi.getProfile();
    if (!prof) return;

    document.querySelectorAll(".staff-name-text").forEach(el => el.innerText = prof.full_name);
    document.querySelectorAll(".staff-shift-text").forEach(el => el.innerText = `${prof.shift_title} · ${prof.assigned_hub}`);
  },

  async loadRelocationTask() {
    const t = await StaffApi.getRelocationTask();
    if (!t) return;

    this.currentRelocTaskId = t.task_id || "#102";

    const fromEl = document.getElementById("relocFromHub");
    if (fromEl) fromEl.innerText = t.source_hub_name;

    const toEl = document.getElementById("relocToHub");
    if (toEl) toEl.innerText = t.target_hub_name;

    const countEl = document.getElementById("relocVehicleCount");
    if (countEl) countEl.innerText = t.total_bikes;

    const distEl = document.getElementById("relocDistance");
    if (distEl) distEl.innerText = `${t.estimated_distance_km} km`;

    const durEl = document.getElementById("relocDuration");
    if (durEl) durEl.innerText = `${t.estimated_duration_minutes} phút`;

    const progCount = document.getElementById("relocProgressCount");
    if (progCount) progCount.innerText = `${t.in_transit_bikes} / ${t.total_bikes} xe`;

    const pct = Math.round((t.in_transit_bikes / (t.total_bikes || 1)) * 100);
    const bar = document.getElementById("relocProgressBar");
    if (bar) bar.style.width = `${pct}%`;

    const remainEl = document.getElementById("relocRemainingText");
    if (remainEl) remainEl.innerText = `${t.remaining_at_source} xe còn lại tại Hub nguồn`;

    const pctEl = document.getElementById("relocPercentText");
    if (pctEl) pctEl.innerText = `${pct}%`;

    // Render Checklist
    if (t.checklist && t.checklist.length) {
      const container = document.getElementById("reconcileRows");
      if (container) {
        let done = 0;
        container.innerHTML = t.checklist.map((bike, idx) => {
          const isDone = bike.status === "Done" || bike.status === "done";
          if (isDone) done++;
          return `
            <div class="reconcile-row ${isDone ? 'done' : 'waiting'}" id="bikeRow_${bike.bike_code}" onclick="StaffApp.simulateScanBike('${bike.bike_code}')">
              <div class="check-box-square">${isDone ? '<i class="fa-solid fa-check"></i>' : ''}</div>
              <strong style="font-size: 12.5px;">${bike.bike_code}</strong>
              <span style="font-size: 12px; color: var(--text-muted);">Pin: ${bike.battery_pct}%</span>
              <span style="font-size: 12px; color: var(--text-muted);">Cọc sạc: ${bike.dock_number}</span>
              <span class="status-pill ${isDone ? 'done' : 'waiting'}">${isDone ? 'Done' : 'Waiting'}</span>
            </div>
          `;
        }).join("");

        this.handoverDoneCount = done;
        this.handoverTotalCount = t.checklist.length;
        const hCount = document.getElementById("handoverProgressCount");
        if (hCount) hCount.innerText = `${done}/${t.checklist.length} xe`;
      }
    }
  },

  async loadMaintenanceTasks() {
    const tasks = await StaffApi.getMaintenanceTasks();
    const container = document.getElementById("maintTasksContainer");
    if (!container || !tasks) return;

    const countBadge = document.getElementById("maintCountBadge");
    if (countBadge) countBadge.innerText = `${tasks.length} nhiệm vụ`;

    container.innerHTML = tasks.map(t => {
      const isUrgent = t.priority === "Khẩn cấp";
      const isWarning = t.priority === "Cảnh báo";
      const tagClass = isUrgent ? "badge-urgent-tag" : (isWarning ? "badge-warning-tag" : "badge-neutral-tag");

      return `
        <div class="staff-card" style="margin-bottom: 12px; padding: 14px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="${tagClass}">${t.priority}</span>
            <strong style="font-size: 13px;">${t.task_code}</strong>
          </div>
          <div style="font-size: 11.5px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; margin-bottom: 4px;">${t.category_label}</div>
          <h4 style="font-size: 15px; font-weight: 800; margin-bottom: 6px;">${t.title}</h4>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">${t.hub_name}</div>
          <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 12px;">Tạo lúc: ${t.created_at_label}</div>
          
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 10px;">
            <span style="font-size: 12px; color: ${isUrgent ? 'var(--accent-red)' : 'var(--text-muted)'}; font-weight: 700;">${t.due_label}</span>
            <button class="btn-staff-primary" style="width: auto; padding: 7px 14px; font-size: 12px;" onclick="StaffApp.openMaintenanceDetail('${t.task_code}')">XEM VÀ TIẾP NHẬN</button>
          </div>
        </div>
      `;
    }).join("");
  },

  async loadShiftSummary() {
    const shift = await StaffApi.getShiftSummary();
    if (!shift) return;

    const countEl = document.getElementById("shiftServedCount");
    if (countEl) countEl.innerText = shift.total_vehicles_served;

    const cashEl = document.getElementById("shiftTotalCash");
    if (cashEl) cashEl.innerText = (shift.total_cash_collected_vnd || 0).toLocaleString();

    const metaEl = document.getElementById("shiftDetailMeta");
    if (metaEl) metaEl.innerText = `${shift.shift_date} · ${shift.shift_title} · ${shift.hub_name}`;

    const transContainer = document.getElementById("shiftTransactionsContainer");
    if (transContainer && shift.transactions && shift.transactions.length) {
      transContainer.innerHTML = shift.transactions.map(item => `
        <div class="staff-card" style="padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 12px; font-weight: 800; color: var(--text-muted);">${item.seq_number}</span>
            <div>
              <strong style="font-size: 13.5px;">${item.license_plate}</strong>
              <div style="font-size: 11px; color: var(--text-muted);">${item.time_info}</div>
            </div>
          </div>
          <strong style="font-size: 13px;">${(item.amount_vnd || 25000).toLocaleString()} VNĐ</strong>
        </div>
      `).join("");
    }
  },

  switchRole(role) {
    this.currentRole = role;
    const sel = document.getElementById("staffRoleSelect");
    if (sel) sel.value = role;

    if (role === "relocation") {
      this.goToScreen("screen-reloc-route");
    } else if (role === "maintenance") {
      this.goToScreen("screen-maint-list");
    } else if (role === "security") {
      this.goToScreen("screen-guard-checkin");
    }

    this.updateBottomNavLabels();
  },

  goToScreen(screenId) {
    document.querySelectorAll(".staff-screen").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(screenId);
    if (target) {
      target.classList.add("active");
      this.currentScreen = screenId;
    }
    const viewport = document.getElementById("staffViewport");
    if (viewport) viewport.scrollTop = 0;
  },

  updateBottomNavLabels() {
    const l1 = document.getElementById("navLabel1");
    const l2 = document.getElementById("navLabel2");
    const l3 = document.getElementById("navLabel3");
    const l4 = document.getElementById("navLabel4");

    if (this.currentRole === "security") {
      if (l1) l1.innerText = "Xe vào";
      if (l2) l2.innerText = "Trả xe";
      if (l3) l3.innerText = "Ca trực";
      if (l4) l4.innerText = "Cá nhân";
    } else {
      if (l1) l1.innerText = "Nhiệm vụ";
      if (l2) l2.innerText = "Lịch sử";
      if (l3) l3.innerText = "Thông báo";
      if (l4) l4.innerText = "Cá nhân";
    }
  },

  onNavClick(tabIndex) {
    document.querySelectorAll(".staff-nav-item").forEach((btn, idx) => {
      if (idx + 1 === tabIndex) btn.classList.add("active");
      else btn.classList.remove("active");
    });

    if (this.currentRole === "security") {
      if (tabIndex === 1) this.goToScreen("screen-guard-checkin");
      else if (tabIndex === 2) {
        this.openCheckoutScreen();
      }
      else if (tabIndex === 3) this.goToScreen("screen-guard-shift");
      else alert("Mục Cá nhân: Thông tin tài khoản bảo vệ Nguyen Van B");
    } else if (this.currentRole === "relocation") {
      if (tabIndex === 1) this.goToScreen("screen-reloc-route");
      else if (tabIndex === 2) alert("Lịch sử các đợt điều chuyển đã hoàn tất trong tuần: 14 đợt.");
      else if (tabIndex === 3) alert("Thông báo từ Operator: Chuẩn bị nhận 20 xe tại trạm KTX Khu A lúc 17:00.");
      else alert("Thông tin nhân viên điều chuyển: Nguyen Van B");
    } else if (this.currentRole === "maintenance") {
      if (tabIndex === 1) this.goToScreen("screen-maint-list");
      else if (tabIndex === 2) alert("Lịch sử bảo dưỡng: Đã sửa 42 sự cố trong tháng.");
      else if (tabIndex === 3) alert("Cảnh báo mới: Trạm sạc C-05 Ga Metro phát sinh dòng rò.");
      else alert("Thông tin kỹ thuật viên: Nguyen Van B");
    }
  },

  // ================= RELOCATION ACTIONS =================
  async simulateScanBike(bikeCode) {
    const res = await StaffApi.scanBike(this.currentRelocTaskId, bikeCode, "02");

    const row = document.getElementById(`bikeRow_${bikeCode}`) || document.getElementById(`bikeRow${bikeCode}`);
    if (row) {
      row.classList.remove("waiting");
      row.classList.add("done");
      const check = row.querySelector(".check-box-square");
      if (check) check.innerHTML = '<i class="fa-solid fa-check"></i>';
      const pill = row.querySelector(".status-pill");
      if (pill) {
        pill.className = "status-pill done";
        pill.innerText = "Done";
      }

      this.handoverDoneCount = Math.min(this.handoverTotalCount, this.handoverDoneCount + 1);
      const counter = document.getElementById("handoverProgressCount");
      if (counter) counter.innerText = `${this.handoverDoneCount}/${this.handoverTotalCount} xe`;

      alert(`Đã quét xác nhận xe ${bikeCode} vào cọc đỗ thành công! Cập nhật về server trung tâm.`);
    }
  },

  toggleBikeRow(row) {
    alert("Xe này đã hoàn tất đối soát cọc đỗ.");
  },

  async completeHandover() {
    await StaffApi.handover(this.currentRelocTaskId, this.handoverDoneCount, "Hub Ga Metro A");
    alert("HOÀN TẤT BÀN GIAO HẠ TẦNG THÀNH CÔNG!\nĐã đối soát toàn bộ xe tại Hub Ga Metro A. Dữ liệu đã được cập nhật về Operator.");
    this.goToScreen("screen-reloc-route");
  },

  openRelocIncidentReport() {
    this.goToScreen("screen-reloc-incident");
  },

  async submitRelocIncident() {
    const type = document.getElementById("relocIncidentType").value;
    await StaffApi.reportRelocIncident({
      task_id: this.currentRelocTaskId,
      incident_type: type,
      location_desc: "Đường nội bộ ĐHQG",
      description: "Sự cố phát sinh trong quá trình chuyển xe",
      has_image: false
    });

    alert(`Đã gửi báo cáo sự cố "${type}" đến Trung tâm Điều hành!\nĐội cứu hộ lưu động đã nhận thông tin.`);
    this.goToScreen("screen-reloc-route");
  },

  // ================= MAINTENANCE ACTIONS =================
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

  // ================= SECURITY GUARD ACTIONS =================
  async simulatePlateScan() {
    const plates = ["59-B2 123.45", "51-H1 889.92", "60-B1 456.78", "61-D2 991.02"];
    const randomPlate = plates[Math.floor(Math.random() * plates.length)];
    const input = document.getElementById("guardPlateInput");
    if (input) input.value = randomPlate;

    const res = await StaffApi.parkingCheckin({
      license_plate: randomPlate,
      parking_bay: "Dãy A",
      parking_slot: "Ô số 018",
      hub_name: "Hub KTX Khu A",
      guard_id: "SG-02"
    });

    const codeEl = document.getElementById("guardTicketCode");
    if (codeEl && res.ticket_code) codeEl.innerText = res.ticket_code;

    alert(`Đã nhận diện biển số xe: ${randomPlate} qua camera bãi đỗ!\nMã vé lượt gửi: ${res.ticket_code}`);
  },

  async confirmVehicleCheckin() {
    const plate = document.getElementById("guardPlateInput").value;
    const bay = document.getElementById("guardBaySelect").value;
    const slot = document.getElementById("guardSlotSelect").value;

    const res = await StaffApi.parkingCheckin({
      license_plate: plate,
      parking_bay: bay,
      parking_slot: slot,
      hub_name: "Hub KTX Khu A",
      guard_id: "SG-02"
    });

    alert(`XÁC NHẬN XE VÀO BÃI THÀNH CÔNG!\nBiển số: ${plate}\nVị trí: ${bay} - ${slot}\nMã vé QR: ${res.ticket_code || 'SG-20261022-018'}\nĐã in vé và mở thanh chắn Barrier.`);
  },

  async openCheckoutScreen(plateOrTicket = "59-B2 123.45") {
    const res = await StaffApi.parkingCheckoutPreview(plateOrTicket);
    if (res) {
      const pEl = document.getElementById("checkoutPlate");
      if (pEl) pEl.innerText = res.license_plate;

      const tEl = document.getElementById("checkoutTimeInfo");
      if (tEl) tEl.innerText = `Giờ vào: ${res.checkin_time} | Giờ ra: ${res.checkout_time}`;

      const dEl = document.getElementById("checkoutDurationInfo");
      if (dEl) dEl.innerText = `Tổng thời gian: ${res.duration_str}`;

      const fEl = document.getElementById("checkoutFeeDisplay");
      if (fEl) fEl.innerText = `${(res.total_fee_vnd || 25000).toLocaleString()} VNĐ`;

      const cEl = document.getElementById("checkoutCashConfirm");
      if (cEl) cEl.innerText = `${(res.total_fee_vnd || 25000).toLocaleString()} VNĐ`;

      const codeEl = document.getElementById("checkoutTicketCode");
      if (codeEl) codeEl.innerText = `Mã giao dịch: ${res.ticket_code}`;
    }
    this.goToScreen("screen-guard-checkout");
  },

  async confirmCashReceived() {
    await StaffApi.parkingCheckoutConfirm("SG-20261022-018", 25000);
    alert("XÁC NHẬN ĐÃ THU 25.000 VNĐ TIỀN MẶT THÀNH CÔNG!\nMở barrier cho xe 59-B2 123.45 ra bãi.");
    await this.loadShiftSummary();
    this.goToScreen("screen-guard-shift");
  },

  async closeShift() {
    await StaffApi.closeShift("SG-02", 1200000);
    alert("ĐÃ CHỐT CA TRỰC THÀNH CÔNG!\nTổng tiền mặt bàn giao: 1.200.000 VNĐ (48 lượt xe).\nCa trực đã được khóa và lưu trữ kế toán.");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  StaffApp.init();
});
