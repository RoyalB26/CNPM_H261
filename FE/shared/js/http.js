/**
 * @fileoverview Bộ khách HTTP dùng chung (Shared HTTP Client) có hỗ trợ chống cache và tự động fallback.
 * @module Shared/HttpClient
 * @description
 * File này cung cấp đối tượng `window.HttpClient`, đóng gói `fetch` API để chuẩn hóa:
 * - Gắn tham số chống lưu đệm (`?_t=timestamp` và `cache: "no-store"`) khi cần lấy dữ liệu thời gian thực.
 * - Tự động tuần tự hóa JSON payload và thiết lập header `Content-Type: application/json`.
 * - Xử lý lỗi HTTP hoặc đứt kết nối mạng bằng cách trả về dữ liệu mẫu dự phòng (offline fallback).
 */
(function (global) {
  /**
   * Tiện ích gửi yêu cầu HTTP JSON tới Backend kèm cơ chế dự phòng ngoại tuyến.
   * @namespace HttpClient
   */
  const HttpClient = {
    /**
     * Gắn tham số thời gian thực `_t` vào URL để buộc trình duyệt không dùng dữ liệu cache cũ.
     *
     * @param {string} url - Đường dẫn URL gốc cần gọi.
     * @returns {string} Đường dẫn URL đã được nối thêm query parameter `_t=<timestamp>`.
     */
    withNoCacheUrl(url) {
      const sep = url.includes("?") ? "&" : "?";
      return `${url}${sep}_t=${Date.now()}`;
    },

    /**
     * Thực thi một yêu cầu HTTP bất đồng bộ và phân tích phản hồi JSON.
     * Nếu máy chủ không phản hồi hoặc lỗi mạng, hàm sẽ trả về giá trị `fallback` (nếu có).
     *
     * @async
     * @param {string} url - Đường dẫn API đích.
     * @param {Object} [options={}] - Tùy chọn cấu hình yêu cầu.
     * @param {string} [options.method="GET"] - Phương thức HTTP (`GET`, `POST`, `PUT`, `DELETE`).
     * @param {Object|null} [options.body=null] - Dữ liệu gửi đi (sẽ được `JSON.stringify`).
     * @param {boolean} [options.noCache=false] - Bật chế độ chống cache trình duyệt.
     * @param {*} [options.fallback=undefined] - Giá trị hoặc hàm trả về dữ liệu dự phòng khi lỗi mạng.
     * @param {boolean} [options.throwOnHttpError=false] - Ném ngoại lệ nếu mã trạng thái HTTP không thuộc nhóm 2xx.
     * @returns {Promise<*>} Dữ liệu JSON từ máy chủ hoặc dữ liệu `fallback`.
     * @throws {Error} Ném lỗi kèm `error.status` và `error.data` nếu `throwOnHttpError=true` và phản hồi lỗi.
     */
    async request(url, { method = "GET", body = null, noCache = false, fallback = undefined, throwOnHttpError = false } = {}) {
      const targetUrl = noCache ? this.withNoCacheUrl(url) : url;
      const fetchOptions = {
        method,
        headers: {}
      };

      if (noCache) {
        fetchOptions.cache = "no-store";
      }

      if (body !== null && body !== undefined) {
        fetchOptions.headers["Content-Type"] = "application/json";
        fetchOptions.body = JSON.stringify(body);
      }

      try {
        const res = await fetch(targetUrl, fetchOptions);
        if (res.ok) {
          return await res.json();
        }
        if (throwOnHttpError) {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData.message || errData.error || `HTTP Error ${res.status}`;
          const error = new Error(errMsg);
          error.status = res.status;
          error.data = errData;
          throw error;
        }
      } catch (err) {
        if (throwOnHttpError && err.status) {
          throw err;
        }
        console.warn(`[HttpClient] ${method} ${url} fallback triggered:`, err.message || err);
      }

      return typeof fallback === "function" ? fallback() : fallback;
    },

    /**
     * Gửi yêu cầu HTTP GET tới máy chủ.
     *
     * @async
     * @param {string} url - Đường dẫn API đích.
     * @param {*} [fallback=undefined] - Dữ liệu trả về nếu Backend ngoại tuyến.
     * @param {Object} [options={}] - Tùy chọn bổ sung (`noCache`, `throwOnHttpError`).
     * @returns {Promise<*>} Kết quả phản hồi JSON hoặc dữ liệu dự phòng.
     */
    async get(url, fallback = undefined, options = {}) {
      return this.request(url, { ...options, method: "GET", fallback });
    },

    /**
     * Gửi yêu cầu HTTP POST kèm dữ liệu JSON tới máy chủ.
     *
     * @async
     * @param {string} url - Đường dẫn API đích.
     * @param {Object} body - Dữ liệu payload gửi lên server.
     * @param {*} [fallback=undefined] - Dữ liệu trả về nếu Backend ngoại tuyến.
     * @param {Object} [options={}] - Tùy chọn bổ sung (`throwOnHttpError`).
     * @returns {Promise<*>} Kết quả phản hồi JSON hoặc dữ liệu dự phòng.
     */
    async post(url, body, fallback = undefined, options = {}) {
      return this.request(url, { ...options, method: "POST", body, fallback });
    },

    /**
     * Gửi yêu cầu HTTP PUT kèm dữ liệu JSON để cập nhật tài nguyên trên máy chủ.
     *
     * @async
     * @param {string} url - Đường dẫn API đích.
     * @param {Object} body - Dữ liệu payload cập nhật.
     * @param {*} [fallback=undefined] - Dữ liệu trả về nếu Backend ngoại tuyến.
     * @param {Object} [options={}] - Tùy chọn bổ sung (`throwOnHttpError`).
     * @returns {Promise<*>} Kết quả phản hồi JSON hoặc dữ liệu dự phòng.
     */
    async put(url, body, fallback = undefined, options = {}) {
      return this.request(url, { ...options, method: "PUT", body, fallback });
    }
  };

  global.HttpClient = HttpClient;
})(window);
