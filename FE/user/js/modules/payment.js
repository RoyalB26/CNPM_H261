/**
 * @fileoverview Module Hóa đơn & Thanh toán (Payment Module).
 * @module User/Modules/Payment
 */
(function (global) {
  "use strict";
  global.UserModules = global.UserModules || {};

  global.UserModules.Payment = {
  async loadRentalInvoice(tripId = AppState.lastReturnedTripId) {
    // Chỉ lấy hóa đơn chuyến đã trả; không chọn hóa đơn thuê xe mới nhất làm dự phòng.
    const payButton = document.getElementById("btnPayRental");
    const retryButton = document.getElementById("retryRentalInvoice");
    const notice = document.getElementById("invoiceRentalNotice");
    if (payButton) payButton.disabled = true;
    if (retryButton) retryButton.style.display = "none";
    if (!tripId || tripId !== AppState.lastReturnedTripId) {
      if (notice) notice.innerText = "Chưa chọn chuyến đã trả để xem hóa đơn.";
      this.showToast("Chưa có hóa đơn của chuyến vừa trả xe.");
      return null;
    }
    AppState.currentInvoice = {
      ...AppState.currentInvoice, type: "rental", id: null, amount: 0,
      trip_id: tripId, startRideOnSuccess: false
    };
    for (const id of ["invoiceRentalItemCost", "invoiceRentalTotalCost"]) {
      const element = document.getElementById(id);
      if (element) element.innerText = "—";
    }
    if (notice) notice.innerText = "Đang tải hóa đơn của chuyến vừa trả xe...";
    try {
      const invoice = await ApiService.getInvoice("rental", { trip_id: tripId });
      if (!invoice?.id || invoice.service_type !== "rental"
          || !Number.isInteger(invoice.total_amount) || invoice.total_amount < 0) {
        throw new Error("Hóa đơn thuê xe không hợp lệ.");
      }
      // Bỏ kết quả muộn nếu người dùng đã bắt đầu chuyến khác.
      if (tripId !== AppState.lastReturnedTripId) return null;
      Object.assign(AppState.currentInvoice, {
        id: invoice.id, amount: invoice.total_amount, reference_id: invoice.reference_id
      });
      const title = document.getElementById("invoiceRentalTitle");
      if (title) title.innerText = `${invoice.title} · ${invoice.reference_id}`;
      const label = document.getElementById("invoiceRentalItemLabel");
      const item = invoice.items?.[0];
      if (label) label.innerText = item?.label || item?.description || "Cước thuê xe";
      const cost = document.getElementById("invoiceRentalItemCost");
      if (cost) cost.innerText = `${(item?.amount ?? invoice.total_amount).toLocaleString()} đ`;
      const total = document.getElementById("invoiceRentalTotalCost");
      if (total) total.innerText = `${invoice.total_amount.toLocaleString()} đ`;
      if (notice) notice.innerText = `Chuyến ${tripId} · ${invoice.status === "paid" ? "Đã thanh toán" : "Cước đã chốt sau khi trả xe"}`;
      if (payButton) {
        payButton.disabled = invoice.status === "paid";
        payButton.innerText = invoice.status === "paid" ? "Đã thanh toán" : "Chọn thanh toán";
      }
      return invoice;
    } catch (error) {
      if (tripId !== AppState.lastReturnedTripId) return null;
      if (notice) notice.innerText = `Đã trả xe, nhưng chưa tải được hóa đơn: ${error.message}`;
      if (retryButton) retryButton.style.display = "block";
      return null;
    }
  },

  async setupInvoiceAndPay(type, defaultAmount, returnScreen = "screen-invoice-rental", startRideOnSuccess = false) {
    AppState.currentInvoice.type = type;
    AppState.currentInvoice.returnScreen = returnScreen;
    // Thanh toán hóa đơn không tự nhận xe hoặc khởi tạo chuyến đi mới.
    AppState.currentInvoice.startRideOnSuccess = false;

    let amount = defaultAmount;
    try {
      const invData = type === "rental"
        ? await this.loadRentalInvoice()
        : await ApiService.getInvoice(type);
      if (type === "rental" && !invData) {
        this.navigateTo(returnScreen);
        return;
      }
      if (!invData || !invData.id || !Number.isInteger(invData.total_amount)) {
        throw new Error("Chưa lấy được hóa đơn hợp lệ từ hệ thống");
      }
      if (invData && Number.isInteger(invData.total_amount)) {
        amount = invData.total_amount;
        AppState.currentInvoice.id = invData.id;
        AppState.currentInvoice.amount = invData.total_amount;
        AppState.currentInvoice.reference_id = invData.reference_id;
        if (type === "rental" && invData.status === "paid") {
          this.showToast("Hóa đơn chuyến này đã được thanh toán.");
          this.navigateTo(returnScreen);
          return;
        }

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
      this.showToast(e.message);
      this.navigateTo(returnScreen);
      return;
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
        payDesc.innerText = `Hóa đơn cước thuê xe điện (${AppState.currentInvoice.reference_id})`;
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
    if (AppState.currentInvoice.type === "rental" && (
      !AppState.lastReturnedTripId || AppState.currentInvoice.trip_id !== AppState.lastReturnedTripId
      || !AppState.currentInvoice.id
    )) {
      this.showToast("Vui lòng tải đúng hóa đơn sau khi trả xe trước khi thanh toán.");
      return;
    }
    this.navigateTo("screen-payment-pending");
    try {
      const result = await ApiService.payInvoice({
        invoice_id: AppState.currentInvoice.id,
        method: AppState.user.paymentMethod,
        amount: AppState.currentInvoice.amount,
        simulate: true
      });
      if (result.status === "pending" && result.payment_url) {
        window.location.assign(result.payment_url);
        return;
      }
      if (result.status !== "completed") throw new Error("Giao dịch đang chờ xác nhận");
      const receipt = document.getElementById("paymentSuccessReceipt");
      if (receipt) receipt.innerText = `Giao dịch ${result.transaction_id} hoàn tất. ${result.is_simulated ? "Mô phỏng demo, không trừ tiền thật." : ""}`;
      this.showToast(result.message || "Thanh toán thành công!");
      this.navigateTo("screen-payment-success");
    } catch (error) {
      const reason = document.getElementById("paymentFailureReason");
      if (reason) reason.innerText = error.message;
      this.showToast(error.message, "error");
      this.navigateTo("screen-payment-failed");
    }
  },

  handlePaymentSuccessNext() {
    AppState.currentInvoice.startRideOnSuccess = false;
    this.navigateTo("screen-map-home");
    this.showToast("Đã hoàn tất thanh toán và trở về màn hình chính.");
  },

  };
})(window);
