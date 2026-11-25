/**
 * @fileoverview Module Mô phỏng Kịch bản What-If (Simulation Module).
 * @module Operator/Modules/Simulation
 */
(function (global) {
  "use strict";
  global.OperatorModules = global.OperatorModules || {};

  global.OperatorModules.Simulation = {
    goToSimStep(stepNumber) {
      this.currentSimStep = stepNumber;

      for (let i = 1; i <= 3; i++) {
        const stepView = document.getElementById(`simStep${i}View`);
        const stepPill = document.getElementById(`stepperPill${i}`);
        if (stepView) stepView.classList.remove("active");
        if (stepPill) {
          stepPill.classList.remove("active");
          stepPill.classList.remove("completed");
          if (i < stepNumber) stepPill.classList.add("completed");
          if (i === stepNumber) stepPill.classList.add("active");
        }
      }

      const activeView = document.getElementById(`simStep${stepNumber}View`);
      if (activeView) activeView.classList.add("active");

      if (stepNumber === 1) {
        this.loadSimSourceState();
      }
    },

    selectSourceOption(opt) {
      this.selectedSourceOpt = opt;
      const c1 = document.getElementById("sourceOption1") || document.getElementById("simSourceOpt1");
      const c2 = document.getElementById("sourceOption2") || document.getElementById("simSourceOpt2");
      if (c1) c1.classList.toggle("selected", opt === 1);
      if (c2) c2.classList.toggle("selected", opt === 2);
      return this.setSimSourceOpt(opt);
    },

    setSimSourceOpt(opt) {
      this.selectedSourceOpt = opt;
      const r1 = document.getElementById("simSourceRealtime");
      const r2 = document.getElementById("simSourceManual");
      const card1 = document.getElementById("simSourceOpt1");
      const card2 = document.getElementById("simSourceOpt2");

      if (opt === 1) {
        if (r1) r1.checked = true;
        if (card1) card1.classList.add("selected");
        if (card2) card2.classList.remove("selected");
      } else {
        if (r2) r2.checked = true;
        if (card2) card2.classList.add("selected");
        if (card1) card1.classList.remove("selected");
      }
    },

    async loadSimSourceState() {
      const state = await OperatorApi.getSimStateSource();
      const body = document.getElementById("simSourceStateBody");
      if (!body || !state) return;

      body.innerHTML = state.map(s => `
        <tr>
          <td><strong>${s.hub_name}</strong></td>
          <td>${s.available_bikes}/${s.total_bikes}</td>
          <td>${s.free_parking}/${s.total_parking}</td>
          <td>${s.active_chargers}/${s.total_chargers}</td>
          <td>${s.power_usage}</td>
          <td><span class="badge ${s.status === 'Bình thường' ? 'badge-success' : 'badge-danger'}">${s.status}</span></td>
        </tr>
      `).join("");
    },

    async triggerSimulationCalculation() {
      return this.runSimulationWithProgress();
    },

    async runSimulationWithProgress() {
      const nameEl = document.getElementById("scenarioNameInput");
      const scenarioName = (nameEl && nameEl.value.trim()) || "Nhu cầu sạc tăng cao";
      const checkedRadio = document.querySelector('input[name="scenarioType"]:checked');
      const scenarioType = checkedRadio && checkedRadio.nextElementSibling
        ? checkedRadio.nextElementSibling.innerText.trim()
        : "Nhu cầu sạc tăng đột biến";
      const sliderEl = document.getElementById("demandSlider");
      const demandPct = sliderEl ? parseInt(sliderEl.value, 10) || 50 : 50;

      const mLoad = document.getElementById("modalSimLoading");
      const pBar = document.getElementById("simProgressBar");
      const pText = document.getElementById("simProgressPercent");

      if (mLoad) mLoad.classList.add("show");
      let progress = 0;

      if (this.simProgressInterval) clearInterval(this.simProgressInterval);
      this.simProgressInterval = setInterval(() => {
        progress += 20;
        if (progress > 100) progress = 100;
        if (pBar) pBar.style.width = `${progress}%`;
        if (pText) pText.innerText = `${progress}%`;

        if (progress >= 100) {
          clearInterval(this.simProgressInterval);
          setTimeout(async () => {
            this.closeModal("modalSimLoading");
            const res = await OperatorApi.runSimulation({
              source_type: this.selectedSourceOpt === 2 ? "MANUAL_A_PRIME" : "LIVE_A",
              config: {
                scenario_name: scenarioName,
                scenario_type: scenarioType,
                demand_increase_pct: demandPct,
                duration_minutes: 60,
                start_time: "18:00"
              }
            });
            if (res && res.simulation_id) {
              this.lastSimulationId = res.simulation_id;
            }
            this.goToSimStep(3);
            if (typeof this.loadSimHistory === "function") {
              await this.loadSimHistory();
            }
          }, 250);
        }
      }, 100);
    },

    openSaveRuleModal() {
      const m = document.getElementById("modalSaveFallbackRule") || document.getElementById("modalSaveRule");
      if (m) m.classList.add("show");
    },

    async confirmSaveFallbackRule() {
      return this.executeSaveFallbackRule();
    },

    async executeSaveFallbackRule() {
      const nameEl = document.getElementById("fallbackRuleName") || document.getElementById("ruleName");
      const descEl = document.getElementById("fallbackRuleDesc") || document.getElementById("ruleCondition");
      const autoEl = document.getElementById("autoMatchRuleCheck");

      const name = (nameEl && nameEl.value.trim()) || "Kịch bản dự phòng";
      const desc = (descEl && descEl.value.trim()) || "Điều chuyển xe khi tải cao";
      const autoMatch = autoEl ? autoEl.checked : true;

      await OperatorApi.saveFallbackRule({
        simulation_id: this.lastSimulationId || "SIM-20261018-01",
        rule_name: name,
        operation_instructions: desc,
        auto_match_on_high_load: autoMatch
      });
      this.closeModal("modalSaveFallbackRule");
      this.closeModal("modalSaveRule");
      alert(`Đã lưu kịch bản dự phòng "${name}" thành công vào bộ quy tắc tự động!`);
      if (typeof this.loadSimHistory === "function") {
        await this.loadSimHistory();
      }
    },

    applyDispatchPlan() {
      alert("ĐÃ KÍCH HOẠT KỊCH BẢN ĐIỀU PHỐI:\n• Ban hành lệnh điều phối 20 xe từ KTX Khu A đến Ga Metro A.\n• Tăng công suất trạm sạc Ga Metro cổng 1-5.\nCác nhiệm vụ đã được chuyển tới ứng dụng nhân viên hiện trường.");
      this.switchTab("tab-relocation");
      this.loadRelocations();
    },

    async captureSnapshotNow() {
      try {
        const res = await OperatorApi.captureSimulationSnapshot({
          source_type: this.selectedSourceOpt === 2 ? "MANUAL_A_PRIME" : "LIVE_A"
        });
        this.lastSnapshotId = res.snapshot_id;
        await this.loadSimSourceState();
        alert(`Đã chụp snapshot mạng lưới thành công (${res.snapshot_id})!`);
      } catch (err) {
        alert("Lỗi chụp snapshot: " + (err.message || "Lỗi kết nối"));
      }
    },

    async testValidateParams() {
      const nameEl = document.getElementById("scenarioNameInput");
      const scenarioName = (nameEl && nameEl.value.trim()) || "Nhu cầu sạc tăng cao";
      const sliderEl = document.getElementById("demandSlider");
      const demandPct = sliderEl ? parseInt(sliderEl.value, 10) || 50 : 50;
      try {
        const res = await OperatorApi.validateSimulation({
          source_type: this.selectedSourceOpt === 2 ? "MANUAL_A_PRIME" : "LIVE_A",
          config: {
            scenario_name: scenarioName,
            scenario_type: "Nhu cầu sạc tăng đột biến",
            demand_increase_pct: demandPct,
            duration_minutes: 60,
            start_time: "18:00"
          }
        });
        alert(res.message || "Dữ liệu đầu vào hợp lệ!");
      } catch (err) {
        alert("Kiểm tra tham số thất bại: " + (err.message || "Dữ liệu không hợp lệ"));
      }
    },

    async saveOperationPlan() {
      const simId = this.lastSimulationId || "SIM-20261018-01";
      const plan = prompt("Nhập phương án vận hành cần lưu cho phiên " + simId + ":", "Điều chuyển xe dự phòng và phân tải cổng sạc giờ cao điểm.");
      if (!plan || !plan.trim()) return;
      try {
        await OperatorApi.saveSimulationPlan(simId, plan.trim());
        alert("Đã lưu phương án vận hành thành công!");
        await this.loadSimHistory();
      } catch (err) {
        alert("Không thể lưu phương án: " + (err.message || "Lỗi nghiệp vụ"));
      }
    },

    async showSimulationHistory() {
      document.querySelectorAll("#tab-simulation .sim-subview").forEach(el => el.classList.remove("active"));
      const histView = document.getElementById("simHistoryView");
      if (histView) histView.classList.add("active");
      await this.loadSimHistory();
    },

    async inspectHistoryItem(simId) {
      let item = (this.cachedSimHistory || []).find(i => i.sim_id === simId || i.id === simId);
      try {
        const detail = await OperatorApi.getSimulationDetail(simId);
        if (detail) item = detail;
      } catch (e) {}
      if (!item) return;
      const titleEl = document.getElementById("inspTitle");
      if (titleEl) titleEl.innerText = item.scenario_name || item.title || simId;
      const paramsEl = document.getElementById("inspParams");
      if (paramsEl) paramsEl.innerText = item.what_if_params || item.parameters_summary || "Kịch bản What-If";
      const resEl = document.getElementById("inspResult");
      if (resEl) resEl.innerText = item.recorded_result || `Đỉnh tải ${item.peak_power_kw ?? 185} kW`;
      const ruleEl = document.getElementById("inspRule");
      if (ruleEl) ruleEl.innerText = item.saved_rule || "Chưa có quy tắc ứng phó được lưu.";
    },

    async retryFailedSimulation(simId) {
      try {
        const res = await OperatorApi.retrySimulation(simId);
        if (res && res.simulation_id) this.lastSimulationId = res.simulation_id;
        alert(`Đã chạy lại phiên ${simId} thành công!`);
        await this.loadSimHistory();
      } catch (err) {
        alert("Không thể chạy lại phiên " + simId + ": " + (err.message || "Lỗi nghiệp vụ"));
      }
    },

    reloadScenarioParams(simId) {
      alert(`Đã nạp lại tham số kịch bản ${simId} vào bước cấu hình.`);
      this.goToSimStep(2);
    },

    async loadSimHistory() {
      const history = await OperatorApi.getSimHistory();
      this.cachedSimHistory = history || [];
      const tbody = document.getElementById("simHistoryTableBody");
      if (!tbody || !history) return;

      tbody.innerHTML = history.map(item => {
        const isOk = item.status === "Thành công" || item.status === "COMPLETED";
        const isFailed = item.status === "Thất bại" || item.status === "FAILED";
        const retryBtn = isFailed
          ? `<button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11px; margin-left: 4px;" onclick="event.stopPropagation(); OperatorApp.retryFailedSimulation('${item.sim_id}')">Thử lại</button>`
          : "";
        return `
          <tr onclick="OperatorApp.inspectHistoryItem('${item.sim_id}')" style="cursor: pointer;">
            <td><strong>${item.sim_id}</strong></td>
            <td>
              <div style="font-weight: 700;">${item.scenario_name}</div>
              <div style="font-size: 11.5px; color: var(--text-muted);">${item.what_if_params || ""}</div>
            </td>
            <td style="font-size: 12px;">${item.created_at}</td>
            <td><span class="badge ${isOk ? 'badge-success' : 'badge-danger'}">${item.status}</span></td>
            <td>
              <button class="btn-secondary-light" style="padding: 4px 8px; font-size: 11.5px;" onclick="event.stopPropagation(); OperatorApp.inspectHistoryItem('${item.sim_id}')">Xem</button>${retryBtn}
            </td>
          </tr>
        `;
      }).join("");
    }
  };
})(window);
