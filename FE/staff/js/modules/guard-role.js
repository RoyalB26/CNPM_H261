/**
 * @fileoverview Module Nghiệp vụ Bảo vệ Bãi đỗ (Guard Role).
 * @module Staff/Modules/GuardRole
 */
(function (global) {
  "use strict";
  global.StaffModules = global.StaffModules || {};

  global.StaffModules.GuardRole = {
  async loadShiftSummary() {
    const summary = await StaffApi.getShiftSummary();
    if (!summary) return;
    this.lastShiftSummary = summary;
    const metaEl = document.getElementById("shiftDetailMeta");
    if (metaEl) metaEl.innerText = `${summary.shift_date} · ${summary.shift_title} · ${summary.hub_name}`;
    const countEl = document.getElementById("shiftServedCount");
    if (countEl) countEl.innerText = summary.total_vehicles_served ?? 0;
    const cashEl = document.getElementById("shiftTotalCash");
    if (cashEl) cashEl.innerText = Number(summary.total_cash_collected_vnd || 0).toLocaleString();
    const badgeEl = document.getElementById("shiftTransCountBadge");
    if (badgeEl) badgeEl.innerText = `${summary.total_vehicles_served ?? 0} lượt`;
    const listEl = document.getElementById("shiftTransactionsContainer");
    if (listEl && Array.isArray(summary.transactions) && summary.transactions.length) {
      listEl.innerHTML = summary.transactions.map(tr => `
        <div class="staff-card" style="padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 12px; font-weight: 800; color: var(--text-muted);">${tr.seq_number}</span>
            <div>
              <strong style="font-size: 13.5px;">${tr.license_plate}</strong>
              <div style="font-size: 11px; color: var(--text-muted);">${tr.time_info}</div>
            </div>
          </div>
          <strong style="font-size: 13px;">${Number(tr.amount_vnd || 0).toLocaleString()} VNĐ</strong>
        </div>
      `).join("");
    }
  },

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
    let res;
    try {
      res = await StaffApi.parkingCheckoutPreview(plateOrTicket);
    } catch (error) {
      alert(error.message);
      return;
    }
    if (res) {
      this.lastCheckoutPreview = res;
      const pEl = document.getElementById("checkoutPlate");
      if (pEl) pEl.innerText = res.license_plate;

      const tEl = document.getElementById("checkoutTimeInfo");
      if (tEl) tEl.innerText = `Giờ vào: ${res.checkin_time} | Giờ ra: ${res.checkout_time}`;

      const dEl = document.getElementById("checkoutDurationInfo");
      if (dEl) dEl.innerText = `Tổng thời gian: ${res.duration_str}`;

      const fEl = document.getElementById("checkoutFeeDisplay");
      if (fEl) fEl.innerText = `${(res.total_fee_vnd ?? 0).toLocaleString()} VNĐ`;

      const cEl = document.getElementById("checkoutCashConfirm");
      if (cEl) cEl.innerText = `${(res.total_fee_vnd ?? 0).toLocaleString()} VNĐ`;

      const codeEl = document.getElementById("checkoutTicketCode");
      if (codeEl) codeEl.innerText = `Mã giao dịch: ${res.ticket_code}`;
    }
    this.goToScreen("screen-guard-checkout");
  },

  async confirmCashReceived() {
    const prev = this.lastCheckoutPreview || {};
    const ticketCode = prev.ticket_code || "SG-20261022-018";
    const fee = prev.total_fee_vnd ?? 25000;
    const plate = prev.license_plate || "59-B2 123.45";
    try {
      await StaffApi.parkingCheckoutConfirm(ticketCode, fee, prev.quote_token);
    } catch (error) {
      alert(error.message);
      return;
    }
    alert(`XÁC NHẬN ĐÃ THU ${Number(fee).toLocaleString()} VNĐ TIỀN MẶT THÀNH CÔNG!\nMở barrier cho xe ${plate} ra bãi.`);
    await this.loadShiftSummary();
    this.goToScreen("screen-guard-shift");
  },

  async closeShift() {
    const cash = (this.lastShiftSummary && this.lastShiftSummary.total_cash_collected_vnd) || 1200000;
    const count = (this.lastShiftSummary && this.lastShiftSummary.total_vehicles_served) || 48;
    const res = await StaffApi.closeShift("SG-02", cash);
    if (res && res.success === false) {
      alert(`Không thể chốt ca trực (${res.error || "Lỗi máy chủ"}).`);
      return;
    }
    alert(`ĐÃ CHỐT CA TRỰC THÀNH CÔNG!\nTổng tiền mặt bàn giao: ${Number(cash).toLocaleString()} VNĐ (${count} lượt xe).\nCa trực đã được khóa và lưu trữ kế toán.`);
  }
};

})(window);
