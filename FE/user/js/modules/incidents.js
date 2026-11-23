/**
 * @fileoverview Module Báo cáo sự cố thiết bị (Incident Reporting) & Tra cứu Lịch sử sự cố.
 * @module User/Modules/Incidents
 * @description
 * File này định nghĩa `UserModules.Incidents`, cung cấp các chức năng:
 * - Tải danh sách sự cố đã gửi từ Backend (`loadIncidents`) và kết xuất lên màn hình `screen-incident-history`.
 * - Xem chi tiết trạng thái xử lý và phản hồi từ Trung tâm Điều hành (`openIncidentDetail`).
 * - Điền sẵn thông tin mã thiết bị hỏng (`prepareReport`) và gửi báo cáo sự cố mới (`handleIncidentSubmit`).
 */
(function (global) {
  global.UserModules = global.UserModules || {};

  /**
   * Tập hợp các phương thức báo cáo và theo dõi sự cố của End-User.
   * @namespace UserModules.Incidents
   */
  global.UserModules.Incidents = {
    /**
     * Tải danh sách các báo cáo sự cố từ Backend (`ApiService.getIncidents`)
     * và kết xuất lên giao diện.
     *
     * @async
     * @returns {Promise<void>}
     */
    async loadIncidents() {
      try {
        const incidents = await ApiService.getIncidents();
        if (incidents && incidents.length) {
          AppState.incidents = incidents;
        }
      } catch (e) {
        console.warn("Could not load incidents:", e);
      }
      this.renderIncidents();
    },

    /**
     * Kết xuất danh sách lịch sử các phiếu báo cáo sự cố vào `#incidentHistoryList`
     * trên màn hình `screen-incident-history`.
     *
     * @returns {void}
     */
    renderIncidents() {
      const container = document.getElementById("incidentHistoryList");
      if (!container) return;

      if (!AppState.incidents || AppState.incidents.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
            <i class="fa-solid fa-clipboard-check" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
            <div style="font-weight: 600;">Không có sự cố nào</div>
            <div style="font-size: 12px; margin-top: 4px;">Mọi thiết bị đang hoạt động ổn định!</div>
          </div>
        `;
        return;
      }

      container.innerHTML = AppState.incidents.map(inc => {
        const isResolved = inc.status === "Đã giải quyết";
        const statusColor = isResolved ? "#059669" : "#d97706";
        const statusBg = isResolved ? "#ecfdf5" : "#fef3c7";
        const resCode = inc.resource_code || inc.resourceCode || "Thiết bị";
        const incType = inc.incident_type || inc.incidentType || "Sự cố";
        const rawDate = inc.created_at || inc.createdAt || "Hôm nay";
        let dateStr = rawDate;
        if (typeof rawDate === "string" && rawDate.includes("T")) {
          const parsed = new Date(rawDate);
          if (!Number.isNaN(parsed.getTime())) {
            dateStr = parsed.toLocaleString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
              day: "2-digit",
              month: "2-digit",
              year: "numeric"
            });
          }
        }

        return `
          <div class="card-box" style="cursor: pointer; margin-bottom: 12px;" onclick="App.openIncidentDetail('${inc.id}')">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 8px;">
              <div style="font-weight: 700; font-size: 14px; word-break: break-word;">${inc.id} · ${resCode}</div>
              <span style="font-size: 11.5px; color: ${statusColor}; background: ${statusBg}; padding: 3px 8px; border-radius: 6px; font-weight: 700; white-space: nowrap; flex-shrink: 0;">${inc.status}</span>
            </div>
            <div style="font-size: 12.5px; color: var(--text-muted);">${incType} · ${dateStr}</div>
          </div>
        `;
      }).join("");
    },

    /**
     * Mở màn hình chi tiết phiếu báo cáo sự cố (`screen-report-detail`) và hiển thị
     * trạng thái xử lý cùng ghi chú phản hồi từ Operator.
     *
     * @param {string} incId - Mã định danh của phiếu báo cáo sự cố.
     * @returns {void}
     */
    openIncidentDetail(incId) {
      const inc = AppState.incidents.find(i => i.id === incId) || AppState.incidents[0];
      if (!inc) return;

      const idEl = document.getElementById("reportDetailId");
      if (idEl) idEl.innerText = inc.id;

      const stEl = document.getElementById("reportDetailStatus");
      if (stEl) {
        stEl.innerText = inc.status;
        const isResolved = inc.status === "Đã giải quyết";
        stEl.style.background = isResolved ? "#ecfdf5" : "#fef3c7";
        stEl.style.color = isResolved ? "#10b981" : "#d97706";
      }

      const resEl = document.getElementById("reportDetailResource");
      if (resEl) resEl.innerText = `${inc.resource_code || inc.resourceCode} (${inc.resource_type || inc.resourceType || 'Thiết bị'})`;

      const hubEl = document.getElementById("reportDetailHub");
      if (hubEl) hubEl.innerText = inc.hub_name || inc.hubName || "Hub Ga Metro ĐHQG";

      const issueEl = document.getElementById("reportDetailIssue");
      if (issueEl) issueEl.innerText = `${inc.incident_type || inc.incidentType} - ${inc.description}`;

      const noteEl = document.getElementById("reportDetailOperatorNote");
      if (noteEl) noteEl.innerText = inc.operator_note || inc.operatorNote || "Đã tiếp nhận yêu cầu, kỹ thuật viên đang đến kiểm tra thiết bị.";

      this.navigateTo("screen-report-detail");
    },

    /**
     * Điền sẵn loại tài nguyên và mã thiết bị vào biểu mẫu báo cáo sự cố
     * rồi chuyển tới màn hình `screen-report-incident`.
     *
     * @param {string} resourceType - Loại thiết bị gặp sự cố (ví dụ: `"Phương tiện"`, `"Cổng sạc"`).
     * @param {string} resourceCode - Mã định danh thiết bị (ví dụ: `"XE-024"`, `"S03"`).
     * @returns {void}
     */
    prepareReport(resourceType, resourceCode) {
      const typeSelect = document.getElementById("incResourceType");
      const codeInput = document.getElementById("incResourceCode");
      if (typeSelect) typeSelect.value = resourceType;
      if (codeInput) codeInput.value = resourceCode;
      this.navigateTo("screen-report-incident");
    },

    /**
     * Xử lý sự kiện gửi biểu mẫu báo cáo sự cố mới lên Backend (`ApiService.reportIncident`),
     * thêm phiếu mới vào danh sách và điều hướng sang màn hình xác nhận đã gửi (`screen-report-sent`).
     *
     * @async
     * @param {Event} [e] - Sự kiện submit form.
     * @returns {Promise<void>}
     */
    async handleIncidentSubmit(e) {
      if (e) e.preventDefault();
      const type = document.getElementById("incResourceType").value;
      const code = document.getElementById("incResourceCode").value;
      const hub = document.getElementById("incHubName").value;
      const incType = document.getElementById("incType").value;
      const desc = document.getElementById("incDescription").value;

      const payload = {
        resource_type: type,
        resource_code: code,
        hub_name: hub,
        incident_type: incType,
        description: desc
      };

      const newInc = await ApiService.reportIncident(payload);
      AppState.incidents.unshift(newInc);

      const sentIdEl = document.getElementById("createdIncidentId");
      if (sentIdEl) sentIdEl.innerText = newInc.id;

      this.renderIncidents();
      this.showToast("Đã gửi báo cáo đến Operator.");
      this.navigateTo("screen-report-sent");
    }
  };
})(window);
