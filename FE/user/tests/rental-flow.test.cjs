/** Kiểm thử luồng thuê xe bằng HTTP/DOM giả lập, không gọi Backend hay thanh toán thật. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

async function fixture() {
  const nodes = new Map();
  const requests = [];
  const screens = [];
  const messages = [];
  const flags = {};
  const ride = { trip_id: "TRIP-NEW", vehicle_id: "XE-101", booking_id: "BOOK-NEW",
    origin_hub: "Hub Thư viện", destination_hub: "Hub Quốc Tế", destination_hub_id: "hub-04",
    elapsed_minutes: 0, battery_level: 84, status: "Đang sử dụng" };
  const invoice = { id: "INV-TRIP-NEW", reference_id: "XE-101", service_type: "rental",
    title: "Hóa đơn thuê xe", status: "unpaid", total_amount: 334,
    items: [{ label: "Thuê xe 2 phút", amount: 334 }] };
  const oldInvoice = { ...invoice, id: "INV-OLD", total_amount: 2167 };
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { innerText: "", innerHTML: "", disabled: false,
      style: {}, setAttribute() {} });
    return nodes.get(id);
  };
  const state = {
    user: { paymentMethod: "wallet" }, selectedBookingId: "BOOK-NEW",
    bookings: [{ id: "BOOK-NEW", plan_type: "rental", status: "Đã xác nhận" }],
    activeServices: { ride: null, parking: null, charging: null }, activeRide: null,
    lastReturnedTripId: "TRIP-OLD", currentInvoice: { type: "rental", id: "INV-OLD", amount: 2167,
      trip_id: "TRIP-OLD", startRideOnSuccess: true },
  };
  const context = {
    URLSearchParams, AppState: state, console: { log() {}, warn() {}, error() {} },
    sessionStorage: { getItem: () => "fixture-token", setItem() {} },
    document: { getElementById: node, querySelector: node, querySelectorAll: () => [] },
    fetch: async (url, options = {}) => {
      const request = { url: new URL(url), method: options.method || "GET",
        body: options.body ? JSON.parse(options.body) : null };
      requests.push(request);
      let status = 200;
      let data = {};
      if (request.url.pathname.endsWith("/start")) {
        data = { success: true, ride };
      } else if (request.url.pathname.endsWith("/return-vehicle")) {
        if (flags.returnNetworkError) throw new Error("Mất kết nối khi trả xe");
        status = flags.returnStatus || 200;
        data = status === 200 ? { success: true, trip_id: ride.trip_id, total_fee: 334 }
          : { success: false, error: "Hub chưa thể nhận xe" };
      } else if (request.url.pathname.endsWith("/invoices/current")) {
        status = flags.invoiceStatus || 200;
        // Mô phỏng hóa đơn cũ mới nhất nếu FE quên truyền trip_id.
        data = status === 200 ? (request.url.searchParams.get("trip_id") === ride.trip_id ? invoice : oldInvoice)
          : { error: "Chưa tải được hóa đơn của chuyến" };
      } else if (request.url.pathname.endsWith("/invoices/pay")) {
        invoice.status = "paid";
        status = flags.paymentStatus || 200;
        data = status === 200 ? { status: "completed", transaction_id: "DEMO-TEST", is_simulated: true } : { error: "Số tiền không khớp hóa đơn" };
      }
      return { ok: status < 400, status, json: async () => data };
    },
  };
  context.window = context;
  vm.createContext(context);
  const root = path.resolve(__dirname, "..");
  for (const file of ["js/api.js", "js/modules/booking.js", "js/modules/active-services.js", "js/modules/payment.js"]) {
    vm.runInContext(fs.readFileSync(path.join(root, file), "utf8"), context, { filename: file });
  }
  vm.runInContext("globalThis.api = ApiService;", context);
  await Promise.resolve();
  await Promise.resolve();
  context.api.isBackendAvailable = true;
  const app = { ...context.UserModules.Booking, ...context.UserModules.ActiveServices,
    ...context.UserModules.Payment, showToast: message => messages.push(message),
    navigateTo: screen => screens.push(screen) };
  return { app, state, flags, invoice, ride, node, requests, screens, messages, api: context.api };
}

async function run() {
  const results = [];
  async function check(name, test) {
    await test(await fixture());
    results.push(name);
  }
  await check("Nhận xe gọi start, không mở hóa đơn/thanh toán cũ", async f => {
    await f.app.payAndStartRide();
    assert.equal(f.state.activeRide.trip_id, f.ride.trip_id);
    assert.equal(f.state.lastReturnedTripId, null);
    assert.equal(f.state.currentInvoice.id, null);
    assert.equal(f.screens.at(-1), "screen-ride-active");
    assert(!f.requests.some(r => r.url.pathname.includes("/invoices/")));
  });
  await check("Trả xe rồi thanh toán đúng chuyến, không nhận xe lần hai", async f => {
    await f.app.startRide();
    await f.app.finishReturnRental();
    const returned = f.requests.find(r => r.url.pathname.endsWith("/return-vehicle"));
    assert.deepEqual(returned.body, { trip_id: "TRIP-NEW", hub_id: "hub-04" });
    assert.equal(f.state.activeRide, null);
    assert.equal(f.state.activeServices.ride, null);
    assert.equal(f.state.currentInvoice.id, f.invoice.id);
    assert.equal(f.state.currentInvoice.amount, 334);
    assert.equal(f.node("btnPayRental").disabled, false);
    await f.app.setupInvoiceAndPay("rental", 0);
    assert(f.requests.filter(r => r.url.pathname.endsWith("/invoices/current"))
      .every(r => r.url.searchParams.get("trip_id") === "TRIP-NEW"));
    await f.app.executePaymentProcess();
    const payment = f.requests.find(r => r.url.pathname.endsWith("/invoices/pay"));
    assert.equal(payment.body.invoice_id, "INV-TRIP-NEW");
    assert.equal(payment.body.amount, 334);
    assert.equal(payment.body.simulate, true);
    assert(f.screens.includes("screen-payment-success"));
    assert(f.node("paymentSuccessReceipt").innerText.includes("DEMO-TEST"));
    assert(f.node("paymentSuccessReceipt").innerText.includes("không trừ tiền thật"));
    f.state.currentInvoice.startRideOnSuccess = true;
    f.app.handlePaymentSuccessNext();
    assert.equal(f.requests.filter(r => r.url.pathname.endsWith("/start")).length, 1);
  });
  for (const fault of [401, 409, "network", "offline"]) {
    await check(`Trả xe lỗi ${fault}: giữ chuyến, không tạo thanh toán`, async f => {
      await f.app.startRide();
      if (fault === "network") f.flags.returnNetworkError = true;
      else if (fault === "offline") f.api.isBackendAvailable = false;
      else f.flags.returnStatus = fault;
      await f.app.finishReturnRental();
      assert.equal(f.state.activeServices.ride.trip_id, "TRIP-NEW");
      assert.equal(f.state.lastReturnedTripId, null);
      assert(!f.requests.some(r => r.url.pathname.includes("/invoices/")));
      assert(!f.screens.includes("screen-invoice-rental"));
    });
  }
  await check("Hóa đơn lỗi 404 khóa thanh toán, thử lại vẫn đúng trip_id", async f => {
    await f.app.startRide();
    f.flags.invoiceStatus = 404;
    await f.app.finishReturnRental();
    assert.equal(f.state.activeServices.ride, null);
    assert.equal(f.state.currentInvoice.id, null);
    assert.equal(f.node("btnPayRental").disabled, true);
    assert.equal(f.node("retryRentalInvoice").style.display, "block");
    await f.app.executePaymentProcess();
    assert(!f.requests.some(r => r.url.pathname.endsWith("/invoices/pay")));
    f.flags.invoiceStatus = 200;
    await f.app.loadRentalInvoice();
    assert.equal(f.state.currentInvoice.id, "INV-TRIP-NEW");
    assert.equal(f.node("btnPayRental").disabled, false);
  });
  await check("Chưa trả chuyến nào thì không lấy hóa đơn mới nhất", async f => {
    f.state.lastReturnedTripId = null;
    await f.app.setupInvoiceAndPay("rental", 2167);
    await f.app.executePaymentProcess();
    assert(!f.requests.some(r => r.url.pathname.includes("/invoices/")));
  });
  await check("Hóa đơn đã paid không tạo thanh toán nữa", async f => {
    await f.app.startRide();
    await f.app.finishReturnRental();
    f.invoice.status = "paid";
    await f.app.setupInvoiceAndPay("rental", 0);
    assert.equal(f.node("btnPayRental").disabled, true);
    assert(!f.requests.some(r => r.url.pathname.endsWith("/invoices/pay")));
  });
  await check("Thanh toán lỗi hiện trang thất bại và lý do, không báo thành công", async f => {
    await f.app.startRide();
    await f.app.finishReturnRental();
    f.flags.paymentStatus = 409;
    await f.app.executePaymentProcess();
    assert.equal(f.screens.at(-1), "screen-payment-failed");
    assert.equal(f.node("paymentFailureReason").innerText, "Số tiền không khớp hóa đơn");
    assert(!f.screens.includes("screen-payment-success"));
  });
  return { passed: results.length, results };
}

module.exports = { run };
if (require.main === module) run().then(result => console.log(JSON.stringify(result, null, 2)));
