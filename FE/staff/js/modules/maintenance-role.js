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
    if (detail) {
      this.currentMaintDetail = detail;
      const setTxt = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined && v !== null) el.innerText = v; };
      setTxt("maintDetailTaskTitle", `Nhiệm vụ ${detail.task_code || taskCode}`);
      setTxt("maintDetailPriority", detail.priority || "THƯỜNG");
      setTxt("maintDetailCategory", detail.category_label || "BẢO TRÌ");
      setTxt("maintDetailHeadline", detail.title || taskCode);
      setTxt("maintDetailReporter", detail.reported_by || "Hệ thống");
      setTxt("maintDetailDeviceCode", detail.device_code || "N/A");
      setTxt("maintDetailLocation", detail.exact_location || detail.location_hub || "Hub ĐHQG");
      setTxt("maintDetailDescription", detail.reporter_notes || detail.description || "");
      setTxt("maintDetailPhotoName", detail.attachment_filename || (detail.photo_url ? "anh-su-co.jpg" : "Không có ảnh đính kèm"));

      setTxt("maintScanTaskCode", detail.task_code || taskCode);
      const scanInput = document.getElementById("maintScanCodeInput");
      if (scanInput) scanInput.value = detail.device_code || "BK-EB-018";
      setTxt("maintReportTaskCode", detail.task_code || taskCode);
      setTxt("maintReportHeaderId", `Nhiệm vụ ${detail.task_code || taskCode}`);
      setTxt("maintReportDeviceLabel", `${detail.device_code || "Thiết bị"} · ${detail.exact_location || detail.location_hub || ""}`);

      const photoImg = document.getElementById("maintDetailPhotoImg");
      const photoIcon = document.getElementById("maintDetailPhotoIcon");
      if (photoImg && photoIcon) {
        if (detail.photo_url) {
          StaffApi.fetchAttachmentBlobUrl(detail.photo_url)
            .then(url => {
              photoImg.src = url;
              photoImg.style.display = "block";
              photoIcon.style.display = "none";
            })
            .catch(() => {
              photoImg.style.display = "none";
              photoIcon.style.display = "block";
            });
        } else {
          photoImg.style.display = "none";
          photoIcon.style.display = "block";
        }
      }
    }

    this.goToScreen("screen-maint-detail");
  },

  async verifyScannedDevice() {
    const taskCode = this.currentMaintTaskCode || "MT-102";
    const qrCode = document.getElementById("maintScanCodeInput")?.value?.trim() || "BK-EB-018";
    try {
      const res = await StaffApi.verifyDevice(taskCode, qrCode);
      const statusEl = document.getElementById("maintScanStatusText");
      if (statusEl) statusEl.innerText = "ĐÃ XÁC THỰC";
      const titleEl = document.getElementById("maintVerifyBannerTitle");
      if (titleEl) titleEl.innerText = "Xác thực thành công";
      const descEl = document.getElementById("maintVerifyBannerDesc");
      if (descEl) descEl.innerText = res.message || `Đúng thiết bị ${qrCode}`;
      this.goToScreen("screen-maint-report");
    } catch (err) {
      alert("Xác thực thiết bị thất bại: " + (err.message || "Mã QR không khớp"));
    }
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
    this.maintOutcome = outcomeType === "workshop" ? "TRANSFER_TO_WORKSHOP" : "FIXED_ON_SITE";
    document.querySelectorAll(".radio-card-select").forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    const radio = card.querySelector("input[type='radio']");
    if (radio) radio.checked = true;
  },

  async submitMaintResult() {
    const taskCode = this.currentMaintTaskCode || "MT-102";
    const notes = document.getElementById("maintTechNotes") ? document.getElementById("maintTechNotes").value : "";
    let photoUrl = null;
    const photoInput = document.getElementById("maintPhotoFile");
    if (photoInput && photoInput.files && photoInput.files[0]) {
      try {
        const up = await StaffApi.uploadMaintenancePhoto(taskCode, photoInput.files[0]);
        if (up && up.photo_url) photoUrl = up.photo_url;
        photoInput.value = "";
        const lbl = document.getElementById("maintPhotoLabel");
        if (lbl) lbl.innerText = "ĐÍNH KÈM ẢNH PNG/JPEG";
      } catch (err) {
        alert("Lỗi upload ảnh hiện trường: " + (err.message || "Ảnh không hợp lệ"));
        return;
      }
    }

    const result = await StaffApi.resolveMaintenance({
      task_code: taskCode,
      outcome: this.maintOutcome || "FIXED_ON_SITE",
      technical_notes: notes,
      ...(photoUrl ? { photo_attachment_url: photoUrl } : {})
    });

    if (!result || !result.success) {
      alert((result && result.detail) || "Gửi kết quả bảo trì thất bại.");
      return;
    }
    alert(result.message);
    await this.loadMaintenanceTasks();
    this.goToScreen("screen-maint-list");
  },

  };
})(window);
