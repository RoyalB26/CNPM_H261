/**
 * @fileoverview Module Nghiệp vụ Nhân viên Điều chuyển xe (Relocation Role).
 * @module Staff/Modules/RelocationRole
 */
(function (global) {
  "use strict";
  global.StaffModules = global.StaffModules || {};

  global.StaffModules.RelocationRole = {
  async loadRelocationTask() {
    const task = await StaffApi.getRelocationTask();
    if (!task) return;
    if (task.task_id) this.currentRelocTaskId = task.task_id;
    if (typeof task.in_transit_bikes === "number") this.handoverDoneCount = task.in_transit_bikes;
    if (typeof task.total_bikes === "number") this.handoverTotalCount = task.total_bikes;
    const counter = document.getElementById("handoverProgressCount");
    if (counter && task.total_bikes !== undefined) {
      counter.innerText = `${this.handoverDoneCount}/${this.handoverTotalCount} xe`;
    }
  },

  async simulateScanBike(bikeCode) {
    const res = await StaffApi.scanBike(this.currentRelocTaskId, bikeCode, "02");

    const row = document.getElementById(`bikeRow_${bikeCode}`) || document.getElementById(`bikeRow${bikeCode}`);
    if (row) {
      row.classList.remove("waiting");
      row.classList.add("done");
      const check = row.querySelector(".check-box-square");
      if (check) check.innerHTML = '<i class="fa-solid fa-check"></i>';
      const pill = row.querySelector(".status-pill");
      if (pill) {
        pill.className = "status-pill done";
        pill.innerText = "Done";
      }

      this.handoverDoneCount = Math.min(this.handoverTotalCount, this.handoverDoneCount + 1);
      const counter = document.getElementById("handoverProgressCount");
      if (counter) counter.innerText = `${this.handoverDoneCount}/${this.handoverTotalCount} xe`;

      alert(`Đã quét xác nhận xe ${bikeCode} vào cọc đỗ thành công! Cập nhật về server trung tâm.`);
    }
  },

  toggleBikeRow(row) {
    alert("Xe này đã hoàn tất đối soát cọc đỗ.");
  },

  async completeHandover() {
    await StaffApi.handover(this.currentRelocTaskId, this.handoverDoneCount, "Hub Ga Metro A");
    alert("HOÀN TẤT BÀN GIAO HẠ TẦNG THÀNH CÔNG!\nĐã đối soát toàn bộ xe tại Hub Ga Metro A. Dữ liệu đã được cập nhật về Operator.");
    this.goToScreen("screen-reloc-route");
  },

  openRelocIncidentReport() {
    this.goToScreen("screen-reloc-incident");
  },

  async submitRelocIncident() {
    const type = document.getElementById("relocIncidentType").value;
    await StaffApi.reportRelocIncident({
      task_id: this.currentRelocTaskId,
      incident_type: type,
      location_desc: "Đường nội bộ ĐHQG",
      description: "Sự cố phát sinh trong quá trình chuyển xe",
      has_image: false
    });

    alert(`Đã gửi báo cáo sự cố "${type}" đến Trung tâm Điều hành!\nĐội cứu hộ lưu động đã nhận thông tin.`);
    this.goToScreen("screen-reloc-route");
  },

  };
})(window);
