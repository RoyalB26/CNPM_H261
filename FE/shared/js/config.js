/**
 * @fileoverview Cấu hình môi trường & tham số hệ thống dùng chung (Shared Configuration).
 * @module Shared/Config
 * @description
 * File này định nghĩa đối tượng toàn cục `window.EMobilityConfig`, quản lý tập trung:
 * - Đường dẫn cơ sở (Base URL) kết nối tới Unified Mock Backend cho cả 3 cổng: User, Operator, Staff.
 * - Tọa độ trung tâm mặc định, mức thu phóng (zoom) và nguồn bản đồ nền OpenStreetMap tại Khu đô thị ĐHQG-HCM.
 * - Chu kỳ tự động đồng bộ dữ liệu thời gian thực (polling intervals) và thời lượng hiển thị thông báo.
 */
(function (global) {
  /**
   * Địa chỉ máy chủ Backend mặc định khi chạy cục bộ.
   * @constant {string}
   */
  const API_HOST = "http://127.0.0.1:8000";

  /**
   * Đối tượng chứa toàn bộ hằng số cấu hình dùng chung trên Frontend.
   * @namespace EMobilityConfig
   */
  const EMobilityConfig = {
    /** @type {string} Địa chỉ gốc của máy chủ Backend */
    API_HOST,
    /** @type {string} Endpoint gốc cho ứng dụng Người dùng (End-User) */
    USER_API_BASE: `${API_HOST}/api`,
    /** @type {string} Endpoint gốc cho bảng điều khiển Trung tâm Điều hành (Operator) */
    OPERATOR_API_BASE: `${API_HOST}/api/v1/operator`,
    /** @type {string} Endpoint gốc cho ứng dụng Nhân viên hiện trường & Bảo vệ (Staff) */
    STAFF_API_BASE: `${API_HOST}/api/v1/staff`,

    /**
     * Cấu hình mặc định cho bản đồ tương tác MapLibre GL JS.
     * @property {number[]} center - Tọa độ trung tâm Khu đô thị ĐHQG-HCM [kinh độ, vĩ độ]
     * @property {number} userZoom - Mức zoom mặc định trên ứng dụng User
     * @property {number} operatorZoom - Mức zoom mặc định trên Dashboard Operator
     * @property {number} focusZoom - Mức zoom khi định vị chi tiết một trạm Hub hoặc địa điểm
     * @property {string} tileUrl - Đường dẫn mẫu lấy mảnh bản đồ nền OpenStreetMap
     */
    MAP_DEFAULTS: {
      center: [106.8005, 10.8753],
      userZoom: 14.2,
      operatorZoom: 13.8,
      focusZoom: 16.5,
      tileUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    },

    /**
     * Cấu hình chu kỳ thời gian (tính bằng mili-giây) cho các tiến trình định kỳ.
     * @property {number} operatorSyncMs - Chu kỳ tự động đồng bộ lệnh điều phối trên Operator (8 giây)
     * @property {number} rideTickerMs - Chu kỳ tăng bộ đếm phút chuyến đi trên User (60 giây)
     * @property {number} toastDurationMs - Thời gian hiển thị thông báo nổi Toast (3.5 giây)
     */
    POLLING: {
      operatorSyncMs: 8000,
      rideTickerMs: 60000,
      toastDurationMs: 3500
    }
  };

  global.EMobilityConfig = EMobilityConfig;
})(window);
