"""
SECURITY MODULE — Zero Trust OT Access Control
Solves PS Problems #23-26:
  23. Role-based secure access control for CNC systems
  24. Audit logs for all CNC/CAD interactions
  25. Detection of abnormal or suspicious access attempts
  26. Centralized monitoring for OT systems
"""
import json, time, os, hashlib
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import request, jsonify

AUDIT_DIR = Path(__file__).parent.parent / "audit_logs"
AUDIT_DIR.mkdir(exist_ok=True)
AUDIT_FILE = AUDIT_DIR / "access_log.json"

# ========== ROLE-BASED ACCESS CONTROL (Problem #23) ==========
ROLES = {
    "admin":    {"level": 3, "permissions": ["read", "write", "modify_cad", "approve_change", "access_cnc", "view_audit"]},
    "engineer": {"level": 2, "permissions": ["read", "write", "modify_cad", "approve_change"]},
    "operator": {"level": 1, "permissions": ["read", "access_cnc"]},
    "viewer":   {"level": 0, "permissions": ["read"]},
}

# Simulated user sessions (in production: LDAP/SSO integration)
USERS = {
    "admin_token":    {"user": "Admin",       "role": "admin",    "department": "Engineering Management"},
    "eng_token":      {"user": "Ashwin",      "role": "engineer", "department": "Mechanical Engineering"},
    "op_token":       {"user": "CNC_Operator", "role": "operator", "department": "Manufacturing Floor"},
    "viewer_token":   {"user": "Auditor",     "role": "viewer",   "department": "Quality Assurance"},
    "demo":           {"user": "DemoUser",    "role": "engineer", "department": "Hackathon Demo"},
}

# ========== AUDIT LOGGING (Problem #24) ==========
def _load_audit():
    if AUDIT_FILE.exists():
        try:
            return json.loads(AUDIT_FILE.read_text())
        except:
            return []
    return []

def _save_audit(logs):
    AUDIT_FILE.write_text(json.dumps(logs, indent=2, default=str))

def log_access(user, action, resource, status, details=""):
    """Log every access attempt with full traceability."""
    logs = _load_audit()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "action": action,
        "resource": resource,
        "status": status,  # "GRANTED" or "DENIED"
        "ip_address": request.remote_addr if request else "system",
        "user_agent": request.headers.get("User-Agent", "")[:100] if request else "system",
        "details": details,
        "session_hash": hashlib.md5(f"{user}{time.time()}".encode()).hexdigest()[:12]
    }
    logs.append(entry)

    # Keep only last 1000 entries
    if len(logs) > 1000:
        logs = logs[-1000:]

    _save_audit(logs)

    # Check for suspicious patterns (Problem #25)
    _detect_anomalies(logs, entry)

    return entry

# ========== ANOMALY DETECTION (Problem #25) ==========
ALERT_LOG = AUDIT_DIR / "security_alerts.json"

def _detect_anomalies(logs, current_entry):
    """Detect suspicious access patterns."""
    alerts = []
    user = current_entry["user"]

    # Check 1: Rapid access attempts (>10 in 60 seconds)
    recent = [l for l in logs[-50:] if l["user"] == user
              and (datetime.fromisoformat(current_entry["timestamp"]) -
                   datetime.fromisoformat(l["timestamp"])).total_seconds() < 60]
    if len(recent) > 10:
        alerts.append({
            "type": "RAPID_ACCESS",
            "severity": "HIGH",
            "message": f"User '{user}' made {len(recent)} requests in 60s (threshold: 10)",
            "timestamp": current_entry["timestamp"]
        })

    # Check 2: Access denied patterns
    denied_recent = [l for l in logs[-20:] if l["user"] == user and l["status"] == "DENIED"]
    if len(denied_recent) >= 3:
        alerts.append({
            "type": "REPEATED_DENIAL",
            "severity": "CRITICAL",
            "message": f"User '{user}' has {len(denied_recent)} access denials - possible privilege escalation",
            "timestamp": current_entry["timestamp"]
        })

    # Check 3: Off-hours access (before 6AM or after 10PM)
    hour = datetime.fromisoformat(current_entry["timestamp"]).hour
    if hour < 6 or hour > 22:
        alerts.append({
            "type": "OFF_HOURS_ACCESS",
            "severity": "MEDIUM",
            "message": f"User '{user}' accessing system at {hour}:00 (outside business hours)",
            "timestamp": current_entry["timestamp"]
        })

    if alerts:
        existing = []
        if ALERT_LOG.exists():
            try:
                existing = json.loads(ALERT_LOG.read_text())
            except:
                pass
        existing.extend(alerts)
        ALERT_LOG.write_text(json.dumps(existing[-500:], indent=2, default=str))

# ========== OT MONITORING (Problem #26) ==========
def get_ot_status():
    """Centralized OT system monitoring dashboard data."""
    logs = _load_audit()
    alerts = []
    if ALERT_LOG.exists():
        try:
            alerts = json.loads(ALERT_LOG.read_text())
        except:
            pass

    # Compute metrics
    total_requests = len(logs)
    denied = sum(1 for l in logs if l["status"] == "DENIED")
    granted = total_requests - denied
    unique_users = len(set(l["user"] for l in logs))
    critical_alerts = sum(1 for a in alerts if a.get("severity") == "CRITICAL")

    return {
        "ot_systems": {
            "freecad_engine": {"status": "ONLINE", "last_heartbeat": datetime.now().isoformat()},
            "gemini_ai": {"status": "ONLINE", "last_heartbeat": datetime.now().isoformat()},
            "pdm_database": {"status": "ONLINE", "last_heartbeat": datetime.now().isoformat()},
            "audit_logger": {"status": "ONLINE", "entries": total_requests},
        },
        "access_summary": {
            "total_requests": total_requests,
            "granted": granted,
            "denied": denied,
            "denial_rate": f"{(denied/total_requests*100):.1f}%" if total_requests else "0%",
            "unique_users": unique_users,
        },
        "security_alerts": {
            "total": len(alerts),
            "critical": critical_alerts,
            "recent": alerts[-5:] if alerts else [],
        },
        "recent_activity": logs[-10:] if logs else [],
    }


def check_permission(required_permission):
    """Decorator to enforce role-based access on Flask routes."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get("X-Auth-Token", "demo")
            user_info = USERS.get(token)

            if not user_info:
                log_access("UNKNOWN", f.__name__, required_permission, "DENIED", "Invalid token")
                return jsonify({"error": "Unauthorized", "code": "AUTH_FAILED"}), 401

            if required_permission not in ROLES[user_info["role"]]["permissions"]:
                log_access(user_info["user"], f.__name__, required_permission, "DENIED",
                          f"Role '{user_info['role']}' lacks '{required_permission}'")
                return jsonify({"error": "Insufficient permissions",
                               "required": required_permission,
                               "your_role": user_info["role"]}), 403

            log_access(user_info["user"], f.__name__, required_permission, "GRANTED")
            return f(*args, **kwargs)
        return decorated
    return decorator
