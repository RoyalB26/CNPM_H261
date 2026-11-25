/**
 * @fileoverview Module điều hướng màn hình (Router), quản lý thanh Bottom Bar và hiển thị thông báo nổi (Toast).
 * @module User/Modules/Router
 * @description
 * File này định nghĩa `UserModules.Router`, chịu trách nhiệm:
 * - Chuyển đổi mượt mà giữa 58 màn hình wireframe trong ứng dụng Single Page Application (SPA).
 * - Đồng bộ trạng thái nút Back của trình duyệt (`window.history.pushState` / `popstate`).
 * - Tự động ẩn/hiện và làm nổi bật tab đang chọn trên thanh điều hướng dưới (`#globalBottomNav`).
 * - Hiển thị thông báo trạng thái thành công hoặc cảnh báo lỗi (`showToast`).
 */
(function (global) {
  global.UserModules = global.UserModules || {};

  /**
   * Tập hợp các phương thức điều hướng giao diện và thông báo cho ứng dụng End-User.
   * @namespace UserModules.Router
   */
  global.UserModules.Router = {
    /**
     * Đăng ký các trình lắng nghe sự kiện toàn cục:
     * - Sự kiện `popstate` khi người dùng bấm nút Back/Forward trên trình duyệt.
     * - Sự kiện `change` trên ô chọn Hub đích (`#selectDestHub`) để cập nhật bản nháp đặt xe.
     *
     * @returns {void}
     */
    bindEvents() {
      window.addEventListener("popstate", (e) => {
        if (e.state && e.state.screenId) {
          this.navigateTo(e.state.screenId, false);
        }
      });

      const destSelect = document.getElementById("selectDestHub");
      if (destSelect) {
        destSelect.addEventListener("change", (e) => {
          AppState.bookingDraft.destHub = e.target.value;
          const rDest = document.getElementById("reviewRentalDestHub");
          if (rDest) rDest.innerText = e.target.value;
        });
      }
    },

    /**
     * Chuyển đổi giao diện tới màn hình có mã `screenId`, cuộn khung nhìn lên đầu trang,
     * đồng bộ dữ liệu động tương ứng từ Backend và lưu lịch sử trình duyệt.
     *
     * @param {string} screenId - Mã `id` của màn hình đích (ví dụ: `"screen-map-home"`, `"screen-my-bookings"`).
     * @param {boolean} [pushHistory=true] - Có đẩy trạng thái vào `window.history` hay không.
     * @returns {void}
     */
    navigateTo(screenId, pushHistory = true) {
      if (!screenId) return;
      const targetScreen = document.getElementById(screenId);
      if (!targetScreen) {
        console.warn(`Screen ${screenId} not found!`);
        return;
      }

      const allScreens = document.querySelectorAll(".screen");
      allScreens.forEach(s => s.classList.remove("active"));

      targetScreen.classList.add("active");
      this.currentScreenId = screenId;

      const viewport = document.getElementById("viewport");
      if (viewport) viewport.scrollTop = 0;

      this.updateBottomNavState(screenId);

      // Tự động làm mới dữ liệu khi chuyển tới các màn hình chức năng tương ứng
      if (screenId === "screen-my-bookings") {
        this.loadBookings();
      } else if (screenId === "screen-booking-history") {
        this.renderBookingHistory();
      } else if (screenId === "screen-active-services") {
        this.loadActiveServices();
      } else if (screenId === "screen-incident-history") {
        this.loadIncidents();
      } else if (screenId === "screen-profile") {
        this.loadUserProfile();
      } else if (screenId === "screen-review-rental") {
        this.updateReviewRentalView();
      } else if (screenId === "screen-review-parking") {
        this.updateReviewParkingView();
      } else if (screenId === "screen-review-swap") {
        this.updateReviewSwapView();
      } else if (screenId === "screen-select-charging" && typeof this.loadChargingSchedules === "function") {
        this.loadChargingSchedules();
      }

      if (screenId === "screen-map-home" && this.mapInstance) {
        setTimeout(() => {
          try { this.mapInstance.resize(); } catch (e) {}
        }, 100);
      }

      if (pushHistory) {
        history.pushState({ screenId }, "", `#${screenId}`);
      }
    },

    /**
     * Cập nhật trạng thái hiển thị (ẩn/hiện) và đánh dấu tab đang kích hoạt (`.active`)
     * trên thanh điều hướng dưới cùng (`#globalBottomNav`) dựa theo màn hình hiện tại.
     *
     * @param {string} screenId - Mã `id` của màn hình đang hiển thị.
     * @returns {void}
     */
    updateBottomNavState(screenId) {
      const bottomNav = document.getElementById("globalBottomNav");
      if (!bottomNav) return;

      const noNavScreens = [
        "screen-login", "screen-register", "screen-forgot-password",
        "screen-reset-requested", "screen-pickup", "screen-payment-pending"
      ];

      if (noNavScreens.includes(screenId)) {
        bottomNav.classList.add("hidden");
      } else {
        bottomNav.classList.remove("hidden");
      }

      const tabs = {
        navItemMap: ["screen-map-home", "screen-search-hub", "screen-hub-detail"],
        navItemBookings: ["screen-my-bookings", "screen-booking-detail", "screen-cancel-confirm", "screen-cancelled", "screen-booking-history", "screen-personal-booking"],
        navItemActive: [
          "screen-active-services", "screen-ride-active", "screen-return-vehicle",
          "screen-parking-arrival", "screen-parking-active", "screen-parking-exit-confirm",
          "screen-charging-start", "screen-charging-active", "screen-charging-end-confirm",
          "screen-battery-swap"
        ],
        navItemReport: ["screen-report-incident", "screen-report-validation", "screen-report-sent", "screen-report-detail", "screen-incident-history"]
      };

      Object.keys(tabs).forEach(tabId => {
        const el = document.getElementById(tabId);
        if (el) {
          if (tabs[tabId].includes(screenId)) {
            el.classList.add("active");
          } else {
            el.classList.remove("active");
          }
        }
      });
    },

    /**
     * Hàm bọc tương thích ngược để cập nhật trạng thái hiển thị thanh điều hướng dưới.
     *
     * @param {string} screenId - Mã `id` của màn hình đang hiển thị.
     * @returns {void}
     */
    updateBottomNavVisibility(screenId) {
      this.updateBottomNavState(screenId);
    },

    /**
     * Hiển thị thông báo nổi (Toast) ở phía trên màn hình và tự động ẩn sau 3.5 giây.
     *
     * @param {string} message - Nội dung thông báo cần hiển thị.
     * @param {string} [type="success"] - Kiểu thông báo: `"success"` (màu xanh) hoặc `"error"` (màu đỏ).
     * @returns {void}
     */
    showToast(message, type = "success") {
      const toast = document.getElementById("toastMessage");
      const toastText = document.getElementById("toastText");
      if (toast && toastText) {
        toastText.innerText = message;
        const icon = toast.querySelector("i");
        if (icon) {
          if (type === "error") {
            icon.className = "fa-solid fa-circle-exclamation";
            icon.style.color = "#ef4444";
            toast.style.borderColor = "#fca5a5";
            toast.style.background = "#fff1f2";
            toast.style.color = "#991b1b";
          } else {
            icon.className = "fa-solid fa-circle-check";
            icon.style.color = "#10b981";
            toast.style.borderColor = "";
            toast.style.background = "";
            toast.style.color = "";
          }
        }
        toast.classList.add("show");
        setTimeout(() => {
          toast.classList.remove("show");
        }, (window.EMobilityConfig && window.EMobilityConfig.POLLING.toastDurationMs) || 3500);
      }
    }
  };
})(window);
