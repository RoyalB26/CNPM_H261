/**
 * @fileoverview Bộ điều khiển trung tâm & hợp nhất các module của Bảng điều khiển Điều hành (Operator Dashboard Bootstrapper).
 * @module Operator/OperatorApp
 * @description
 * File này khởi tạo đối tượng toàn cục `OperatorApp`, kết hợp 4 module chức năng từ `js/modules/`:
 *  - `OperatorModules.Overview`        : Xác thực 2FA, KPIs, Bản đồ giám sát MapLibre, Telemetry và Dừng khẩn cấp.
 *  - `OperatorModules.Relocation`      : Quản lý lệnh điều phối phương tiện và đồng bộ trực tiếp lên màn hình Tổng quan.
 *  - `OperatorModules.MaintenanceHubs` : Quản lý phiếu bảo trì kỹ thuật và cấu hình sức chứa/tạm ngưng trạm Hub.
 *  - `OperatorModules.Simulation`      : Mô phỏng kịch bản What-If, lưu quy tắc dự phòng và tra cứu lịch sử mô phỏng.
 */

/**
 * Đối tượng điều khiển trung tâm của Bảng điều khiển Điều hành (Operator Dashboard).
 * @namespace OperatorApp
 */
const OperatorApp = {
  /** @type {Object|null} Thực thể bản đồ MapLibre GL trên màn hình Tổng quan */
  map: null,
  /** @type {string} Tên trạm Hub đang được chọn để tạm ngưng hoạt động */
  currentDeactivatingHub: "",
  /** @type {number} Bước hiện tại (1, 2 hoặc 3) trong trình thuật sĩ mô phỏng What-If */
  currentSimStep: 1,
  /** @type {number} Tùy chọn nguồn dữ liệu mô phỏng (`1`: trạng thái thực tế, `2`: nhập thủ công) */
  selectedSourceOpt: 1,
  /** @type {number|null} ID của bộ hẹn giờ tiến trình chạy mô phỏng */
  simProgressInterval: null,
  /** @type {Array<Object>} Bộ nhớ đệm lưu danh sách lịch sử các phiên mô phỏng */
  cachedSimHistory: [],
  /** @type {Array<Object>} Bộ nhớ đệm lưu danh sách các lệnh điều phối phương tiện */
  cachedRelocations: [],

  /**
   * Khởi tạo Bảng điều khiển Operator khi DOM đã sẵn sàng:
   * gắn sự kiện cho các ô nhập mã OTP 2FA, tải song song toàn bộ dữ liệu từ Backend,
   * khởi tạo bản đồ giám sát và thiết lập bộ hẹn giờ tự động đồng bộ lệnh điều phối mỗi 8 giây.
   *
   * @async
   * @returns {Promise<void>}
   */
  async init() {
    console.log("Operator Dashboard Initialized (Modular Architecture).");
    if (window.HtmlInclude) {
      await window.HtmlInclude.loadAll();
    }
    this.initOtpInputs();

    if (!sessionStorage.getItem("operator_access_token")) {
      this.showLoginView();
      return;
    }

    await this.loadDashboardData();
  },

  async loadDashboardData() {
    // Tải song song toàn bộ dữ liệu khởi đầu từ Backend API
    await Promise.allSettled([
      this.loadKpis(),
      this.loadTelemetry(),
      this.loadRelocations(),
      this.loadMaintenance(),
      this.loadHubsConfig(),
      this.loadSimSourceState(),
      this.loadSimHistory(),
      this.loadAutomationTab ? this.loadAutomationTab() : Promise.resolve(),
      this.loadOperatorNotifications ? this.loadOperatorNotifications() : Promise.resolve()
    ]);

    this.initMap();

    // Tự động đồng bộ danh sách lệnh điều phối và trạng thái Dashboard mỗi 8 giây
    const syncMs = (window.EMobilityConfig && window.EMobilityConfig.POLLING.operatorSyncMs) || 8000;
    if (!this.autoSyncTimer) {
      this.autoSyncTimer = setInterval(() => {
        const activeTab = document.querySelector(".section-panel.active");
        if (activeTab && (activeTab.id === "tab-relocation" || activeTab.id === "tab-overview")) {
          this.loadRelocations();
        }
      }, syncMs);
    }
  },

  /**
   * Chuyển đổi giữa các phân hệ chức năng trên thanh menu bên trái (`tab-overview`, `tab-relocation`,
   * `tab-maintenance`, `tab-hubs`, `tab-simulation`) và tự động gọi API làm mới dữ liệu của tab tương ứng.
   *
   * @async
   * @param {string} tabId - Mã `id` của phân hệ cần hiển thị.
   * @returns {Promise<void>}
   */
  async switchTab(tabId) {
    document.querySelectorAll(".menu-item").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".section-panel").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(tabId);
    if (targetTab) {
      targetTab.classList.add("active");
    }

    const buttons = document.querySelectorAll(".menu-item");
    buttons.forEach(btn => {
      if (btn.getAttribute("onclick") && btn.getAttribute("onclick").includes(tabId)) {
        btn.classList.add("active");
      }
    });

    if (tabId === "tab-relocation") {
      await this.loadRelocations();
    } else if (tabId === "tab-overview") {
      await this.loadKpis();
      await this.loadRelocations();
      if (this.map) {
        setTimeout(() => {
          try { this.map.resize(); } catch (e) {}
        }, 150);
      }
    } else if (tabId === "tab-maintenance") {
      await this.loadMaintenance();
    } else if (tabId === "tab-hubs") {
      await this.loadHubsConfig();
    } else if (tabId === "tab-automation") {
      await this.loadAutomationTab();
    }
  },

  /**
   * Đóng hộp thoại Modal hoặc ngăn kéo Drawer theo `modalId`.
   *
   * @param {string} modalId - Mã `id` của hộp thoại cần đóng.
   * @returns {void}
   */
  closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove("show");
  }
};

// Hợp nhất toàn bộ các module chức năng vào OperatorApp
if (window.OperatorModules) {
  Object.assign(
    OperatorApp,
    window.OperatorModules.Overview,
    window.OperatorModules.Relocation,
    window.OperatorModules.MaintenanceHubs,
    window.OperatorModules.Automation,
    window.OperatorModules.Simulation
  );
}

window.OperatorApp = OperatorApp;

document.addEventListener("DOMContentLoaded", () => {
  OperatorApp.init();
});
