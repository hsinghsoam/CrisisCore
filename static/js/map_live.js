// CrisisCore - Live Interactive Disaster Map (Leaflet & OpenStreetMap)

let mainMap = null;
let incidentLayerGroup = null;
let rescueLayerGroup = null;
let campLayerGroup = null;

let allIncidents = [];
let allTeams = [];
let allCamps = [];

function initDisasterMap() {
  const mapEl = document.getElementById("disasterMap");
  if (!mapEl) return;

  // Initialize center over India
  mainMap = L.map('disasterMap', {
    zoomControl: true,
    minZoom: 4,
    maxZoom: 18
  }).setView([21.7679, 78.8718], 5);

  // Modern Dark-themed / High-contrast OpenStreetMap layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors | CrisisCore Emergency Map'
  }).addTo(mainMap);

  incidentLayerGroup = L.layerGroup().addTo(mainMap);
  rescueLayerGroup = L.layerGroup().addTo(mainMap);
  campLayerGroup = L.layerGroup().addTo(mainMap);

  loadMapData();
}

async function loadMapData() {
  try {
    const res = await fetch("/api/map-data");
    const data = await res.json();

    if (data.success) {
      allIncidents = data.incidents || [];
      allTeams = data.rescue_teams || [];
      allCamps = data.relief_camps || [];
      renderMapLayers();
    }
  } catch (err) {
    console.error("Failed to load map telemetry:", err);
  }
}

function renderMapLayers() {
  if (!mainMap) return;

  incidentLayerGroup.clearLayers();
  rescueLayerGroup.clearLayers();
  campLayerGroup.clearLayers();

  const bounds = [];

  // 1. Incidents
  allIncidents.forEach(inc => {
    if (!inc.lat || !inc.lng) return;

    const latLng = [inc.lat, inc.lng];
    bounds.push(latLng);

    const pLevel = (inc.priority_level || "MEDIUM").toLowerCase();
    
    // Choose disaster icon
    let iconChar = "⚠️";
    if (inc.disaster_type.includes("Flood")) iconChar = "🌊";
    else if (inc.disaster_type.includes("Landslide")) iconChar = "⛰️";
    else if (inc.disaster_type.includes("Cyclone")) iconChar = "🌀";
    else if (inc.disaster_type.includes("Fire")) iconChar = "🔥";
    else if (inc.disaster_type.includes("Building")) iconChar = "🏚️";
    else if (inc.disaster_type.includes("Earthquake")) iconChar = "🌋";

    const customIcon = L.divIcon({
      className: `crisis-marker ${pLevel}`,
      html: `<span>${iconChar}</span>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
      popupAnchor: [0, -18]
    });

    const marker = L.marker(latLng, { icon: customIcon });

    const popupHtml = `
      <div class="map-popup-card">
        <div class="popup-header">
          <span class="popup-tracking">${inc.tracking_id}</span>
          <span class="badge-priority ${pLevel}">${inc.priority_level}</span>
        </div>
        <div class="popup-title">${inc.disaster_type}</div>
        <div class="popup-location">📍 ${inc.district}, ${inc.state}</div>
        <div class="popup-stats-row">
          <span>👥 Affected: <b>${inc.affected_count}</b></span>
          <span>🩹 Injured: <b>${inc.injured_count}</b></span>
        </div>
        <p style="font-size:0.75rem; color:#cbd5e1; margin-bottom:8px;">${inc.description ? inc.description.substring(0, 90) + '...' : ''}</p>
        <div class="popup-actions">
          <a href="/incident/${inc.tracking_id}" class="btn btn-primary btn-sm" style="flex:1;">View Dossier</a>
          <button onclick="openAssignModal(${inc.id}, '${inc.tracking_id}')" class="btn btn-outline btn-sm">Assign Unit</button>
        </div>
      </div>
    `;

    marker.bindPopup(popupHtml);
    incidentLayerGroup.addLayer(marker);
  });

  // 2. Rescue Teams
  allTeams.forEach(team => {
    if (!team.lat || !team.lng) return;

    const latLng = [team.lat, team.lng];
    const teamIcon = L.divIcon({
      className: 'crisis-marker rescue-team',
      html: `<span>🛡️</span>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -15]
    });

    const marker = L.marker(latLng, { icon: teamIcon });
    marker.bindPopup(`
      <div class="map-popup-card">
        <div class="popup-header">
          <span style="font-weight:700; color:#60a5fa;">${team.agency} RESCUE UNIT</span>
          <span class="badge-status ${team.status.toLowerCase().replace(' ', '-')}">${team.status}</span>
        </div>
        <div class="popup-title">${team.name}</div>
        <div class="popup-location">📍 Base: ${team.base_location}</div>
        <p style="font-size:0.75rem; color:#94a3b8;"><b>Lead:</b> ${team.contact_lead} (${team.phone})</p>
        <p style="font-size:0.72rem; color:#cbd5e1; margin-top:4px;"><b>Equipment:</b> ${team.capacity_info}</p>
      </div>
    `);
    rescueLayerGroup.addLayer(marker);
  });

  // 3. Verified Relief Camps & Hospitals
  allCamps.forEach(camp => {
    if (!camp.lat || !camp.lng) return;

    const isHospital = camp.type === "Hospital";
    const iconClass = isHospital ? "hospital" : "relief-camp";
    const emoji = isHospital ? "🏥" : "⛺";

    const campIcon = L.divIcon({
      className: `crisis-marker ${iconClass}`,
      html: `<span>${emoji}</span>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      popupAnchor: [0, -14]
    });

    const marker = L.marker([camp.lat, camp.lng], { icon: campIcon });
    marker.bindPopup(`
      <div class="map-popup-card">
        <div class="popup-header">
          <span style="font-weight:700; color:${isHospital ? '#f87171' : '#34d399'};">${camp.type.toUpperCase()}</span>
          <span style="font-size:0.7rem; color:#94a3b8;">✓ Verified Facility</span>
        </div>
        <div class="popup-title">${camp.name}</div>
        <div class="popup-location">📍 ${camp.district}, ${camp.state}</div>
        <div class="popup-stats-row">
          <span>Capacity: <b>${camp.total_capacity}</b></span>
          <span>Available: <b style="color:#34d399;">${camp.available_capacity}</b></span>
        </div>
        <p style="font-size:0.74rem; color:#94a3b8;">Emergency Desk: <b>${camp.contact_phone}</b></p>
      </div>
    `);
    campLayerGroup.addLayer(marker);
  });

  // Fit bounds if incidents exist
  if (bounds.length > 0) {
    mainMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
  }
}

// Layer Toggle Handlers
function toggleMapLayer(layerType, btn) {
  if (!mainMap) return;

  btn.classList.toggle("active");
  const isActive = btn.classList.contains("active");

  if (layerType === "incidents") {
    if (isActive) mainMap.addLayer(incidentLayerGroup);
    else mainMap.removeLayer(incidentLayerGroup);
  } else if (layerType === "teams") {
    if (isActive) mainMap.addLayer(rescueLayerGroup);
    else mainMap.removeLayer(rescueLayerGroup);
  } else if (layerType === "camps") {
    if (isActive) mainMap.addLayer(campLayerGroup);
    else mainMap.removeLayer(campLayerGroup);
  }
}

// Map Search Location helper
function searchMapLocation(query) {
  if (!query || !mainMap) return;
  const q = query.toLowerCase();

  const match = allIncidents.find(i => 
    i.district.toLowerCase().includes(q) || 
    i.state.toLowerCase().includes(q) || 
    i.address.toLowerCase().includes(q) ||
    i.tracking_id.toLowerCase().includes(q)
  );

  if (match) {
    mainMap.setView([match.lat, match.lng], 12);
    showToast(`Focused on ${match.district}, ${match.state}`, "info");
  } else {
    showToast("No active incidents found in this location.", "warning");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initDisasterMap();
});
