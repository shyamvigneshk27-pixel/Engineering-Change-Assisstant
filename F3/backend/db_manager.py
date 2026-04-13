"""
db_manager.py — Supabase Version-Control Integration
Saves every ECA analysis as a complete, versioned record:
  - Original prompt / EWR
  - Full BOM before/after
  - Inspection plan changes
  - Cost analysis
  - Validation checks
  - PDF (base64)
  - Revision type & label (Major/Minor)
  - Auto-incrementing version number per part
"""
import os, base64, json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Lazy-init Supabase client
_supabase = None

def _get_client():
    global _supabase
    if _supabase is not None:
        return _supabase
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  [⚠️ DB] SUPABASE_URL or SUPABASE_KEY not set — DB operations skipped")
        return None
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("  [✅ DB] Supabase client connected")
        return _supabase
    except Exception as e:
        print(f"  [❌ DB] Supabase connect error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN: Save a full ECA session as a version-controlled record
# ─────────────────────────────────────────────────────────────────────────────

def save_session(session_id: str, prompt: str, parsed: dict, impact: dict,
                 validation: dict, report: dict, cad_result: dict = None,
                 cad_storage_path: str = None, step_storage_path: str = None) -> dict | None:
    """
    Persists a complete ECA analysis to Supabase table `eca_sessions`.
    Returns the inserted row or None on failure.

    Supabase table schema (create once via SQL editor):
    ┌──────────────────────┬───────────────────┐
    │ column               │ type              │
    ├──────────────────────┼───────────────────┤
    │ id                   │ uuid (PK default) │
    │ session_id           │ text              │
    │ created_at           │ timestamptz       │
    │ version_number       │ int8              │
    │ prompt               │ text              │
    │ revision_type        │ text              │
    │ revision_label       │ text              │
    │ change_category      │ text              │
    │ parts_affected       │ int4              │
    │ assemblies_affected  │ int4              │
    │ inspection_steps     │ int4              │
    │ documents_updated    │ int4              │
    │ safety_critical      │ int4              │
    │ total_effort_hours   │ int4              │
    │ risk_score           │ int4              │
    │ overall_safe         │ bool              │
    │ bom_data             │ jsonb             │
    │ cost_analysis        │ jsonb             │
    │ inspection_data      │ jsonb             │
    │ validation_checks    │ jsonb             │
    │ barlow_details       │ jsonb             │
    │ affected_parts       │ jsonb             │
    │ affected_assemblies  │ jsonb             │
    │ document_impacts     │ jsonb             │
    │ safety_warnings      │ jsonb             │
    │ narrative            │ text              │
    │ pdf_base64           │ text              │
    │ cad_method           │ text              │
    │ vol_removed_mm3      │ float8            │
    │ mass_reduction_pct   │ float8            │
    └──────────────────────┴───────────────────┘
    """
    sb = _get_client()
    if not sb:
        return None

    try:
        # Auto-increment version_number globally
        try:
            hist = sb.table("eca_sessions").select("version_number").order("version_number", desc=True).limit(1).execute()
            last_ver = hist.data[0]["version_number"] if hist.data else 0
        except Exception:
            last_ver = 0
        version_number = last_ver + 1

        rev = validation.get("revision_data", {})
        summary = impact.get("summary", {})
        effort = validation.get("effort_data", {})

        # Encode PDF bytes as base64 string (safe for JSON/Supabase text column)
        pdf_b64 = ""
        try:
            pdf_raw = report.get("pdf_bytes", b"")
            if isinstance(pdf_raw, (bytes, bytearray)) and pdf_raw:
                pdf_b64 = base64.b64encode(pdf_raw).decode("utf-8")
        except Exception:
            pass

        row = {
            "session_id":           str(session_id),
            "created_at":           datetime.utcnow().isoformat(),
            "version_number":       version_number,
            "prompt":               str(prompt)[:4000],
            "revision_type":        rev.get("revision_type", "Minor"),
            "revision_label":       rev.get("revision_label", "Rev A"),
            "change_category":      parsed.get("change_category", "dimensional"),
            "parts_affected":       summary.get("total_parts_affected", 0),
            "assemblies_affected":  summary.get("total_assemblies_affected", 0),
            "inspection_steps":     summary.get("total_inspection_steps_to_update", 0),
            "documents_updated":    summary.get("total_documents_to_update", 0),
            "safety_critical":      summary.get("safety_critical_assemblies", 0),
            "total_effort_hours":   effort.get("total_hours", 0),
            "risk_score":           rev.get("risk_score", 0),
            "overall_safe":         bool(validation.get("overall_safe", True)),
            "bom_data":             json.dumps(impact.get("bom_before_after", [])),
            "cost_analysis":        json.dumps(impact.get("cost_analysis", {})),
            "inspection_data":      json.dumps(impact.get("inspection_before_after", [])),
            "validation_checks":    json.dumps(validation.get("validation_checks", [])),
            "barlow_details":       json.dumps(impact.get("barlow_details", [])),
            "affected_parts":       json.dumps(impact.get("affected_parts", [])),
            "affected_assemblies":  json.dumps(impact.get("affected_assemblies", [])),
            "document_impacts":     json.dumps(impact.get("document_impacts", [])),
            "safety_warnings":      json.dumps(impact.get("safety_warnings", [])),
            "narrative":            str(report.get("narrative", "")),
            "pdf_base64":           pdf_b64,
            "cad_method":           cad_result.get("cad_method", "simulation") if cad_result else "simulation",
            "vol_removed_mm3":      float(cad_result.get("vol_removed_mm3", 0) or 0) if cad_result else 0.0,
            "mass_reduction_pct":   float(cad_result.get("mass_reduction_pct", 0) or 0) if cad_result else 0.0,
            "cad_storage_path":     cad_storage_path,
            "step_storage_path":    step_storage_path
        }

        res = sb.table("eca_sessions").insert(row).execute()
        print(f"  [✅ DB] Session v{version_number} saved → id={res.data[0].get('id','?') if res.data else '?'}")
        return res.data[0] if res.data else None

    except Exception as e:
        print(f"  [❌ DB] save_session error: {e}")
        return None


def upload_cad_model(local_path: str, supabase_path: str) -> str | None:
    """Uploads a local .FCStd file to Supabase Storage bucket `eca-cad-models`."""
    sb = _get_client()
    if not sb: return None
    print(f"  [DB] Starting upload: {local_path} -> {supabase_path}")
    try:
        # Ensure bucket exists
        try:
            sb.storage.get_bucket("eca-cad-models")
        except Exception:
            try:
                sb.storage.create_bucket("eca-cad-models", options={"public": True})
                print("  [DB] Created storage bucket 'eca-cad-models'")
            except Exception as e:
                print(f"  [DB] Bucket creation failed: {e}")

        if not os.path.exists(local_path):
            print(f"  [⚠️ DB] CAD file NOT FOUND for upload at: {local_path}")
            return None
            
        with open(local_path, "rb") as f:
            # We use upsert=true to allow overwriting if the same session is re-run
            sb.storage.from_("eca-cad-models").upload(
                path=supabase_path,
                file=f,
                file_options={"cache-control": "3600", "upsert": True}
            )
        print(f"  [✅ DB] CAD model archived to Storage: {supabase_path}")
        return supabase_path
    except Exception as e:
        print(f"  [❌ DB] upload_cad_model error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  LEGACY: Save individual parameter change (model_versions table)
# ─────────────────────────────────────────────────────────────────────────────

def save_version(part_id, parameter, old_val, new_val, session_id):
    """Legacy: logs a single parameter change row into model_versions table."""
    sb = _get_client()
    if not sb:
        return None
    try:
        data = {
            "part_id":        str(part_id),
            "parameter_name": str(parameter),
            "old_value":      float(old_val) if old_val is not None else 0.0,
            "new_value":      float(new_val) if new_val is not None else 0.0,
            "session_id":     str(session_id),
        }
        res = sb.table("model_versions").insert(data).execute()
        return res.data
    except Exception as e:
        print(f"  [⚠️ DB] save_version error (non-fatal): {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  READ: Version history (all sessions, newest first)
# ─────────────────────────────────────────────────────────────────────────────

def get_history(limit: int = 50) -> list:
    """
    Returns all ECA sessions ordered by version_number descending.
    Each row contains the full metadata needed to render the version history UI.
    Heavy fields (pdf_base64, bom_data …) are excluded from the list view
    to keep the response small — use get_session() for full detail.
    """
    sb = _get_client()
    if not sb:
        return []
    try:
        cols = ",".join([
            "id", "session_id", "created_at", "version_number", "prompt",
            "revision_type", "revision_label", "change_category",
            "parts_affected", "assemblies_affected", "inspection_steps",
            "documents_updated", "safety_critical", "total_effort_hours",
            "risk_score", "overall_safe", "cad_method",
            "vol_removed_mm3", "mass_reduction_pct", "narrative",
            "cad_storage_path", "step_storage_path"
        ])
        res = sb.table("eca_sessions").select(cols).order("version_number", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"  [❌ DB] get_history error: {e}")
        return []


def get_session(session_id: str) -> dict | None:
    """Returns the full record (including PDF base64 and all JSON blobs) for one session."""
    sb = _get_client()
    if not sb:
        return None
    try:
        res = sb.table("eca_sessions").select("*").eq("session_id", session_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"  [❌ DB] get_session error: {e}")
        return None
