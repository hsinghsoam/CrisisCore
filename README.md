# CrisisCore - Emergency & Disaster Response Coordination Platform

**CrisisCore** is an integrated disaster management platform aligning citizen distress reporting with real-time official command and rescue operations. Built with emergency agency standards (NDMA / SDMA / NDRF / SDRF) in mind, it provides triage scoring, geo-mapping, resource dispatch, and CAP v1.2 incident transmission.

---

## 🚀 Key Features

- **Citizen Emergency Portal**: Fast, mobile-responsive distress submission with GPS auto-detection, offline-tolerant workflows, vulnerability counting (children, elderly, injured), and anti-abuse arithmetic captcha.
- **Explainable Priority Scoring Engine (0-100)**: Transparent algorithmic triage weighing disaster hazard severity, casualty counts, vulnerable individuals, assistance urgency, and time escalation.
- **Operations Dashboard & Live Map**: Interactive Leaflet.js command center displaying verified incidents, rescue staging locations, severity heat indicators, and quick action bars.
- **NDMA / SDMA CAP Gateway**: OASIS Common Alerting Protocol (CAP v1.2) compliant JSON alert dispatcher with digital signing and mock transmission simulation.
- **SITREP Generator**: One-click generation of official National/State Disaster Management Situation Reports in PDF format (ReportLab) and CSV exports.
- **Role-Based Access Control (RBAC)**: Secure access tiers for `admin`, `official`, `responder`, and `citizen` users with audit activity logging.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, Flask 3.x, Werkzeug
- **Database**: SQLite3 with thread-safe connection pooling
- **Reporting**: ReportLab (PDF generation)
- **Frontend**: Responsive HTML5, Vanilla JavaScript, Leaflet.js, FontAwesome, modern CSS

---

## 📋 Quickstart & Setup Guide

### 1. Prerequisites
Ensure Python 3.10 or higher is installed and accessible in your system's PATH.

### 2. Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize & Seed Database
```bash
python seed_data.py
```
*Note: A pre-seeded `crisiscore.db` with realistic test scenarios across India (floods, landslides, earthquakes) is included by default.*

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

### 6. Run Automated Integration Tests
In a separate terminal while the server is running (or via automated test runner):
```bash
python test_system.py
```

---

## 🔐 Default Demo Credentials

| Role | Username | Password | Organization / Clearance |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `Admin@123` | National Disaster Management Authority (NDMA) |
| **State Official** | `sdma_officer` | `Sdma@123` | Kerala State Disaster Management Authority (SDMA) |
| **Field Responder** | `ndrf_lead` | `Ndrf@123` | NDRF 4th Battalion Rapid Response |
| **Citizen** | `citizen_priya` | `Priya@123` | Civilian / Verified Citizen |

---

## 📁 Project Structure

```
CrisisCore/
├── app.py                  # Core Flask server and route endpoints
├── config.py               # Application configuration & gateway endpoints
├── database.py             # SQLite schemas, connection handling & activity logging
├── priority_engine.py      # Algorithmic priority score computation
├── gov_integration.py      # OASIS CAP v1.2 protocol generator & mock gateway
├── reports_generator.py    # ReportLab SITREP PDF & CSV generator
├── seed_data.py            # Initial users, rescue teams, and realistic incident seeds
├── test_system.py          # Automated end-to-end integration test suite
├── requirements.txt        # Python package dependencies
├── .gitignore              # Git ignore rules
├── static/
│   ├── css/                # Stylesheets (citizen, dashboard, map, main)
│   ├── js/                 # Client scripts (map_live, tracking, citizen, dashboard)
│   └── uploads/            # Uploaded citizen distress photos/evidence
└── templates/              # Jinja2 templates (dashboard, citizen, tracking, etc.)
```
