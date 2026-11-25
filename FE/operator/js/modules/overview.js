/**
 * @fileoverview Module Tổng quan Điều hành (Overview Module).
 * @module Operator/Modules/Overview
 * @description Quản lý OTP 2FA, chuyển Tab, KPIs, Bản đồ MapLibre, Telemetry & Dừng khẩn cấp.
 */
(function (global) {
  "use strict";
  global.OperatorModules = global.OperatorModules || {};

  global.OperatorModules.Overview = {
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

    async requestOtp() {
      const email = document.getElementById("loginEmail")?.value?.trim() || "admin@e-mobility.com";
      const password = document.getElementById("loginPassword")?.value || "";
      const statusEl = document.getElementById("loginChallengeStatus");
      try {
        const res = await OperatorApi.login(email, password);
        this.pendingChallengeId = res.challenge_id;
        if (statusEl) {
          statusEl.style.color = "#059669";
          statusEl.innerText = res.message || "Đã tạo phiên 2FA. Nhập mã TOTP từ ứng dụng Authenticator.";
        }
        return res.challenge_id;
      } catch (err) {
        if (statusEl) {
          statusEl.style.color = "#dc2626";
          statusEl.innerText = err.message || "Đăng nhập thất bại";
        }
        throw err;
      }
    },

    async completeLogin() {
      const email = document.getElementById("loginEmail")?.value?.trim() || "admin@e-mobility.com";
      const otpCode = Array.from(document.querySelectorAll(".otp-digit")).map(i => i.value.trim()).join("");
      const statusEl = document.getElementById("loginChallengeStatus");

      try {
        if (!this.pendingChallengeId) {
          await this.requestOtp();
        }
        await OperatorApi.verify2fa(email, this.pendingChallengeId, otpCode);
        this.pendingChallengeId = null;
        const v = document.getElementById("operatorLoginView");
        if (v) v.classList.remove("show");
        if (typeof this.loadDashboardData === "function") {
          await this.loadDashboardData();
        } else {
          await this.loadKpis();
        }
      } catch (err) {
        if (statusEl) {
          statusEl.style.color = "#dc2626";
          statusEl.innerText = err.message || "Xác thực 2FA thất bại";
        } else {
          alert(err.message || "Xác thực 2FA thất bại");
        }
      }
    },

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

      const elReloc = document.getElementById("kpiActiveRelocations");
      if (elReloc && data.active_relocations !== undefined) {
        elReloc.innerText = data.active_relocations;
      }
    },

    async initMap() {
      const container = document.getElementById("operatorMap");
      if (!container || typeof maplibregl === "undefined") return;

      try {
        const mapCfg = (window.EMobilityConfig && window.EMobilityConfig.MAP_DEFAULTS) || {
          center: [106.8005, 10.8753],
          operatorZoom: 13.8,
          tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        };

        this.map = new maplibregl.Map({
          container: "operatorMap",
          style: {
            version: 8,
            sources: {
              "osm-tiles": {
                type: "raster",
                tiles: [mapCfg.tileUrl],
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
          center: mapCfg.center,
          zoom: mapCfg.operatorZoom
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

            let relocInfo = "";
            if (Array.isArray(this.cachedRelocations)) {
              const rel = this.cachedRelocations.find(r =>
                (r.source_hub_name && (r.source_hub_name.includes(hub.name) || hub.name.includes(r.source_hub_name))) ||
                (r.target_hub_name && (r.target_hub_name.includes(hub.name) || hub.name.includes(r.target_hub_name)))
              );
              if (rel && !(rel.status || '').toLowerCase().includes('hoàn thành')) {
                relocInfo = `<div style="font-size: 11.5px; color: #2563eb; margin-bottom: 6px; font-weight: 600;"><i class="fa-solid fa-truck-fast"></i> Lệnh ${rel.id}: điều chuyển ${rel.bike_count || 5} xe</div>`;
              }
            }

            const popupHtml = `
              <div style="font-family: inherit; font-size: 13px; min-width: 190px; padding: 4px;">
                <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px;">${hub.name}</div>
                <div style="display: inline-block; padding: 2px 7px; font-size: 11px; font-weight: 700; border-radius: 4px; background: ${hub.is_high_load ? '#fee2e2' : '#dcfce7'}; color: ${hub.color}; margin-bottom: 8px;">
                  ${hub.status}
                </div>
                ${relocInfo}
                <div style="font-size: 12px; color: #475569; margin-bottom: 3px;">• ${hub.free_slots || hub.freeSlots}</div>
                <div style="font-size: 12px; color: #475569; margin-bottom: 3px;">• ${hub.chargers}/${hub.chargers_total || 50} cổng sạc rảnh</div>
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

    openTelemetryDrawer() {
      const d = document.getElementById("drawerTelemetry");
      if (d) d.classList.add("show");
    },

    async loadTelemetry() {
      const events = await OperatorApi.getTelemetry();
      if (!events) return;

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
    }
  };
})(window);
