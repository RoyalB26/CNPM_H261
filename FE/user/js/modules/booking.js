/**
 * @fileoverview Module Đặt trước tài nguyên (Booking Module).
 * @module User/Modules/Booking
 */
(function (global) {
  "use strict";
  global.UserModules = global.UserModules || {};

  global.UserModules.Booking = {
  switchBookingTab(targetScreen) {
    this.navigateTo(targetScreen);
  },

  selectBike(bikeId, battery, elementId) {
    AppState.bookingDraft.selectedBike = bikeId;
    AppState.bookingDraft.bikeBattery = battery;

    document.querySelectorAll("#screen-select-bike .card-box").forEach(el => el.classList.remove("selected"));
    document.querySelectorAll("#screen-select-bike .radio-circle").forEach(el => el.classList.remove("checked"));

    const item = document.getElementById(elementId);
    if (item) {
      item.classList.add("selected");
      const r = item.querySelector(".radio-circle");
      if (r) r.classList.add("checked");
    }
    this.showToast(`Đã chọn xe ${bikeId} (${battery}%)`);
  },

  selectCharger(chargerName, elementId) {
    AppState.bookingDraft.chargingPort = chargerName;
    document.querySelectorAll("#screen-select-charging .card-box").forEach(el => el.classList.remove("selected"));
    document.querySelectorAll("#screen-select-charging .radio-circle").forEach(el => el.classList.remove("checked"));

    const item = document.getElementById(elementId);
    if (item) {
      item.classList.add("selected");
      const r = item.querySelector(".radio-circle");
      if (r) r.classList.add("checked");
    }
  },

  async confirmBooking(planType) {
    if (planType === "swap") {
      return this.confirmSwapAndPay();
    }
    if (planType === "rental") {
      return this.confirmRental();
    }
    const payload = {
      plan_type: planType,
      hub_id: AppState.bookingDraft.hubId,
      personal_plate: AppState.bookingDraft.personalPlate,
      services: [
        {
          service_type: planType,
          detail: "Chỗ đỗ + Sạc",
          price_est: 20000
        }
      ]
    };

    const newBooking = await ApiService.createBooking(payload);
    AppState.bookings.unshift(newBooking);

    const successIdEl = document.getElementById("successBookingId");
    if (successIdEl) successIdEl.innerText = `Mã đặt: ${newBooking.id || 'EMH-1024'}`;

    this.showToast("Đặt chỗ giữ tài nguyên thành công!");
    this.navigateTo("screen-booking-success");
  },

  /**
   * Alias xác nhận thuê xe tương thích ngược.
   * @async
   * @returns {Promise<void>}
   */
  async confirmRentalAndPay() {
    return this.confirmRental();
  },

  async confirmRental() {
    const destHubName = document.getElementById("selectDestHub") 
      ? document.getElementById("selectDestHub").value 
      : "Hub Đại học Bách khoa";

    const payload = {
      plan_type: "rental",
      hub_id: AppState.bookingDraft.hubId || "hub-01",
      destination_hub_name: destHubName,
      personal_plate: null,
      resource_name: `${AppState.bookingDraft.selectedBike || "XE-024"} · Xe đạp điện`,
      services: [
        {
          service_type: "rental",
          detail: `Thuê xe đạp điện ${AppState.bookingDraft.selectedBike || 'XE-024'} (Pin ${AppState.bookingDraft.bikeBattery || 85}%)`,
          price_est: 10000
        }
      ]
    };

    let newBooking = null;
    try {
      newBooking = await ApiService.createBooking(payload);
      if (newBooking) {
        AppState.bookings.unshift(newBooking);
        AppState.selectedBookingId = newBooking.id;
      }
    } catch (e) {
      console.warn("createBooking error:", e);
      this.showToast(e.message || "Tài nguyên không khả dụng, vui lòng chọn lại.");
      return;
    }

    const bookingCode = newBooking && newBooking.id ? newBooking.id : "EMH-1025";
    const successIdEl = document.getElementById("successBookingId");
    if (successIdEl) successIdEl.innerText = `Mã đặt: ${bookingCode}`;
    const successHubEl = document.getElementById("successBookingHub");
    if (successHubEl) successHubEl.innerText = (newBooking && newBooking.hub_name) || AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";
    const successHoldEl = document.getElementById("successBookingHoldUntil");
    if (successHoldEl) successHoldEl.innerText = (newBooking && (newBooking.hold_until || newBooking.holdUntil)) || "15 phút";

    this.showToast("Đặt xe thành công! Xe đã được giữ trước cho bạn.");
    this.renderBookings();
    this.navigateTo("screen-booking-success");
  },

  payAndStartRide() {
    this.showToast("Đang chuyển sang thanh toán cước thuê xe...");
    this.setupInvoiceAndPay("rental", 10000, "screen-vehicle-ready", true);
  },

  async confirmSwapAndPay() {
    const payload = {
      plan_type: "swap",
      hub_id: AppState.bookingDraft.hubId || "HUB-METRO",
      personal_plate: AppState.bookingDraft.personalPlate || "59-X1 123.45",
      services: [
        {
          service_type: "swap",
          detail: "Đổi pin xe điện B48 (2 pin)",
          price_est: 25000
        }
      ]
    };

    try {
      const newBooking = await ApiService.createBooking(payload);
      AppState.bookings.unshift(newBooking);
    } catch (e) {}

    this.showToast("Đã xác nhận đặt pin. Đang chuyển sang thanh toán...");
    this.setupInvoiceAndPay("swap", 25000, "screen-review-swap", false);
  },

  async executeCancelBooking() {
    const targetId = AppState.selectedBookingId || "EMH-1023";
    try {
      await ApiService.cancelBooking(targetId);
      const found = AppState.bookings.find(b => b.id === targetId);
      if (found) {
        found.status = "Đã hủy";
      }
    } catch (e) {
      console.warn("Cancel booking error:", e);
    }
    this.showToast(`Đã hủy đặt chỗ ${targetId} thành công.`);
    // Immediately remove from screen-my-bookings
    this.renderBookings();
    // Immediately display in screen-booking-history
    this.renderBookingHistory();
    this.navigateTo("screen-cancelled");
  },

  async loadBookings() {
    try {
      const bookings = await ApiService.getBookings();
      if (bookings && bookings.length) {
        const cancelledIds = (AppState.bookings || [])
          .filter(b => b.status === "Đã hủy")
          .map(b => b.id);

        AppState.bookings = bookings.map(b => {
          if (cancelledIds.includes(b.id)) {
            return { ...b, status: "Đã hủy" };
          }
          return b;
        });
      }
    } catch (e) {
      console.warn("Could not load bookings from BE:", e);
    }
    this.renderBookings();
    this.renderBookingHistory();
  },

  renderBookings() {
    const container = document.getElementById("bookingCardsContainer");
    if (!container) return;

    // Filter out cancelled bookings so they NO LONGER appear in screen-my-bookings
    const activeList = (AppState.bookings || []).filter(b => b.status !== "Đã hủy" && b.status !== "Hoàn thành" && b.status !== "Đã hoàn thành");

    if (activeList.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-regular fa-calendar-xmark" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
          <div style="font-weight: 600;">Bạn không có đặt chỗ nào sắp tới</div>
          <div style="font-size: 12px; margin-top: 4px;">Các đơn đã hủy hoặc hoàn tất đã được lưu trong tab "Lịch sử".</div>
          <button class="btn-secondary" style="margin-top: 14px; font-size: 12px; border-radius: 20px;" onclick="App.navigateTo('screen-booking-history')">Xem lịch sử đặt chỗ</button>
        </div>
      `;
      return;
    }

    container.innerHTML = activeList.map(bk => {
      const isRental = bk.plan_type === "rental" || bk.planType === "rental";
      const isSwap = bk.plan_type === "swap" || bk.planType === "swap";
      const planTitle = isRental ? "Thuê xe" : (isSwap ? "Đổi pin" : "Xe cá nhân");
      const resourceText = bk.resource_name || (bk.services && bk.services[0] ? bk.services[0].detail : (bk.personal_plate ? `Biển số: ${bk.personal_plate}` : 'Tài nguyên đã đặt'));
      const hubText = bk.hub_name || bk.hubName || "Hub Ga Metro ĐHQG";
      const holdText = bk.hold_until ? `Giữ đến ${bk.hold_until}` : (bk.created_at || "Đã xác nhận");
      const statusText = bk.status || "Đã xác nhận";

      return `
        <div class="card-box" style="margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 800; font-size: 14.5px;">${bk.id} · ${planTitle}</span>
            <span style="font-size: 11px; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 4px; font-weight: 600;">${statusText}</span>
          </div>
          <div style="font-size: 13px; margin-bottom: 4px;">${resourceText} · ${hubText}</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px;">${holdText}</div>
          <button class="${isRental ? 'btn-primary' : 'btn-secondary'}" onclick="App.openBookingDetail('${bk.id}')">${isRental ? 'Chi tiết và nhận xe' : 'Xem chi tiết đặt trước'}</button>
        </div>
      `;
    }).join("");
  },

  renderBookingHistory() {
    const container = document.getElementById("bookingHistoryContainer");
    if (!container) return;

    // Collect all cancelled bookings from AppState.bookings
    const cancelledFromBookings = (AppState.bookings || [])
      .filter(b => b.status === "Đã hủy")
      .map(b => ({
        id: b.id,
        planType: b.plan_type || b.planType || "rental",
        hubName: b.hub_name || b.hubName || "Hub Ga Metro ĐHQG",
        resourceName: b.resource_name || (b.services && b.services[0] ? b.services[0].detail : "Tài nguyên"),
        status: "Đã hủy",
        createdAt: b.created_at || "18/10/2026",
        totalPrice: b.total_price || 0
      }));

    // Combine with historyBookings without duplicating by id
    const existingIds = new Set(cancelledFromBookings.map(b => b.id));
    const otherHistory = (AppState.historyBookings || []).filter(b => !existingIds.has(b.id));

    const combinedList = [...cancelledFromBookings, ...otherHistory];

    if (combinedList.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-regular fa-clock" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
          <div style="font-weight: 600;">Chưa có lịch sử đặt chỗ</div>
          <div style="font-size: 12px; margin-top: 4px;">Lịch sử chuyến đi và các đơn đã hủy sẽ hiển thị tại đây.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = combinedList.map(item => {
      const isCancelled = item.status === "Đã hủy";
      const statusBadge = isCancelled 
        ? `<span style="font-size: 11px; background: #fee2e2; color: #ef4444; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Đã hủy</span>`
        : `<span style="font-size: 11px; background: #ecfdf5; color: #10b981; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Hoàn thành</span>`;
      
      const typeLabel = item.planType === "rental" ? "Thuê xe" : (item.planType === "swap" ? "Đổi pin" : "Đỗ xe cá nhân");
      const detailText = isCancelled 
        ? `${item.createdAt || '18/10/2026'} · Đã hủy & hoàn tài nguyên`
        : `${item.createdAt || 'Gần đây'} · ${(item.totalPrice || 15000).toLocaleString()}đ`;

      return `
        <div class="card-box" style="margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; font-size: 14px;">${item.id} · ${typeLabel}</span>
            ${statusBadge}
          </div>
          <div style="font-size: 13px; margin-bottom: 3px;">${item.resourceName || item.hubName || 'Hub Ga Metro ĐHQG'}</div>
          <div style="font-size: 12px; color: var(--text-muted);">${detailText}</div>
        </div>
      `;
    }).join("");
  },

  openBookingDetail(bookingId) {
    const bk = AppState.bookings.find(b => b.id === bookingId) || AppState.bookings[0];
    if (!bk) return;

    AppState.selectedBookingId = bk.id;

    const subEl = document.getElementById("bookingDetailSubtitle");
    if (subEl) {
      const typeLabel = bk.plan_type === "rental" || bk.planType === "rental" ? "Xe dùng chung" : (bk.plan_type === "swap" ? "Đổi pin" : "Xe cá nhân");
      subEl.innerText = `${bk.id} · ${typeLabel}`;
    }

    const stEl = document.getElementById("bookingDetailStatus");
    if (stEl) {
      stEl.innerText = bk.status || "Đã xác nhận";
      if (bk.status === "Đã hủy") {
        stEl.style.borderColor = "#ef4444";
        stEl.style.color = "#ef4444";
      } else {
        stEl.style.borderColor = "#0f172a";
        stEl.style.color = "#0f172a";
      }
    }

    const resEl = document.getElementById("bookingDetailResource");
    if (resEl) {
      resEl.innerText = bk.resource_name || (bk.services && bk.services[0] ? bk.services[0].detail : "XE-024 · Pin 85%");
    }

    const origEl = document.getElementById("bookingDetailOriginHub");
    if (origEl) origEl.innerText = bk.hub_name || bk.hubName || "Hub Ga Metro ĐHQG";

    const destEl = document.getElementById("bookingDetailDestHub");
    if (destEl) destEl.innerText = bk.destination_hub_name || "ĐH Bách khoa";

    const timeEl = document.getElementById("bookingDetailTime");
    if (timeEl) timeEl.innerText = bk.created_at || "08:00";

    const holdEl = document.getElementById("bookingDetailHoldUntil");
    if (holdEl) holdEl.innerText = bk.hold_until || "08:10";

    this.navigateTo("screen-booking-detail");
  },

  switchBookingListTab(tab) {
    document.getElementById("tabBookingUpcoming").classList.toggle("active", tab === "upcoming");
    document.getElementById("tabBookingActive").classList.toggle("active", tab === "active");
    document.getElementById("tabBookingHistory").classList.toggle("active", tab === "history");

    if (tab === "history") {
      this.navigateTo("screen-booking-history");
    } else if (tab === "active") {
      this.navigateTo("screen-active-services");
    }
  },

  async loadChargingSchedules() {
    const listEl = document.getElementById("userChargingSchedulesList");
    if (!listEl) return;
    try {
      const items = await ApiService.getChargingSchedules();
      if (!items.length) {
        listEl.innerHTML = "Chưa có lịch sạc nào.";
        return;
      }
      listEl.innerHTML = items.map(s => `
        <div style="border-top: 1px solid var(--border-color); padding: 8px 0; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
          <div>
            <strong>${s.id}</strong> · ${s.hub_id} (${s.port_id || "Hàng đợi"})<br>
            <span>${(s.starts_at || "").slice(11, 16)} - ${(s.ends_at || "").slice(11, 16)} · ${s.status}</span>
          </div>
          <div style="display: flex; gap: 4px;">
            ${s.status === "RESERVED" ? `<button type="button" class="btn-primary" style="padding: 4px 8px; font-size: 11px; width: auto;" onclick="App.runChargingScheduleAction('${s.id}', 'start')">Sạc</button>` : ""}
            ${["RESERVED", "WAITING"].includes(s.status) ? `<button type="button" class="btn-secondary" style="padding: 4px 8px; font-size: 11px; width: auto;" onclick="App.runChargingScheduleAction('${s.id}', 'cancel')">Hủy</button>` : ""}
          </div>
        </div>
      `).join("");
    } catch (e) {
      listEl.innerHTML = "Đăng nhập để xem lịch sạc.";
    }
  },

  async submitChargingSchedule() {
    const hubId = AppState.bookingDraft.hubId || "hub-01";
    const plate = (document.getElementById("chargingPersonalVehicle")?.value || "59-X1 123.45").split("·").pop().trim();
    const offsetMin = Math.max(0, parseInt(document.getElementById("schedStartOffsetMin")?.value || "15", 10));
    const batteryPct = Math.min(100, Math.max(0, parseInt(document.getElementById("schedBatteryPct")?.value || "35", 10)));
    const start = new Date(Date.now() + offsetMin * 60000);
    const end = new Date(start.getTime() + 60 * 60000);
    try {
      const row = await ApiService.createChargingSchedule({
        hub_id: hubId,
        port_id: null,
        plate_number: plate,
        starts_at: start.toISOString(),
        ends_at: end.toISOString(),
        battery_pct: batteryPct,
        join_queue: true
      });
      this.showToast(`Đã đặt lịch sạc ${row.id} (${row.status})!`);
      await this.loadChargingSchedules();
    } catch (err) {
      this.showToast(err.message || "Không thể đặt lịch sạc.");
    }
  },

  async runChargingScheduleAction(scheduleId, action) {
    try {
      const res = await ApiService.actionChargingSchedule(scheduleId, action);
      this.showToast(action === "start" ? "Đã bắt đầu phiên sạc theo lịch!" : "Đã hủy lịch sạc.");
      await this.loadChargingSchedules();
      if (action === "start" && res && res.booking_id) {
        await this.loadActiveServices();
        this.navigateTo("screen-charging-active");
      }
    } catch (err) {
      this.showToast(err.message || "Thao tác lịch sạc thất bại.");
    }
  },

  };
})(window);
