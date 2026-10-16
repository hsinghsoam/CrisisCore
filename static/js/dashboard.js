// CrisisCore - Command Center Dashboard Interactions & API Handlers

let currentActiveIncidentId = null;

// Open Assign Team Modal
function openAssignModal(incidentId, trackingId, currentTeamId = "") {
  currentActiveIncidentId = incidentId;
  const modalTracking = document.getElementById("assignModalTracking");
  const teamSelect = document.getElementById("assignTeamSelect");
  const notesInput = document.getElementById("assignNotesInput");

  if (modalTracking) modalTracking.textContent = trackingId;
  if (teamSelect && currentTeamId) teamSelect.value = currentTeamId;
  if (notesInput) notesInput.value = "Dispatched from Forward Staging Base with priority medical equipment.";

  openModal("assignTeamModal");
}

async function submitAssignTeam(e) {
  e.preventDefault();
  if (!currentActiveIncidentId) return;

  const teamSelect = document.getElementById("assignTeamSelect");
  const notesInput = document.getElementById("assignNotesInput");
  const submitBtn = document.getElementById("confirmAssignBtn");

  const teamId = teamSelect.value;
  if (!teamId) {
    showToast("Please choose a rescue battalion.", "warning");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Assigning...";

  try {
    const res = await fetch(`/api/incident/${currentActiveIncidentId}/assign-team`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        team_id: teamId,
        notes: notesInput.value.trim()
      })
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, "success");
      closeModal("assignTeamModal");
      setTimeout(() => window.location.reload(), 1000);
    } else {
      showToast(data.error || "Failed to assign team.", "error");
    }
  } catch (err) {
    showToast("Communication error.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Confirm & Dispatch Team";
  }
}

// Open Update Status Modal
function openStatusModal(incidentId, trackingId, currentStatus) {
  currentActiveIncidentId = incidentId;
  const modalTracking = document.getElementById("statusModalTracking");
  const statusSelect = document.getElementById("statusSelectInput");
  const notesInput = document.getElementById("statusNotesInput");

  if (modalTracking) modalTracking.textContent = trackingId;
  if (statusSelect) statusSelect.value = currentStatus;
  if (notesInput) notesInput.value = "";

  openModal("updateStatusModal");
}

async function submitUpdateStatus(e) {
  e.preventDefault();
  if (!currentActiveIncidentId) return;

  const statusSelect = document.getElementById("statusSelectInput");
  const notesInput = document.getElementById("statusNotesInput");
  const submitBtn = document.getElementById("confirmStatusBtn");

  const notes = notesInput.value.trim();
  if (!notes) {
    showToast("Operational field notes are required.", "warning");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Updating...";

  try {
    const res = await fetch(`/api/incident/${currentActiveIncidentId}/update-status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: statusSelect.value,
        notes: notes
      })
    });
    const data = await res.json();

    if (data.success) {
      showToast(data.message, "success");
      closeModal("updateStatusModal");
      setTimeout(() => window.location.reload(), 1000);
    } else {
      showToast(data.error || "Failed to update status.", "error");
    }
  } catch (err) {
    showToast("Error updating status.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Save Operational Status";
  }
}

// Open Priority Breakdown Modal (Explainable AI)
function openPriorityBreakdownModal(incidentId, trackingId, score, level, breakdownJson) {
  currentActiveIncidentId = incidentId;
  const titleEl = document.getElementById("priorityModalTitle");
  const scoreBadge = document.getElementById("priorityModalScoreBadge");
  const container = document.getElementById("factorsListContainer");

  if (titleEl) titleEl.textContent = `Priority Analysis: ${trackingId}`;
  if (scoreBadge) {
    scoreBadge.className = `badge-priority ${level.toLowerCase()}`;
    scoreBadge.textContent = `${level} // ${score}/100`;
  }

  let factors = {};
  try {
    factors = typeof breakdownJson === "string" ? JSON.parse(breakdownJson) : breakdownJson;
  } catch (e) {
    factors = {};
  }

  if (container) {
    container.innerHTML = "";
    const factorLabels = {
      "injured_points": "Trauma & Injured Count Urgency",
      "vulnerable_points": "Vulnerable Persons (Children & Elderly)",
      "affected_scale_points": "Scale of Affected Population",
      "disaster_hazard_points": "Intrinsic Disaster Hazard Factor",
      "assistance_urgency_points": "Critical Assistance Demands (Medical/Rescue)",
      "severity_assessment_points": "Citizen Self-Reported Severity",
      "time_escalation_points": "Time Elapsed Escalation (Anti-Neglect)"
    };

    for (const [key, label] of Object.entries(factorLabels)) {
      const item = factors[key] || { value: 0, max: 20, detail: "Standard base score" };
      const pct = Math.min(100, Math.round((item.value / item.max) * 100));

      const box = document.createElement("div");
      box.className = "breakdown-factor-item";
      box.innerHTML = `
        <div class="factor-top">
          <span>${label}</span>
          <span class="factor-score-pill">${item.value} / ${item.max} pts</span>
        </div>
        <div class="factor-bar-bg">
          <div class="factor-bar-fill" style="width: ${pct}%"></div>
        </div>
        <div class="factor-desc">${item.detail}</div>
      `;
      container.appendChild(box);
    }
  }

  openModal("priorityBreakdownModal");
}

// Submit Manual Priority Override
async function submitPriorityOverride(e) {
  e.preventDefault();
  if (!currentActiveIncidentId) return;

  const select = document.getElementById("overrideLevelSelect");
  const reason = document.getElementById("overrideReasonInput");
  const submitBtn = document.getElementById("confirmOverrideBtn");

  if (!reason.value.trim()) {
    showToast("Written commander justification is required.", "warning");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Applying Override...";

  try {
    const res = await fetch(`/api/incident/${currentActiveIncidentId}/override-priority`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        priority_level: select.value,
        reason: reason.value.trim()
      })
    });
    const data = await res.json();

    if (data.success) {
      showToast("Priority override logged into official audit.", "success");
      closeModal("priorityBreakdownModal");
      setTimeout(() => window.location.reload(), 1000);
    } else {
      showToast(data.error || "Failed to override priority.", "error");
    }
  } catch (err) {
    showToast("Error updating priority.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Authorize Override";
  }
}

// Open Government Transmission Modal
function openGovTransmitModal(incidentId, trackingId, state, district) {
  currentActiveIncidentId = incidentId;
  const trackingEl = document.getElementById("govModalTracking");
  const locEl = document.getElementById("govModalLocation");
  const notesEl = document.getElementById("govTransmitNotes");

  if (trackingEl) trackingEl.textContent = trackingId;
  if (locEl) locEl.textContent = `${district}, ${state}`;
  if (notesEl) notesEl.value = "Verified distress telemetry authorized for multi-agency dispatch.";

  openModal("govTransmitModal");
}

async function submitGovTransmit(e) {
  e.preventDefault();
  if (!currentActiveIncidentId) return;

  const agencySelect = document.getElementById("govAgencySelect");
  const notesInput = document.getElementById("govTransmitNotes");
  const simulateFailCheckbox = document.getElementById("simulateFailCheck");
  const submitBtn = document.getElementById("confirmGovTransmitBtn");

  submitBtn.disabled = true;
  submitBtn.innerHTML = "⏳ Transmitting OASIS CAP v1.2 Packet...";

  try {
    const res = await fetch(`/api/incident/${currentActiveIncidentId}/transmit-gov`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_agency: agencySelect.value,
        notes: notesInput.value.trim(),
        simulate_failure: simulateFailCheckbox ? simulateFailCheckbox.checked : false
      })
    });
    const data = await res.json();

    if (data.success) {
      showToast(`✅ Transmitted to ${data.target_agency}! Receipt: ${data.receipt_id}`, "success");
      closeModal("govTransmitModal");
      setTimeout(() => window.location.reload(), 1200);
    } else {
      showToast(`🚨 Transmission Failed: ${data.error}`, "error");
      submitBtn.disabled = false;
      submitBtn.innerHTML = "Retry Transmission";
    }
  } catch (err) {
    showToast("Government gateway unreachable.", "error");
    submitBtn.disabled = false;
    submitBtn.innerHTML = "Authorize & Securely Transmit";
  }
}

// Polling live KPI counters
function startLiveStatsPolling() {
  setInterval(async () => {
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) return;
      const data = await res.json();

      const kpiActive = document.getElementById("kpiActiveIncidents");
      const kpiCritical = document.getElementById("kpiCriticalIncidents");
      const kpiAffected = document.getElementById("kpiTotalAffected");
      const kpiInjured = document.getElementById("kpiTotalInjured");
      const kpiTeams = document.getElementById("kpiDeployedTeams");

      if (kpiActive) kpiActive.textContent = data.active_incidents;
      if (kpiCritical) kpiCritical.textContent = data.critical_incidents;
      if (kpiAffected) kpiAffected.textContent = data.total_affected;
      if (kpiInjured) kpiInjured.textContent = data.total_injured;
      if (kpiTeams) kpiTeams.textContent = data.deployed_teams;
    } catch (e) {
      // Background poll failure
    }
  }, 15000);
}

document.addEventListener("DOMContentLoaded", () => {
  startLiveStatsPolling();

  // Attach modal forms
  const assignForm = document.getElementById("assignTeamForm");
  if (assignForm) assignForm.addEventListener("submit", submitAssignTeam);

  const statusForm = document.getElementById("updateStatusForm");
  if (statusForm) statusForm.addEventListener("submit", submitUpdateStatus);

  const overrideForm = document.getElementById("overridePriorityForm");
  if (overrideForm) overrideForm.addEventListener("submit", submitPriorityOverride);

  const govForm = document.getElementById("govTransmitForm");
  if (govForm) govForm.addEventListener("submit", submitGovTransmit);
});
