// CrisisCore - Citizen Live Request Tracking & Follow-up

let trackingMap = null;

function initTrackingMap(lat, lng, label = "Reported Incident") {
  const mapEl = document.getElementById("incidentTrackingMap");
  if (!mapEl) return;

  trackingMap = L.map('incidentTrackingMap').setView([lat, lng], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors'
  }).addTo(trackingMap);

  const marker = L.marker([lat, lng]).addTo(trackingMap);
  marker.bindPopup(`<b>${label}</b><br>Coordinates: ${lat.toFixed(4)}, ${lng.toFixed(4)}`).openPopup();
}

async function submitCitizenUpdate(e) {
  e.preventDefault();
  const trackingId = document.getElementById("currentTrackingId")?.value;
  const noteInput = document.getElementById("citizenNoteInput");
  const submitBtn = document.getElementById("postUpdateBtn");

  if (!trackingId || !noteInput || !noteInput.value.trim()) {
    showToast("Please enter an update message.", "warning");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Posting...";

  try {
    const res = await fetch(`/api/incident/${trackingId}/citizen-update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note: noteInput.value.trim() })
    });
    const data = await res.json();

    if (data.success) {
      showToast("Update posted to rescue timeline!", "success");
      noteInput.value = "";
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      showToast(data.error || "Failed to post update.", "error");
    }
  } catch (err) {
    showToast("Network error while posting update.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Post Update to Timeline";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const updateForm = document.getElementById("citizenUpdateForm");
  if (updateForm) {
    updateForm.addEventListener("submit", submitCitizenUpdate);
  }

  // Auto-reload tracking page every 25 seconds for real-time triage updates
  const trackingId = document.getElementById("currentTrackingId")?.value;
  if (trackingId) {
    setInterval(() => {
      // Background check if user is not typing in the textarea
      const noteInput = document.getElementById("citizenNoteInput");
      if (noteInput && document.activeElement !== noteInput) {
        window.location.reload();
      }
    }, 25000);
  }
});
