/**
 * @fileoverview Tiện ích nạp động các thành phần giao diện con (HTML Partial Loader).
 * @module Shared/HtmlInclude
 * @description
 * Cung cấp giải pháp module hóa giao diện người dùng bằng cách tách các màn hình,
 * thanh điều hướng, modal và bảng điều khiển thành các tệp `.html` con độc lập trong thư mục `partials/`.
 * 
 * Khi trang web khởi chạy, module này sẽ tự động tìm kiếm các phần tử có thuộc tính `data-include="path/to/file.html"`,
 * tải nội dung bất đồng bộ qua `fetch()` và thay thế thẻ giữ chỗ bằng mã HTML thực tế.
 * 
 * Đặc điểm nổi bật:
 *  - Hỗ trợ nạp lồng nhiều cấp (Nested Partials): Tự động nạp tiếp các file con nằm bên trong file con vừa được nạp.
 *  - Bộ nhớ đệm bộ nhớ (In-memory Cache): Tránh gửi request lặp lại nếu cùng một partial được dùng ở nhiều nơi.
 *  - Cảnh báo trực quan khi chạy sai môi trường (ví dụ mở bằng giao thức `file://` thay vì Web Server).
 *  - Viết theo chuẩn tài liệu JSDoc, dễ bảo trì và tích hợp với mọi ứng dụng trong hệ thống.
 */

(function (window) {
  "use strict";

  /**
   * Bộ nhớ đệm nội dung các partial đã tải thành công trong phiên làm việc.
   * @type {Map<string, string>}
   */
  const partialCache = new Map();

  /**
   * Module quản lý nạp partial HTML động.
   * @namespace HtmlInclude
   */
  const HtmlInclude = {
    /**
     * Tải nội dung HTML từ một URL tương đối hoặc tuyệt đối.
     * Có sử dụng bộ nhớ đệm để tối ưu số lượt truy vấn mạng.
     *
     * @async
     * @param {string} url - Đường dẫn tới file partial HTML cần nạp.
     * @returns {Promise<string>} Chuỗi HTML nội dung của partial.
     * @throws {Error} Ném lỗi nếu HTTP request thất bại hoặc file không tồn tại.
     */
    async fetchPartial(url) {
      if (partialCache.has(url)) {
        return partialCache.get(url);
      }

      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const html = await res.text();
      partialCache.set(url, html);
      return html;
    },

    /**
     * Thay thế một phần tử giữ chỗ (`placeholder`) bằng chuỗi mã HTML tương ứng.
     * Sử dụng `createContextualFragment` để bảo đảm các thẻ và cấu trúc DOM được giữ nguyên vẹn.
     *
     * @param {HTMLElement} placeholder - Phần tử giữ chỗ mang thuộc tính `data-include`.
     * @param {string} htmlContent - Nội dung HTML vừa tải về để thay thế.
     * @returns {void}
     */
    replacePlaceholder(placeholder, htmlContent) {
      const range = document.createRange();
      range.selectNode(placeholder);
      const fragment = range.createContextualFragment(htmlContent);
      placeholder.replaceWith(fragment);
    },

    /**
     * Tạo thông báo lỗi trực quan ngay tại vị trí phần tử giữ chỗ bị lỗi tải.
     *
     * @param {HTMLElement} placeholder - Phần tử giữ chỗ bị lỗi.
     * @param {string} url - Đường dẫn tệp gây ra lỗi.
     * @param {string} message - Chi tiết thông điệp lỗi.
     * @returns {void}
     */
    renderError(placeholder, url, message) {
      const isFileProtocol = window.location.protocol === "file:";
      const tipText = isFileProtocol
        ? "⚠️ Đang mở bằng giao thức file://. Hãy chạy trang web qua máy chủ HTTP (VD: python -m http.server 3000 --directory FE)."
        : `⚠️ Lỗi nạp thành phần giao diện (${url}): ${message}`;

      const errBox = document.createElement("div");
      errBox.className = "include-error-notice";
      errBox.style.cssText = "padding: 12px; margin: 8px 0; background: #fff1f0; border: 1px dashed #ff4d4f; border-radius: 6px; color: #cf1322; font-size: 13px; font-family: sans-serif;";
      errBox.innerHTML = `
        <strong>Lỗi tải giao diện:</strong> ${tipText}
        <div style="font-size: 11px; color: #888; margin-top: 4px;">Đường dẫn: <code>${url}</code></div>
      `;
      placeholder.replaceWith(errBox);
    },

    /**
     * Quét và nạp toàn bộ các thành phần `[data-include]` nằm trong phạm vi gốc chỉ định.
     * Tự động lặp lại quét cho tới khi nạp xong tất cả các partial lồng nhau (tối đa `maxDepth` lần).
     *
     * @async
     * @param {HTMLElement} [rootElement=document.body] - Phần tử gốc chứa các thẻ cần quét (mặc định là `document.body`).
     * @param {number} [maxDepth=10] - Số cấp lồng nhau tối đa để phòng tránh đệ quy vô hạn.
     * @returns {Promise<void>} Hoàn tất khi toàn bộ các partial đã được chèn vào DOM.
     *
     * @example
     * // Sử dụng trong Controller khởi động của ứng dụng
     * await HtmlInclude.loadAll();
     * console.log("Giao diện đã nạp xong, sẵn sàng truy vấn DOM.");
     */
    async loadAll(rootElement = document.body, maxDepth = 10) {
      let currentDepth = 0;

      while (currentDepth < maxDepth) {
        const placeholders = Array.from((rootElement || document.body).querySelectorAll("[data-include]"));
        if (placeholders.length === 0) {
          break;
        }

        // Tải song song toàn bộ partials trong lượt quét hiện tại
        await Promise.all(
          placeholders.map(async (placeholder) => {
            const url = placeholder.getAttribute("data-include");
            if (!url) return;

            try {
              const htmlContent = await this.fetchPartial(url);
              this.replacePlaceholder(placeholder, htmlContent);
            } catch (err) {
              console.error(`[HtmlInclude] Thất bại khi nạp partial từ '${url}':`, err);
              this.renderError(placeholder, url, err.message);
            }
          })
        );

        currentDepth++;
      }

      if (currentDepth >= maxDepth) {
        console.warn(`[HtmlInclude] Đã chạm giới hạn độ sâu ${maxDepth}. Vui lòng kiểm tra nguy cơ vòng lặp đệ quy nạp partial.`);
      }
    }
  };

  window.HtmlInclude = HtmlInclude;
})(window);
