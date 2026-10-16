import math
from datetime import datetime, timezone

# Disaster intrinsic hazard weights
DISASTER_WEIGHTS = {
    "Earthquake": 20,
    "Flash Flood / Inundation": 19,
    "Landslide / Mudflow": 19,
    "Cyclone / Super Storm": 18,
    "Industrial Fire / Explosion": 18,
    "Building Collapse": 19,
    "Tsunami / Coastal Surge": 22,
    "Forest Wildfire": 16,
    "Severe Cloudburst": 20,
    "Other": 10
}

SEVERITY_INPUT_WEIGHTS = {
    "Life Threatening": 15,
    "Immediate Danger": 10,
    "Moderate": 5,
    "Precautionary": 2
}

def calculate_priority_score(
    disaster_type: str,
    affected_count: int,
    injured_count: int,
    children_count: int,
    elderly_count: int,
    assistance_list: list,
    severity_input: str,
    created_at_str: str = None
) -> dict:
    """
    Computes an explainable Priority Score (0-100) and Level.
    Returns:
        {
            'score': int (0-100),
            'level': 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW',
            'breakdown': { ... },
            'recommended_action': str
        }
    """
    breakdown = {}
    
    # 1. Injured Factor (Max 30)
    # Injured citizens take highest medical urgency
    inj_pts = min(30, int(injured_count * 7.5))
    breakdown["injured_points"] = {
        "value": inj_pts,
        "max": 30,
        "detail": f"{injured_count} injured person(s) (7.5 pts per injured, max 30)"
    }
    
    # 2. Vulnerable Individuals Factor (Children + Elderly) (Max 20)
    vuln_count = children_count + elderly_count
    vuln_pts = min(20, int(vuln_count * 4.0))
    breakdown["vulnerable_points"] = {
        "value": vuln_pts,
        "max": 20,
        "detail": f"{children_count} children + {elderly_count} elderly ({vuln_count} vulnerable, 4 pts each)"
    }
    
    # 3. Scale of Affected Population (Max 15)
    aff_pts = min(15, int(math.log10(max(1, affected_count) + 1) * 8.0))
    breakdown["affected_scale_points"] = {
        "value": aff_pts,
        "max": 15,
        "detail": f"{affected_count} affected citizens (logarithmic scale up to 15 pts)"
    }
    
    # 4. Disaster Type Hazard Factor (Max 22)
    hazard_pts = DISASTER_WEIGHTS.get(disaster_type, 12)
    breakdown["disaster_hazard_points"] = {
        "value": hazard_pts,
        "max": 22,
        "detail": f"Inherent severity rating for {disaster_type}"
    }
    
    # 5. Immediate Assistance Urgency (Max 20)
    asst_pts = 0
    asst_reasons = []
    asst_lower = [a.lower() for a in assistance_list] if assistance_list else []
    
    if any("rescue" in a or "evacuation" in a or "boat" in a for a in asst_lower):
        asst_pts += 10
        asst_reasons.append("Rescue/Evacuation required (+10)")
    if any("medical" in a or "ambulance" in a or "trauma" in a for a in asst_lower):
        asst_pts += 10
        asst_reasons.append("Medical/Trauma aid required (+10)")
    if any("shelter" in a for a in asst_lower):
        asst_pts += 3
        asst_reasons.append("Shelter needed (+3)")
    if any("food" in a or "water" in a for a in asst_lower):
        asst_pts += 3
        asst_reasons.append("Food/Water needed (+3)")
        
    asst_pts = min(20, asst_pts)
    breakdown["assistance_urgency_points"] = {
        "value": asst_pts,
        "max": 20,
        "detail": ", ".join(asst_reasons) if asst_reasons else "Standard supplies"
    }
    
    # 6. Citizen Reported Urgency (Max 15)
    sev_pts = SEVERITY_INPUT_WEIGHTS.get(severity_input, 5)
    breakdown["severity_assessment_points"] = {
        "value": sev_pts,
        "max": 15,
        "detail": f"Citizen evaluated situation as: '{severity_input}'"
    }
    
    # 7. Time Elapsed Escalation Factor (Max 15)
    # Unresolved incidents escalate over time to prevent lower-priority calls from being forgotten
    time_pts = 0
    time_detail = "Reported recently"
    if created_at_str:
        try:
            # support ISO format
            created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            if created_dt.tzinfo is None:
                # assume UTC
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            minutes_elapsed = max(0, (now_dt - created_dt).total_seconds() / 60)
            
            # +2 points for every 30 minutes unaddressed, up to 15 points
            time_pts = min(15, int((minutes_elapsed // 30) * 2))
            time_detail = f"{int(minutes_elapsed)} mins elapsed (+{time_pts} escalation points)"
        except Exception:
            time_pts = 0
            
    breakdown["time_escalation_points"] = {
        "value": time_pts,
        "max": 15,
        "detail": time_detail
    }
    
    raw_total = inj_pts + vuln_pts + aff_pts + hazard_pts + asst_pts + sev_pts + time_pts
    final_score = min(100, max(5, raw_total))
    
    if final_score >= 80:
        level = "CRITICAL"
        rec_action = "🚨 IMMEDIATE DISPATCH REQUIRED: Alert nearest NDRF/SDRF unit and mobilize Emergency Medical Services."
    elif final_score >= 60:
        level = "HIGH"
        rec_action = "⚡ HIGH PRIORITY: Assign Rescue Team and notify District Disaster Management Officer."
    elif final_score >= 35:
        level = "MEDIUM"
        rec_action = "📋 MEDIUM PRIORITY: Queue for field responder assessment and relief distribution."
    else:
        level = "LOW"
        rec_action = "ℹ️ MONITOR: Precautionary or localized incident. Route to local Panchayat / Civil Defense."
        
    return {
        "score": final_score,
        "level": level,
        "breakdown": breakdown,
        "recommended_action": rec_action
    }
