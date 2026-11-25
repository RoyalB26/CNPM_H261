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
        const photoBtn = t.photo_url
          ? `<button class="btn-secondary-light" style="padding: 5px 8px; font-size: 11.5px; margin-right: 4px;" onclick="OperatorApp.previewMaintenancePhoto('${t.photo_url}')"><i class="fa-regular fa-image"></i> Ảnh</button>`
          : "";
        return `
          <tr>
            <td><strong>${t.ticket_code}</strong></td>
            <td>${t.resource_code}</td>
            <td>${t.source || "Hệ thống"}</td>
            <td>${t.issue_type}</td>
            <td>${staffDisplay}</td>
            <td><span class="badge ${isAssigned ? 'badge-info' : (isUrgent ? 'badge-danger' : 'badge-warning')}">${t.status}</span></td>
            <td>${photoBtn}<button class="btn-primary-dark" style="padding: 5px 12px; font-size: 12px;" onclick="OperatorApp.openAssignMaintenanceModal('${t.ticket_code}')">${isAssigned ? 'Điều chỉnh NV' : 'Phân công'}</button></td>
          </tr>
        `;
      }).join("");
    },

    async previewMaintenancePhoto(photoUrl) {
      try {
        const blobUrl = await OperatorApi.fetchAttachmentBlobUrl(photoUrl);
        window.open(blobUrl, "_blank");
      } catch (err) {
        alert("Không thể tải ảnh đính kèm: " + (err.message || "Lỗi kết nối"));
      }
    },

    openCreateMaintenanceModal() {
      const m = document.getElementById("modalCreateMaintenance");
      if (m) m.classList.add("show");
    },

    async submitCreateMaintenance() {
      const hub_name = document.getElementById("createMaintHub")?.value || "Hub Ga Metro ĐHQG";
      const device_code = document.getElementById("createMaintDevice")?.value?.trim() || "";
      const fault_category = document.getElementById("createMaintFault")?.value?.trim() || "";
      const severity = document.getElementById("createMaintSeverity")?.value || "Cảnh báo";
      const assigned_staff_id = document.getElementById("createMaintStaff")?.value || null;
      const description = document.getElementById("createMaintDesc")?.value?.trim() || fault_category;

      if (!device_code || !fault_category) {
        alert("Vui lòng nhập đầy đủ mã thiết bị và phân loại lỗi.");
        return;
      }

      try {
        await OperatorApi.createMaintenanceTicket({
          device_code,
          hub_name,
          source: "Operator thủ công",
          fault_category,
          severity,
          description: description || "Kiểm tra thiết bị",
          assigned_staff_id: assigned_staff_id || null
        });
        this.closeModal("modalCreateMaintenance");
        alert(`Đã tạo phiếu bảo trì cho thiết bị ${device_code} thành công!`);
        await this.loadMaintenance();
      } catch (err) {
        alert("Không thể tạo phiếu bảo trì: " + (err.message || "Lỗi dữ liệu"));
      }
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
              <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11.5px; margin-right: 4px;" onclick="OperatorApp.openHubDevicesModal('${h.hub_id}', '${h.hub_name}')">Thiết bị</button>
              <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11.5px; color: var(--accent-red);" onclick="OperatorApp.openDeactivateModal('${h.hub_id}', '${h.hub_name}')">Tạm ngưng</button>
            </td>
          </tr>
        `;
      }).join("");
    },

    openCreateHubModal() {
      const m = document.getElementById("modalCreateHub");
      if (m) m.classList.add("show");
      setTimeout(() => this.initCreateHubPickerMap(), 80);
    },

    initCreateHubPickerMap() {
      const container = document.getElementById("createHubPickerMap");
      if (!container || typeof maplibregl === "undefined") return;

      const lat = parseFloat(document.getElementById("newHubLat")?.value || "10.8765") || 10.8765;
      const lng = parseFloat(document.getElementById("newHubLng")?.value || "106.7985") || 106.7985;

      if (this.createHubPickerMap) {
        try {
          this.createHubPickerMap.resize();
          this.createHubPickerMap.setCenter([lng, lat]);
          if (this.createHubPickerMarker) this.createHubPickerMarker.setLngLat([lng, lat]);
        } catch (e) {}
        return;
      }

      const mapCfg = (window.EMobilityConfig && window.EMobilityConfig.MAP_DEFAULTS) || {
        tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      };

      this.createHubPickerMap = new maplibregl.Map({
        container: "createHubPickerMap",
        style: {
          version: 8,
          sources: {
            "osm-tiles": {
              type: "raster",
              tiles: [mapCfg.tileUrl],
              tileSize: 256
            }
          },
          layers: [{ id: "osm-layer", type: "raster", source: "osm-tiles" }]
        },
        center: [lng, lat],
        zoom: 14.5
      });

      this.createHubPickerMap.addControl(new maplibregl.NavigationControl(), "top-right");

      const updateCoords = (newLng, newLat) => {
        const latEl = document.getElementById("newHubLat");
        const lngEl = document.getElementById("newHubLng");
        if (latEl) latEl.value = Number(newLat).toFixed(4);
        if (lngEl) lngEl.value = Number(newLng).toFixed(4);
      };

      this.createHubPickerMarker = new maplibregl.Marker({ draggable: true, color: "#0f172a" })
        .setLngLat([lng, lat])
        .addTo(this.createHubPickerMap);

      this.createHubPickerMarker.on("dragend", () => {
        const pos = this.createHubPickerMarker.getLngLat();
        updateCoords(pos.lng, pos.lat);
      });

      this.createHubPickerMap.on("click", (e) => {
        this.createHubPickerMarker.setLngLat([e.lngLat.lng, e.lngLat.lat]);
        updateCoords(e.lngLat.lng, e.lngLat.lat);
      });
    },

    syncCreateHubMarkerFromInputs() {
      const lat = parseFloat(document.getElementById("newHubLat")?.value);
      const lng = parseFloat(document.getElementById("newHubLng")?.value);
      if (Number.isNaN(lat) || Number.isNaN(lng)) return;
      if (this.createHubPickerMarker) {
        this.createHubPickerMarker.setLngLat([lng, lat]);
      }
      if (this.createHubPickerMap) {
        this.createHubPickerMap.flyTo({ center: [lng, lat] });
      }
    },

    async submitCreateHub() {
      const payload = {
        hub_code: document.getElementById("newHubCode")?.value?.trim() || "",
        name: document.getElementById("newHubName")?.value?.trim() || "",
        address: document.getElementById("newHubAddress")?.value?.trim() || "",
        lat: parseFloat(document.getElementById("newHubLat")?.value || "10.8765"),
        lng: parseFloat(document.getElementById("newHubLng")?.value || "106.7985"),
        parking_capacity: parseInt(document.getElementById("newHubParkingCap")?.value || "30", 10),
        charger_capacity: parseInt(document.getElementById("newHubChargerCap")?.value || "6", 10),
        max_power_kw: parseFloat(document.getElementById("newHubMaxPower")?.value || "120"),
        load_warning_threshold_pct: parseInt(document.getElementById("newHubThreshold")?.value || "85", 10)
      };
      if (!payload.hub_code || !payload.name || !payload.address) {
        alert("Vui lòng nhập đầy đủ mã Hub, tên Hub và địa chỉ.");
        return;
      }
      try {
        await OperatorApi.createHub(payload);
        this.closeModal("modalCreateHub");
        alert(`Đã tạo mới Hub "${payload.name}" thành công!`);
        await this.loadHubsConfig();
        if (typeof this.loadKpis === "function") await this.loadKpis();
        if (typeof this.refreshOverviewMapMarkers === "function") await this.refreshOverviewMapMarkers();
      } catch (err) {
        alert("Không thể tạo Hub: " + (err.message || "Lỗi dữ liệu"));
      }
    },

    async openHubDevicesModal(hubId, hubName) {
      this.currentDevicesHubId = hubId;
      const titleEl = document.getElementById("hubDevicesModalTitle");
      if (titleEl) titleEl.innerText = `THIẾT BỊ · ${hubName}`;
      const m = document.getElementById("modalHubDevices");
      if (m) m.classList.add("show");
      await this.loadHubDevicesList();
    },

    async loadHubDevicesList() {
      const tbody = document.getElementById("hubDevicesTableBody");
      if (!tbody || !this.currentDevicesHubId) return;
      try {
        const items = await OperatorApi.getHubDevices(this.currentDevicesHubId);
        if (!items.length) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 16px;">Hub này chưa có thiết bị nào.</td></tr>`;
          return;
        }
        tbody.innerHTML = items.map(d => {
          const isEnabled = !d.disabled;
          const label = d.name || d.battery_type || d.id;
          return `
            <tr>
              <td><strong>${d.id}</strong></td>
              <td>${d.kind}</td>
              <td>${label}</td>
              <td><span class="badge ${isEnabled ? 'badge-success' : 'badge-danger'}">${isEnabled ? (d.status || 'Bật') : 'Vô hiệu'}</span></td>
              <td>
                <button class="btn-secondary-light" style="padding: 3px 8px; font-size: 11px;" onclick="OperatorApp.toggleDeviceState('${d.kind}', '${d.id}', ${!isEnabled})">
                  ${isEnabled ? 'Tắt' : 'Bật'}
                </button>
              </td>
            </tr>
          `;
        }).join("");
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #dc2626; padding: 16px;">${err.message || 'Lỗi tải thiết bị'}</td></tr>`;
      }
    },

    async toggleDeviceState(kind, deviceId, enabled) {
      try {
        await OperatorApi.toggleHubDevice(this.currentDevicesHubId, kind, deviceId, enabled);
        await this.loadHubDevicesList();
      } catch (err) {
        alert("Không thể cập nhật thiết bị: " + (err.message || "Lỗi kết nối"));
      }
    },

    async submitCreateHubDevice() {
      if (!this.currentDevicesHubId) return;
      const kind = document.getElementById("newDeviceKind")?.value || "bike";
      const id = document.getElementById("newDeviceId")?.value?.trim() || "";
      const name = document.getElementById("newDeviceName")?.value?.trim() || "";
      const param = parseFloat(document.getElementById("newDeviceParam")?.value || "100");
      if (!id || !name) {
        alert("Vui lòng nhập mã thiết bị và tên hiển thị.");
        return;
      }
      const payload = { kind, id, name };
      if (kind === "port") payload.power_kw = param;
      else if (kind === "bike") payload.battery_level = Math.min(100, Math.max(0, Math.round(param)));
      else if (kind === "battery") payload.available_count = Math.max(1, Math.round(param));

      try {
        await OperatorApi.createHubDevice(this.currentDevicesHubId, payload);
        document.getElementById("newDeviceId").value = "";
        document.getElementById("newDeviceName").value = "";
        await this.loadHubDevicesList();
        await this.loadHubsConfig();
      } catch (err) {
        alert("Không thể thêm thiết bị: " + (err.message || "Lỗi dữ liệu"));
      }
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
