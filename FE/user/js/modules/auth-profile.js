/**
 * @fileoverview Module xác thực tài khoản (Authentication) & quản lý hồ sơ người dùng (User Profile).
 * @module User/Modules/AuthProfile
 * @description
 * File này định nghĩa `UserModules.AuthProfile`, xử lý các nghiệp vụ:
 * - Tải và hiển thị thông tin cá nhân cùng danh sách phương tiện cá nhân từ Backend.
 * - Xử lý đăng nhập (`handleLogin`), đăng ký (`handleRegister`), đăng xuất (`handleLogout`).
 * - Cập nhật thông tin hồ sơ (`saveProfile`) và thiết lập phương thức thanh toán mặc định (`setPaymentPreference`).
 */
(function (global) {
  global.UserModules = global.UserModules || {};

  /**
   * Tập hợp các phương thức xác thực và quản lý hồ sơ cá nhân của End-User.
   * @namespace UserModules.AuthProfile
   */
  global.UserModules.AuthProfile = {
    /**
     * Tải hồ sơ cá nhân và danh sách xe cá nhân của người dùng từ `ApiService`,
     * sau đó điền dữ liệu vào màn hình Hồ sơ (`screen-profile`), Chỉnh sửa hồ sơ (`screen-edit-profile`)
     * và các ô chọn biển số xe trong luồng đặt chỗ đỗ/sạc/đổi pin.
     *
     * @async
     * @returns {Promise<void>}
     */
    async loadUserProfile() {
      try {
        const user = await ApiService.getProfile();
        if (user) {
          AppState.user.id = user.id || AppState.user.id;
          AppState.user.fullName = user.full_name || user.fullName || AppState.user.fullName;
          AppState.user.email = user.email || AppState.user.email;
          AppState.user.phone = user.phone || AppState.user.phone;
          AppState.user.paymentMethod = user.default_payment_method || AppState.user.paymentMethod;

          const pName = document.getElementById("profileName");
          if (pName) pName.innerText = AppState.user.fullName;
          const pEmail = document.getElementById("profileEmail");
          if (pEmail) pEmail.innerText = AppState.user.email;
          const pPhone = document.getElementById("profilePhone");
          if (pPhone) pPhone.innerText = AppState.user.phone;

          const eName = document.getElementById("editFullName");
          if (eName) eName.value = AppState.user.fullName;
          const eEmail = document.getElementById("editEmail");
          if (eEmail) eEmail.value = AppState.user.email;
          const ePhone = document.getElementById("editPhone");
          if (ePhone) ePhone.value = AppState.user.phone;
        }

        const vehicles = await ApiService.getUserVehicles();
        if (vehicles && vehicles.length) {
          AppState.user.vehicles = vehicles;
          const optionsHtml = vehicles.map(v => `<option value="${v.type} · ${v.plate_number}">${v.type} · ${v.plate_number} (${v.model || ''})</option>`).join("");
          ["parkingPersonalVehicle", "chargingPersonalVehicle", "swapPersonalVehicle"].forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            const previousValue = el.value;
            el.innerHTML = optionsHtml;
            if (Array.from(el.options).some(option => option.value === previousValue)) {
              el.value = previousValue;
            }
          });
          if (vehicles[0]) {
            AppState.bookingDraft.personalPlate = vehicles[0].plate_number;
          }
        }
      } catch (e) {
        console.warn("Could not load user profile from BE:", e);
      }
    },

    /**
     * Xử lý sự kiện gửi biểu mẫu Đăng nhập:
     * xác thực qua `ApiService.login`, đồng bộ dữ liệu người dùng và điều hướng vào màn hình bản đồ chính.
     *
     * @async
     * @param {Event} [e] - Sự kiện submit form.
     * @returns {Promise<void>}
     */
    async handleLogin(e) {
      if (e) e.preventDefault();
      const phone = document.getElementById("loginPhone").value;
      const pass = document.getElementById("loginPassword").value;

      try {
        const res = await ApiService.login(phone, pass);
        if (res && (res.success || res.token)) {
          if (res.user) {
            AppState.user = { ...AppState.user, ...res.user };
          }
          await this.loadInitialDataFromBE();
          this.showToast("Đăng nhập thành công!");
          this.navigateTo("screen-map-home");
        }
      } catch (err) {
        this.showToast(err.message || "Sai tài khoản hoặc mật khẩu");
      }
    },

    /**
     * Xử lý sự kiện gửi biểu mẫu Đăng ký tài khoản mới và chuyển về màn hình đăng nhập.
     *
     * @async
     * @param {Event} [e] - Sự kiện submit form.
     * @returns {Promise<void>}
     */
    async handleRegister(e) {
      if (e) e.preventDefault();
      const full_name = document.getElementById("regFullName")?.value?.trim() || "";
      const phone = document.getElementById("regPhone")?.value?.trim() || "";
      const email = document.getElementById("regEmail")?.value?.trim() || "";
      const password = document.getElementById("regPassword")?.value || "";
      const confirm_password = document.getElementById("regConfirmPassword")?.value || "";

      try {
        await ApiService.register({ full_name, phone, email, password, confirm_password });
        this.showToast("Tạo tài khoản thành công! Vui lòng đăng nhập.");
        this.navigateTo("screen-login");
      } catch (err) {
        this.showToast(err.message || "Không thể đăng ký tài khoản.");
      }
    },

    /**
     * Đăng xuất khỏi phiên làm việc hiện tại và đưa người dùng về màn hình đăng nhập (`screen-login`).
     *
     * @returns {void}
     */
    handleLogout() {
      sessionStorage.removeItem("user_access_token");
      this.showToast("Đã đăng xuất tài khoản.");
      this.navigateTo("screen-login");
    },

    /**
     * Lưu các thay đổi thông tin cá nhân (Họ tên, Email, Số điện thoại) lên Backend
     * và cập nhật lại giao diện màn hình Hồ sơ.
     *
     * @async
     * @returns {Promise<void>}
     */
    async saveProfile() {
      const newName = document.getElementById("editFullName").value;
      const newEmail = document.getElementById("editEmail").value;
      const newPhone = document.getElementById("editPhone").value;

      AppState.user.fullName = newName;
      AppState.user.email = newEmail;
      AppState.user.phone = newPhone;

      try {
        await ApiService.updateProfile({
          full_name: newName,
          email: newEmail,
          phone: newPhone
        });
      } catch (e) {
        console.warn("Update profile API error:", e);
      }

      document.getElementById("profileName").innerText = newName;
      document.getElementById("profileEmail").innerText = newEmail;
      document.getElementById("profilePhone").innerText = newPhone;

      this.showToast("Cập nhật thông tin thành công!");
      this.navigateTo("screen-profile");
    },

    /**
     * Thay đổi phương thức thanh toán mặc định (`"Ví điện tử"` hoặc `"Thẻ ngân hàng"`)
     * trong màn hình tùy chọn thanh toán của người dùng.
     *
     * @param {string} pref - Tên phương thức thanh toán được chọn.
     * @returns {void}
     */
    setPaymentPreference(pref) {
      AppState.user.paymentMethod = pref;
      const isWallet = pref === "Ví điện tử";

      document.getElementById("prefWallet").classList.toggle("selected", isWallet);
      document.getElementById("prefBank").classList.toggle("selected", !isWallet);

      document.getElementById("radioPrefWallet").classList.toggle("checked", isWallet);
      document.getElementById("radioPrefBank").classList.toggle("checked", !isWallet);
    },

    async openUserNotifications() {
      const box = document.getElementById("userNotificationsBox");
      const list = document.getElementById("userNotificationsList");
      if (!box || !list) return;
      const isShown = box.style.display === "block";
      if (isShown) {
        box.style.display = "none";
        return;
      }
      box.style.display = "block";
      list.innerHTML = "Đang tải thông báo...";
      try {
        const items = await ApiService.getNotifications();
        if (!items.length) {
          list.innerHTML = "Chưa có thông báo mới.";
          return;
        }
        list.innerHTML = items.map(n => `
          <div style="border-top: 1px solid var(--border-color); padding: 8px 0;">
            <strong style="color: var(--text-main);">${n.title || "Thông báo"}</strong>
            <div>${n.message || n.body || ""}</div>
          </div>
        `).join("");
      } catch (err) {
        list.innerHTML = err.message || "Không thể tải thông báo.";
      }
    }
  };
})(window);
