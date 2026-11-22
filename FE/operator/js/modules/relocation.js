/**
 * @fileoverview Module Quản lý Điều phối Phương tiện (Relocation Module).
 * @module Operator/Modules/Relocation
 */
(function (global) {
  "use strict";
  global.OperatorModules = global.OperatorModules || {};

  global.OperatorModules.Relocation = {
    /**
     * Tải danh sách lệnh điều phối phương tiện từ Backend,
     * lưu vào bộ nhớ đệm và kết xuất vào bảng điều chuyển (`#relocationTableBody`).
     *
     * @async
     * @returns {Promise<void>}
     */
    async loadRelocations() {
      const raw = await OperatorApi.getRelocations();
      const list = Array.isArray(raw) ? raw : (raw && (raw.items || raw.commands)) || [];
      this.cachedRelocations = list;
      this.syncRelocationCommandsToOverview(this.cachedRelocations);

      const tbody = document.getElementById("relocationTableBody");
      if (!tbody) return;

      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">Chưa có lệnh điều phối nào.</td></tr>`;
        return;
      }

      tbody.innerHTML = list.map(item => {
        const statusStr = (item.status || "").toLowerCase();
        let badgeClass = "badge-warning";
        if (statusStr.includes("hoàn thành") || statusStr.includes("done") || statusStr.includes("completed")) {
          badgeClass = "badge-success";
        } else if (statusStr.includes("di chuyển") || statusStr.includes("running") || statusStr.includes("active") || statusStr.includes("transit")) {
          badgeClass = "badge-info";
        }

        let priorityBadge = '<span class="badge badge-info">Bình thường</span>';
        if (item.priority === "urgent" || item.priority === "Khẩn cấp" || item.priority === "high") {
          priorityBadge = '<span class="badge badge-danger">Khẩn cấp</span>';
        }

        const src = item.source_hub_name || item.source_hub || "N/A";
        const dst = item.target_hub_name || item.dest_hub || "N/A";
        const count = item.bike_count ?? item.vehicle_count ?? 5;
        const staff = item.assigned_staff_name ?? item.assigned_staff ?? "Chưa gán";
        const progress = item.progress_percent !== undefined
          ? `${item.progress_percent}%`
          : (item.progress_current !== undefined && item.progress_total !== undefined
              ? `${item.progress_current}/${item.progress_total} xe`
              : "Đang thực hiện");

        return `
          <tr>
            <td><strong>${item.id}</strong></td>
            <td>${src}</td>
            <td>${dst}</td>
            <td>${count} xe</td>
            <td>${progress}</td>
            <td>${staff}</td>
            <td>${priorityBadge}</td>
            <td><span class="badge ${badgeClass}">${item.status}</span></td>
            <td>
              <button class="btn-secondary-light" style="padding: 4px 10px; font-size: 12px;" onclick="alert('Lộ trình điều chuyển ${item.id}: ${src} -> ${dst} (${count} xe)')">
                Chi tiết
              </button>
            </td>
          </tr>
        `;
      }).join("");
    },

    /**
     * Đồng bộ danh sách lệnh điều phối đang hoạt động sang màn hình Tổng quan (`#tab-overview`).
     *
     * @param {Array<Object>} commands - Mảng các đối tượng lệnh điều chuyển xe.
     * @returns {void}
     */
    syncRelocationCommandsToOverview(commands) {
      const tbody = document.getElementById("overviewRelocationBody");
      const badge = document.getElementById("overviewRelocBadge");
      const kpiReloc = document.getElementById("kpiActiveRelocations");

      if (!commands || !commands.length) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">Không có lệnh điều phối nào đang hoạt động.</td></tr>`;
        if (badge) { badge.className = "badge badge-success"; badge.innerText = "Bình thường"; }
        if (kpiReloc) kpiReloc.innerText = "0";
        return;
      }

      const activeList = commands.filter(c => !(c.status || "").toLowerCase().includes("hoàn thành"));
      if (kpiReloc) kpiReloc.innerText = activeList.length;

      if (badge) {
        if (activeList.length > 0) {
          badge.className = "badge badge-info";
          badge.innerText = `${activeList.length} lệnh đang chạy`;
        } else {
          badge.className = "badge badge-success";
          badge.innerText = "Hoàn tất";
        }
      }

      if (!tbody) return;

      tbody.innerHTML = commands.map(cmd => {
        const statusStr = (cmd.status || "").toLowerCase();
        let badgeClass = "badge-warning";
        if (statusStr.includes("hoàn thành") || statusStr.includes("done") || statusStr.includes("completed")) {
          badgeClass = "badge-success";
        } else if (statusStr.includes("di chuyển") || statusStr.includes("running") || statusStr.includes("active") || statusStr.includes("transit")) {
          badgeClass = "badge-info";
        }

        let priorityBadge = '<span class="badge badge-info">Bình thường</span>';
        if (cmd.priority === "urgent" || cmd.priority === "Khẩn cấp" || cmd.priority === "high") {
          priorityBadge = '<span class="badge badge-danger">Khẩn cấp</span>';
        }

        const src = cmd.source_hub_name || cmd.source_hub || "Hub Ga Metro A";
        const dst = cmd.target_hub_name || cmd.dest_hub || "Hub KTX Khu B";
        const count = cmd.bike_count ?? cmd.vehicle_count ?? 10;
        const staff = cmd.assigned_staff_name ?? cmd.assigned_staff ?? "Đội cơ động A";
        const progress = cmd.progress_percent !== undefined
          ? `${cmd.progress_percent}%`
          : (cmd.progress_current !== undefined && cmd.progress_total !== undefined
              ? `${cmd.progress_current}/${cmd.progress_total} xe`
              : "Đang thực hiện");

        return `
          <tr>
            <td><strong>${cmd.id}</strong></td>
            <td>${src}</td>
            <td>${dst}</td>
            <td><strong>${count} xe</strong></td>
            <td>${progress}</td>
            <td>${staff}</td>
            <td>${priorityBadge}</td>
            <td><span class="badge ${badgeClass}">${cmd.status}</span></td>
            <td>
              <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11.5px;" onclick="OperatorApp.switchTab('tab-relocation')">
                Chi tiết
              </button>
            </td>
          </tr>
        `;
      }).join("");
    },

    /**
     * Mở hộp thoại modal Tạo lệnh điều phối xe mới (`#modalCreateRelocation`).
     *
     * @returns {void}
     */
    openCreateRelocationModal() {
      const m = document.getElementById("modalCreateRelocation");
      if (m) m.classList.add("show");
    },

    /**
     * Tên hàm viết tắt (alias) tương thích ngược.
     * @returns {void}
     */
    openCreateRelocModal() {
      this.openCreateRelocationModal();
    },

    /**
     * Gửi yêu cầu tạo lệnh điều chuyển mới qua `OperatorApi.createRelocation`
     * và tự động cập nhật lại bảng dữ liệu cũng như chỉ số KPIs.
     *
     * @async
     * @returns {Promise<void>}
     */
    async submitRelocation() {
      const sourceEl = document.getElementById("relocSourceHub") || document.getElementById("createRelocSource");
      const destEl = document.getElementById("relocDestHub") || document.getElementById("createRelocDest");
      const countEl = document.getElementById("relocCount") || document.getElementById("createRelocCount");
      const staffEl = document.getElementById("relocStaff");
      const priorityEl = document.getElementById("relocPriority") || document.getElementById("createRelocPriority");
      const notesEl = document.getElementById("relocNotes") || document.getElementById("createRelocReason");

      const src = sourceEl ? sourceEl.value : "hub-01";
      const dst = destEl ? destEl.value : "hub-02";
      const count = countEl ? (parseInt(countEl.value, 10) || 5) : 5;
      const staff = staffEl ? staffEl.value : "STF-01";
      const priority = priorityEl ? priorityEl.value : "Bình thường";
      const notes = notesEl ? notesEl.value : "Điều phối xe";

      const payload = {
        source_hub_id: src,
        target_hub_id: dst,
        bike_count: count,
        assigned_staff_id: staff,
        priority: priority,
        notes: notes
      };

      try {
        await OperatorApi.createRelocation(payload);
        this.closeModal("modalCreateRelocation");
        await this.loadRelocations();
        if (typeof this.loadKpis === "function") {
          await this.loadKpis();
        }
        alert(`Đã ban hành lệnh điều phối thành công!\nTừ ${src} đến ${dst} (${count} xe).`);
      } catch (err) {
        console.error("Lỗi khi tạo lệnh điều phối:", err);
        alert("Không thể tạo lệnh điều phối: " + (err.message || "Lỗi kết nối"));
      }
    },

    /**
     * Alias phương thức submitCreateRelocation tương thích ngược.
     * @async
     * @returns {Promise<void>}
     */
    async submitCreateRelocation() {
      return this.submitRelocation();
    }
  };
})(window);
