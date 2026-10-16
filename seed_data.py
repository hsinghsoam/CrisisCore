import json
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash
from database import get_db, init_db
from priority_engine import calculate_priority_score

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if already seeded
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return
        
    print("Seeding CrisisCore database with realistic production disaster data...")
    now = datetime.now(timezone.utc)
    
    # 1. Users
    users_data = [
        ("admin", generate_password_hash("Admin@123"), "admin", "Rajesh Kumar IAS", "National Disaster Management Authority (NDMA)", "+91 98110 00112", "NDMA-DIR-01"),
        ("sdma_officer", generate_password_hash("Sdma@123"), "official", "Dr. Meenakshi Nair", "Kerala State Disaster Management Authority (SDMA)", "+91 94470 12345", "SDMA-KL-402"),
        ("ndrf_lead", generate_password_hash("Ndrf@123"), "responder", "Inspector Vikramaditya Singh", "NDRF 4th Battalion Rapid Response", "+91 94190 88765", "NDRF-INSP-408"),
        ("citizen_priya", generate_password_hash("Priya@123"), "citizen", "Priya Sharma", "Civilian", "+91 98201 99887", None)
    ]
    for u in users_data:
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, agency, phone, badge_no, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (u[0], u[1], u[2], u[3], u[4], u[5], u[6], now.isoformat()))
        
    # 2. Rescue Teams
    rescue_teams = [
        ("NDRF 4th Battalion - Water Rescue Unit Alpha", "NDRF", "Commandant S. K. Rao", "+91 94440 22331", "Arakkonam / Aluva Forward Staging Base", 10.1070, 76.3500, "Dispatched", "Swift Water & Flood Rescue, Diving Triage", "45 Operators, 12 Zodiac Inflatable Boats, 80 Life Vests"),
        ("NDRF 8th Battalion - Urban Search & Rescue (USAR)", "NDRF", "Dy. Commandant Amit Verma", "+91 98100 44552", "Ghaziabad / Mumbai Regional Hub", 19.0765, 72.8770, "Dispatched", "Collapsed Structure Search & Rescue, Canine Unit", "50 Specialists, Hydraulic Spreaders, Acoustic Sensors"),
        ("SDRF Mountain High-Altitude Triage Unit", "SDRF", "Inspector Harsh Joshi", "+91 94120 77663", "Chamoli / Joshimath Base Camp", 30.5560, 79.5670, "On Site", "Landslide Clearance, High Angle Rope Rescue", "30 Mountain Rescue Specialists, Drones, Stretcher Winch"),
        ("Kerala Fire & Rescue Special Task Force", "Fire Service", "Station Officer K. George", "+91 94471 88990", "Ernakulam Central Station", 9.9820, 76.3000, "Available", "Fire Suppression, Hazardous Materials, Flood Pumps", "25 Firefighters, 4 High-Volume Submersible Dewatering Pumps"),
        ("Red Cross Emergency Medical & Trauma Unit", "Medical EMS", "Dr. Shalini Barua", "+91 97060 33221", "Guwahati Disaster Support Hub", 26.1800, 91.7500, "Available", "Mobile Trauma Surgery, Emergency Triage, Vaccination", "18 Paramedics & Doctors, 4 Advanced Life Support Ambulances"),
        ("Indian Coast Guard Air & Marine Evac Flight", "Coast Guard", "Squadron Leader R. Sengupta", "+91 98300 11998", "Paradip Coast Guard Station", 19.8100, 85.8300, "Available", "Offshore Evacuation, Aerial Supply Drops", "2 Chetak Helicopters, 1 Hovercraft, 3 Fast Patrol Craft")
    ]
    for team in rescue_teams:
        cursor.execute("""
            INSERT INTO rescue_teams (name, agency, contact_lead, phone, base_location, lat, lng, status, specialization, capacity_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, team)
        
    # 3. Emergency Resources
    resources_data = [
        ("Motorized Inflatable Rescue Boats (Zodiac)", "Rescue Boat", 85, 38, "Boats", "Ernakulam", "Kerala"),
        ("Advanced Life Support (ALS) Ambulances", "Ambulance", 120, 42, "Vehicles", "Chamoli", "Uttarakhand"),
        ("Ready-to-Eat Emergency Food & Clean Water Rations", "Emergency Food & Water", 25000, 14200, "Packs", "Wayanad", "Kerala"),
        ("Heavy Earthmover Excavators & Hydraulic Cranes", "Earthmover / Excavator", 35, 11, "Machines", "Chamoli", "Uttarakhand"),
        ("Emergency Tarpaulins & Disaster Tent Bundles", "Temporary Shelter Beds", 8000, 4800, "Bundles", "Puri", "Odisha"),
        ("Trauma & Burn Surgical Treatment Kits", "Medical Trauma Kit", 300, 95, "Kits", "Guwahati", "Assam"),
        ("Portable Diesel High-Discharge Dewatering Pumps", "Equipment", 60, 18, "Units", "Mumbai Suburban", "Maharashtra")
    ]
    for r in resources_data:
        cursor.execute("""
            INSERT INTO resources (resource_name, category, total_qty, available_qty, unit, location_district, state, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r[0], r[1], r[2], r[3], r[4], r[5], r[6], now.isoformat()))
        
    # 4. Relief Camps & Verified Hospitals
    camps_data = [
        ("District General Hospital Disaster Wing", "Hospital", 9.9816, 76.2999, "Ernakulam", "Kerala", 500, 142, "+91 484 2351234", 1),
        ("AIIMS Rishikesh Trauma & Emergency Command", "Hospital", 30.0768, 78.2882, "Dehradun", "Uttarakhand", 800, 94, "+91 135 2462929", 1),
        ("Rajiv Gandhi Community Cyclone & Flood Shelter 4", "Relief Camp", 11.6854, 76.1320, "Wayanad", "Kerala", 450, 220, "+91 4936 202244", 1),
        ("Biju Patnaik Multi-Purpose Cyclone Shelter", "Relief Camp", 19.8135, 85.8312, "Puri", "Odisha", 1200, 680, "+91 6752 222107", 1),
        ("Guwahati Medical College Emergency Triage Hospital", "Hospital", 26.1584, 91.7744, "Kamrup Metropolitan", "Assam", 650, 112, "+91 361 2529457", 1),
        ("KEM Hospital & Disaster Trauma Ward", "Hospital", 19.0020, 72.8420, "Mumbai", "Maharashtra", 900, 140, "+91 22 24107000", 1)
    ]
    for c in camps_data:
        cursor.execute("""
            INSERT INTO relief_camps_hospitals (name, type, lat, lng, district, state, total_capacity, available_capacity, contact_phone, verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, c)
        
    # 5. Pre-seeded Emergency Incidents
    incidents = [
        {
            "tracking_id": "CRISIS-2026-IND-0101",
            "citizen_name": "Ramesh K. Pillai",
            "phone": "+91 98471 22910",
            "disaster_type": "Flash Flood / Inundation",
            "severity_input": "Life Threatening",
            "affected_count": 28,
            "injured_count": 3,
            "children_count": 6,
            "elderly_count": 5,
            "lat": 10.1076,
            "lng": 76.3516,
            "state": "Kerala",
            "district": "Ernakulam",
            "address": "Near Periyar River Bank, Bank Road, Aluva",
            "description": "Periyar river overflowed submerging ground floors up to 7 feet. 28 citizens stranded on concrete terrace without food or drinking water for 14 hours. 3 elderly residents show signs of acute hypothermia.",
            "problems": "Submerged power lines, rapid current, rising water level, 3 hypothermic elderly individuals.",
            "assistance_required": "Rescue Boat / Evacuation, Urgent Medical Care / Trauma, Emergency Food & Potable Water",
            "status": "Rescue Team Dispatched",
            "assigned_team_id": 1,
            "government_sync_status": "TRANSMITTED",
            "sync_receipt_id": "RECEIPT-NDMA_CENTRAL-261016-A92B1F",
            "media_url": "/static/uploads/flood_rescue_scene.jpg",
            "created_offset_mins": 95
        },
        {
            "tracking_id": "CRISIS-2026-IND-0102",
            "citizen_name": "Devendra Rawat",
            "phone": "+91 94120 55431",
            "disaster_type": "Landslide / Mudflow",
            "severity_input": "Immediate Danger",
            "affected_count": 45,
            "injured_count": 4,
            "children_count": 8,
            "elderly_count": 7,
            "lat": 30.5562,
            "lng": 79.5678,
            "state": "Uttarakhand",
            "district": "Chamoli",
            "address": "KM 14 Mountain Pass, Govindghat Road",
            "description": "Massive landslide brought down boulders and slurry across 200m stretch. 3 passenger buses and 6 small vehicles trapped between slide zones. 4 commuters have fracture injuries from tumbling stone debris.",
            "problems": "Road completely obliterated, continuing stone fall risk, heavy fog, acute fracture injuries.",
            "assistance_required": "Specialized Rescue Equipment (Earthmover / Rope Triage), Urgent Medical Care / Trauma, Temporary Shelter",
            "status": "Assigned to Rescue Team",
            "assigned_team_id": 3,
            "government_sync_status": "TRANSMITTED",
            "sync_receipt_id": "RECEIPT-SDMA_STATE-261016-D41E80",
            "media_url": "/static/uploads/landslide_scene.jpg",
            "created_offset_mins": 60
        },
        {
            "tracking_id": "CRISIS-2026-IND-0103",
            "citizen_name": "Sunita Mohapatra",
            "phone": "+91 87630 19822",
            "disaster_type": "Cyclone / Super Storm",
            "severity_input": "Immediate Danger",
            "affected_count": 60,
            "injured_count": 1,
            "children_count": 15,
            "elderly_count": 10,
            "lat": 19.8055,
            "lng": 85.8239,
            "state": "Odisha",
            "district": "Puri",
            "address": "Ward 7 Coastal Hamlet, Near Astaranga Jetty",
            "description": "Extreme cyclonic gusts up to 130 km/h blew off roofs of 35 thatched fishermen huts. Coastal tidal surge approaching settlement boundary. 60 citizens need urgent relocation to cyclone center.",
            "problems": "Uprooted trees blocking access roads, snapped live HT electrical wires, sea water ingress.",
            "assistance_required": "Rescue Boat / Evacuation, Temporary Shelter, Emergency Food & Potable Water",
            "status": "Verified",
            "assigned_team_id": None,
            "government_sync_status": "PENDING_REVIEW",
            "sync_receipt_id": None,
            "media_url": None,
            "created_offset_mins": 45
        },
        {
            "tracking_id": "CRISIS-2026-IND-0104",
            "citizen_name": "Anupam Bora",
            "phone": "+91 97061 44320",
            "disaster_type": "Flash Flood / Inundation",
            "severity_input": "Moderate",
            "affected_count": 18,
            "injured_count": 0,
            "children_count": 4,
            "elderly_count": 2,
            "lat": 26.1820,
            "lng": 91.7580,
            "state": "Assam",
            "district": "Kamrup Metropolitan",
            "address": "Pandu Port Road, Low-lying residential pocket",
            "description": "Brahmaputra backwaters causing knee-deep waterlogging in village ward. All municipal drinking water handpumps submerged and contaminated with silt. Requesting chlorination kits and drinking water cans.",
            "problems": "Contaminated drinking water, silt deposition, food shortage.",
            "assistance_required": "Emergency Food & Potable Water, Clothing / Blankets",
            "status": "Under Review",
            "assigned_team_id": None,
            "government_sync_status": "NOT_FORWARDED",
            "sync_receipt_id": None,
            "media_url": None,
            "created_offset_mins": 30
        },
        {
            "tracking_id": "CRISIS-2026-IND-0105",
            "citizen_name": "Farhan Qureshi",
            "phone": "+91 98200 81290",
            "disaster_type": "Building Collapse",
            "severity_input": "Life Threatening",
            "affected_count": 12,
            "injured_count": 5,
            "children_count": 3,
            "elderly_count": 1,
            "lat": 19.0760,
            "lng": 72.8777,
            "state": "Maharashtra",
            "district": "Mumbai Suburban",
            "address": "Nehru Nagar, 4-Storey Residential Chawl Rear Wing",
            "description": "Rear wing of 40-year old residential building collapsed suddenly following 48 hours of continuous torrential rain. 5 residents severely injured; 3 children and 1 elderly person believed trapped in crawl spaces.",
            "problems": "Live gas leak smell detected, unstable remaining structure threatening adjacent tenements.",
            "assistance_required": "Specialized Rescue Equipment (Earthmover / Rope Triage), Urgent Medical Care / Trauma, Rescue Boat / Evacuation",
            "status": "Rescue Team Dispatched",
            "assigned_team_id": 2,
            "government_sync_status": "TRANSMITTED",
            "sync_receipt_id": "RECEIPT-ERSS_112-261016-C18B44",
            "media_url": None,
            "created_offset_mins": 110
        }
    ]
    
    for inc in incidents:
        c_time = (now - timedelta(minutes=inc["created_offset_mins"])).isoformat()
        p_res = calculate_priority_score(
            disaster_type=inc["disaster_type"],
            affected_count=inc["affected_count"],
            injured_count=inc["injured_count"],
            children_count=inc["children_count"],
            elderly_count=inc["elderly_count"],
            assistance_list=inc["assistance_required"].split(", "),
            severity_input=inc["severity_input"],
            created_at_str=c_time
        )
        
        cursor.execute("""
            INSERT INTO incidents (
                tracking_id, citizen_name, phone, disaster_type, severity_input,
                priority_score, priority_level, affected_count, injured_count,
                children_count, elderly_count, lat, lng, state, district,
                address, description, problems, assistance_required, status,
                assigned_team_id, government_sync_status, sync_receipt_id,
                sync_timestamp, media_url, priority_breakdown_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inc["tracking_id"], inc["citizen_name"], inc["phone"], inc["disaster_type"],
            inc["severity_input"], p_res["score"], p_res["level"], inc["affected_count"],
            inc["injured_count"], inc["children_count"], inc["elderly_count"], inc["lat"],
            inc["lng"], inc["state"], inc["district"], inc["address"], inc["description"],
            inc["problems"], inc["assistance_required"], inc["status"], inc["assigned_team_id"],
            inc["government_sync_status"], inc["sync_receipt_id"],
            c_time if inc["government_sync_status"] == "TRANSMITTED" else None,
            inc["media_url"], json.dumps(p_res["breakdown"]), c_time, now.isoformat()
        ))
        
        inc_id = cursor.lastrowid
        
        # Add initial submission update
        cursor.execute("""
            INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (inc_id, None, "Submitted", "Citizen submitted emergency assistance request via CrisisCore Portal.", inc["citizen_name"], "Citizen", c_time))
        
        # Add progression updates based on status
        if inc["status"] in ["Under Review", "Verified", "Assigned to Rescue Team", "Rescue Team Dispatched", "Assistance in Progress", "Resolved"]:
            t1 = (now - timedelta(minutes=inc["created_offset_mins"] - 10)).isoformat()
            cursor.execute("""
                INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inc_id, "Submitted", "Under Review", "Duty Operations Officer initiated geo-verification and incident priority scoring.", "Dr. Meenakshi Nair", "Official", t1))
            
        if inc["status"] in ["Verified", "Assigned to Rescue Team", "Rescue Team Dispatched", "Assistance in Progress", "Resolved"]:
            t2 = (now - timedelta(minutes=inc["created_offset_mins"] - 20)).isoformat()
            cursor.execute("""
                INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inc_id, "Under Review", "Verified", "Incident coordinates and severe distress state verified with local emergency services.", "Rajesh Kumar IAS", "Admin", t2))
            
        if inc["status"] in ["Assigned to Rescue Team", "Rescue Team Dispatched", "Assistance in Progress", "Resolved"]:
            t3 = (now - timedelta(minutes=inc["created_offset_mins"] - 35)).isoformat()
            cursor.execute("""
                INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inc_id, "Verified", "Assigned to Rescue Team", "Incident assigned to designated rapid rescue battalion.", "Rajesh Kumar IAS", "Admin", t3))
            
        if inc["status"] in ["Rescue Team Dispatched", "Assistance in Progress", "Resolved"]:
            t4 = (now - timedelta(minutes=inc["created_offset_mins"] - 50)).isoformat()
            cursor.execute("""
                INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (inc_id, "Assigned to Rescue Team", "Rescue Team Dispatched", "Rescue convoy departed forward staging base with motorized inflatable boats and medical triage crew.", "Inspector Vikramaditya Singh", "Responder", t4))
            
        # Log initial submission
        cursor.execute("""
            INSERT INTO activity_logs (action, entity_type, entity_id, user_name, role, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("REPORT_SUBMITTED", "INCIDENT", str(inc_id), inc["citizen_name"], "Citizen", f"Emergency reported in {inc['district']}, {inc['state']} (Priority: {p_res['level']} - {p_res['score']})", "127.0.0.1", c_time))
        
    conn.commit()
    conn.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
