import json
from pathlib import Path

DB = Path(__file__).parent.parent / "database"

def classify_revision(parsed: dict, impact: dict) -> dict:
    rules = json.load(open(DB / "revision_rules.json"))
    parts = json.load(open(DB / "parts.json"))
    triggered_major = []
    changes = parsed.get("changes", [])

    for c in changes:
        pct = abs(c.get("delta_pct", 0))
        param = c.get("parameter", "")
        pid = c.get("part_id", "")
        cat = parts.get(pid, {}).get("category", "")

        if "wall_thickness" in param and pct > 10:
            triggered_major.append({"rule_id": "MJ-01",
                "description": f"Wall thickness change {pct:.1f}% > 10% ASME threshold",
                "rationale": "Pressure vessel re-qualification required per ASME VIII"})
        if parsed.get("material_change"):
            triggered_major.append({"rule_id": "MJ-02",
                "description": f"Material substitution to {parsed.get('new_material', 'new material')}",
                "rationale": "Full re-qualification, PMI, weld procedure required"})
        if cat == "pressure_retaining" and pct > 5:
            triggered_major.append({"rule_id": "MJ-03",
                "description": f"Pressure-retaining part changed by {pct:.1f}%",
                "rationale": "Safety-critical boundary re-certification per API 6D"})
        if parsed.get("affects_mating_interface"):
            triggered_major.append({"rule_id": "MJ-04",
                "description": "Mating interface dimension modified",
                "rationale": "Assembly re-validation required"})

    if impact["summary"]["total_assemblies_affected"] > 2:
        triggered_major.append({"rule_id": "MJ-05",
            "description": f"Change propagates to {impact['summary']['total_assemblies_affected']} assemblies",
            "rationale": "System-level re-verification required"})

    if impact["summary"]["has_safety_violations"]:
        triggered_major.append({"rule_id": "MJ-SAFETY",
            "description": "CRITICAL safety constraint violation detected",
            "rationale": "Engineering hold — cannot proceed without Principal Engineer sign-off"})

    is_major = len(triggered_major) > 0
    if not is_major:
        triggered_minor = [{"rule_id": "MN-03",
            "description": "Change below all major revision thresholds"}]
    else:
        triggered_minor = []

    rev_ids = [parts.get(pid, {}).get("current_revision", "A")
               for pid in parsed.get("affected_part_ids", [])]
    cur = max(rev_ids) if rev_ids else "A"
    if is_major:
        nxt = chr(ord(cur) + 1) if cur < "Z" else "AA"
        label = f"{cur} -> {nxt}"
        note = f"New ECR/ECO required. Drawings advance to Rev {nxt}."
    else:
        label = f"{cur} -> {cur}1"
        note = "Sub-revision. Note update only. No new ECO required."

    return {"revision_type": "Major" if is_major else "Minor",
            "triggered_rules": triggered_major if is_major else triggered_minor,
            "revision_label": label, "revision_note": note,
            "requires_engineering_hold": impact["summary"]["has_safety_violations"]}


def estimate_effort(revision: dict, impact: dict, parsed: dict) -> dict:
    rules = json.load(open(DB / "revision_rules.json"))
    m = rules["effort_matrix_hours"]
    rev = revision["revision_type"]
    np_ = impact["summary"]["total_parts_affected"]
    na = impact["summary"]["total_assemblies_affected"]
    sc = impact["summary"]["safety_critical_assemblies"] > 0
    sv = impact["summary"]["has_safety_violations"]

    if rev == "Minor":
        base = m["minor_single_part"] if na == 0 else (m["minor_with_assembly"] if np_ == 1 else m["minor_multi_part"])
    else:
        if sv: base = m["major_multi_assembly_safety_critical"]
        elif na > 2: base = m["major_multi_assembly_safety_critical"] if sc else m["major_multi_assembly"]
        elif np_ > 1: base = m["major_multi_part"]
        elif sc: base = m["major_safety_critical"]
        else: base = m["major_single_part"]

    mult = 1.0
    if parsed.get("material_change"): mult += 0.4
    if na > 3: mult += 0.2
    if sv: mult += 0.5

    total = round(base * mult)
    breakdown = {k: round(total * v / 100) for k, v in rules["effort_breakdown_pct"].items()}
    return {"total_hours": total, "total_days": round(total / 8, 1),
            "breakdown": breakdown, "cost_estimate_usd": total * 30,
            "basis": f"Base: {base}h x {mult:.1f}x multiplier", "confidence": "±20%"}
