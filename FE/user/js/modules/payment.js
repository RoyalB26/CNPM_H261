/**
 * @fileoverview Module Hóa đơn & Thanh toán (Payment Module).
 * @module User/Modules/Payment
 */
(function (global) {
  "use strict";
  global.UserModules = global.UserModules || {};

  global.UserModules.Payment = {
  async setupInvoiceAndPay(type, defaultAmount, returnScreen = "screen-invoice-rental", startRideOnSuccess = false) {
    AppState.currentInvoice.type = type;
    AppState.currentInvoice.returnScreen = returnScreen;
    AppState.currentInvoice.startRideOnSuccess = startRideOnSuccess;

    let amount = defaultAmount;
    try {
      const invData = await ApiService.getInvoice(type);
      if (invData && invData.total_amount) {
        amount = invData.total_amount;
        AppState.currentInvoice.id = invData.id;
        AppState.currentInvoice.amount = invData.total_amount;

        // Populate invoice screen details
        if (type === "rental") {
          const itemLabel = document.getElementById("invoiceRentalItemLabel");
          if (itemLabel && invData.items && invData.items[0]) itemLabel.innerText = invData.items[0].label;
          const itemCost = document.getElementById("invoiceRentalItemCost");
          if (itemCost && invData.items && invData.items[0]) itemCost.innerText = `${invData.items[0].amount.toLocaleString()} đ`;
          const totCost = document.getElementById("invoiceRentalTotalCost");
          if (totCost) totCost.innerText = `${invData.total_amount.toLocaleString()} đ`;
        } else if (type === "charging") {
          const itemLabel = document.getElementById("invoiceChargingItemLabel");
          if (itemLabel && invData.items && invData.items[0]) itemLabel.innerText = invData.items[0].label;
          const itemCost = document.getElementById("invoiceChargingItemCost");
          if (itemCost && invData.items && invData.items[0]) itemCost.innerText = `${invData.items[0].amount.toLocaleString()} đ`;
          const totCost = document.getElementById("invoiceChargingTotalCost");
          if (totCost) totCost.innerText = `${invData.total_amount.toLocaleString()} đ`;
        } else if (type === "swap") {
          const itemLabel = document.getElementById("invoiceSwapItemLabel");
          if (itemLabel && invData.items && invData.items[0]) itemLabel.innerText = invData.items[0].label;
          const itemCost = document.getElementById("invoiceSwapItemCost");
          if (itemCost && invData.items && invData.items[0]) itemCost.innerText = `${invData.items[0].amount.toLocaleString()} đ`;
          const totCost = document.getElementById("invoiceSwapTotalCost");
          if (totCost) totCost.innerText = `${invData.total_amount.toLocaleString()} đ`;
        }
      }
    } catch (e) {
      console.warn("Fetch invoice error:", e);
    }

    AppState.currentInvoice.amount = amount;

    const payDisp = document.getElementById("payAmountDisplay");
    const confDisp = document.getElementById("confirmPayAmount");
    const payDesc = document.getElementById("payServiceDesc");
    const confTitle = document.getElementById("confirmPayTitle");

    if (payDisp) payDisp.innerText = `${amount.toLocaleString()} đ`;
    if (confDisp) confDisp.innerText = `${amount.toLocaleString()} đ`;

    if (payDesc) {
      if (type === "swap" || type === "battery_swap") {
        payDesc.innerText = "Hóa đơn dịch vụ đổi pin xe điện";
      } else if (type === "rental") {
        payDesc.innerText = "Hóa đơn cước thuê xe điện (XE-024)";
      } else if (type === "charging") {
        payDesc.innerText = "Hóa đơn dịch vụ sạc xe điện";
      } else if (type === "parking") {
        payDesc.innerText = "Hóa đơn dịch vụ giữ xe cá nhân";
      } else {
        payDesc.innerText = "Hóa đơn dịch vụ Smart E-Mobility";
      }
    }

    if (confTitle) {
      if (type === "swap" || type === "battery_swap") {
        confTitle.innerText = "Xác nhận thanh toán dịch vụ đổi pin";
      } else if (type === "rental") {
        confTitle.innerText = "Xác nhận thanh toán cước thuê xe";
      } else {
        confTitle.innerText = "Xác nhận trừ tiền từ ví";
      }
    }

    const payMethodBackBtn = document.querySelector("#screen-payment-method .nav-back");
    if (payMethodBackBtn) {
      payMethodBackBtn.setAttribute("onclick", `App.navigateTo('${returnScreen}')`);
    }

    this.navigateTo("screen-payment-method");
  },

  selectPayMethod(method, elementId) {
    AppState.user.paymentMethod = method;

    document.querySelectorAll("#screen-payment-method .card-box").forEach(c => c.classList.remove("selected"));
    document.querySelectorAll("#screen-payment-method .radio-circle").forEach(r => r.classList.remove("checked"));

    const item = document.getElementById(elementId);
    if (item) {
      item.classList.add("selected");
      const r = item.querySelector(".radio-circle");
      if (r) r.classList.add("checked");
    }

    const confMethod = document.getElementById("confirmPayMethod");
    if (confMethod) confMethod.innerText = method;
  },

  async executePaymentProcess() {
    this.navigateTo("screen-payment-pending");
    try {
      await ApiService.payInvoice({
        invoice_id: AppState.currentInvoice.id || "INV-2026-901",
        method: AppState.user.paymentMethod,
        amount: AppState.currentInvoice.amount
      });
    } catch (e) {
      console.warn("Pay invoice error:", e);
    }

    const willStartRide = AppState.currentInvoice.startRideOnSuccess;

    setTimeout(() => {
      this.showToast("Thanh toán thành công!");

      const successBtn = document.getElementById("btnPaymentSuccessAction");
      if (successBtn) {
        if (willStartRide) {
          successBtn.innerText = "Bắt đầu chuyến đi";
        } else {
          successBtn.innerText = "Về màn hình chính";
        }
      }

      this.navigateTo("screen-payment-success");

      // Tự động chuyển màn hình tiếp theo sau khi hiển thị thành công
      setTimeout(() => {
        const successEl = document.getElementById("screen-payment-success");
        if (successEl && successEl.classList.contains("active")) {
          this.handlePaymentSuccessNext();
        }
      }, 2000);
    }, 1200);
  },

  handlePaymentSuccessNext() {
    if (AppState.currentInvoice.startRideOnSuccess) {
      this.startRide();
    } else {
      this.navigateTo("screen-map-home");
      this.showToast("Đã hoàn tất thanh toán và trở về màn hình chính.");
    }
  },

  };
})(window);
