/**
 * @fileoverview Module Dịch vụ đang hoạt động & Vận hành (Active Services Module).
 * @module User/Modules/ActiveServices
 */
(function (global) {
  "use strict";
  global.UserModules = global.UserModules || {};

  global.UserModules.ActiveServices = {
  async loadActiveServices() {
    try {
      const active = await ApiService.getActiveServices();
      if (active) {
        AppState.activeServices = {
          ...active,
          has_active: Boolean(active.ride || active.parking || active.charging)
        };
        // Đồng bộ cache cũ; parking=null từ BE phải xóa phiên đã checkout.
        AppState.activeRide = active.ride ?? null;
        AppState.activeParking = active.parking ?? null;
        AppState.activeCharging = active.charging ?? null;
        this.renderActiveServices(active);
      }
    } catch (e) {
      console.warn("Could not load active services:", e);
      const container = document.getElementById("activeServicesContainer");
      if (container) {
        container.innerHTML = `
          <div class="card-box" style="text-align: center;">
            <p>Chưa tải được trạng thái dịch vụ. Vui lòng kiểm tra kết nối hoặc đăng nhập lại.</p>
            <button class="btn-secondary" onclick="App.loadActiveServices()">Thử lại</button>
          </div>
        `;
      }
    }
  },

  renderActiveServices(data) {
    const container = document.getElementById("activeServicesContainer");
    if (!container || !data) return;

    // Dynamically update map bottom floating pill
    const pill = document.getElementById("activeRidePill");
    if (pill) {
      if (data.ride) {
        pill.style.display = "flex";
        const pillText = document.getElementById("activeRidePillText");
        if (pillText) {
          pillText.innerText = `Chuyến đi: ${data.ride.vehicle_id || data.ride.vehicleId} đang hoạt động`;
        }
      } else {
        pill.style.display = "none";
      }
    }

    let items = [];
    if (data.ride) {
      items.push(`
        <div class="card-box selectable" onclick="App.navigateTo('screen-ride-active')">
          <div>
            <div style="font-weight: 700; font-size: 14px;">Xe đạp điện ${data.ride.vehicle_id || data.ride.vehicleId}</div>
            <div style="font-size: 12px; color: var(--text-muted);">${data.ride.status || 'Đang sử dụng'} · ${data.ride.elapsed_minutes ?? data.ride.elapsedMinutes ?? 0} phút</div>
          </div>
          <span style="font-size: 11px; background: #ecfdf5; color: #10b981; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Hoạt động</span>
        </div>
      `);

      const rideSub = document.getElementById("rideActiveSubtitle");
      if (rideSub) rideSub.innerText = `${data.ride.vehicle_id || data.ride.vehicleId} · ${data.ride.origin_hub || data.ride.originHub} → ${data.ride.destination_hub || data.ride.destHub}`;
      const timerEl = document.getElementById("rideTimer");
      if (timerEl) this.updateRideClock();
      const batEl = document.getElementById("rideBatteryLevel");
      if (batEl) batEl.innerText = `${data.ride.battery_level ?? data.ride.batteryLevel ?? 0}%`;
      const stEl = document.getElementById("rideStatusBadge");
      if (stEl) stEl.innerText = data.ride.status || "Đang sử dụng";
    }

    if (data.parking) {
      items.push(`
        <div class="card-box selectable" onclick="App.navigateTo('screen-parking-active')">
          <div>
            <div style="font-weight: 700; font-size: 14px;">Gửi xe cá nhân (${data.parking.plate_number || data.parking.plate})</div>
            <div style="font-size: 12px; color: var(--text-muted);">Chỗ đỗ ${data.parking.slot_id || data.parking.slot} · ${data.parking.elapsed_minutes || data.parking.elapsedMinutes || 45} phút</div>
          </div>
          <span style="font-size: 11px; background: #e0f2fe; color: #0284c7; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Đang đỗ</span>
        </div>
      `);

      const parkSub = document.getElementById("parkingActiveSubtitle");
      if (parkSub) parkSub.innerText = `${data.parking.ticket_id || "Vé gửi xe"} · ${data.parking.hub_name || data.parking.hubName}`;
      const parkPlate = document.getElementById("parkingActivePlate");
      if (parkPlate) parkPlate.innerText = data.parking.plate_number || data.parking.plate;
      const parkSlot = document.getElementById("parkingActiveSlot");
      if (parkSlot) parkSlot.innerText = data.parking.slot_id || data.parking.slot;
      const parkIn = document.getElementById("parkingActiveCheckin");
      if (parkIn) parkIn.innerText = data.parking.checkin_time || data.parking.checkin || "10:00";
    }

    if (data.charging) {
      items.push(`
        <div class="card-box selectable" onclick="App.navigateTo('screen-charging-active')">
          <div>
            <div style="font-weight: 700; font-size: 14px;">Sạc trụ nhanh ${data.charging.port_id || data.charging.port}</div>
            <div style="font-size: 12px; color: var(--text-muted);">Đã nạp ${data.charging.power_consumed_kwh || data.charging.powerConsumed || 2.4} kWh · ${data.charging.current_charge || data.charging.batteryPercent || 65}%</div>
          </div>
          <span style="font-size: 11px; background: #fef3c7; color: #d97706; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Đang sạc</span>
        </div>
      `);

      const chgPort = document.getElementById("chargingActivePort");
      if (chgPort) chgPort.innerText = `Trụ sạc ${data.charging.port_id || data.charging.port}`;
      const chgPct = document.getElementById("chargingActivePercent");
      if (chgPct) chgPct.innerText = `${data.charging.current_charge || data.charging.batteryPercent || 65}%`;
      const chgPwr = document.getElementById("chargingActivePower");
      if (chgPwr) chgPwr.innerText = `${data.charging.power_consumed_kwh || data.charging.powerConsumed || 2.4} kWh`;
      const chgTime = document.getElementById("chargingActiveTime");
      if (chgTime) chgTime.innerText = `${data.charging.elapsed_minutes || data.charging.elapsedMinutes || 25} phút`;
    }

    if (items.length > 0) {
      container.innerHTML = items.join("");
    } else {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-solid fa-bolt" style="font-size: 30px; margin-bottom: 10px; opacity: 0.4;"></i>
          <div style="font-weight: 600;">Chưa có dịch vụ nào đang hoạt động</div>
        </div>
      `;
    }
  },

  updateReviewRentalView() {
    const bike = AppState.bookingDraft.selectedBike || "XE-024";
    const batt = AppState.bookingDraft.bikeBattery || 85;
    const origin = AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";
    const destSelect = document.getElementById("selectDestHub");
    const dest = destSelect ? destSelect.value : "Hub Đại học Bách khoa";

    const rBike = document.getElementById("reviewRentalBike");
    if (rBike) rBike.innerText = `${bike} (Pin ${batt}%)`;
    const rOrig = document.getElementById("reviewRentalOriginHub");
    if (rOrig) rOrig.innerText = origin;
    const rDest = document.getElementById("reviewRentalDestHub");
    if (rDest) rDest.innerText = dest;
    const rNote = document.getElementById("reviewRentalPolicyNote");
    if (rNote) rNote.innerText = `Thời gian giữ xe: 10 phút sau khi xác nhận. Cước phí tạm tính: 10,000đ/giờ (thanh toán khi quét mã mở xe tại Hub).`;
  },

  updateReviewParkingView() {
    const plateEl = document.getElementById("parkingPersonalVehicle");
    const plate = plateEl ? plateEl.value : "Xe máy điện · 59-X1 123.45";
    const timeEl = document.getElementById("parkingArrivalTime");
    const time = timeEl ? timeEl.value : "18/10/2026 · 10:00";
    const durEl = document.getElementById("parkingDuration");
    const dur = durEl ? durEl.value : "2 giờ";
    const hub = AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";

    const rPlate = document.getElementById("reviewParkingPlate");
    if (rPlate) rPlate.innerText = plate;
    const rSlot = document.getElementById("reviewParkingSlotHub");
    if (rSlot) rSlot.innerText = `Chỗ đỗ khả dụng (${hub})`;
    const rTime = document.getElementById("reviewParkingTime");
    if (rTime) rTime.innerText = `${time} (${dur})`;
  },

  updateReviewSwapView() {
    const typeEl = document.getElementById("swapBatteryType");
    const bType = typeEl ? typeEl.value : "Pin chuẩn 48V-20Ah";
    const qtyEl = document.getElementById("swapBatteryQuantity");
    const qty = qtyEl ? qtyEl.value : "1 pin";
    const hub = AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";

    const rType = document.getElementById("reviewSwapType");
    if (rType) rType.innerText = `${bType} (${qty})`;
    const rHub = document.getElementById("reviewSwapHub");
    if (rHub) rHub.innerText = `Tủ pin ${hub}`;
    const rFee = document.getElementById("reviewSwapFee");
    if (rFee) rFee.innerText = `${(25000 * (parseInt(qty) || 1)).toLocaleString()}đ / lần`;
  },

  async startRide() {
    const bookingId = AppState.selectedBookingId;

    if (!bookingId) {
      this.showToast("Không tìm thấy mã đặt xe!");
      return;
    }

    try {
      // Gọi API Backend
      const result = await ApiService.startRide(bookingId);

      // Cập nhật dữ liệu chuyến đi trên Frontend
      AppState.activeServices = {
        ...AppState.activeServices,
        has_active: true,
        ride: result.ride
      };

      AppState.activeRide = result.ride;
      // Chuyến mới không dùng lại hóa đơn hoặc mã chuyến đã trả trước đó.
      AppState.lastReturnedTripId = null;
      AppState.currentInvoice = {
        ...AppState.currentInvoice, type: "rental", id: null, amount: 0,
        trip_id: null, startRideOnSuccess: false
      };

      // Cập nhật trạng thái Booking
      const booking = AppState.bookings.find(
        b => b.id === bookingId
      );

      if (booking) {
        booking.status = "Đang sử dụng";
      }

      this.renderActiveServices(AppState.activeServices);
      // Chỉ chuyển màn hình khi Backend thành công
      this.showToast("Đã nhận xe. Chuyến đi đang hoạt động, thanh toán sau khi trả xe.");
      this.navigateTo("screen-ride-active");

    } catch (error) {
      console.error("Start ride error:", error);
      this.showToast(error.message || "Không thể bắt đầu chuyến đi!");
    }
  },

  updateRideClock(now = Date.now()) {
    // Tính lại từ mốc BE mỗi lần vẽ, tránh lệch khi tab ngủ hoặc đổi chuyến.
    const ride = AppState.activeServices?.ride || AppState.activeRide;
    const setText = (id, text) => {
      const element = document.getElementById(id);
      if (element) element.innerText = text;
    };
    const time = value => {
      const timestamp = value ? Date.parse(value) : NaN;
      return Number.isFinite(timestamp)
        ? new Date(timestamp).toLocaleTimeString("vi-VN", { hour12: false }) : "—";
    };
    if (!ride) {
      for (const id of ["rideTimer", "rideBookedAt", "rideStartedAt", "rideClockUpdatedAt"]) setText(id, "—");
      return;
    }
    const start = Date.parse(ride.billing_started_at || ride.started_at || "");
    if (Number.isFinite(start)) {
      const seconds = Math.max(0, Math.floor((now - start) / 1000));
      setText("rideTimer", `${Math.floor(seconds / 60)} phút ${String(seconds % 60).padStart(2, "0")} giây`);
    } else {
      // Seed cũ chỉ có snapshot số phút; không bịa mốc bắt đầu để chạy đồng hồ.
      setText("rideTimer", `${ride.elapsed_minutes ?? ride.elapsedMinutes ?? 0} phút (dữ liệu mẫu)`);
    }
    setText("rideBookedAt", time(ride.billing_started_at));
    setText("rideStartedAt", time(ride.started_at));
    setText("rideClockUpdatedAt", time(new Date(now).toISOString()));
  },

  startRideTicker() {
    // Chỉ tạo một bộ đếm, kể cả khi khởi tạo lại giao diện.
    if (this.rideTickerId != null) clearInterval(this.rideTickerId);
    this.updateRideClock();
    this.rideTickerId = setInterval(() => this.updateRideClock(), 1000);
  },

  async finishReturnRental() {
    const activeRide = AppState.activeServices?.ride || AppState.activeRide;
    if (!activeRide?.trip_id) {
      this.showToast("Không tìm thấy chuyến đang sử dụng. Vui lòng mở lại mục Đang dùng.");
      return;
    }
    let returned;
    try {
      const destination = activeRide.destination_hub_id
        ? { hub_id: activeRide.destination_hub_id }
        : { hub_name: activeRide.destination_hub };
      if (!destination.hub_id && !destination.hub_name) {
        throw new Error("Chuyến đi thiếu Hub trả xe, vui lòng kiểm tra lại đặt chỗ.");
      }
      returned = await ApiService.returnVehicle({ trip_id: activeRide.trip_id, ...destination });
      if (returned?.success !== true || returned.trip_id !== activeRide.trip_id) {
        throw new Error("Kết quả trả xe không khớp chuyến đang sử dụng.");
      }
    } catch (e) {
      this.showToast(e.message || "Chưa thể trả xe, vui lòng thử lại.");
      return;
    }

    AppState.lastReturnedTripId = returned.trip_id;
    AppState.activeRide = null;
    AppState.activeServices = {
      ...AppState.activeServices, ride: null,
      has_active: Boolean(AppState.activeServices?.parking || AppState.activeServices?.charging)
    };
    const booking = AppState.bookings.find(b => b.id === activeRide.booking_id);
    if (booking) booking.status = "Hoàn thành";
    this.renderActiveServices(AppState.activeServices);
    this.showToast("Đã trả xe thành công. Đang tải hóa đơn của chuyến vừa kết thúc.");
    this.navigateTo("screen-invoice-rental");
    await this.loadRentalInvoice(returned.trip_id);
  },

  selectChargerSlot(slotText, elementId) {
    document.querySelectorAll("#screen-select-charging .card-box").forEach(c => c.classList.remove("selected"));
    document.querySelectorAll("#screen-select-charging .radio-circle").forEach(r => r.classList.remove("checked"));
    const el = document.getElementById(elementId);
    if (el) {
      el.classList.add("selected");
      const rc = el.querySelector(".radio-circle");
      if (rc) rc.classList.add("checked");
      const radio = el.querySelector("input[type='radio']");
      if (radio) radio.checked = true;
    }
  },

  async startChargingSession() {
    const bookingId = AppState.selectedBookingId
      || (AppState.bookings.find(b => (b.plan_type === "charging" || b.plan_type === "personal") && b.status === "Đã xác nhận") || {}).id;
    if (!bookingId) {
      this.showToast("Không tìm thấy mã đặt chỗ sạc khả dụng!");
      return;
    }
    try {
      const res = await ApiService.startCharging(bookingId);
      if (res && res.charging) {
        AppState.activeServices = { ...AppState.activeServices, has_active: true, charging: res.charging };
        this.renderActiveServices(AppState.activeServices);
      }
      this.showToast("Đã kích hoạt cổng sạc an toàn!");
      this.navigateTo("screen-charging-active");
    } catch (err) {
      this.showToast(err.message || "Không thể bắt đầu phiên sạc.");
    }
  },

  finishParkingExit() {
    // User chỉ xem hướng dẫn; Staff xác nhận checkout mới kết thúc phiên và hoàn chỗ.
    this.showToast("Vui lòng đến quầy bảo vệ để thanh toán và xác nhận ra bãi.");
    this.navigateTo("screen-active-services");
  },

  async finishChargingSession() {
    const activeChg = AppState.activeServices?.charging;
    const sessionId = activeChg?.session_id;
    const kwh = parseFloat(document.getElementById("stopChargingKwhInput")?.value || "2.4") || 2.4;
    const finalPct = parseInt(document.getElementById("stopChargingFinalPct")?.value || "80", 10) || 80;
    if (sessionId) {
      try {
        const res = await ApiService.stopCharging({
          session_id: sessionId,
          power_consumed_kwh: kwh,
          final_charge: finalPct
        });
        if (res && res.invoice) {
          AppState.currentInvoice.id = res.invoice.id;
          AppState.currentInvoice.amount = res.invoice.total_amount;
        }
        await this.loadActiveServices();
        this.showToast(`Đã dừng sạc (${res.total_fee?.toLocaleString() || ""}đ).`);
        this.navigateTo("screen-invoice-charging");
        return;
      } catch (err) {
        this.showToast(err.message || "Không thể dừng phiên sạc.");
        return;
      }
    }
    this.showToast("Đã dừng sạc điện an toàn.");
    this.navigateTo("screen-invoice-charging");
  },

  async finishBatterySwap() {
    const bookingId = AppState.selectedBookingId
      || (AppState.bookings.find(b => (b.plan_type === "swap" || b.plan_type === "battery_swap") && b.status === "Đã xác nhận") || {}).id;
    if (bookingId) {
      try {
        const res = await ApiService.completeSwap(bookingId);
        if (res && res.invoice) {
          AppState.currentInvoice.id = res.invoice.id;
          AppState.currentInvoice.amount = res.invoice.total_amount;
        }
        await this.loadBookings();
        this.showToast("Đã xác nhận đổi pin thành công!");
        this.navigateTo("screen-invoice-swap");
        return;
      } catch (err) {
        this.showToast(err.message || "Không thể xác nhận đổi pin.");
        return;
      }
    }
    this.showToast("Đã nhận pin 100% thành công.");
    this.navigateTo("screen-invoice-swap");
  },

  };
})(window);
