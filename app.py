import os
import io
import json
import random
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    session, flash, send_file, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import get_db, init_db, log_activity
from priority_engine import calculate_priority_score
from gov_integration import transmit_to_government_authority, generate_cap_v12_payload
from reports_generator import generate_sitrep_pdf, generate_incidents_csv

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ----------------- Helper Functions & Decorators -----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in with authorized credentials to access this portal.", "warning")
            return redirect(url_for("login_page", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login_page", next=request.url))
            if session.get("role") not in allowed_roles:
                flash("Access denied: You do not possess the required clearance level for this resource.", "danger")
                return redirect(url_for("dashboard_page"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_tracking_id():
    year = datetime.now().strftime("%Y")
    rand_hex = uuid.uuid4().hex[:6].upper()
    return f"CRISIS-{year}-IND-{rand_hex}"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# ----------------- Citizen Facing Routes -----------------

@app.route("/")
def citizen_home():
    """Citizen landing portal: Quick SOS, Detailed Report, Track Request, Helplines."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as active FROM incidents WHERE status != 'Resolved'")
    active_incidents = cursor.fetchone()["active"]
    cursor.execute("SELECT COUNT(*) as deployed FROM rescue_teams WHERE status = 'Dispatched'")
    deployed_teams = cursor.fetchone()["deployed"]
    conn.close()
    return render_template("citizen_home.html", active_incidents=active_incidents, deployed_teams=deployed_teams)

@app.route("/report")
def report_page():
    """Detailed emergency reporting form."""
    # Generate simple anti-bot math challenge
    num1 = random.randint(3, 9)
    num2 = random.randint(2, 8)
    session["captcha_answer"] = num1 + num2
    captcha_question = f"{num1} + {num2} = ?"
    return render_template("report_emergency.html", captcha_question=captcha_question)

@app.route("/api/report", methods=["POST"])
def submit_emergency_report():
    """API endpoint for citizen emergency submission."""
    # Anti-bot verification
    user_captcha = request.form.get("captcha_answer", "").strip()
    expected_captcha = str(session.get("captcha_answer", ""))
    if not user_captcha or user_captcha != expected_captcha:
        return jsonify({"success": False, "error": "Anti-spam verification failed. Please solve the simple math puzzle correctly."}), 400

    # Required fields validation
    citizen_name = request.form.get("citizen_name", "").strip()
    phone = request.form.get("phone", "").strip()
    disaster_type = request.form.get("disaster_type", "").strip()
    severity_input = request.form.get("severity_input", "Moderate").strip()
    state = request.form.get("state", "").strip()
    district = request.form.get("district", "").strip()
    address = request.form.get("address", "").strip()
    description = request.form.get("description", "").strip()
    problems = request.form.get("problems", "").strip()
    
    if not (citizen_name and phone and disaster_type and state and district and address and description):
        return jsonify({"success": False, "error": "Please fill in all mandatory fields (Name, Phone, Disaster Type, Location, Description)."}), 400

    # Location coordinates
    try:
        lat = float(request.form.get("lat", 20.5937))
        lng = float(request.form.get("lng", 78.9629))
    except (ValueError, TypeError):
        lat, lng = 20.5937, 78.9629

    # Counts
    try:
        affected_count = max(1, int(request.form.get("affected_count", 1)))
        injured_count = max(0, int(request.form.get("injured_count", 0)))
        children_count = max(0, int(request.form.get("children_count", 0)))
        elderly_count = max(0, int(request.form.get("elderly_count", 0)))
    except (ValueError, TypeError):
        affected_count, injured_count, children_count, elderly_count = 1, 0, 0, 0

    # Assistance required
    assistance_list = request.form.getlist("assistance_required")
    if not assistance_list:
        raw_asst = request.form.get("assistance_required_str", "")
        assistance_list = [a.strip() for a in raw_asst.split(",") if a.strip()]
    if not assistance_list:
        assistance_list = ["Rescue / Evacuation"]

    assistance_required = ", ".join(assistance_list)

    # File upload handling
    media_url = None
    if "media_file" in request.files:
        file = request.files["media_file"]
        if file and file.filename and allowed_file(file.filename):
            sec_name = secure_filename(file.filename)
            uniq_name = f"{uuid.uuid4().hex[:8]}_{sec_name}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], uniq_name)
            file.save(save_path)
            media_url = f"/static/uploads/{uniq_name}"

    # Generate tracking ID
    tracking_id = generate_tracking_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Calculate Explainable Priority Score
    p_result = calculate_priority_score(
        disaster_type=disaster_type,
        affected_count=affected_count,
        injured_count=injured_count,
        children_count=children_count,
        elderly_count=elderly_count,
        assistance_list=assistance_list,
        severity_input=severity_input,
        created_at_str=now_iso
    )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incidents (
            tracking_id, citizen_name, phone, disaster_type, severity_input,
            priority_score, priority_level, affected_count, injured_count,
            children_count, elderly_count, lat, lng, state, district,
            address, description, problems, assistance_required, status,
            government_sync_status, media_url, priority_breakdown_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', 'NOT_FORWARDED', ?, ?, ?, ?)
    """, (
        tracking_id, citizen_name, phone, disaster_type, severity_input,
        p_result["score"], p_result["level"], affected_count, injured_count,
        children_count, elderly_count, lat, lng, state, district,
        address, description, problems, assistance_required,
        media_url, json.dumps(p_result["breakdown"]), now_iso, now_iso
    ))
    incident_id = cursor.lastrowid

    # Add initial update entry
    cursor.execute("""
        INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
        VALUES (?, NULL, 'Submitted', 'Emergency assistance request registered in system by citizen.', ?, 'Citizen', ?)
    """, (incident_id, citizen_name, now_iso))

    # Activity log
    log_activity(
        action="REPORT_SUBMITTED",
        entity_type="INCIDENT",
        entity_id=str(incident_id),
        user_name=citizen_name,
        role="Citizen",
        details=f"New {disaster_type} request from {district}, {state}. Priority: {p_result['level']} ({p_result['score']}/100)",
        ip=request.remote_addr or "127.0.0.1"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "tracking_id": tracking_id,
        "priority_level": p_result["level"],
        "priority_score": p_result["score"],
        "message": "Emergency request registered successfully. Triage operators have been alerted.",
        "redirect_url": f"/track?id={tracking_id}"
    })

@app.route("/api/quick-sos", methods=["POST"])
def quick_sos_submit():
    """Rapid one-click panic SOS report for high-stress imminent danger situations."""
    data = request.get_json(silent=True) or request.form
    phone = data.get("phone", "Unknown SOS Call").strip()
    disaster_type = data.get("disaster_type", "Flash Flood / Inundation").strip()
    state = data.get("state", "Emergency Alert Area").strip()
    district = data.get("district", "Rapid Response Zone").strip()
    address = data.get("address", "GPS Triangulated SOS Point").strip()

    try:
        lat = float(data.get("lat", 20.5937))
        lng = float(data.get("lng", 78.9629))
    except (ValueError, TypeError):
        lat, lng = 20.5937, 78.9629

    tracking_id = generate_tracking_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    # SOS calls default to Critical/Immediate urgency
    p_result = calculate_priority_score(
        disaster_type=disaster_type,
        affected_count=5,
        injured_count=1,
        children_count=1,
        elderly_count=1,
        assistance_list=["Rescue / Evacuation", "Urgent Medical Care / Trauma"],
        severity_input="Life Threatening",
        created_at_str=now_iso
    )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incidents (
            tracking_id, citizen_name, phone, disaster_type, severity_input,
            priority_score, priority_level, affected_count, injured_count,
            children_count, elderly_count, lat, lng, state, district,
            address, description, problems, assistance_required, status,
            government_sync_status, priority_breakdown_json, created_at, updated_at
        ) VALUES (?, 'CITIZEN IN DISTRESS (ONE-TOUCH SOS)', ?, ?, 'Life Threatening', ?, 'CRITICAL', 5, 1, 1, 1, ?, ?, ?, ?, ?, 'IMMEDIATE SOS PANIC SIGNAL ACTIVATED. Citizen in severe distress requiring emergency rescue.', 'Immediate life threat indicated by SOS trigger.', 'Rescue Boat / Evacuation, Urgent Medical Care / Trauma', 'Submitted', 'NOT_FORWARDED', ?, ?, ?)
    """, (
        tracking_id, phone, disaster_type, p_result["score"], lat, lng,
        state, district, address, json.dumps(p_result["breakdown"]), now_iso, now_iso
    ))
    inc_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
        VALUES (?, NULL, 'Submitted', 'ONE-CLICK SOS ALARM DISPATCHED: Immediate geolocation triage initiated.', 'CrisisCore QuickSOS Engine', 'System', ?)
    """, (inc_id, now_iso))

    log_activity(
        action="QUICK_SOS_ACTIVATED",
        entity_type="INCIDENT",
        entity_id=str(inc_id),
        user_name="Citizen SOS",
        role="Citizen",
        details=f"🚨 CRITICAL SOS: Phone {phone} at ({lat}, {lng})",
        ip=request.remote_addr or "127.0.0.1"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "tracking_id": tracking_id,
        "message": "🚨 SOS Panic Signal Received! Rescue teams and control rooms alerted.",
        "redirect_url": f"/track?id={tracking_id}"
    })

@app.route("/track")
def track_request_page():
    """Citizen emergency request tracking portal."""
    tracking_id = request.args.get("id", "").strip()
    phone_query = request.args.get("phone", "").strip()
    incident = None
    updates = []
    assigned_team = None
    nearby_camps = []

    if tracking_id or phone_query:
        conn = get_db()
        cursor = conn.cursor()
        if tracking_id:
            cursor.execute("SELECT * FROM incidents WHERE tracking_id = ?", (tracking_id,))
        else:
            cursor.execute("SELECT * FROM incidents WHERE phone LIKE ? ORDER BY id DESC LIMIT 1", (f"%{phone_query}%",))
        
        inc_row = cursor.fetchone()
        if inc_row:
            incident = dict(inc_row)
            # Fetch updates
            cursor.execute("SELECT * FROM incident_updates WHERE incident_id = ? ORDER BY id ASC", (incident["id"],))
            updates = [dict(u) for u in cursor.fetchall()]

            # Fetch assigned rescue team if any
            if incident.get("assigned_team_id"):
                cursor.execute("SELECT * FROM rescue_teams WHERE id = ?", (incident["assigned_team_id"],))
                team_row = cursor.fetchone()
                if team_row:
                    assigned_team = dict(team_row)

            # Fetch nearby relief camps/hospitals in same district/state
            cursor.execute("""
                SELECT * FROM relief_camps_hospitals
                WHERE district = ? OR state = ?
                ORDER BY available_capacity DESC LIMIT 4
            """, (incident["district"], incident["state"]))
            nearby_camps = [dict(c) for c in cursor.fetchall()]

        conn.close()

    return render_template(
        "tracking.html",
        tracking_id=tracking_id,
        phone_query=phone_query,
        incident=incident,
        updates=updates,
        assigned_team=assigned_team,
        nearby_camps=nearby_camps
    )

@app.route("/api/incident/<tracking_id>/citizen-update", methods=["POST"])
def citizen_post_update(tracking_id):
    """Allows citizen to post a follow-up status note to their emergency report."""
    data = request.get_json(silent=True) or request.form
    note = data.get("note", "").strip()
    if not note:
        return jsonify({"success": False, "error": "Update message cannot be empty."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, citizen_name FROM incidents WHERE tracking_id = ?", (tracking_id,))
    inc = cursor.fetchone()
    if not inc:
        conn.close()
        return jsonify({"success": False, "error": "Incident not found."}), 404

    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
        VALUES (?, ?, ?, ?, ?, 'Citizen Follow-up', ?)
    """, (inc["id"], inc["status"], inc["status"], f"[Citizen Note]: {note}", inc["citizen_name"], now_iso))

    cursor.execute("UPDATE incidents SET updated_at = ? WHERE id = ?", (now_iso, inc["id"]))

    log_activity(
        action="CITIZEN_UPDATE_POSTED",
        entity_type="INCIDENT",
        entity_id=str(inc["id"]),
        user_name=inc["citizen_name"],
        role="Citizen",
        details=f"Citizen follow-up added to {tracking_id}: {note[:50]}...",
        ip=request.remote_addr or "127.0.0.1"
    )

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Follow-up update posted to rescue log."})

# ----------------- Authority & Command Center Routes -----------------

@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def handle_login():
    data = request.get_json(silent=True) or request.form
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        session["agency"] = user["agency"]

        log_activity(
            action="LOGIN_SUCCESS",
            entity_type="USER",
            entity_id=str(user["id"]),
            user_name=user["full_name"],
            role=user["role"],
            details=f"User {username} authenticated successfully.",
            ip=request.remote_addr or "127.0.0.1"
        )
        return jsonify({"success": True, "redirect_url": url_for("dashboard_page")})
    
    return jsonify({"success": False, "error": "Invalid username or security credentials."}), 401

@app.route("/logout")
def handle_logout():
    user_name = session.get("full_name", "Unknown")
    session.clear()
    flash(f"Signed out successfully. Incident log session terminated.", "info")
    return redirect(url_for("citizen_home"))

@app.route("/dashboard")
@login_required
def dashboard_page():
    """Main Operational Command Dashboard."""
    conn = get_db()
    cursor = conn.cursor()

    # Metrics
    cursor.execute("SELECT COUNT(*) as total FROM incidents")
    total_incidents = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as critical FROM incidents WHERE priority_level = 'CRITICAL' AND status != 'Resolved'")
    critical_count = cursor.fetchone()["critical"]

    cursor.execute("SELECT SUM(affected_count) as affected, SUM(injured_count) as injured FROM incidents WHERE status != 'Resolved'")
    row_sum = cursor.fetchone()
    total_affected = row_sum["affected"] or 0
    total_injured = row_sum["injured"] or 0

    cursor.execute("SELECT COUNT(*) as active_teams FROM rescue_teams WHERE status IN ('Dispatched', 'On Site')")
    active_rescue_teams = cursor.fetchone()["active_teams"]

    cursor.execute("SELECT COUNT(*) as pending_gov FROM incidents WHERE government_sync_status IN ('NOT_FORWARDED', 'PENDING_REVIEW') AND status != 'Resolved'")
    pending_gov_transmissions = cursor.fetchone()["pending_gov"]

    # Filter parameters
    disaster_filter = request.args.get("disaster_type", "")
    priority_filter = request.args.get("priority", "")
    status_filter = request.args.get("status", "")
    state_filter = request.args.get("state", "")
    search_q = request.args.get("q", "").strip()

    sql = """
        SELECT i.*, r.name as team_name, r.agency as team_agency
        FROM incidents i
        LEFT JOIN rescue_teams r ON i.assigned_team_id = r.id
        WHERE 1=1
    """
    params = []

    if disaster_filter:
        sql += " AND i.disaster_type = ?"
        params.append(disaster_filter)
    if priority_filter:
        sql += " AND i.priority_level = ?"
        params.append(priority_filter)
    if status_filter:
        sql += " AND i.status = ?"
        params.append(status_filter)
    if state_filter:
        sql += " AND i.state = ?"
        params.append(state_filter)
    if search_q:
        sql += " AND (i.tracking_id LIKE ? OR i.citizen_name LIKE ? OR i.phone LIKE ? OR i.district LIKE ? OR i.address LIKE ?)"
        like_term = f"%{search_q}%"
        params.extend([like_term, like_term, like_term, like_term, like_term])

    sql += " ORDER BY CASE i.priority_level WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, i.priority_score DESC, i.id DESC"

    cursor.execute(sql, params)
    incidents = [dict(row) for row in cursor.fetchall()]

    # Available rescue teams for quick assignment
    cursor.execute("SELECT * FROM rescue_teams ORDER BY status = 'Available' DESC, name ASC")
    rescue_teams = [dict(row) for row in cursor.fetchall()]

    # Unique states for filter dropdown
    cursor.execute("SELECT DISTINCT state FROM incidents ORDER BY state ASC")
    states_list = [r["state"] for r in cursor.fetchall()]

    # Recent activity logs
    cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT 10")
    recent_activities = [dict(row) for row in cursor.fetchall()]

    conn.close()

    stats = {
        "total_incidents": total_incidents,
        "critical_count": critical_count,
        "total_affected": total_affected,
        "total_injured": total_injured,
        "active_rescue_teams": active_rescue_teams,
        "pending_gov_transmissions": pending_gov_transmissions
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        incidents=incidents,
        rescue_teams=rescue_teams,
        states_list=states_list,
        recent_activities=recent_activities,
        disaster_filter=disaster_filter,
        priority_filter=priority_filter,
        status_filter=status_filter,
        state_filter=state_filter,
        search_q=search_q
    )

@app.route("/incident/<tracking_id>")
@login_required
def incident_detail_page(tracking_id):
    """Detailed incident management dossier."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.*, r.name as team_name, r.agency as team_agency, r.contact_lead, r.phone as team_phone, r.status as team_status
        FROM incidents i
        LEFT JOIN rescue_teams r ON i.assigned_team_id = r.id
        WHERE i.tracking_id = ?
    """, (tracking_id,))
    incident_row = cursor.fetchone()

    if not incident_row:
        conn.close()
        flash("Incident dossier not found.", "danger")
        return redirect(url_for("dashboard_page"))

    incident = dict(incident_row)

    # Decode priority breakdown json
    try:
        incident["priority_breakdown"] = json.loads(incident.get("priority_breakdown_json") or "{}")
    except Exception:
        incident["priority_breakdown"] = {}

    # Updates timeline
    cursor.execute("SELECT * FROM incident_updates WHERE incident_id = ? ORDER BY id ASC", (incident["id"],))
    updates = [dict(u) for u in cursor.fetchall()]

    # Available rescue teams
    cursor.execute("SELECT * FROM rescue_teams ORDER BY status = 'Available' DESC, name ASC")
    rescue_teams = [dict(t) for t in cursor.fetchall()]

    # Transmissions history
    cursor.execute("SELECT * FROM government_transmissions WHERE incident_id = ? ORDER BY id DESC", (incident["id"],))
    transmissions = [dict(t) for t in cursor.fetchall()]

    conn.close()

    # Pre-generate standard CAP v1.2 preview
    cap_preview = generate_cap_v12_payload(incident)

    return render_template(
        "incident_detail.html",
        incident=incident,
        updates=updates,
        rescue_teams=rescue_teams,
        transmissions=transmissions,
        cap_preview_json=json.dumps(cap_preview, indent=2)
    )

# ----------------- Incident Management Actions -----------------

@app.route("/api/incident/<int:incident_id>/assign-team", methods=["POST"])
@login_required
def assign_rescue_team(incident_id):
    """Assigns an emergency rescue unit to an incident."""
    data = request.get_json(silent=True) or request.form
    team_id = data.get("team_id")
    dispatch_notes = data.get("notes", "Rescue unit assigned by Incident Commander.")

    if not team_id:
        return jsonify({"success": False, "error": "Please select a valid rescue unit."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Fetch incident and team
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    inc = cursor.fetchone()
    cursor.execute("SELECT * FROM rescue_teams WHERE id = ?", (team_id,))
    team = cursor.fetchone()

    if not inc or not team:
        conn.close()
        return jsonify({"success": False, "error": "Incident or Rescue Team record not found."}), 404

    now_iso = datetime.now(timezone.utc).isoformat()
    old_status = inc["status"]
    new_status = "Assigned to Rescue Team" if old_status in ["Submitted", "Under Review", "Verified"] else old_status

    cursor.execute("""
        UPDATE incidents
        SET assigned_team_id = ?, status = ?, updated_at = ?
        WHERE id = ?
    """, (team_id, new_status, now_iso, incident_id))

    # Update team status to dispatched if it was available
    cursor.execute("UPDATE rescue_teams SET status = 'Dispatched' WHERE id = ?", (team_id,))

    # Log progression update
    full_note = f"Assigned to {team['name']} ({team['agency']}). {dispatch_notes}"
    cursor.execute("""
        INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (incident_id, old_status, new_status, full_note, session.get("full_name", "Officer"), session.get("role", "Official"), now_iso))

    log_activity(
        action="TEAM_ASSIGNED",
        entity_type="INCIDENT",
        entity_id=str(incident_id),
        user_name=session.get("full_name", "Officer"),
        role=session.get("role", "Official"),
        details=f"Assigned team '{team['name']}' to incident {inc['tracking_id']}",
        ip=request.remote_addr or "127.0.0.1"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Successfully assigned {team['name']} to {inc['tracking_id']}.",
        "new_status": new_status,
        "team_name": team["name"]
    })

@app.route("/api/incident/<int:incident_id>/update-status", methods=["POST"])
@login_required
def update_incident_status(incident_id):
    """Updates the rescue operational status through the 7 designated workflow steps."""
    data = request.get_json(silent=True) or request.form
    new_status = data.get("status")
    notes = data.get("notes", "").strip()

    valid_statuses = [
        "Submitted",
        "Under Review",
        "Verified",
        "Assigned to Rescue Team",
        "Rescue Team Dispatched",
        "Assistance in Progress",
        "Resolved"
    ]

    if new_status not in valid_statuses:
        return jsonify({"success": False, "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400

    if not notes:
        return jsonify({"success": False, "error": "Operational field notes are mandatory when updating incident status."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    inc = cursor.fetchone()

    if not inc:
        conn.close()
        return jsonify({"success": False, "error": "Incident not found."}), 404

    old_status = inc["status"]
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE incidents
        SET status = ?, updated_at = ?
        WHERE id = ?
    """, (new_status, now_iso, incident_id))

    # If resolved, set rescue team back to available if assigned
    if new_status == "Resolved" and inc["assigned_team_id"]:
        cursor.execute("UPDATE rescue_teams SET status = 'Available' WHERE id = ?", (inc["assigned_team_id"],))

    # Append to update history
    cursor.execute("""
        INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (incident_id, old_status, new_status, notes, session.get("full_name", "Officer"), session.get("role", "Official"), now_iso))

    log_activity(
        action="STATUS_UPDATED",
        entity_type="INCIDENT",
        entity_id=str(incident_id),
        user_name=session.get("full_name", "Officer"),
        role=session.get("role", "Official"),
        details=f"Status changed from '{old_status}' -> '{new_status}' on {inc['tracking_id']}. Notes: {notes[:40]}",
        ip=request.remote_addr or "127.0.0.1"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Incident {inc['tracking_id']} status updated to '{new_status}'.",
        "old_status": old_status,
        "new_status": new_status
    })

@app.route("/api/incident/<int:incident_id>/override-priority", methods=["POST"])
@login_required
@role_required(["admin", "official"])
def override_priority(incident_id):
    """Allows authorized commanders to override algorithmic priority with written justification."""
    data = request.get_json(silent=True) or request.form
    new_level = data.get("priority_level", "").upper()
    override_reason = data.get("reason", "").strip()

    if new_level not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        return jsonify({"success": False, "error": "Invalid priority level."}), 400
    if not override_reason:
        return jsonify({"success": False, "error": "A written commander justification note is required to override automated priority."}), 400

    score_map = {"CRITICAL": 95, "HIGH": 75, "MEDIUM": 50, "LOW": 25}
    new_score = score_map[new_level]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    inc = cursor.fetchone()
    if not inc:
        conn.close()
        return jsonify({"success": False, "error": "Incident not found."}), 404

    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE incidents
        SET priority_level = ?, priority_score = ?, updated_at = ?
        WHERE id = ?
    """, (new_level, new_score, now_iso, incident_id))

    note_text = f"[PRIORITY OVERRIDE to {new_level}]: {override_reason}"
    cursor.execute("""
        INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
        VALUES (?, ?, ?, ?, ?, 'Commander Override', ?)
    """, (incident_id, inc["status"], inc["status"], note_text, session.get("full_name", "Commander"), now_iso))

    log_activity(
        action="PRIORITY_OVERRIDE",
        entity_type="INCIDENT",
        entity_id=str(incident_id),
        user_name=session.get("full_name", "Commander"),
        role=session.get("role", "Admin"),
        details=f"Override priority on {inc['tracking_id']} to {new_level}. Justification: {override_reason}",
        ip=request.remote_addr or "127.0.0.1"
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True, "new_level": new_level, "new_score": new_score, "message": "Priority updated with operational audit log."})

# ----------------- Government Portal Integration Endpoints -----------------

@app.route("/gov-gateway")
@login_required
def gov_gateway_page():
    """Government Gateway & Interoperability Control Room."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT gt.*, i.disaster_type, i.state, i.district, i.priority_level
        FROM government_transmissions gt
        LEFT JOIN incidents i ON gt.incident_id = i.id
        ORDER BY gt.id DESC
    """)
    transmissions = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE government_sync_status = 'TRANSMITTED'")
    transmitted_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE government_sync_status = 'PENDING_REVIEW'")
    pending_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE government_sync_status = 'NOT_FORWARDED'")
    unforwarded_count = cursor.fetchone()["count"]

    conn.close()

    return render_template(
        "gov_transmission.html",
        transmissions=transmissions,
        transmitted_count=transmitted_count,
        pending_count=pending_count,
        unforwarded_count=unforwarded_count
    )

@app.route("/api/incident/<int:incident_id>/transmit-gov", methods=["POST"])
@login_required
@role_required(["admin", "official"])
def transmit_incident_to_gov(incident_id):
    """
    Transmits verified incident to designated Government authority node
    (NDMA / SDMA / DDMA / 112 ERSS) using official CAP v1.2 standard.
    Never falsely claims success.
    """
    data = request.get_json(silent=True) or request.form
    target_agency = data.get("target_agency", "NDMA_CENTRAL")
    official_notes = data.get("notes", "Verified by CrisisCore Incident Commander.")
    simulate_fail = data.get("simulate_failure", False)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    inc = cursor.fetchone()

    if not inc:
        conn.close()
        return jsonify({"success": False, "error": "Incident record not found."}), 404

    inc_dict = dict(inc)
    result = transmit_to_government_authority(
        incident=inc_dict,
        target_agency=target_agency,
        official_name=session.get("full_name", "Duty Officer"),
        official_notes=official_notes,
        simulate_failure=bool(simulate_fail)
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    if result["success"]:
        # Update incident record with transmission confirmation
        cursor.execute("""
            UPDATE incidents
            SET government_sync_status = 'TRANSMITTED',
                sync_receipt_id = ?,
                sync_timestamp = ?,
                updated_at = ?
            WHERE id = ?
        """, (result["receipt_id"], result["timestamp"], now_iso, incident_id))

        # Insert into government_transmissions audit table
        cursor.execute("""
            INSERT INTO government_transmissions (
                incident_id, tracking_id, target_agency, transmission_status,
                protocol, payload_json, response_hash, timestamp, transmitted_by,
                receipt_id, acknowledgement_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_id, inc["tracking_id"], target_agency, "TRANSMITTED",
            result["protocol"], result["payload_json"], result["payload_hash"],
            result["timestamp"], result["transmitted_by"], result["receipt_id"],
            result["acknowledgement_code"]
        ))

        # Add progression update
        cursor.execute("""
            INSERT INTO incident_updates (incident_id, status_from, status_to, notes, author_name, author_role, created_at)
            VALUES (?, ?, ?, ?, ?, 'Government Gateway', ?)
        """, (
            incident_id, inc["status"], inc["status"],
            f"Transmitted to {target_agency} Gateway. Receipt ID: {result['receipt_id']}. SHA256: {result['payload_hash'][:16]}...",
            session.get("full_name", "Officer"), now_iso
        ))

        log_activity(
            action="GOV_TRANSMISSION_SUCCESS",
            entity_type="INCIDENT",
            entity_id=str(incident_id),
            user_name=session.get("full_name", "Officer"),
            role=session.get("role", "Official"),
            details=f"Securely transmitted {inc['tracking_id']} to {target_agency}. Receipt: {result['receipt_id']}",
            ip=request.remote_addr or "127.0.0.1"
        )
        conn.commit()
        conn.close()
        return jsonify(result)
    else:
        # Explicit failure recording
        cursor.execute("""
            UPDATE incidents
            SET government_sync_status = 'TRANSMISSION_FAILED',
                updated_at = ?
            WHERE id = ?
        """, (now_iso, incident_id))

        cursor.execute("""
            INSERT INTO government_transmissions (
                incident_id, tracking_id, target_agency, transmission_status,
                protocol, payload_json, response_hash, timestamp, transmitted_by,
                receipt_id, acknowledgement_code
            ) VALUES (?, ?, ?, 'FAILED', 'OASIS CAP v1.2', '{}', '', ?, ?, NULL, NULL)
        """, (incident_id, inc["tracking_id"], target_agency, now_iso, session.get("full_name", "Officer")))

        conn.commit()
        conn.close()
        return jsonify(result), 502

@app.route("/api/incident/<int:incident_id>/cap-payload")
@login_required
def get_cap_payload(incident_id):
    """Returns standardized OASIS CAP v1.2 JSON payload for external interoperability."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    inc = cursor.fetchone()
    conn.close()

    if not inc:
        return jsonify({"error": "Incident not found"}), 404

    payload = generate_cap_v12_payload(dict(inc))
    return jsonify(payload)

# ----------------- Resources Management -----------------

@app.route("/resources")
@login_required
def resources_page():
    """Emergency resource inventory monitoring & allocation."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources ORDER BY category ASC, location_district ASC")
    resources_list = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM relief_camps_hospitals ORDER BY state ASC, type ASC")
    camps_list = [dict(c) for c in cursor.fetchall()]

    conn.close()
    return render_template("resources.html", resources=resources_list, camps=camps_list)

@app.route("/api/resources/<int:resource_id>/update", methods=["POST"])
@login_required
@role_required(["admin", "official"])
def update_resource(resource_id):
    data = request.get_json(silent=True) or request.form
    try:
        available_qty = int(data.get("available_qty", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid quantity."}), 400

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE resources SET available_qty = ?, last_updated = ? WHERE id = ?", (available_qty, now_iso, resource_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Resource quantity updated successfully."})

# ----------------- Analytics & Reporting -----------------

@app.route("/analytics")
@login_required
def analytics_page():
    """Emergency reports, metrics, response speed, and priority distribution."""
    conn = get_db()
    cursor = conn.cursor()

    # Disaster breakdown
    cursor.execute("""
        SELECT disaster_type, COUNT(*) as count, SUM(affected_count) as total_affected, SUM(injured_count) as total_injured
        FROM incidents
        GROUP BY disaster_type
        ORDER BY count DESC
    """)
    by_disaster = [dict(r) for r in cursor.fetchall()]

    # Priority level distribution
    cursor.execute("""
        SELECT priority_level, COUNT(*) as count
        FROM incidents
        GROUP BY priority_level
    """)
    by_priority = [dict(r) for r in cursor.fetchall()]

    # Status distribution
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM incidents
        GROUP BY status
    """)
    by_status = [dict(r) for r in cursor.fetchall()]

    # State breakdown
    cursor.execute("""
        SELECT state, COUNT(*) as count, SUM(affected_count) as affected
        FROM incidents
        GROUP BY state
        ORDER BY count DESC
    """)
    by_state = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return render_template(
        "analytics.html",
        by_disaster=by_disaster,
        by_priority=by_priority,
        by_status=by_status,
        by_state=by_state
    )

@app.route("/api/export/sitrep.pdf")
@login_required
def export_sitrep_pdf():
    """Generates official NDMA-compliant Disaster Situation Report (SITREP) in PDF format."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM incidents ORDER BY priority_score DESC, id DESC")
    incidents = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM incidents")
    total_incidents = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as critical FROM incidents WHERE priority_level = 'CRITICAL'")
    critical_count = cursor.fetchone()["critical"]
    cursor.execute("SELECT SUM(affected_count) as aff, SUM(injured_count) as inj FROM incidents")
    sums = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as teams FROM rescue_teams WHERE status = 'Dispatched'")
    active_teams = cursor.fetchone()["teams"]

    conn.close()

    stats = {
        "total_incidents": total_incidents,
        "critical_count": critical_count,
        "total_affected": sums["aff"] or 0,
        "total_injured": sums["inj"] or 0,
        "active_rescue_teams": active_teams
    }

    pdf_buffer = generate_sitrep_pdf(
        incidents_list=incidents,
        stats=stats,
        official_name=session.get("full_name", "Incident Commander")
    )

    filename = f"CrisisCore_NDMA_SITREP_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

@app.route("/api/export/incidents.csv")
@login_required
def export_incidents_csv():
    """Exports all incident data in standardized CSV format."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY id DESC")
    incidents = [dict(r) for r in cursor.fetchall()]
    conn.close()

    csv_data = generate_incidents_csv(incidents)
    filename = f"CrisisCore_Incidents_Registry_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    return send_file(
        io.BytesIO(csv_data.encode("utf-8")),
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv"
    )

# ----------------- Real-Time Map & Data Polling API -----------------

@app.route("/api/map-data")
def get_map_data():
    """Returns dynamic geo-coordinates and metadata for Leaflet map layers."""
    conn = get_db()
    cursor = conn.cursor()

    # Active Incidents
    cursor.execute("""
        SELECT id, tracking_id, disaster_type, priority_level, priority_score,
               status, affected_count, injured_count, lat, lng, district, state,
               address, description, assistance_required, government_sync_status,
               created_at
        FROM incidents
        WHERE status != 'Resolved'
    """)
    incidents = [dict(r) for r in cursor.fetchall()]

    # Rescue Teams
    cursor.execute("SELECT * FROM rescue_teams")
    teams = [dict(r) for r in cursor.fetchall()]

    # Relief Camps & Hospitals
    cursor.execute("SELECT * FROM relief_camps_hospitals WHERE verified = 1")
    camps = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return jsonify({
        "success": True,
        "incidents": incidents,
        "rescue_teams": teams,
        "relief_camps": camps
    })

@app.route("/api/stats")
def get_live_stats():
    """Live JSON counters for auto-refreshing dashboard without page reloads."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE status != 'Resolved'")
    active_incidents = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE priority_level = 'CRITICAL' AND status != 'Resolved'")
    critical = cursor.fetchone()["count"]

    cursor.execute("SELECT SUM(affected_count) as aff, SUM(injured_count) as inj FROM incidents WHERE status != 'Resolved'")
    sums = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM rescue_teams WHERE status = 'Dispatched'")
    deployed = cursor.fetchone()["count"]

    conn.close()

    return jsonify({
        "active_incidents": active_incidents,
        "critical_incidents": critical,
        "total_affected": sums["aff"] or 0,
        "total_injured": sums["inj"] or 0,
        "deployed_teams": deployed
    })

# ----------------- App Boot -----------------

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
