// CrisisCore - Citizen Portal & Emergency Reporting Handlers

const DISTRICTS_BY_STATE = {
  "Kerala": ["Ernakulam", "Wayanad", "Idukki", "Alappuzha", "Kottayam", "Thrissur", "Kozhikode", "Malappuram", "Thiruvananthapuram"],
  "Uttarakhand": ["Chamoli", "Dehradun", "Rudraprayag", "Uttarkashi", "Pithoragarh", "Tehri Garhwal", "Nainital", "Haridwar"],
  "Odisha": ["Puri", "Kendrapara", "Jagatsinghpur", "Balasore", "Bhadrak", "Ganjam", "Khordha", "Cuttack"],
  "Assam": ["Kamrup Metropolitan", "Dhubri", "Barpeta", "Morigaon", "Nagaon", "Golaghat", "Dhemaji", "Dibrugarh"],
  "Maharashtra": ["Mumbai", "Mumbai Suburban", "Thane", "Raigad", "Ratnagiri", "Pune", "Kolhapur", "Satara"],
  "Himachal Pradesh": ["Kullu", "Mandi", "Shimla", "Kinnaur", "Lahaul and Spiti", "Kangra", "Chamba"],
  "Tamil Nadu": ["Chennai", "Cuddalore", "Nagapattinam", "Kanyakumari", "Thanjavur", "Tirunelveli"],
  "West Bengal": ["South 24 Parganas", "North 24 Parganas", "Purba Medinipur", "Howrah", "Kolkata", "Darjeeling"],
  "Gujarat": ["Kutch", "Jamnagar", "Devbhumi Dwarka", "Porbandar", "Surat", "Valsad"]
};

let miniMap = null;
let miniMarker = null;

function initMiniMap(lat = 20.5937, lng = 78.9629) {
  const mapEl = document.getElementById("miniMapContainer");
  if (!mapEl) return;

  if (miniMap) {
    miniMap.remove();
  }

  miniMap = L.map('miniMapContainer', { zoomControl: true }).setView([lat, lng], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors'
  }).addTo(miniMap);

  miniMarker = L.marker([lat, lng], { draggable: true }).addTo(miniMap);
  miniMarker.bindPopup("<b>Incident Coordinates</b><br>Drag pin to exact location.").openPopup();

  miniMarker.on('dragend', function(e) {
    const pos = miniMarker.getLatLng();
    updateCoordsDisplay(pos.lat, pos.lng);
  });

  miniMap.on('click', function(e) {
    miniMarker.setLatLng(e.latlng);
    updateCoordsDisplay(e.latlng.lat, e.latlng.lng);
  });
}

function updateCoordsDisplay(lat, lng) {
  const latInput = document.getElementById("latInput");
  const lngInput = document.getElementById("lngInput");
  const textEl = document.getElementById("gpsCoordsDisplay");
  
  if (latInput) latInput.value = lat.toFixed(6);
  if (lngInput) lngInput.value = lng.toFixed(6);
  if (textEl) {
    textEl.textContent = `Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
  }
}

// HTML5 Geolocation
function acquireGpsLocation() {
  const statusEl = document.getElementById("gpsCoordsDisplay");
  if (!navigator.geolocation) {
    showToast("Geolocation is not supported by your browser.", "warning");
    return;
  }

  if (statusEl) statusEl.textContent = "Acquiring GPS satellite fix...";
  showToast("Detecting current coordinates...", "info");

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      updateCoordsDisplay(lat, lng);
      showToast("GPS Location acquired successfully!", "success");

      if (miniMap && miniMarker) {
        miniMap.setView([lat, lng], 15);
        miniMarker.setLatLng([lat, lng]);
      } else {
        initMiniMap(lat, lng);
      }
    },
    (error) => {
      console.warn("GPS error:", error);
      showToast("Could not access precise GPS. Please select location manually.", "warning");
      if (statusEl) statusEl.textContent = "GPS Unavailable. Please pinpoint manually.";
      if (!miniMap) initMiniMap(20.5937, 78.9629);
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}

// Indian State & District Dropdown sync
function handleStateChange() {
  const stateSelect = document.getElementById("stateSelect");
  const districtSelect = document.getElementById("districtSelect");
  if (!stateSelect || !districtSelect) return;

  const selectedState = stateSelect.value;
  districtSelect.innerHTML = '<option value="">-- Select District --</option>';

  if (selectedState && DISTRICTS_BY_STATE[selectedState]) {
    DISTRICTS_BY_STATE[selectedState].forEach(dist => {
      const opt = document.createElement("option");
      opt.value = dist;
      opt.textContent = dist;
      districtSelect.appendChild(opt);
    });
  } else {
    // Generic default districts
    ["District Center", "North Sub-division", "South Sub-division", "Coastal Zone", "Hill Sector"].forEach(d => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      districtSelect.appendChild(opt);
    });
  }
}

// Counter Stepper (+/-)
function adjustCounter(counterId, delta) {
  const input = document.getElementById(counterId);
  const display = document.getElementById(`${counterId}_display`);
  if (!input) return;

  let current = parseInt(input.value, 10) || 0;
  let nextVal = Math.max(0, current + delta);

  // affected count minimum is 1
  if (counterId === "affected_count") {
    nextVal = Math.max(1, nextVal);
  }

  input.value = nextVal;
  if (display) display.textContent = nextVal;
}

// File Upload Preview
function handleMediaUpload(e) {
  const file = e.target.files[0];
  const previewBox = document.getElementById("mediaPreviewContainer");
  const imgEl = document.getElementById("mediaPreviewImg");
  const infoEl = document.getElementById("mediaFileName");

  if (file && previewBox && imgEl) {
    const reader = new FileReader();
    reader.onload = function(evt) {
      imgEl.src = evt.target.result;
      previewBox.style.display = "block";
      if (infoEl) infoEl.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
    };
    reader.readAsDataURL(file);
  }
}

// Submit Full Emergency Form
async function submitEmergencyForm(e) {
  e.preventDefault();
  const form = document.getElementById("emergencyReportForm");
  const submitBtn = document.getElementById("submitReportBtn");
  if (!form) return;

  const formData = new FormData(form);

  // Validate disaster selection
  if (!formData.get("disaster_type")) {
    showToast("Please select the disaster type.", "warning");
    return;
  }

  // Validate assistance
  const assistanceChecked = document.querySelectorAll(".assistance-chip input:checked");
  if (assistanceChecked.length === 0) {
    showToast("Please select at least one required assistance category.", "warning");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = "⏳ Transmitting Distress Telemetry...";

  try {
    const res = await fetch("/api/report", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.success) {
      showToast(`🚨 Emergency Logged! Tracking ID: ${data.tracking_id}`, "success");
      setTimeout(() => {
        window.location.href = data.redirect_url;
      }, 1200);
    } else {
      showToast(data.error || "Failed to submit emergency report.", "error");
      submitBtn.disabled = false;
      submitBtn.innerHTML = "🚨 Submit Emergency Request";
    }
  } catch (err) {
    console.error("Submission failed:", err);
    showToast("Network error. Retrying submission...", "error");
    submitBtn.disabled = false;
    submitBtn.innerHTML = "🚨 Submit Emergency Request";
  }
}

// Quick SOS Handler from Home Page
async function triggerQuickSos() {
  const phone = prompt("Enter your mobile number for emergency callback (or press OK to dispatch on GPS coordinates):", "");
  if (phone === null) return; // User cancelled

  showToast("🚨 Acquiring GPS coordinates for Rapid SOS...", "info");

  const sendSos = async (lat, lng) => {
    try {
      const res = await fetch("/api/quick-sos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: phone || "Emergency SOS Caller",
          disaster_type: "Flash Flood / Inundation",
          lat: lat,
          lng: lng,
          state: "Rapid Response Zone",
          district: "Emergency District",
          address: `GPS Pin: ${lat.toFixed(4)}, ${lng.toFixed(4)}`
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast("🚨 SOS Distress Call Dispatched! Forwarding to live tracking...", "success");
        setTimeout(() => {
          window.location.href = data.redirect_url;
        }, 1200);
      } else {
        showToast("Failed to dispatch SOS: " + data.error, "error");
      }
    } catch (e) {
      showToast("Emergency network transmission error.", "error");
    }
  };

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => sendSos(pos.coords.latitude, pos.coords.longitude),
      () => sendSos(20.5937, 78.9629),
      { timeout: 5000 }
    );
  } else {
    sendSos(20.5937, 78.9629);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Init mini map if present
  if (document.getElementById("miniMapContainer")) {
    initMiniMap(20.5937, 78.9629);
    // Auto-acquire location on load
    acquireGpsLocation();
  }

  // Disaster radio selection visual sync
  document.querySelectorAll(".disaster-option-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".disaster-option-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      const radio = card.querySelector("input[type='radio']");
      if (radio) radio.checked = true;
    });
  });

  // Assistance chips visual sync
  document.querySelectorAll(".assistance-chip").forEach(chip => {
    chip.addEventListener("click", (e) => {
      const checkbox = chip.querySelector("input[type='checkbox']");
      if (e.target !== checkbox) {
        checkbox.checked = !checkbox.checked;
      }
      chip.classList.toggle("selected", checkbox.checked);
    });
  });

  // Form submit event
  const form = document.getElementById("emergencyReportForm");
  if (form) {
    form.addEventListener("submit", submitEmergencyForm);
  }

  // File upload input
  const mediaInput = document.getElementById("mediaFileInput");
  if (mediaInput) {
    mediaInput.addEventListener("change", handleMediaUpload);
  }
});
