/**
 * @fileoverview Bộ điều khiển trung tâm & hợp nhất các module (Application Bootstrapper & Module Aggregator) cho End-User App.
 * @module User/App
 * @description
 * File này khởi tạo đối tượng toàn cục `App`, đóng vai trò là Controller chính gắn kết 7 module chức năng từ `js/modules/`:
 *  - `UserModules.Router`         : Điều hướng màn hình, thanh điều hướng dưới và thông báo Toast.
 *  - `UserModules.AuthProfile`    : Đăng nhập, đăng ký, quản lý hồ sơ cá nhân và cấu hình thanh toán.
 *  - `UserModules.MapHubs`        : Bản đồ MapLibre GL, hiển thị lớp GeoJSON, chi tiết Hub và tìm kiếm địa điểm.
 *  - `UserModules.Booking`        : Luồng đặt xe/chỗ đỗ/cổng sạc/đổi pin, xử lý lỗi 409 Conflict và lịch sử đặt chỗ.
 *  - `UserModules.ActiveServices` : Theo dõi dịch vụ đang chạy, bộ đếm thời gian chuyến đi và hoàn tất trả xe.
 *  - `UserModules.Payment`        : Lập hóa đơn, xác nhận thanh toán và điều hướng sau thanh toán.
 *  - `UserModules.Incidents`      : Gửi báo cáo sự cố và theo dõi tiến độ xử lý sự cố.
 */

/**
 * Đối tượng điều khiển trung tâm của ứng dụng Người dùng (End-User).
 * @namespace App
 */
const App = {
  /** @type {string} Mã màn hình hiện đang hiển thị */
  currentScreenId: "screen-login",
  /** @type {Object|null} Thực thể bản đồ MapLibre GL */
  mapInstance: null,
  /** @type {Array<Object>} Danh sách các marker đang ghim trên bản đồ */
  mapMarkers: [],
  /** @type {Object|null} Marker ghim tạm thời khi người dùng tìm kiếm một địa điểm */
  searchPinMarker: null,
  /** @type {string} Từ khóa tìm kiếm Hub/địa điểm hiện tại */
  currentQuery: "",

  /**
   * Khởi tạo ứng dụng khi DOM đã sẵn sàng:
   * thiết lập thanh điều hướng, gắn sự kiện, khởi chạy bộ đếm thời gian chuyến đi,
   * khởi tạo bản đồ MapLibre, hiển thị danh sách tìm kiếm và đồng bộ dữ liệu ban đầu từ Backend.
   *
   * @async
   * @returns {Promise<void>}
   */
  async init() {
    console.log("Smart E-Mobility App Initialized (Modular Architecture).");
    if (window.HtmlInclude) {
      await window.HtmlInclude.loadAll();
    }
    this.updateBottomNavVisibility("screen-login");
    this.bindEvents();
    this.startRideTicker();
    this.initMapLibre();
    this.renderSearchList();

    // Kiểm tra kết nối Backend; chỉ tải dữ liệu bảo vệ nếu đã có phiên đăng nhập
    await ApiService.checkBackend();
    if (sessionStorage.getItem("user_access_token")) {
      await this.loadInitialDataFromBE();
    }

    // Tự động co giãn kích thước khung bản đồ khi xoay màn hình hoặc thay đổi kích thước cửa sổ
    window.addEventListener("resize", () => {
      if (this.mapInstance) {
        try { this.mapInstance.resize(); } catch (e) {}
      }
    });
  },

  /**
   * Kiểm tra kết nối Backend và tải song song toàn bộ dữ liệu ban đầu
   * (Hồ sơ người dùng, danh sách Hub, lịch đặt chỗ, dịch vụ đang dùng và lịch sử sự cố).
   *
   * @async
   * @returns {Promise<void>}
   */

  /**
   * Phương thức dự phòng tải danh sách Hub từ Backend (Ủy quyền cho module MapHubs).
   * @async
   * @returns {Promise<void>}
   */
  async loadHubsFromBE() {
    if (window.UserModules && window.UserModules.MapHubs && typeof window.UserModules.MapHubs.loadHubsFromBE === "function") {
      return window.UserModules.MapHubs.loadHubsFromBE.call(this);
    }
  },

  async loadInitialDataFromBE() {
    await ApiService.checkBackend();
    await Promise.allSettled([
      this.loadUserProfile(),
      this.loadHubsFromBE(),
      this.loadBookings(),
      this.loadActiveServices(),
      this.loadIncidents()
    ]);
  }
};

// Hợp nhất toàn bộ các module miền nghiệp vụ vào đối tượng điều khiển App
if (window.UserModules) {
  Object.assign(
    App,
    window.UserModules.Router,
    window.UserModules.AuthProfile,
    window.UserModules.MapHubs,
    window.UserModules.Booking,
    window.UserModules.ActiveServices,
    window.UserModules.Payment,
    window.UserModules.Incidents
  );
}

window.App = App;

// Tự động khởi chạy ứng dụng khi tài liệu HTML đã tải xong
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
