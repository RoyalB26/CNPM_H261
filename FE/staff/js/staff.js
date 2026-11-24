/**
 * @fileoverview Bộ điều khiển trung tâm & hợp nhất các module theo vai trò của ứng dụng Nhân viên Hiện trường (Staff App Bootstrapper).
 * @module Staff/StaffApp
 * @description
 * File này khởi tạo đối tượng toàn cục `StaffApp`, kết hợp 3 module nghiệp vụ theo vai trò từ `js/modules/`:
 *  - `StaffModules.RelocationRole`  : Nghiệp vụ Nhân viên điều chuyển xe (lộ trình, quét QR cọc đỗ, bàn giao hạ tầng).
 *  - `StaffModules.MaintenanceRole` : Nghiệp vụ Kỹ thuật viên bảo trì (danh sách sự cố, xác thực thiết bị, gửi kết quả sửa chữa).
 *  - `StaffModules.GuardRole`       : Nghiệp vụ Bảo vệ bãi đỗ (nhận diện xe vào, thu tiền mặt xe ra, chốt ca trực).
 */

/**
 * Đối tượng điều khiển trung tâm của ứng dụng Nhân viên hiện trường & Bảo vệ.
 * @namespace StaffApp
 */
const StaffApp = {
  /** @type {string} Vai trò hiện đang kích hoạt (`"relocation" | "maintenance" | "security"`) */
  currentRole: "relocation",
  /** @type {string} Mã màn hình hiện đang hiển thị */
  currentScreen: "screen-reloc-route",
  /** @type {number} Số lượng xe đã quét đối soát hoàn tất trong đợt bàn giao */
  handoverDoneCount: 18,
  /** @type {number} Tổng số xe cần đối soát trong đợt bàn giao */
  handoverTotalCount: 20,
  /** @type {string} Mã nhiệm vụ điều phối xe hiện hành */
  currentRelocTaskId: "#102",
  /** @type {string} Mã phiếu nhiệm vụ bảo trì kỹ thuật đang mở */
  currentMaintTaskCode: "MT-102",

  /**
   * Khởi tạo ứng dụng Nhân viên hiện trường khi DOM đã sẵn sàng:
   * cập nhật nhãn thanh điều hướng dưới và tải song song dữ liệu của cả 3 vai trò từ Backend.
   *
   * @async
   * @returns {Promise<void>}
   */
  async init() {
    console.log("Staff App Initialized (Modular Architecture).");
    if (window.HtmlInclude) {
      await window.HtmlInclude.loadAll();
    }
    this.updateBottomNavLabels();

    if (!sessionStorage.getItem("staff_access_token")) {
      this.showLoginView();
      return;
    }

    await this.loadInitialData();
  },

  showLoginView() {
    const view = document.getElementById("staffLoginView");
    if (view) view.style.display = "flex";
  },

  async submitLogin(e) {
    if (e) e.preventDefault();
    const errEl = document.getElementById("staffLoginError");
    if (errEl) errEl.style.display = "none";
    const username = document.getElementById("staffLoginUsername")?.value?.trim() || "staff_b";
    const password = document.getElementById("staffLoginPassword")?.value || "";
    try {
      await StaffApi.login(username, password);
      const view = document.getElementById("staffLoginView");
      if (view) view.style.display = "none";
      await this.loadInitialData();
    } catch (err) {
      if (errEl) {
        errEl.innerText = err.message || "Đăng nhập thất bại";
        errEl.style.display = "block";
      } else {
        alert(err.message || "Đăng nhập thất bại");
      }
    }
  },

  async loadInitialData() {
    await Promise.allSettled([
      this.loadProfile(),
      this.loadRelocationTask(),
      this.loadMaintenanceTasks(),
      this.loadShiftSummary()
    ]);
  },

  /**
   * Tải thông tin hồ sơ nhân viên hiện trường từ `StaffApi.getProfile()`
   * và hiển thị họ tên, ca trực, trạm Hub phụ trách lên đầu các màn hình.
   *
   * @async
   * @returns {Promise<void>}
   */
  async loadProfile() {
    const prof = await StaffApi.getProfile();
    if (!prof) return;

    document.querySelectorAll(".staff-name-text").forEach(el => (el.innerText = prof.full_name));
    document.querySelectorAll(".staff-shift-text").forEach(el => (el.innerText = `${prof.shift_title} · ${prof.assigned_hub}`));
  },

  /**
   * Chuyển đổi vai trò làm việc (`"relocation"`, `"maintenance"`, `"security"`),
   * điều hướng tới màn hình chính của vai trò đó và cập nhật lại nhãn thanh Bottom Bar.
   *
   * @param {string} role - Mã vai trò cần chuyển sang.
   * @returns {void}
   */
  switchRole(role) {
    this.currentRole = role;
    const sel = document.getElementById("staffRoleSelect");
    if (sel) sel.value = role;

    if (role === "relocation") {
      this.goToScreen("screen-reloc-route");
    } else if (role === "maintenance") {
      this.goToScreen("screen-maint-list");
    } else if (role === "security") {
      this.goToScreen("screen-guard-checkin");
    }

    this.updateBottomNavLabels();
  },

  /**
   * Chuyển tới màn hình có mã `screenId` và cuộn khung nhìn `#staffViewport` lên đầu trang.
   *
   * @param {string} screenId - Mã `id` của màn hình cần hiển thị.
   * @returns {void}
   */
  goToScreen(screenId) {
    document.querySelectorAll(".staff-screen").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(screenId);
    if (target) {
      target.classList.add("active");
      this.currentScreen = screenId;
    }
    const viewport = document.getElementById("staffViewport");
    if (viewport) viewport.scrollTop = 0;
  },

  /**
   * Cập nhật tên 4 nút trên thanh điều hướng dưới cùng (`#staffBottomNav`)
   * tùy theo vai trò đang chọn (Bảo vệ bãi đỗ hoặc Nhân viên kỹ thuật/điều chuyển).
   *
   * @returns {void}
   */
  updateBottomNavLabels() {
    const l1 = document.getElementById("navLabel1");
    const l2 = document.getElementById("navLabel2");
    const l3 = document.getElementById("navLabel3");
    const l4 = document.getElementById("navLabel4");

    if (this.currentRole === "security") {
      if (l1) l1.innerText = "Xe vào";
      if (l2) l2.innerText = "Trả xe";
      if (l3) l3.innerText = "Ca trực";
      if (l4) l4.innerText = "Cá nhân";
    } else {
      if (l1) l1.innerText = "Nhiệm vụ";
      if (l2) l2.innerText = "Lịch sử";
      if (l3) l3.innerText = "Thông báo";
      if (l4) l4.innerText = "Cá nhân";
    }
  },

  /**
   * Xử lý sự kiện khi người dùng nhấn vào một trong 4 tab (`1..4`) trên thanh điều hướng dưới cùng.
   *
   * @param {number} tabIndex - Chỉ số thứ tự của tab được nhấn (`1`, `2`, `3` hoặc `4`).
   * @returns {void}
   */
  onNavClick(tabIndex) {
    document.querySelectorAll(".staff-nav-item").forEach((btn, idx) => {
      if (idx + 1 === tabIndex) btn.classList.add("active");
      else btn.classList.remove("active");
    });

    if (this.currentRole === "security") {
      if (tabIndex === 1) this.goToScreen("screen-guard-checkin");
      else if (tabIndex === 2) {
        this.openCheckoutScreen();
      } else if (tabIndex === 3) this.goToScreen("screen-guard-shift");
      else alert("Mục Cá nhân: Thông tin tài khoản bảo vệ Nguyen Van B");
    } else if (this.currentRole === "relocation") {
      if (tabIndex === 1) this.goToScreen("screen-reloc-route");
      else if (tabIndex === 2) alert("Lịch sử các đợt điều chuyển đã hoàn tất trong tuần: 14 đợt.");
      else if (tabIndex === 3) alert("Thông báo từ Operator: Chuẩn bị nhận 20 xe tại trạm KTX Khu A lúc 17:00.");
      else alert("Thông tin nhân viên điều chuyển: Nguyen Van B");
    } else if (this.currentRole === "maintenance") {
      if (tabIndex === 1) this.goToScreen("screen-maint-list");
      else if (tabIndex === 2) alert("Lịch sử bảo dưỡng: Đã sửa 42 sự cố trong tháng.");
      else if (tabIndex === 3) alert("Cảnh báo mới: Trạm sạc C-05 Ga Metro phát sinh dòng rò.");
      else alert("Thông tin kỹ thuật viên: Nguyen Van B");
    }
  }
};

// Hợp nhất cả 3 module vai trò vào đối tượng điều khiển StaffApp
if (window.StaffModules) {
  Object.assign(
    StaffApp,
    window.StaffModules.RelocationRole,
    window.StaffModules.MaintenanceRole,
    window.StaffModules.GuardRole
  );
}

window.StaffApp = StaffApp;

document.addEventListener("DOMContentLoaded", () => {
  StaffApp.init();
});
