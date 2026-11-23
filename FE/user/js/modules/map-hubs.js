/**
 * @fileoverview Module Bản đồ & Tra cứu Trạm Hub (Map & Hubs Module).
 * @module User/Modules/MapHubs
 */
(function (global) {
  "use strict";
  global.UserModules = global.UserModules || {};

  global.UserModules.MapHubs = {
    /**
     * Tải danh sách trạm Hub từ Backend thông qua `ApiService.getHubs()`,
     * cập nhật vào `AppState.hubs`, đồng thời làm mới danh sách tìm kiếm và thông tin Hub hiện tại.
     *
     * @async
     * @returns {Promise<void>}
     */
    async loadHubsFromBE() {
      try {
        const raw = await ApiService.getHubs();
        const list = Array.isArray(raw) ? raw : (raw && (raw.items || raw.hubs)) || [];
        if (list && list.length > 0) {
          AppState.hubs = list;
          if (typeof this.renderSearchList === "function") {
            this.renderSearchList();
          }
          const curId = (AppState.bookingDraft && AppState.bookingDraft.hubId) || list[0].id;
          const currentHub = AppState.hubs.find(h => h.id === curId) || list[0];
          if (currentHub && typeof this.populateHubData === "function") {
            this.populateHubData(currentHub);
          }
        }
      } catch (e) {
        console.warn("Could not load hubs from BE:", e);
      }
    },

    /**
     * Tên hàm viết tắt (alias) tương thích ngược.
     * @async
     * @returns {Promise<void>}
     */
    async loadHubs() {
      return this.loadHubsFromBE();
    },

  initMapLibre() {
    const container = document.getElementById("maplibre-container");
    if (!container || typeof maplibregl === "undefined") {
      console.warn("MapLibre GL not available, using SVG fallback.");
      const fallback = document.getElementById("fallbackSvgMap");
      if (fallback) fallback.style.display = "block";
      return;
    }

    try {
      this.mapInstance = new maplibregl.Map({
        container: "maplibre-container",
        style: {
          version: 8,
          sources: {
            "osm-tiles": {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "&copy; OpenStreetMap Contributors"
            }
          },
          layers: [
            {
              id: "osm-tiles-layer",
              type: "raster",
              source: "osm-tiles",
              minzoom: 0,
              maxzoom: 19
            }
          ]
        },
        center: [106.8005, 10.8753],
        zoom: 14.2
      });

      this.mapInstance.addControl(new maplibregl.NavigationControl(), "top-right");

      this.mapInstance.on("load", async () => {
        // 1. Add clipping boundary layer from FE/map/clipping_boundary.geojson
        try {
          const bRes = await fetch("../map/clipping_boundary.geojson");
          if (bRes.ok) {
            const bData = await bRes.json();
            this.mapInstance.addSource("boundary-src", {
              type: "geojson",
              data: bData
            });
            this.mapInstance.addLayer({
              id: "boundary-line",
              type: "line",
              source: "boundary-src",
              paint: {
                "line-color": "#2563eb",
                "line-width": 2,
                "line-dasharray": [3, 2]
              }
            });
          }
        } catch (e) {
          console.warn("Could not load clipping boundary geojson", e);
        }

        // 2. Add DHQG Named Places & Hubs from DHQG.geojson
        try {
          const pRes = await fetch("../map/DHQG.geojson");
          if (pRes.ok) {
            const pData = await pRes.json();
            this.mapInstance.addSource("dhqg-places-src", {
              type: "geojson",
              data: pData
            });

            // Layer for Mobility Hub points directly from DHQG.geojson (rendered native on map layer)
            this.mapInstance.addLayer({
              id: "dhqg-hub-points",
              type: "circle",
              source: "dhqg-places-src",
              filter: ["all", ["==", "$type", "Point"], ["==", "is_hub", true]],
              paint: {
                "circle-radius": 6.5,
                "circle-color": "#0f172a", // Dark black / monochrome matching wireframe
                "circle-stroke-width": 2,
                "circle-stroke-color": "#ffffff"
              }
            });

            // Handle click on Hub points -> open bottom sheet
            this.mapInstance.on("click", "dhqg-hub-points", (e) => {
              const props = e.features[0].properties;
              this.openHubSheet(props.id);
            });

            this.mapInstance.on("mouseenter", "dhqg-hub-points", () => this.mapInstance.getCanvas().style.cursor = "pointer");
            this.mapInstance.on("mouseleave", "dhqg-hub-points", () => this.mapInstance.getCanvas().style.cursor = "");
          }
        } catch (e) {
          console.warn("Could not load DHQG.geojson layer", e);
        }
      });
    } catch (err) {
      console.warn("MapLibre init error, falling back to SVG:", err);
      const fallback = document.getElementById("fallbackSvgMap");
      if (fallback) fallback.style.display = "block";
    }
  },

  openHubSheet(hubId) {
    const sheet = document.getElementById("hubBottomSheet");
    if (!sheet) return;

    const hub = AppState.hubs.find(h => h.id === hubId) || AppState.hubs[0];

    document.getElementById("sheetHubName").innerText = hub.name;
    document.getElementById("sheetHubAddress").innerText = hub.address;
    document.getElementById("sheetHubBikes").innerText = `${hub.available_bikes} xe khả dụng`;
    document.getElementById("sheetHubParking").innerText = `${hub.available_parking} chỗ đỗ trống`;
    document.getElementById("sheetHubChargers").innerText = `${hub.available_chargers} cổng khả dụng`;
    AppState.bookingDraft.hubId = hub.id;
    AppState.bookingDraft.hubName = hub.name;

    this.populateHubData(hub);
    sheet.classList.add("open");
  },

  closeHubSheet() {
    const sheet = document.getElementById("hubBottomSheet");
    if (sheet) sheet.classList.remove("open");
  },

  startBookingFromHub() {
    this.closeHubSheet();
    this.navigateTo("screen-select-bike");
  },

  async selectHubAndOpenDetail(hubId) {
    let hub = AppState.hubs.find(h => h.id === hubId) || AppState.hubs[0];
    try {
      const detail = await ApiService.getHubDetail(hubId);
      if (detail && detail.id) {
        hub = { ...hub, ...detail };
      }
    } catch (e) {
      console.warn("Could not fetch hub detail:", e);
    }
    if (hub) {
      this.populateHubData(hub);
    }
    this.navigateTo("screen-hub-detail");
  },

  populateHubData(hub) {
    if (!hub) return;
    AppState.bookingDraft.hubId = hub.id;
    AppState.bookingDraft.hubName = hub.name;

    const fullTitle = document.getElementById("fullHubDetailTitle");
    if (fullTitle) fullTitle.innerText = hub.name;

    const addrBadge = document.getElementById("hubDetailAddressBadge");
    if (addrBadge) addrBadge.innerText = hub.address || "Khu đô thị ĐHQG - HCM";

    const bikesEl = document.getElementById("hubDetailBikeCount");
    if (bikesEl) bikesEl.innerText = hub.available_bikes ?? 5;

    const parkEl = document.getElementById("hubDetailParkingCount");
    if (parkEl) parkEl.innerText = hub.available_parking ?? 8;

    const chgEl = document.getElementById("hubDetailChargerCount");
    if (chgEl) chgEl.innerText = hub.available_chargers ?? 2;

    const batEl = document.getElementById("hubDetailBatteryCount");
    if (batEl) batEl.innerText = hub.available_batteries ?? 6;

    // Update hub name displays across wizard screens
    document.querySelectorAll(".hub-name-display").forEach(el => {
      el.innerText = hub.name;
    });

    const parkingBadge = document.getElementById("parkingAvailBadge");
    if (parkingBadge) parkingBadge.innerText = `${hub.available_parking ?? 8} chỗ trống`;

    // Populate destination hub dropdown
    const destSelect = document.getElementById("selectDestHub");
    if (destSelect && AppState.hubs && AppState.hubs.length) {
      destSelect.innerHTML = AppState.hubs
        .filter(h => h.id !== hub.id)
        .map(h => `<option value="${h.name}">${h.name}</option>`)
        .join("");
    }

    // Populate dynamic charging ports
    const chargerContainer = document.getElementById("chargerSlotsContainer");
    if (chargerContainer && hub.ports && hub.ports.length) {
      chargerContainer.innerHTML = hub.ports.map((port, idx) => {
        const isSel = idx === 0;
        if (isSel) {
          AppState.bookingDraft.chargingPort = port.id;
        }
        const availClass = port.is_available ? "selectable" : "disabled";
        const timeSlot = port.time_slots && port.time_slots.length ? port.time_slots[0] : "10:00 – 11:00";
        return `
          <div class="card-box ${availClass} ${isSel ? 'selected' : ''}" id="slot-${port.id.toLowerCase()}" style="display: flex; justify-content: space-between; align-items: center; padding: 14px; margin-bottom: 10px;" onclick="${port.is_available ? `App.selectChargerSlot('${timeSlot} · ${port.id}', 'slot-${port.id.toLowerCase()}')` : ''}">
            <div>
              <span style="font-size: 14px; font-weight: 700;">${timeSlot} · ${port.name || port.id}</span>
              <div style="font-size: 11.5px; color: var(--text-muted);">${port.status || (port.is_available ? 'Sẵn sàng' : 'Bận')} · ${port.rate_per_kwh || 3500}đ/kWh</div>
            </div>
            <div class="radio-circle ${isSel ? 'checked' : ''}"></div>
          </div>
        `;
      }).join("");
    }

    // Populate dynamic battery options
    const swapSelect = document.getElementById("swapBatteryType");
    if (swapSelect && hub.batteries && hub.batteries.length) {
      swapSelect.innerHTML = hub.batteries.map(b => 
        `<option value="${b.battery_type}">${b.name} (${b.available_count} có sẵn · ${b.swap_fee.toLocaleString()}đ)</option>`
      ).join("");
      AppState.bookingDraft.swapBatteryType = hub.batteries[0].battery_type;
    }

    this.renderHubBikes(hub);
  },

  renderHubBikes(hub) {
    const container = document.getElementById("bikeListContainer");
    if (!container) return;

    const bikes = hub.bikes || [
      { id: "XE-024", name: "Xe đạp điện", battery_level: 85, status: "Sẵn sàng" },
      { id: "XE-031", name: "Xe đạp điện", battery_level: 92, status: "Sẵn sàng" }
    ];

    container.innerHTML = bikes.map((bike, index) => {
      const itemIndex = index + 1;
      const isSelected = itemIndex === 1;
      if (isSelected) {
        AppState.bookingDraft.selectedBike = bike.id;
        AppState.bookingDraft.bikeBattery = bike.battery_level;
      }
      return `
        <div class="card-box selectable ${isSelected ? 'selected' : ''}" id="bike-item-${itemIndex}" onclick="App.selectBike('${bike.id}', ${bike.battery_level}, 'bike-item-${itemIndex}')">
          <div>
            <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 4px;">${bike.id} · ${bike.name || 'Xe đạp điện'}</div>
            <div style="font-size: 12.5px; color: var(--text-muted);">Pin ${bike.battery_level}% · ${bike.status || 'Sẵn sàng'}</div>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fa-solid fa-bicycle" style="font-size: 18px;"></i>
            <div class="radio-circle ${isSelected ? 'checked' : ''}" id="radio-bike-${itemIndex}"></div>
          </div>
        </div>
      `;
    }).join("");
  },

  setSearchCategory(cat) {
    AppState.searchCategory = cat;
    const tabs = ["filterTabAll", "filterTabHub", "filterTabSchool", "filterTabDorm", "filterTabAmenity"];
    tabs.forEach(t => {
      const el = document.getElementById(t);
      if (el) el.classList.remove("active");
    });

    const activeMap = {
      all: "filterTabAll",
      hub: "filterTabHub",
      school: "filterTabSchool",
      dorm: "filterTabDorm",
      amenity: "filterTabAmenity"
    };
    const activeEl = document.getElementById(activeMap[cat]);
    if (activeEl) activeEl.classList.add("active");

    this.renderSearchList();
  },

  filterHubs(query) {
    this.currentQuery = (query || "").trim().toLowerCase();
    this.renderSearchList();
  },

  renderSearchList() {
    const container = document.getElementById("hubListContainer");
    if (!container) return;

    const countEl = document.getElementById("searchResultCount");
    const q = this.currentQuery;
    const cat = AppState.searchCategory;

    let items = [];

    // 1. Add Hubs
    if (cat === "all" || cat === "hub") {
      AppState.hubs.forEach(h => {
        if (!q || h.name.toLowerCase().includes(q) || h.address.toLowerCase().includes(q)) {
          items.push({
            type: "hub",
            id: h.id,
            name: h.name,
            address: h.address,
            subtitle: `${h.available_bikes} xe sẵn sàng · ${h.available_parking} chỗ đỗ trống · ${h.available_chargers} sạc`,
            icon: "fa-solid fa-bicycle",
            lat: h.lat,
            lng: h.lng
          });
        }
      });
    }

    // 2. Add Named Places from places-data.js (DHQG.geojson)
    if (typeof DHQG_NAMED_PLACES !== "undefined" && cat !== "hub") {
      DHQG_NAMED_PLACES.forEach(p => {
        // Skip hub entries from DHQG_NAMED_PLACES to avoid duplication with AppState.hubs
        if (p.is_hub || p.type === "mobility_hub" || (p.name && p.name.startsWith("Hub "))) {
          return;
        }

        const nameLower = p.name.toLowerCase();
        const typeLower = (p.type || "").toLowerCase();

        // Categorize
        const isSchool = nameLower.includes("đại học") || nameLower.includes("khoa") || nameLower.includes("viện") || nameLower.includes("trường");
        const isDorm = nameLower.includes("ktx") || nameLower.includes("ký túc xá");

        if (cat === "school" && !isSchool) return;
        if (cat === "dorm" && !isDorm) return;
        if (cat === "amenity" && (isSchool || isDorm)) return;

        if (!q || nameLower.includes(q) || typeLower.includes(q)) {
          let icon = "fa-solid fa-location-dot";
          if (isSchool) icon = "fa-solid fa-graduation-cap";
          else if (isDorm) icon = "fa-solid fa-building";
          else if (typeLower.includes("restaurant") || typeLower.includes("food")) icon = "fa-solid fa-utensils";
          else if (typeLower.includes("bus")) icon = "fa-solid fa-bus";

          items.push({
            type: "place",
            name: p.name,
            address: `Tọa độ: ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)} · ĐHQG-HCM`,
            subtitle: p.type !== "Địa điểm" ? `Thể loại: ${p.type}` : "Địa điểm nội khu ĐHQG",
            icon: icon,
            lat: p.lat,
            lng: p.lng
          });
        }
      });
    }

    if (countEl) {
      countEl.innerText = `${items.length} kết quả`;
    }

    // Render up to 50 items for super smooth scrolling
    const displayItems = items.slice(0, 50);

    if (displayItems.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-solid fa-map-pin" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
          <div style="font-weight: 600;">Không tìm thấy địa điểm phù hợp</div>
          <div style="font-size: 12px; margin-top: 4px;">Thử tìm kiếm với từ khóa khác như "Bách khoa", "KTX", "Hub"...</div>
        </div>
      `;
      return;
    }

    container.innerHTML = displayItems.map(item => {
      if (item.type === "hub") {
        return `
          <div class="card-box selectable" style="margin-bottom: 8px;" onclick="App.locateHubOnMap('${item.id}')">
            <div style="display: flex; gap: 12px; align-items: center;">
              <div style="width: 38px; height: 38px; border-radius: 50%; background: #0f172a; color: #fff; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <i class="${item.icon}"></i>
              </div>
              <div>
                <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 2px;">${item.name}</div>
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">${item.address}</div>
                <div style="font-size: 12px; color: #10b981; font-weight: 600;">${item.subtitle}</div>
              </div>
            </div>
            <button class="btn-secondary" style="width: auto; padding: 6px 12px; font-size: 11.5px; border-radius: 20px;">Xem map</button>
          </div>
        `;
      } else {
        return `
          <div class="card-box selectable" style="margin-bottom: 8px;" onclick="App.locatePlaceOnMap('${item.name.replace(/'/g, "\\'")}', ${item.lat}, ${item.lng})">
            <div style="display: flex; gap: 12px; align-items: center;">
              <div style="width: 38px; height: 38px; border-radius: 50%; background: #e0f2fe; color: #0284c7; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <i class="${item.icon}"></i>
              </div>
              <div>
                <div style="font-weight: 700; font-size: 14px; margin-bottom: 2px;">${item.name}</div>
                <div style="font-size: 11.5px; color: var(--text-muted); margin-bottom: 2px;">${item.address}</div>
                <div style="font-size: 11.5px; color: #64748b;">${item.subtitle}</div>
              </div>
            </div>
            <button class="btn-secondary" style="width: auto; padding: 6px 12px; font-size: 11.5px; border-radius: 20px;">Xem map</button>
          </div>
        `;
      }
    }).join("");
  },

  locateHubOnMap(hubId) {
    const hub = AppState.hubs.find(h => h.id === hubId) || AppState.hubs[0];
    this.navigateTo("screen-map-home");

    if (this.mapInstance && typeof maplibregl !== "undefined") {
      setTimeout(() => {
        // Fly directly to the hub's location
        this.mapInstance.flyTo({ center: [hub.lng, hub.lat], zoom: 16.5 });

        // Remove previous search pin if any
        if (this.searchPinMarker) {
          this.searchPinMarker.remove();
          this.searchPinMarker = null;
        }

        // Open the bottom sheet preview for this hub
        this.openHubSheet(hub.id);
      }, 200);
    } else {
      this.openHubSheet(hub.id);
    }

    this.showToast(`Đã chuyển tới: ${hub.name}`);
  },

  locatePlaceOnMap(name, lat, lng) {
    this.navigateTo("screen-map-home");
    if (this.mapInstance && typeof maplibregl !== "undefined") {
      setTimeout(() => {
        // Fly smoothly to selected place
        this.mapInstance.flyTo({ center: [lng, lat], zoom: 16.5 });

        // Remove previous search pin if any
        if (this.searchPinMarker) {
          this.searchPinMarker.remove();
          this.searchPinMarker = null;
        }

        // Create temporary highlight pin for the searched location
        const pinEl = document.createElement("div");
        pinEl.style.width = "24px";
        pinEl.style.height = "24px";
        pinEl.style.borderRadius = "50%";
        pinEl.style.background = "#2563eb";
        pinEl.style.border = "3px solid #ffffff";
        pinEl.style.boxShadow = "0 3px 10px rgba(37,99,235,0.5)";
        pinEl.style.cursor = "pointer";

        this.searchPinMarker = new maplibregl.Marker({ element: pinEl, anchor: "center" })
          .setLngLat([lng, lat])
          .setPopup(
            new maplibregl.Popup({ offset: 12 })
              .setHTML(`<b>${name}</b><br><small style="color: #64748b;">Địa điểm bạn đã tìm kiếm</small>`)
          )
          .addTo(this.mapInstance);

        // Auto toggle popup
        this.searchPinMarker.togglePopup();
      }, 200);
    }
    this.showToast(`Đã định vị: ${name}`);
  },

  };
})(window);
