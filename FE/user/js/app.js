/**
 * Application Controller & UI Navigation Logic
 * Smart E-Mobility Hub - End-User App
 */

const App = {
  currentScreenId: "screen-login",
  mapInstance: null,
  mapMarkers: [],
  searchPinMarker: null,
  currentQuery: "",

  async init() {
    console.log("Smart E-Mobility App Initialized.");
    this.updateBottomNavVisibility("screen-login");
    this.bindEvents();
    this.startRideTicker();
    this.initMapLibre();
    this.renderSearchList();

    // Auto sync dynamic data from BE
    await this.loadInitialDataFromBE();

    // Auto resize map when window size changes (Mobile orientation or Desktop resize)
    window.addEventListener("resize", () => {
      if (this.mapInstance) {
        try { this.mapInstance.resize(); } catch (e) {}
      }
    });
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
  },

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

      // Load user vehicles dynamically from BE
      const vehicles = await ApiService.getUserVehicles();
      if (vehicles && vehicles.length) {
        AppState.user.vehicles = vehicles;
        const optionsHtml = vehicles.map(v => `<option value="${v.type} · ${v.plate_number}">${v.type} · ${v.plate_number} (${v.model || ''})</option>`).join("");
        ["parkingPersonalVehicle", "chargingPersonalVehicle", "swapPersonalVehicle"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.innerHTML = optionsHtml;
        });
        if (vehicles[0]) {
          AppState.bookingDraft.personalPlate = vehicles[0].plate_number;
        }
      }
    } catch (e) {
      console.warn("Could not load user profile from BE:", e);
    }
  },

  async loadHubsFromBE() {
    try {
      const hubs = await ApiService.getHubs();
      if (hubs && hubs.length) {
        AppState.hubs = hubs;
        this.renderSearchList();
        if (hubs[0]) {
          this.populateHubData(hubs[0]);
        }
      }
    } catch (e) {
      console.warn("Could not load hubs from BE:", e);
    }
  },

  bindEvents() {
    // Listen for history changes if needed
    window.addEventListener("popstate", (e) => {
      if (e.state && e.state.screenId) {
        this.navigateTo(e.state.screenId, false);
      }
    });

    // Destination Hub Change Listener
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
   * Navigate to any of the 58 wireframe screens seamlessly
   */
  navigateTo(screenId, pushHistory = true) {
    if (!screenId) return;
    const targetScreen = document.getElementById(screenId);
    if (!targetScreen) {
      console.warn(`Screen ${screenId} not found!`);
      return;
    }

    // Hide all screens
    const allScreens = document.querySelectorAll(".screen");
    allScreens.forEach(s => s.classList.remove("active"));

    // Activate target
    targetScreen.classList.add("active");
    this.currentScreenId = screenId;

    // Scroll viewport to top
    const viewport = document.getElementById("viewport");
    if (viewport) viewport.scrollTop = 0;

    // Update bottom nav bar state
    this.updateBottomNavState(screenId);

    // Sync dynamic data from backend when navigating to specific screens
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
    }

    // Resize map when entering map home
    if (screenId === "screen-map-home" && this.mapInstance) {
      setTimeout(() => {
        try { this.mapInstance.resize(); } catch (e) {}
      }, 100);
    }

    // Push to browser history for back button support
    if (pushHistory) {
      history.pushState({ screenId }, "", `#${screenId}`);
    }
  },

  updateBottomNavState(screenId) {
    const bottomNav = document.getElementById("globalBottomNav");
    if (!bottomNav) return;

    // Hide bottom nav on auth screens
    const noNavScreens = [
      "screen-login", "screen-register", "screen-forgot-password", 
      "screen-reset-requested", "screen-pickup", "screen-payment-pending"
    ];

    if (noNavScreens.includes(screenId)) {
      bottomNav.classList.add("hidden");
    } else {
      bottomNav.classList.remove("hidden");
    }

    // Update active tab highlight
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

  updateBottomNavVisibility(screenId) {
    this.updateBottomNavState(screenId);
  },

  showToast(message) {
    const toast = document.getElementById("toastMessage");
    const toastText = document.getElementById("toastText");
    if (toast && toastText) {
      toastText.innerText = message;
      toast.classList.add("show");
      setTimeout(() => {
        toast.classList.remove("show");
      }, 2500);
    }
  },

  /* ================= 1. AUTHENTICATION ================= */
  async handleLogin(e) {
    if (e) e.preventDefault();
    const phone = document.getElementById("loginPhone").value;
    const pass = document.getElementById("loginPassword").value;
    
    const res = await ApiService.login(phone, pass);
    if (res.success) {
      if (res.user) {
        AppState.user = { ...AppState.user, ...res.user };
      }
      await this.loadInitialDataFromBE();
      this.showToast("Đăng nhập thành công!");
      this.navigateTo("screen-map-home");
    }
  },

  async handleRegister(e) {
    if (e) e.preventDefault();
    this.showToast("Tạo tài khoản thành công!");
    this.navigateTo("screen-login");
  },

  handleLogout() {
    this.showToast("Đã đăng xuất tài khoản.");
    this.navigateTo("screen-login");
  },

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

  setPaymentPreference(pref) {
    AppState.user.paymentMethod = pref;
    const isWallet = pref === "Ví điện tử";

    document.getElementById("prefWallet").classList.toggle("selected", isWallet);
    document.getElementById("prefBank").classList.toggle("selected", !isWallet);

    document.getElementById("radioPrefWallet").classList.toggle("checked", isWallet);
    document.getElementById("radioPrefBank").classList.toggle("checked", !isWallet);
  },

  /* ================= 2. MAP & HUBS ================= */
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
      if (isSelected && !AppState.bookingDraft.selectedBike) {
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

  /* ================= 3. BOOKING WIZARD ================= */
  switchBookingTab(targetScreen) {
    this.navigateTo(targetScreen);
  },

  selectBike(bikeId, battery, elementId) {
    AppState.bookingDraft.selectedBike = bikeId;
    AppState.bookingDraft.bikeBattery = battery;

    document.querySelectorAll("#screen-select-bike .card-box").forEach(el => el.classList.remove("selected"));
    document.querySelectorAll("#screen-select-bike .radio-circle").forEach(el => el.classList.remove("checked"));

    const item = document.getElementById(elementId);
    if (item) {
      item.classList.add("selected");
      const r = item.querySelector(".radio-circle");
      if (r) r.classList.add("checked");
    }
    this.showToast(`Đã chọn xe ${bikeId} (${battery}%)`);
  },

  selectCharger(chargerName, elementId) {
    AppState.bookingDraft.chargingPort = chargerName;
    document.querySelectorAll("#screen-select-charging .card-box").forEach(el => el.classList.remove("selected"));
    document.querySelectorAll("#screen-select-charging .radio-circle").forEach(el => el.classList.remove("checked"));

    const item = document.getElementById(elementId);
    if (item) {
      item.classList.add("selected");
      const r = item.querySelector(".radio-circle");
      if (r) r.classList.add("checked");
    }
  },

  async confirmBooking(planType) {
    if (planType === "swap") {
      return this.confirmSwapAndPay();
    }
    if (planType === "rental") {
      return this.confirmRentalAndPay();
    }
    const payload = {
      plan_type: planType,
      hub_id: AppState.bookingDraft.hubId,
      personal_plate: AppState.bookingDraft.personalPlate,
      services: [
        {
          service_type: planType,
          detail: "Chỗ đỗ + Sạc",
          price_est: 20000
        }
      ]
    };

    const newBooking = await ApiService.createBooking(payload);
    AppState.bookings.unshift(newBooking);

    const successIdEl = document.getElementById("successBookingId");
    if (successIdEl) successIdEl.innerText = `Mã đặt: ${newBooking.id || 'EMH-1024'}`;

    this.showToast("Đặt chỗ giữ tài nguyên thành công!");
    this.navigateTo("screen-booking-success");
  },

  async confirmRental() {
    const destHubName = document.getElementById("selectDestHub") 
      ? document.getElementById("selectDestHub").value 
      : "Hub Đại học Bách khoa";

    const payload = {
      plan_type: "rental",
      hub_id: AppState.bookingDraft.hubId || "hub-01",
      destination_hub_name: destHubName,
      personal_plate: null,
      resource_name: `${AppState.bookingDraft.selectedBike || "XE-024"} · Xe đạp điện`,
      services: [
        {
          service_type: "rental",
          detail: `Thuê xe đạp điện ${AppState.bookingDraft.selectedBike || 'XE-024'} (Pin ${AppState.bookingDraft.bikeBattery || 85}%)`,
          price_est: 10000
        }
      ]
    };

    let newBooking = null;
    try {
      newBooking = await ApiService.createBooking(payload);
      if (newBooking) {
        AppState.bookings.unshift(newBooking);
        AppState.selectedBookingId = newBooking.id;
      }
    } catch (e) {
      console.warn("createBooking error:", e);
    }

    const bookingCode = newBooking && newBooking.id ? newBooking.id : "EMH-1025";
    const successIdEl = document.getElementById("successBookingId");
    if (successIdEl) successIdEl.innerText = `Mã đặt: ${bookingCode}`;

    this.showToast("Đặt xe thành công! Xe đã được giữ trước cho bạn.");
    this.renderBookings();
    this.navigateTo("screen-booking-success");
  },

  payAndStartRide() {
    this.showToast("Đang chuyển sang thanh toán cước thuê xe...");
    this.setupInvoiceAndPay("rental", 10000, "screen-vehicle-ready", true);
  },

  async confirmSwapAndPay() {
    const payload = {
      plan_type: "swap",
      hub_id: AppState.bookingDraft.hubId || "HUB-METRO",
      personal_plate: AppState.bookingDraft.personalPlate || "59-X1 123.45",
      services: [
        {
          service_type: "swap",
          detail: "Đổi pin xe điện B48 (2 pin)",
          price_est: 25000
        }
      ]
    };

    try {
      const newBooking = await ApiService.createBooking(payload);
      AppState.bookings.unshift(newBooking);
    } catch (e) {}

    this.showToast("Đã xác nhận đặt pin. Đang chuyển sang thanh toán...");
    this.setupInvoiceAndPay("swap", 25000, "screen-review-swap", false);
  },

  async executeCancelBooking() {
    const targetId = AppState.selectedBookingId || "EMH-1023";
    try {
      await ApiService.cancelBooking(targetId);
      const found = AppState.bookings.find(b => b.id === targetId);
      if (found) {
        found.status = "Đã hủy";
      }
    } catch (e) {
      console.warn("Cancel booking error:", e);
    }
    this.showToast(`Đã hủy đặt chỗ ${targetId} thành công.`);
    // Immediately remove from screen-my-bookings
    this.renderBookings();
    // Immediately display in screen-booking-history
    this.renderBookingHistory();
    this.navigateTo("screen-cancelled");
  },

  async loadBookings() {
    try {
      const bookings = await ApiService.getBookings();
      if (bookings && bookings.length) {
        const cancelledIds = (AppState.bookings || [])
          .filter(b => b.status === "Đã hủy")
          .map(b => b.id);

        AppState.bookings = bookings.map(b => {
          if (cancelledIds.includes(b.id)) {
            return { ...b, status: "Đã hủy" };
          }
          return b;
        });
      }
    } catch (e) {
      console.warn("Could not load bookings from BE:", e);
    }
    this.renderBookings();
    this.renderBookingHistory();
  },

  renderBookings() {
    const container = document.getElementById("bookingCardsContainer");
    if (!container) return;

    // Filter out cancelled bookings so they NO LONGER appear in screen-my-bookings
    const activeList = (AppState.bookings || []).filter(b => b.status !== "Đã hủy" && b.status !== "Hoàn thành" && b.status !== "Đã hoàn thành");

    if (activeList.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-regular fa-calendar-xmark" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
          <div style="font-weight: 600;">Bạn không có đặt chỗ nào sắp tới</div>
          <div style="font-size: 12px; margin-top: 4px;">Các đơn đã hủy hoặc hoàn tất đã được lưu trong tab "Lịch sử".</div>
          <button class="btn-secondary" style="margin-top: 14px; font-size: 12px; border-radius: 20px;" onclick="App.navigateTo('screen-booking-history')">Xem lịch sử đặt chỗ</button>
        </div>
      `;
      return;
    }

    container.innerHTML = activeList.map(bk => {
      const isRental = bk.plan_type === "rental" || bk.planType === "rental";
      const isSwap = bk.plan_type === "swap" || bk.planType === "swap";
      const planTitle = isRental ? "Thuê xe" : (isSwap ? "Đổi pin" : "Xe cá nhân");
      const resourceText = bk.resource_name || (bk.services && bk.services[0] ? bk.services[0].detail : (bk.personal_plate ? `Biển số: ${bk.personal_plate}` : 'Tài nguyên đã đặt'));
      const hubText = bk.hub_name || bk.hubName || "Hub Ga Metro ĐHQG";
      const holdText = bk.hold_until ? `Giữ đến ${bk.hold_until}` : (bk.created_at || "Đã xác nhận");
      const statusText = bk.status || "Đã xác nhận";

      return `
        <div class="card-box" style="margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 800; font-size: 14.5px;">${bk.id} · ${planTitle}</span>
            <span style="font-size: 11px; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 4px; font-weight: 600;">${statusText}</span>
          </div>
          <div style="font-size: 13px; margin-bottom: 4px;">${resourceText} · ${hubText}</div>
          <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px;">${holdText}</div>
          <button class="${isRental ? 'btn-primary' : 'btn-secondary'}" onclick="App.openBookingDetail('${bk.id}')">${isRental ? 'Chi tiết và nhận xe' : 'Xem chi tiết đặt trước'}</button>
        </div>
      `;
    }).join("");
  },

  renderBookingHistory() {
    const container = document.getElementById("bookingHistoryContainer");
    if (!container) return;

    // Collect all cancelled bookings from AppState.bookings
    const cancelledFromBookings = (AppState.bookings || [])
      .filter(b => b.status === "Đã hủy")
      .map(b => ({
        id: b.id,
        planType: b.plan_type || b.planType || "rental",
        hubName: b.hub_name || b.hubName || "Hub Ga Metro ĐHQG",
        resourceName: b.resource_name || (b.services && b.services[0] ? b.services[0].detail : "Tài nguyên"),
        status: "Đã hủy",
        createdAt: b.created_at || "18/10/2026",
        totalPrice: b.total_price || 0
      }));

    // Combine with historyBookings without duplicating by id
    const existingIds = new Set(cancelledFromBookings.map(b => b.id));
    const otherHistory = (AppState.historyBookings || []).filter(b => !existingIds.has(b.id));

    const combinedList = [...cancelledFromBookings, ...otherHistory];

    if (combinedList.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-regular fa-clock" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
          <div style="font-weight: 600;">Chưa có lịch sử đặt chỗ</div>
          <div style="font-size: 12px; margin-top: 4px;">Lịch sử chuyến đi và các đơn đã hủy sẽ hiển thị tại đây.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = combinedList.map(item => {
      const isCancelled = item.status === "Đã hủy";
      const statusBadge = isCancelled 
        ? `<span style="font-size: 11px; background: #fee2e2; color: #ef4444; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Đã hủy</span>`
        : `<span style="font-size: 11px; background: #ecfdf5; color: #10b981; padding: 2px 8px; border-radius: 4px; font-weight: 700;">Hoàn thành</span>`;
      
      const typeLabel = item.planType === "rental" ? "Thuê xe" : (item.planType === "swap" ? "Đổi pin" : "Đỗ xe cá nhân");
      const detailText = isCancelled 
        ? `${item.createdAt || '18/10/2026'} · Đã hủy & hoàn tài nguyên`
        : `${item.createdAt || 'Gần đây'} · ${(item.totalPrice || 15000).toLocaleString()}đ`;

      return `
        <div class="card-box" style="margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; font-size: 14px;">${item.id} · ${typeLabel}</span>
            ${statusBadge}
          </div>
          <div style="font-size: 13px; margin-bottom: 3px;">${item.resourceName || item.hubName || 'Hub Ga Metro ĐHQG'}</div>
          <div style="font-size: 12px; color: var(--text-muted);">${detailText}</div>
        </div>
      `;
    }).join("");
  },

  openBookingDetail(bookingId) {
    const bk = AppState.bookings.find(b => b.id === bookingId) || AppState.bookings[0];
    if (!bk) return;

    AppState.selectedBookingId = bk.id;

    const subEl = document.getElementById("bookingDetailSubtitle");
    if (subEl) {
      const typeLabel = bk.plan_type === "rental" || bk.planType === "rental" ? "Xe dùng chung" : (bk.plan_type === "swap" ? "Đổi pin" : "Xe cá nhân");
      subEl.innerText = `${bk.id} · ${typeLabel}`;
    }

    const stEl = document.getElementById("bookingDetailStatus");
    if (stEl) {
      stEl.innerText = bk.status || "Đã xác nhận";
      if (bk.status === "Đã hủy") {
        stEl.style.borderColor = "#ef4444";
        stEl.style.color = "#ef4444";
      } else {
        stEl.style.borderColor = "#0f172a";
        stEl.style.color = "#0f172a";
      }
    }

    const resEl = document.getElementById("bookingDetailResource");
    if (resEl) {
      resEl.innerText = bk.resource_name || (bk.services && bk.services[0] ? bk.services[0].detail : "XE-024 · Pin 85%");
    }

    const origEl = document.getElementById("bookingDetailOriginHub");
    if (origEl) origEl.innerText = bk.hub_name || bk.hubName || "Hub Ga Metro ĐHQG";

    const destEl = document.getElementById("bookingDetailDestHub");
    if (destEl) destEl.innerText = bk.destination_hub_name || "ĐH Bách khoa";

    const timeEl = document.getElementById("bookingDetailTime");
    if (timeEl) timeEl.innerText = bk.created_at || "08:00";

    const holdEl = document.getElementById("bookingDetailHoldUntil");
    if (holdEl) holdEl.innerText = bk.hold_until || "08:10";

    this.navigateTo("screen-booking-detail");
  },

  switchBookingListTab(tab) {
    document.getElementById("tabBookingUpcoming").classList.toggle("active", tab === "upcoming");
    document.getElementById("tabBookingActive").classList.toggle("active", tab === "active");
    document.getElementById("tabBookingHistory").classList.toggle("active", tab === "history");

    if (tab === "history") {
      this.navigateTo("screen-booking-history");
    } else if (tab === "active") {
      this.navigateTo("screen-active-services");
    }
  },

  /* ================= 4. ACTIVE SERVICES & OPERATION ================= */
  async loadActiveServices() {
    try {
      const active = await ApiService.getActiveServices();
      if (active) {
        AppState.activeServices = active;
        this.renderActiveServices(active);
      }
    } catch (e) {
      console.warn("Could not load active services:", e);
    }
  },

  renderActiveServices(data) {
    const container = document.getElementById("activeServicesContainer");
    if (!container || !data) return;

    // Dynamically update map bottom floating pill
    const pill = document.getElementById("activeRidePill");
    if (pill) {
      if (data.ride) {
        pill.style.display = "flex";
        const pillText = document.getElementById("activeRidePillText");
        if (pillText) {
          pillText.innerText = `Chuyến đi: ${data.ride.vehicle_id || data.ride.vehicleId} đang hoạt động`;
        }
      } else {
        pill.style.display = "none";
      }
    }

    let items = [];
    if (data.ride) {
      items.push(`
        <div class="card-box selectable" onclick="App.navigateTo('screen-ride-active')">
          <div>
            <div style="font-weight: 700; font-size: 14px;">Xe đạp điện ${data.ride.vehicle_id || data.ride.vehicleId}</div>
            <div style="font-size: 12px; color: var(--text-muted);">${data.ride.status || 'Đang sử dụng'} · ${data.ride.elapsed_minutes || data.ride.elapsedMinutes || 13} phút</div>
          </div>
          <span style="font-size: 11px; background: #ecfdf5; color: #10b981; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Hoạt động</span>
        </div>
      `);

      const rideSub = document.getElementById("rideActiveSubtitle");
      if (rideSub) rideSub.innerText = `${data.ride.vehicle_id || data.ride.vehicleId} · ${data.ride.origin_hub || data.ride.originHub} → ${data.ride.destination_hub || data.ride.destHub}`;
      const timerEl = document.getElementById("rideTimer");
      if (timerEl) timerEl.innerText = `${data.ride.elapsed_minutes || data.ride.elapsedMinutes || 13} phút`;
      const batEl = document.getElementById("rideBatteryLevel");
      if (batEl) batEl.innerText = `${data.ride.battery_level || data.ride.batteryLevel || 78}%`;
      const stEl = document.getElementById("rideStatusBadge");
      if (stEl) stEl.innerText = data.ride.status || "Đang sử dụng";
    }

    if (data.parking) {
      items.push(`
        <div class="card-box selectable" onclick="App.navigateTo('screen-parking-active')">
          <div>
            <div style="font-weight: 700; font-size: 14px;">Gửi xe cá nhân (${data.parking.plate_number || data.parking.plate})</div>
            <div style="font-size: 12px; color: var(--text-muted);">Chỗ đỗ ${data.parking.slot_id || data.parking.slot} · ${data.parking.elapsed_minutes || data.parking.elapsedMinutes || 45} phút</div>
          </div>
          <span style="font-size: 11px; background: #e0f2fe; color: #0284c7; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Đang đỗ</span>
        </div>
      `);

      const parkSub = document.getElementById("parkingActiveSubtitle");
      if (parkSub) parkSub.innerText = `EMH-1024 · ${data.parking.hub_name || data.parking.hubName}`;
      const parkPlate = document.getElementById("parkingActivePlate");
      if (parkPlate) parkPlate.innerText = data.parking.plate_number || data.parking.plate;
      const parkSlot = document.getElementById("parkingActiveSlot");
      if (parkSlot) parkSlot.innerText = data.parking.slot_id || data.parking.slot;
      const parkIn = document.getElementById("parkingActiveCheckin");
      if (parkIn) parkIn.innerText = data.parking.checkin_time || data.parking.checkin || "10:00";
    }

    if (data.charging) {
      items.push(`
        <div class="card-box selectable" onclick="App.navigateTo('screen-charging-active')">
          <div>
            <div style="font-weight: 700; font-size: 14px;">Sạc trụ nhanh ${data.charging.port_id || data.charging.port}</div>
            <div style="font-size: 12px; color: var(--text-muted);">Đã nạp ${data.charging.power_consumed_kwh || data.charging.powerConsumed || 2.4} kWh · ${data.charging.current_charge || data.charging.batteryPercent || 65}%</div>
          </div>
          <span style="font-size: 11px; background: #fef3c7; color: #d97706; font-weight: 700; padding: 2px 8px; border-radius: 4px;">Đang sạc</span>
        </div>
      `);

      const chgPort = document.getElementById("chargingActivePort");
      if (chgPort) chgPort.innerText = `Trụ sạc ${data.charging.port_id || data.charging.port}`;
      const chgPct = document.getElementById("chargingActivePercent");
      if (chgPct) chgPct.innerText = `${data.charging.current_charge || data.charging.batteryPercent || 65}%`;
      const chgPwr = document.getElementById("chargingActivePower");
      if (chgPwr) chgPwr.innerText = `${data.charging.power_consumed_kwh || data.charging.powerConsumed || 2.4} kWh`;
      const chgTime = document.getElementById("chargingActiveTime");
      if (chgTime) chgTime.innerText = `${data.charging.elapsed_minutes || data.charging.elapsedMinutes || 25} phút`;
    }

    if (items.length > 0) {
      container.innerHTML = items.join("");
    }
  },

  updateReviewRentalView() {
    const bike = AppState.bookingDraft.selectedBike || "XE-024";
    const batt = AppState.bookingDraft.bikeBattery || 85;
    const origin = AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";
    const destSelect = document.getElementById("selectDestHub");
    const dest = destSelect ? destSelect.value : "Hub Đại học Bách khoa";

    const rBike = document.getElementById("reviewRentalBike");
    if (rBike) rBike.innerText = `${bike} (Pin ${batt}%)`;
    const rOrig = document.getElementById("reviewRentalOriginHub");
    if (rOrig) rOrig.innerText = origin;
    const rDest = document.getElementById("reviewRentalDestHub");
    if (rDest) rDest.innerText = dest;
    const rNote = document.getElementById("reviewRentalPolicyNote");
    if (rNote) rNote.innerText = `Thời gian giữ xe: 10 phút sau khi xác nhận. Cước phí tạm tính: 10,000đ/giờ (thanh toán khi quét mã mở xe tại Hub).`;
  },

  updateReviewParkingView() {
    const plateEl = document.getElementById("parkingPersonalVehicle");
    const plate = plateEl ? plateEl.value : "Xe máy điện · 59-X1 123.45";
    const timeEl = document.getElementById("parkingArrivalTime");
    const time = timeEl ? timeEl.value : "18/10/2026 · 10:00";
    const durEl = document.getElementById("parkingDuration");
    const dur = durEl ? durEl.value : "2 giờ";
    const hub = AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";

    const rPlate = document.getElementById("reviewParkingPlate");
    if (rPlate) rPlate.innerText = plate;
    const rSlot = document.getElementById("reviewParkingSlotHub");
    if (rSlot) rSlot.innerText = `Chỗ đỗ khả dụng (${hub})`;
    const rTime = document.getElementById("reviewParkingTime");
    if (rTime) rTime.innerText = `${time} (${dur})`;
  },

  updateReviewSwapView() {
    const typeEl = document.getElementById("swapBatteryType");
    const bType = typeEl ? typeEl.value : "Pin chuẩn 48V-20Ah";
    const qtyEl = document.getElementById("swapBatteryQuantity");
    const qty = qtyEl ? qtyEl.value : "1 pin";
    const hub = AppState.bookingDraft.hubName || "Hub Ga Metro ĐHQG";

    const rType = document.getElementById("reviewSwapType");
    if (rType) rType.innerText = `${bType} (${qty})`;
    const rHub = document.getElementById("reviewSwapHub");
    if (rHub) rHub.innerText = `Tủ pin ${hub}`;
    const rFee = document.getElementById("reviewSwapFee");
    if (rFee) rFee.innerText = `${(25000 * (parseInt(qty) || 1)).toLocaleString()}đ / lần`;
  },

  async startRide() {
    const bookingId = AppState.selectedBookingId;

    if (!bookingId) {
      this.showToast("Không tìm thấy mã đặt xe!");
      return;
    }

    try {
      // Gọi API Backend
      const result = await ApiService.startRide(bookingId);

      // Cập nhật dữ liệu chuyến đi trên Frontend
      AppState.activeServices = {
        ...AppState.activeServices,
        has_active: true,
        ride: result.ride
      };

      AppState.activeRide = {
        vehicleId: result.ride.vehicle_id,
        elapsedMinutes: result.ride.elapsed_minutes,
        status: result.ride.status
      };

      // Cập nhật trạng thái Booking
      const booking = AppState.bookings.find(
        b => b.id === bookingId
      );

      if (booking) {
        booking.status = "Đang sử dụng";
      }

      // Chỉ chuyển màn hình khi Backend thành công
      this.showToast("Bắt đầu tính thời gian di chuyển!");
      this.navigateTo("screen-ride-active");

    } catch (error) {
      console.error("Start ride error:", error);
      this.showToast(error.message || "Không thể bắt đầu chuyến đi!");
    }
  },

  startRideTicker() {
    let minutes = AppState.activeServices?.ride?.elapsed_minutes || AppState.activeRide?.elapsedMinutes || 0;
    setInterval(() => {
      minutes++;
      const timerEl = document.getElementById("rideTimer");
      if (timerEl) {
        timerEl.innerText = `${minutes} phút`;
      }
    }, 60000);
  },

  async finishReturnRental() {
    try {
      const activeRide = AppState.activeServices?.ride || AppState.activeRide;
      const vehId = activeRide?.vehicle_id || activeRide?.vehicleId || "XE-024";
      const hubId = activeRide?.destination_hub_id || AppState.bookingDraft.hubId || "hub-02";

      const res = await ApiService.returnVehicle({ vehicle_id: vehId, hub_id: hubId });
      if (res && res.success) {
        this.showToast(res.message || "Xe đã được khóa chốt tại Hub!");
        this.navigateTo("screen-invoice-rental");
      } else {
        this.navigateTo("screen-service-rejected");
      }
    } catch (e) {
      this.showToast("Xe đã được khóa chốt tại Hub!");
      this.navigateTo("screen-invoice-rental");
    }
  },

  selectChargerSlot(slotText, elementId) {
    document.querySelectorAll("#screen-select-charging .card-box").forEach(c => c.classList.remove("selected"));
    document.querySelectorAll("#screen-select-charging .radio-circle").forEach(r => r.classList.remove("checked"));
    const el = document.getElementById(elementId);
    if (el) {
      el.classList.add("selected");
      const rc = el.querySelector(".radio-circle");
      if (rc) rc.classList.add("checked");
      const radio = el.querySelector("input[type='radio']");
      if (radio) radio.checked = true;
    }
  },

  finishParkingExit() {
    this.showToast("Đã xác nhận xe rời chỗ đỗ P08!");
    this.navigateTo("screen-map-home");
  },

  finishChargingSession() {
    this.showToast("Đã dừng sạc điện an toàn.");
    this.navigateTo("screen-invoice-charging");
  },

  finishBatterySwap() {
    this.showToast("Đã nhận pin 100% thành công.");
    this.navigateTo("screen-invoice-swap");
  },

  /* ================= 5. INVOICE & PAYMENT ================= */
  async setupInvoiceAndPay(type, defaultAmount, returnScreen = "screen-invoice-rental", startRideOnSuccess = false) {
    AppState.currentInvoice.type = type;
    AppState.currentInvoice.returnScreen = returnScreen;
    AppState.currentInvoice.startRideOnSuccess = startRideOnSuccess;

    let amount = defaultAmount;
    try {
      const invData = await ApiService.getInvoice(type);
      if (invData && invData.total_amount) {
        amount = invData.total_amount;
        AppState.currentInvoice.id = invData.id;
        AppState.currentInvoice.amount = invData.total_amount;

        // Populate invoice screen details
        if (type === "rental") {
          const itemLabel = document.getElementById("invoiceRentalItemLabel");
          if (itemLabel && invData.items && invData.items[0]) itemLabel.innerText = invData.items[0].label;
          const itemCost = document.getElementById("invoiceRentalItemCost");
          if (itemCost && invData.items && invData.items[0]) itemCost.innerText = `${invData.items[0].amount.toLocaleString()} đ`;
          const totCost = document.getElementById("invoiceRentalTotalCost");
          if (totCost) totCost.innerText = `${invData.total_amount.toLocaleString()} đ`;
        } else if (type === "charging") {
          const itemLabel = document.getElementById("invoiceChargingItemLabel");
          if (itemLabel && invData.items && invData.items[0]) itemLabel.innerText = invData.items[0].label;
          const itemCost = document.getElementById("invoiceChargingItemCost");
          if (itemCost && invData.items && invData.items[0]) itemCost.innerText = `${invData.items[0].amount.toLocaleString()} đ`;
          const totCost = document.getElementById("invoiceChargingTotalCost");
          if (totCost) totCost.innerText = `${invData.total_amount.toLocaleString()} đ`;
        } else if (type === "swap") {
          const itemLabel = document.getElementById("invoiceSwapItemLabel");
          if (itemLabel && invData.items && invData.items[0]) itemLabel.innerText = invData.items[0].label;
          const itemCost = document.getElementById("invoiceSwapItemCost");
          if (itemCost && invData.items && invData.items[0]) itemCost.innerText = `${invData.items[0].amount.toLocaleString()} đ`;
          const totCost = document.getElementById("invoiceSwapTotalCost");
          if (totCost) totCost.innerText = `${invData.total_amount.toLocaleString()} đ`;
        }
      }
    } catch (e) {
      console.warn("Fetch invoice error:", e);
    }

    AppState.currentInvoice.amount = amount;

    const payDisp = document.getElementById("payAmountDisplay");
    const confDisp = document.getElementById("confirmPayAmount");
    const payDesc = document.getElementById("payServiceDesc");
    const confTitle = document.getElementById("confirmPayTitle");

    if (payDisp) payDisp.innerText = `${amount.toLocaleString()} đ`;
    if (confDisp) confDisp.innerText = `${amount.toLocaleString()} đ`;

    if (payDesc) {
      if (type === "swap" || type === "battery_swap") {
        payDesc.innerText = "Hóa đơn dịch vụ đổi pin xe điện";
      } else if (type === "rental") {
        payDesc.innerText = "Hóa đơn cước thuê xe điện (XE-024)";
      } else if (type === "charging") {
        payDesc.innerText = "Hóa đơn dịch vụ sạc xe điện";
      } else if (type === "parking") {
        payDesc.innerText = "Hóa đơn dịch vụ giữ xe cá nhân";
      } else {
        payDesc.innerText = "Hóa đơn dịch vụ Smart E-Mobility";
      }
    }

    if (confTitle) {
      if (type === "swap" || type === "battery_swap") {
        confTitle.innerText = "Xác nhận thanh toán dịch vụ đổi pin";
      } else if (type === "rental") {
        confTitle.innerText = "Xác nhận thanh toán cước thuê xe";
      } else {
        confTitle.innerText = "Xác nhận trừ tiền từ ví";
      }
    }

    const payMethodBackBtn = document.querySelector("#screen-payment-method .nav-back");
    if (payMethodBackBtn) {
      payMethodBackBtn.setAttribute("onclick", `App.navigateTo('${returnScreen}')`);
    }

    this.navigateTo("screen-payment-method");
  },

  selectPayMethod(method, elementId) {
    AppState.user.paymentMethod = method;

    document.querySelectorAll("#screen-payment-method .card-box").forEach(c => c.classList.remove("selected"));
    document.querySelectorAll("#screen-payment-method .radio-circle").forEach(r => r.classList.remove("checked"));

    const item = document.getElementById(elementId);
    if (item) {
      item.classList.add("selected");
      const r = item.querySelector(".radio-circle");
      if (r) r.classList.add("checked");
    }

    const confMethod = document.getElementById("confirmPayMethod");
    if (confMethod) confMethod.innerText = method;
  },

  async executePaymentProcess() {
    this.navigateTo("screen-payment-pending");
    try {
      await ApiService.payInvoice({
        invoice_id: AppState.currentInvoice.id || "INV-2026-901",
        method: AppState.user.paymentMethod,
        amount: AppState.currentInvoice.amount
      });
    } catch (e) {
      console.warn("Pay invoice error:", e);
    }

    const willStartRide = AppState.currentInvoice.startRideOnSuccess;

    setTimeout(() => {
      this.showToast("Thanh toán thành công!");

      const successBtn = document.getElementById("btnPaymentSuccessAction");
      if (successBtn) {
        if (willStartRide) {
          successBtn.innerText = "Bắt đầu chuyến đi";
        } else {
          successBtn.innerText = "Về màn hình chính";
        }
      }

      this.navigateTo("screen-payment-success");

      // Tự động chuyển màn hình tiếp theo sau khi hiển thị thành công
      setTimeout(() => {
        const successEl = document.getElementById("screen-payment-success");
        if (successEl && successEl.classList.contains("active")) {
          this.handlePaymentSuccessNext();
        }
      }, 2000);
    }, 1200);
  },

  handlePaymentSuccessNext() {
    if (AppState.currentInvoice.startRideOnSuccess) {
      this.startRide();
    } else {
      this.navigateTo("screen-map-home");
      this.showToast("Đã hoàn tất thanh toán và trở về màn hình chính.");
    }
  },

  /* ================= 6. INCIDENT REPORTING ================= */
  async loadIncidents() {
    try {
      const incidents = await ApiService.getIncidents();
      if (incidents && incidents.length) {
        AppState.incidents = incidents;
      }
    } catch (e) {
      console.warn("Could not load incidents:", e);
    }
    this.renderIncidents();
  },

  renderIncidents() {
    const container = document.getElementById("incidentHistoryList");
    if (!container) return;

    if (!AppState.incidents || AppState.incidents.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <i class="fa-solid fa-clipboard-check" style="font-size: 32px; margin-bottom: 10px; opacity: 0.5;"></i>
          <div style="font-weight: 600;">Không có sự cố nào</div>
          <div style="font-size: 12px; margin-top: 4px;">Mọi thiết bị đang hoạt động ổn định!</div>
        </div>
      `;
      return;
    }

    container.innerHTML = AppState.incidents.map(inc => {
      const isResolved = inc.status === "Đã giải quyết";
      const statusColor = isResolved ? "#10b981" : "#d97706";
      const resCode = inc.resource_code || inc.resourceCode || "Thiết bị";
      const incType = inc.incident_type || inc.incidentType || "Sự cố";
      const dateStr = inc.created_at || inc.createdAt || "Hôm nay";

      return `
        <div class="card-box selectable" style="margin-bottom: 10px;" onclick="App.openIncidentDetail('${inc.id}')">
          <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-weight: 700; font-size: 14px;">${inc.id} · ${resCode}</span>
            <span style="font-size: 11.5px; color: ${statusColor}; font-weight: 600;">${inc.status}</span>
          </div>
          <div style="font-size: 12.5px; color: var(--text-muted);">${incType} · ${dateStr}</div>
        </div>
      `;
    }).join("");
  },

  openIncidentDetail(incId) {
    const inc = AppState.incidents.find(i => i.id === incId) || AppState.incidents[0];
    if (!inc) return;

    const idEl = document.getElementById("reportDetailId");
    if (idEl) idEl.innerText = inc.id;

    const stEl = document.getElementById("reportDetailStatus");
    if (stEl) {
      stEl.innerText = inc.status;
      const isResolved = inc.status === "Đã giải quyết";
      stEl.style.background = isResolved ? "#ecfdf5" : "#fef3c7";
      stEl.style.color = isResolved ? "#10b981" : "#d97706";
    }

    const resEl = document.getElementById("reportDetailResource");
    if (resEl) resEl.innerText = `${inc.resource_code || inc.resourceCode} (${inc.resource_type || inc.resourceType || 'Thiết bị'})`;

    const hubEl = document.getElementById("reportDetailHub");
    if (hubEl) hubEl.innerText = inc.hub_name || inc.hubName || "Hub Ga Metro ĐHQG";

    const issueEl = document.getElementById("reportDetailIssue");
    if (issueEl) issueEl.innerText = `${inc.incident_type || inc.incidentType} - ${inc.description}`;

    const noteEl = document.getElementById("reportDetailOperatorNote");
    if (noteEl) noteEl.innerText = inc.operator_note || inc.operatorNote || "Đã tiếp nhận yêu cầu, kỹ thuật viên đang đến kiểm tra thiết bị.";

    this.navigateTo("screen-report-detail");
  },

  prepareReport(resourceType, resourceCode) {
    const typeSelect = document.getElementById("incResourceType");
    const codeInput = document.getElementById("incResourceCode");
    if (typeSelect) typeSelect.value = resourceType;
    if (codeInput) codeInput.value = resourceCode;
    this.navigateTo("screen-report-incident");
  },

  async handleIncidentSubmit(e) {
    if (e) e.preventDefault();
    const type = document.getElementById("incResourceType").value;
    const code = document.getElementById("incResourceCode").value;
    const hub = document.getElementById("incHubName").value;
    const incType = document.getElementById("incType").value;
    const desc = document.getElementById("incDescription").value;

    const payload = {
      resource_type: type,
      resource_code: code,
      hub_name: hub,
      incident_type: incType,
      description: desc
    };

    const newInc = await ApiService.reportIncident(payload);
    AppState.incidents.unshift(newInc);

    const sentIdEl = document.getElementById("createdIncidentId");
    if (sentIdEl) sentIdEl.innerText = newInc.id;

    this.renderIncidents();
    this.showToast("Đã gửi báo cáo đến Operator.");
    this.navigateTo("screen-report-sent");
  }
};

// Start application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
