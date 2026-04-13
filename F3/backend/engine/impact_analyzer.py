import json
from pathlib import Path

DB = Path(__file__).parent.parent / "database"

def _load():
    def j(f): return json.load(open(DB / f))
    return j("parts.json"), j("assemblies.json"), j("bom.json"), j("inspection_plans.json"), j("revision_rules.json")

def run_impact_analysis(parsed: dict) -> dict:
    parts, assemblies, bom, inspection, rules = _load()
    direct_ids = parsed.get("affected_part_ids", [])
    cascade_ids = parsed.get("cascade_part_ids", [])
    all_ids = list(set(direct_ids + cascade_ids))
    changes = parsed.get("changes", [])

    # Layer 1: Parts
    affected_parts = []
    for pid in all_ids:
        p = parts.get(pid)
        if not p: continue
        affected_parts.append({
            "part_id": pid, "part_name": p["name"], "material": p["material"],
            "category": p["category"], "current_revision": p["current_revision"],
            "impact_type": "direct_modification" if pid in direct_ids else "cascade_dependency",
            "action_required": "Modify CAD + Re-inspect" if pid in direct_ids else "Verify interface"
        })

    # Layer 2: Assemblies (upward traversal)
    def get_parents(asm_id, visited=None):
        visited = visited or set()
        if asm_id in visited: return []
        visited.add(asm_id)
        parents = []
        for pid in assemblies.get(asm_id, {}).get("parent_assemblies", []):
            parents.append(pid)
            parents.extend(get_parents(pid, visited))
        return parents

    direct_asms = set()
    for asm_id, asm in assemblies.items():
        if any(pid in asm.get("parts", []) for pid in all_ids):
            direct_asms.add(asm_id)

    all_asms = set(direct_asms)
    for asm_id in list(direct_asms):
        all_asms.update(get_parents(asm_id))

    affected_assemblies = []
    for asm_id in all_asms:
        asm = assemblies.get(asm_id, {})
        constraints = []
        for k, v in asm.get("interface_constraints", {}).items():
            parts_in = k.split("_to_")
            if any(pid in parts_in for pid in all_ids):
                constraints.append({"constraint": k, "description": v})
        affected_assemblies.append({
            "assembly_id": asm_id, "assembly_name": asm.get("name"),
            "criticality": asm.get("criticality", "standard"),
            "impact_type": "direct" if asm_id in direct_asms else "cascade_parent",
            "bom_id": asm.get("bom_id"), "test_procedure_id": asm.get("test_procedure_id"),
            "interface_constraints_triggered": constraints
        })

    # Layer 3: Inspection
    changed_params = {c.get("parameter", "").lower() for c in changes}
    tokens = set()
    for p in changed_params:
        tokens.update(p.replace("_mm", "").replace("_", " ").split())
        tokens.add(p.replace("_mm", ""))

    insp_steps = []
    for pid in all_ids:
        part = parts.get(pid, {})
        plan_id = part.get("inspection_plan_id")
        if not plan_id or plan_id not in inspection: continue
        for step in inspection[plan_id]["steps"]:
            kws = [k.lower() for k in step.get("keywords", [])]
            if any(kw in kws for kw in changed_params) or any(tok in step["description"].lower() for tok in tokens):
                insp_steps.append({
                    "part_name": part["name"], "inspection_plan_id": plan_id,
                    "step_number": step["step"], "step_type": step.get("type"),
                    "step_description": step["description"], "tool": step.get("tool", "TBD"),
                    "action": "UPDATE nominal value, tolerance, and acceptance criteria"
                })

    # Layer 4: BOM
    bom_impact = []
    for asm in affected_assemblies:
        bid = asm.get("bom_id")
        if bid and bid in bom:
            b = bom[bid]
            bom_impact.append({"bom_id": bid, "assembly_id": b["assembly_id"],
                                "total_cost_usd": b["total_cost_usd"],
                                "action": "Update weight, cost, lead time"})

    # Layer 5: Documents
    docs = []
    seen = set()
    def add_doc(dtype, ref, action, priority="medium"):
        k = f"{dtype}:{ref}"
        if k not in seen:
            seen.add(k)
            docs.append({"document_type": dtype, "reference": ref, "action": action, "priority": priority})

    for c in changes:
        add_doc("3D CAD Model", c["part_id"], "Update parametric model and regenerate", "high")
        add_doc("Part Drawing", f"DWG-{c['part_id']}", "Update dimension callouts, advance revision", "high")
    for asm in affected_assemblies:
        if asm.get("bom_id"): add_doc("Bill of Materials", asm["bom_id"], "Update weight, cost, lead time", "high")
        if asm.get("test_procedure_id"): add_doc("Test Procedure", asm["test_procedure_id"], "Review and update test parameters", "medium")
    if parsed.get("affects_pressure_boundary"):
        add_doc("Engineering Document", "Pressure Vessel Datasheet", "Review and update", "high")
        add_doc("Engineering Document", "Hydrostatic Test Procedure", "Revise pressure parameters", "high")
    if parsed.get("material_change"):
        add_doc("Engineering Document", "Material Specification Sheet", "Update", "high")
        add_doc("Engineering Document", "Weld Procedure Specification", "Review", "high")
    add_doc("Engineering Document", "ECR - Engineering Change Request", "Issue formal ECR", "high")
    add_doc("Engineering Document", "ECO - Engineering Change Order", "Issue ECO upon approval", "medium")

    # Safety validation
    safety = []
    v = rules["validation"]
    for c in changes:
        if "wall_thickness" in c.get("parameter", ""):
            new_val = c.get("new_value", 0)
            pct = abs(c.get("delta_pct", 0))
            pid = c.get("part_id")
            part = parts.get(pid, {})
            if new_val < v["min_wall_thickness_mm"]:
                safety.append({"severity": "CRITICAL", "part_id": pid,
                                "message": f"New wall {new_val}mm below minimum {v['min_wall_thickness_mm']}mm",
                                "action": "STOP — Principal Engineer review required"})
            elif pct > v["max_wall_reduction_pct"]:
                safety.append({"severity": "WARNING", "part_id": pid,
                                "message": f"Wall reduction {pct:.1f}% exceeds {v['max_wall_reduction_pct']}% guideline",
                                "action": "Mandatory FEA pressure re-analysis required"})
            if part.get("category") == "pressure_retaining" and c.get("new_value"):
                S = v["ss316_allowable_mpa"]
                od = part["dimensions"].get("outer_diameter_mm", 150)
                sf = (2 * S * (new_val / 1000)) / (od / 1000) * 10 / part.get("design_pressure_bar", 150)
                if sf < v["min_safety_factor"]:
                    safety.append({"severity": "CRITICAL", "part_id": pid,
                                   "message": f"Barlow safety factor {sf:.2f} < {v['min_safety_factor']} minimum",
                                   "action": "Change rejected — wall too thin for design pressure"})

    s = {"total_parts_affected": len(affected_parts),
         "total_assemblies_affected": len(affected_assemblies),
         "total_inspection_steps_to_update": len(insp_steps),
         "total_documents_to_update": len(docs),
         "high_priority_documents": sum(1 for d in docs if d["priority"] == "high"),
         "safety_critical_assemblies": sum(1 for a in affected_assemblies if a["criticality"] == "safety_critical"),
         "has_safety_violations": any(w["severity"] == "CRITICAL" for w in safety),
         "has_warnings": len(safety) > 0}

    return {"affected_parts": affected_parts, "affected_assemblies": affected_assemblies,
            "affected_inspection_steps": insp_steps, "bom_impact": bom_impact,
            "document_impacts": docs, "safety_warnings": safety, "summary": s}
