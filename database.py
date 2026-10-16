import sqlite3
import json
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users table (Role-based access: admin, official, responder, citizen)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'official', 'responder', 'citizen')),
        full_name TEXT NOT NULL,
        agency TEXT,
        phone TEXT,
        badge_no TEXT,
        created_at TEXT NOT NULL
    );
    """)
    
    # 2. Emergency Incidents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT UNIQUE NOT NULL,
        citizen_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        disaster_type TEXT NOT NULL,
        severity_input TEXT NOT NULL,
        priority_score INTEGER NOT NULL DEFAULT 50,
        priority_level TEXT NOT NULL DEFAULT 'MEDIUM',
        affected_count INTEGER NOT NULL DEFAULT 1,
        injured_count INTEGER NOT NULL DEFAULT 0,
        children_count INTEGER NOT NULL DEFAULT 0,
        elderly_count INTEGER NOT NULL DEFAULT 0,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        state TEXT NOT NULL,
        district TEXT NOT NULL,
        address TEXT NOT NULL,
        description TEXT NOT NULL,
        problems TEXT,
        assistance_required TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN (
            'Submitted',
            'Under Review',
            'Verified',
            'Assigned to Rescue Team',
            'Rescue Team Dispatched',
            'Assistance in Progress',
            'Resolved'
        )) DEFAULT 'Submitted',
        assigned_team_id INTEGER,
        government_sync_status TEXT NOT NULL DEFAULT 'NOT_FORWARDED',
        sync_receipt_id TEXT,
        sync_timestamp TEXT,
        media_url TEXT,
        priority_breakdown_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (assigned_team_id) REFERENCES rescue_teams(id)
    );
    """)
    
    # 3. Incident Activity & Progress Updates table (for tracking timeline)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incident_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id INTEGER NOT NULL,
        status_from TEXT,
        status_to TEXT NOT NULL,
        notes TEXT NOT NULL,
        author_name TEXT NOT NULL,
        author_role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
    );
    """)
    
    # 4. Rescue Teams table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rescue_teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        agency TEXT NOT NULL,
        contact_lead TEXT NOT NULL,
        phone TEXT NOT NULL,
        base_location TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Available', 'Dispatched', 'On Site', 'Standby')) DEFAULT 'Available',
        specialization TEXT NOT NULL,
        capacity_info TEXT NOT NULL
    );
    """)
    
    # 5. Emergency Resources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_name TEXT NOT NULL,
        category TEXT NOT NULL,
        total_qty INTEGER NOT NULL,
        available_qty INTEGER NOT NULL,
        unit TEXT NOT NULL,
        location_district TEXT NOT NULL,
        state TEXT NOT NULL,
        last_updated TEXT NOT NULL
    );
    """)
    
    # 6. Relief Camps & Verified Hospitals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS relief_camps_hospitals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('Hospital', 'Relief Camp', 'Helipad', 'Emergency Supply Depot')),
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        total_capacity INTEGER NOT NULL,
        available_capacity INTEGER NOT NULL,
        contact_phone TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 1
    );
    """)
    
    # 7. Government Transmissions Audit table (for NDMA / SDMA verification)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS government_transmissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id INTEGER NOT NULL,
        tracking_id TEXT NOT NULL,
        target_agency TEXT NOT NULL,
        transmission_status TEXT NOT NULL,
        protocol TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        response_hash TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        transmitted_by TEXT NOT NULL,
        receipt_id TEXT,
        acknowledgement_code TEXT,
        FOREIGN KEY (incident_id) REFERENCES incidents(id)
    );
    """)
    
    # 8. Activity Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        user_name TEXT NOT NULL,
        role TEXT NOT NULL,
        details TEXT NOT NULL,
        ip_address TEXT,
        timestamp TEXT NOT NULL
    );
    """)
    
    # 9. Anti-Abuse Rate Limit table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT NOT NULL,
        action TEXT NOT NULL,
        request_count INTEGER NOT NULL DEFAULT 1,
        last_attempt TEXT NOT NULL
    );
    """)
    
    conn.commit()
    conn.close()

def log_activity(action: str, entity_type: str, entity_id: str, user_name: str, role: str, details: str, ip: str = "127.0.0.1"):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (action, entity_type, entity_id, user_name, role, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (action, entity_type, str(entity_id), user_name, role, details, ip, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log activity: {e}")
