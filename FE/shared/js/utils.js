/**
 * @fileoverview Bộ tiện ích thao tác DOM & định dạng dữ liệu hiển thị (Shared DOM & Formatting Utilities).
 * @module Shared/Utils
 * @description
 * File này cung cấp hai đối tượng tiện ích toàn cục:
 * - `window.DomUtils`: Các hàm truy vấn, gán nội dung văn bản/HTML, đọc/ghi giá trị input và chuyển đổi class CSS an toàn (không gây lỗi khi phần tử không tồn tại).
 * - `window.Formatters`: Các hàm định dạng số tiền sang chuỗi tiền tệ VNĐ và tính phần trăm tiến độ hoàn thành.
 */
(function (global) {
  /**
   * Tập hợp các hàm thao tác phần tử DOM an toàn.
   * @namespace DomUtils
   */
  const DomUtils = {
    /**
     * Tìm và trả về phần tử DOM theo thuộc tính `id`.
     *
     * @param {string} id - Mã định danh (`id`) của phần tử HTML.
     * @returns {HTMLElement|null} Phần tử DOM tìm thấy hoặc `null`.
     */
    byId(id) {
      return document.getElementById(id);
    },

    /**
     * Gán nội dung văn bản thuần (`innerText`) cho phần tử có `id` tương ứng nếu phần tử tồn tại.
     *
     * @param {string} id - Mã `id` của phần tử mục tiêu.
     * @param {string|number} text - Nội dung văn bản cần hiển thị.
     * @returns {HTMLElement|null} Phần tử DOM đã được cập nhật hoặc `null`.
     */
    setText(id, text) {
      const el = document.getElementById(id);
      if (el && text !== undefined && text !== null) {
        el.innerText = text;
      }
      return el;
    },

    /**
     * Gán mã HTML (`innerHTML`) cho phần tử có `id` tương ứng nếu phần tử tồn tại.
     *
     * @param {string} id - Mã `id` của phần tử mục tiêu.
     * @param {string} html - Chuỗi mã HTML cần gán.
     * @returns {HTMLElement|null} Phần tử DOM đã được cập nhật hoặc `null`.
     */
    setHtml(id, html) {
      const el = document.getElementById(id);
      if (el && html !== undefined && html !== null) {
        el.innerHTML = html;
      }
      return el;
    },

    /**
     * Lấy giá trị (`value`) hiện tại của một ô nhập liệu (`input`, `select`, `textarea`).
     *
     * @param {string} id - Mã `id` của phần tử form.
     * @param {string} [defaultValue=""] - Giá trị mặc định trả về nếu không tìm thấy phần tử.
     * @returns {string} Giá trị hiện tại của phần tử hoặc `defaultValue`.
     */
    getValue(id, defaultValue = "") {
      const el = document.getElementById(id);
      return el && el.value !== undefined ? el.value : defaultValue;
    },

    /**
     * Gán giá trị (`value`) cho một phần tử nhập liệu (`input`, `select`, `textarea`).
     *
     * @param {string} id - Mã `id` của phần tử form.
     * @param {string|number} value - Giá trị cần gán vào ô nhập liệu.
     * @returns {HTMLElement|null} Phần tử DOM đã được cập nhật hoặc `null`.
     */
    setValue(id, value) {
      const el = document.getElementById(id);
      if (el && value !== undefined && value !== null) {
        el.value = value;
      }
      return el;
    },

    /**
     * Bật hoặc tắt một class CSS trên phần tử được truyền vào (hoặc tìm theo `id`).
     *
     * @param {string|HTMLElement} idOrEl - Chuỗi `id` hoặc đối tượng `HTMLElement`.
     * @param {string} className - Tên class CSS cần thêm/xóa.
     * @param {boolean} [force] - Nếu truyền `true` thì ép thêm class, `false` thì ép xóa class.
     * @returns {HTMLElement|null} Phần tử DOM đã thao tác hoặc `null`.
     */
    toggleClass(idOrEl, className, force) {
      const el = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
      if (!el) return null;
      if (force !== undefined) {
        el.classList.toggle(className, force);
      } else {
        el.classList.toggle(className);
      }
      return el;
    },

    /**
     * Thoát ký tự dấu nháy đơn (`'`) trong chuỗi để nhúng an toàn vào sự kiện inline `onclick="..."`.
     *
     * @param {string} str - Chuỗi đầu vào.
     * @returns {string} Chuỗi đã được escape dấu nháy đơn.
     */
    escapeSingleQuotes(str) {
      return String(str || "").replace(/'/g, "\\'");
    },

    /**
     * Chuẩn hóa chuỗi bất kỳ (ví dụ mã `#102`) thành chuỗi chỉ gồm chữ cái, chữ số, `_` và `-`
     * để làm thuộc tính `id` hợp lệ trên DOM.
     *
     * @param {string} str - Chuỗi định danh gốc.
     * @returns {string} Chuỗi định danh an toàn cho DOM.
     */
    sanitizeDomId(str) {
      return String(str || "").replace(/[^a-zA-Z0-9_-]/g, "_");
    }
  };

  /**
   * Tập hợp các hàm định dạng số liệu hiển thị trên giao diện.
   * @namespace Formatters
   */
  const Formatters = {
    /**
     * Định dạng một số thành chuỗi tiền tệ có dấu phân cách hàng nghìn kèm đơn vị (`đ` hoặc `VNĐ`).
     *
     * @param {number|string} amount - Số tiền cần định dạng.
     * @param {string} [suffix="đ"] - Đơn vị tiền tệ nối phía sau.
     * @returns {string} Chuỗi tiền tệ đã định dạng (ví dụ: `"25,000 đ"` hoặc `"25,000 VNĐ"`).
     */
    currency(amount, suffix = "đ") {
      const num = Number(amount) || 0;
      return `${num.toLocaleString()}${suffix === "VNĐ" ? " VNĐ" : ` ${suffix}`}`.trim();
    },

    /**
     * Tính tỷ lệ phần trăm nguyên (từ 0 đến 100) giữa giá trị hiện tại và tổng giá trị.
     *
     * @param {number} current - Giá trị đạt được hiện tại.
     * @param {number} total - Tổng giá trị mục tiêu.
     * @returns {number} Phần trăm làm tròn (0 - 100).
     */
    percent(current, total) {
      const tot = Number(total) || 1;
      const cur = Number(current) || 0;
      return Math.min(100, Math.round((cur / tot) * 100));
    }
  };

  global.DomUtils = DomUtils;
  global.Formatters = Formatters;
})(window);
