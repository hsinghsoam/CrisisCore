import urllib.request
import urllib.parse
import json
import re

BASE_URL = "http://127.0.0.1:5000"

def test_routes():
    print("=== STARTING CRISISCORE AUTOMATED INTEGRATION TESTS ===")
    
    # Cookie jar handler for session
    cookie_processor = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookie_processor)
    urllib.request.install_opener(opener)

    # 1. Citizen Landing Page
    print("\n1. Testing GET / (Citizen Portal)...")
    res = opener.open(f"{BASE_URL}/")
    assert res.getcode() == 200, f"Expected 200, got {res.getcode()}"
    content = res.read().decode('utf-8')
    assert "CrisisCore" in content, "Brand title missing"
    assert "Trapped or in Immediate Danger?" in content, "Hero SOS missing"
    print("   [PASS] Citizen Home Page OK")

    # 2. Emergency Report Page
    print("\n2. Testing GET /report (Emergency Report Form)...")
    res = opener.open(f"{BASE_URL}/report")
    assert res.getcode() == 200
    report_html = res.read().decode('utf-8')
    assert "Submit Emergency Assistance Request" in report_html
    # Extract captcha question
    match = re.search(r'class="captcha-badge">(\d+)\s*\+\s*(\d+)\s*=\s*\?</div>', report_html)
    assert match, "Captcha not found in HTML"
    n1, n2 = int(match.group(1)), int(match.group(2))
    captcha_ans = n1 + n2
    print(f"   [PASS] Solved anti-abuse captcha: {n1} + {n2} = {captcha_ans}")

    # 3. Submit Emergency Request via API
    print("\n3. Testing POST /api/report...")
    form_data = {
        "citizen_name": "Kavita Deshmukh",
        "phone": "+91 98230 44556",
        "disaster_type": "Landslide / Mudflow",
        "severity_input": "Immediate Danger",
        "state": "Maharashtra",
        "district": "Raigad",
        "address": "Mahad Hill Slope, Sector 3, Near Taluka Hospital",
        "description": "Hillock mudflow broke through 4 residential compounds. 14 people cut off from road access. 2 elderly persons need urgent wheelchair evac.",
        "problems": "Active mud slipping, heavy rain, electrical lines submerged.",
        "assistance_required": ["Rescue Boat / Evacuation", "Urgent Medical Care / Trauma", "Temporary Shelter"],
        "affected_count": "14",
        "injured_count": "2",
        "children_count": "3",
        "elderly_count": "2",
        "lat": "18.0827",
        "lng": "73.4243",
        "captcha_answer": str(captcha_ans)
    }

    # Encode multipart/form-data or urlencoded
    encoded_data = urllib.parse.urlencode(form_data, doseq=True).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/report", data=encoded_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    res = opener.open(req)
    assert res.getcode() == 200
    report_resp = json.loads(res.read().decode('utf-8'))
    assert report_resp["success"] is True, f"Report failed: {report_resp}"
    tracking_id = report_resp["tracking_id"]
    priority_level = report_resp["priority_level"]
    priority_score = report_resp["priority_score"]
    print(f"   [PASS] Created incident: {tracking_id} | Priority: {priority_level} ({priority_score}/100)")

    # 4. Quick SOS API
    print("\n4. Testing POST /api/quick-sos...")
    sos_payload = json.dumps({
        "phone": "+91 99999 11111",
        "disaster_type": "Flash Flood / Inundation",
        "lat": 10.1080,
        "lng": 76.3520
    }).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/quick-sos", data=sos_payload, headers={"Content-Type": "application/json"})
    res = opener.open(req)
    sos_resp = json.loads(res.read().decode('utf-8'))
    assert sos_resp["success"] is True
    sos_tracking_id = sos_resp["tracking_id"]
    print(f"   [PASS] Quick SOS Dispatched: {sos_tracking_id}")

    # 5. Tracking Page
    print(f"\n5. Testing GET /track?id={tracking_id}...")
    res = opener.open(f"{BASE_URL}/track?id={tracking_id}")
    assert res.getcode() == 200
    track_html = res.read().decode('utf-8')
    assert tracking_id in track_html
    assert "Rescue Triage Progress" in track_html
    print("   [PASS] Tracking timeline and status rendered")

    # 6. Citizen Post Follow-up
    print(f"\n6. Testing POST /api/incident/{tracking_id}/citizen-update...")
    up_payload = json.dumps({"note": "Rain subsided slightly, water level stable at 4 feet."}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/incident/{tracking_id}/citizen-update", data=up_payload, headers={"Content-Type": "application/json"})
    res = opener.open(req)
    assert res.getcode() == 200
    up_resp = json.loads(res.read().decode('utf-8'))
    assert up_resp["success"] is True
    print("   [PASS] Citizen follow-up update appended to incident timeline")

    # 7. Authority Login
    print("\n7. Testing POST /api/login (Admin Rajesh Kumar IAS)...")
    login_payload = json.dumps({"username": "admin", "password": "Admin@123"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/login", data=login_payload, headers={"Content-Type": "application/json"})
    res = opener.open(req)
    assert res.getcode() == 200
    login_resp = json.loads(res.read().decode('utf-8'))
    assert login_resp["success"] is True
    print("   [PASS] Administrator authenticated successfully")

    # 8. Command Dashboard View
    print("\n8. Testing GET /dashboard...")
    res = opener.open(f"{BASE_URL}/dashboard")
    assert res.getcode() == 200
    dash_html = res.read().decode('utf-8')
    assert "National & Regional Disaster Operations Center" in dash_html
    assert tracking_id in dash_html
    print("   [PASS] Command dashboard and live registry verified")

    # 9. Map Data API
    print("\n9. Testing GET /api/map-data...")
    res = opener.open(f"{BASE_URL}/api/map-data")
    assert res.getcode() == 200
    map_data = json.loads(res.read().decode('utf-8'))
    assert map_data["success"] is True
    assert len(map_data["incidents"]) > 0
    assert len(map_data["rescue_teams"]) > 0
    assert len(map_data["relief_camps"]) > 0
    print(f"   [PASS] Map Telemetry: {len(map_data['incidents'])} incidents, {len(map_data['rescue_teams'])} teams, {len(map_data['relief_camps'])} relief camps")

    # 10. Assign Rescue Team
    print(f"\n10. Testing POST /api/incident/1/assign-team...")
    assign_payload = json.dumps({"team_id": 1, "notes": "Mobilize motorized rafts to river sector."}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/incident/1/assign-team", data=assign_payload, headers={"Content-Type": "application/json"})
    res = opener.open(req)
    assert res.getcode() == 200
    assign_resp = json.loads(res.read().decode('utf-8'))
    assert assign_resp["success"] is True
    print(f"   [PASS] Team assigned: {assign_resp['team_name']}")

    # 11. Update Operational Status across stages
    print(f"\n11. Testing POST /api/incident/1/update-status (Advancing to Rescue Team Dispatched)...")
    status_payload = json.dumps({"status": "Rescue Team Dispatched", "notes": "Convoy in transit, ETA 18 minutes."}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/incident/1/update-status", data=status_payload, headers={"Content-Type": "application/json"})
    res = opener.open(req)
    assert res.getcode() == 200
    stat_resp = json.loads(res.read().decode('utf-8'))
    assert stat_resp["success"] is True
    print(f"   [PASS] Operational status advanced to: {stat_resp['new_status']}")

    # 12. Transmit to Government Gateway (NDMA Central)
    print(f"\n12. Testing POST /api/incident/1/transmit-gov (OASIS CAP v1.2 Gateway)...")
    gov_payload = json.dumps({"target_agency": "NDMA_CENTRAL", "notes": "Distress verified by duty commander."}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/incident/1/transmit-gov", data=gov_payload, headers={"Content-Type": "application/json"})
    res = opener.open(req)
    assert res.getcode() == 200
    gov_resp = json.loads(res.read().decode('utf-8'))
    assert gov_resp["success"] is True
    assert "receipt_id" in gov_resp
    assert "payload_hash" in gov_resp
    print(f"   [PASS] Transmitted to {gov_resp['target_agency']} | Receipt: {gov_resp['receipt_id']} | SHA-256: {gov_resp['payload_hash'][:16]}...")

    # 13. Download Official NDMA SITREP PDF
    print("\n13. Testing GET /api/export/sitrep.pdf (PDF Generation)...")
    res = opener.open(f"{BASE_URL}/api/export/sitrep.pdf")
    assert res.getcode() == 200
    assert res.headers.get("Content-Type") == "application/pdf"
    pdf_bytes = res.read()
    assert pdf_bytes.startswith(b"%PDF"), "Invalid PDF header"
    print(f"   [PASS] NDMA Situation Report PDF generated successfully ({len(pdf_bytes)} bytes)")

    # 14. Export Incidents CSV
    print("\n14. Testing GET /api/export/incidents.csv (CSV Export)...")
    res = opener.open(f"{BASE_URL}/api/export/incidents.csv")
    assert res.getcode() == 200
    csv_text = res.read().decode('utf-8')
    assert "tracking_id" in csv_text
    assert tracking_id in csv_text
    print(f"   [PASS] Incidents CSV generated successfully ({len(csv_text.splitlines())} rows)")

    # 15. Other Core Portals
    print("\n15. Testing GET /resources, /gov-gateway, /analytics...")
    res1 = opener.open(f"{BASE_URL}/resources")
    assert res1.getcode() == 200
    res2 = opener.open(f"{BASE_URL}/gov-gateway")
    assert res2.getcode() == 200
    res3 = opener.open(f"{BASE_URL}/analytics")
    assert res3.getcode() == 200
    print("   [PASS] Resources, Government Gateway, and Analytics pages verified")

    print("\n=== ALL 15 INTEGRATION TEST SUITES PASSED FLAWLESSLY! ===")

if __name__ == "__main__":
    test_routes()
