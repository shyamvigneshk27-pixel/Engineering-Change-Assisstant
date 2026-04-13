"""
AGENT 2 — IMPACT TRACER
5-layer propagation engine: Parts → Assemblies → Inspection → BOM → Documents.
Traces interface constraint dependencies.
"""
import json, time
from pathlib import Path
DB = Path(__file__).parent.parent / "database"

class Agent2Tracer:
    name = "IMPACT TRACER"
    description = "Traces downstream impact across parts, assemblies, BOM, inspection, documents"

    def _load(self):
        def j(f): return json.load(open(DB / f))
        return j("parts.json"), j("assemblies.json"), j("bom.json"), j("inspection_plans.json"), j("revision_rules.json")

    def run(self, parsed: dict) -> dict:
        start = time.time()
        parts, assemblies, bom, inspection, rules = self._load()
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

        # Layer 2: Assemblies
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

        # Layer 4: BOM — EXACT Before/After
        bom_impact = []
        bom_before_after = []
        total_cost_before = 0
        total_cost_after = 0
        total_weight_before = 0
        total_weight_after = 0

        # Build weight change map
        weight_changes = {}
        cost_changes = {}
        for c in changes:
            pid = c.get("part_id")
            p = parts.get(pid, {})
            if "wall_thickness" in c.get("parameter", ""):
                old_w = p.get("weight_kg", 0)
                pct = c.get("delta_pct", 0)
                new_w = round(old_w * (1 + pct/100), 2)
                weight_changes[pid] = {"before": old_w, "after": new_w, "delta": round(new_w - old_w, 2)}
                # Cost drops proportionally with material volume
                for bid, b in bom.items():
                    for item in b.get("items", []):
                        if item["part_id"] == pid:
                            old_cost = item["unit_cost_usd"]
                            new_cost = round(old_cost * (1 + pct/100 * 0.7), 2)  # cost scales ~70% with volume
                            cost_changes[pid] = {"before": old_cost, "after": new_cost, "delta": round(new_cost - old_cost, 2)}

        # Build per-part BOM table
        for pid, p in parts.items():
            wc = weight_changes.get(pid, {"before": p.get("weight_kg",0), "after": p.get("weight_kg",0), "delta": 0})
            cc = cost_changes.get(pid, {"before": 0, "after": 0, "delta": 0})
            if cc["before"] == 0:
                for bid, b in bom.items():
                    for item in b.get("items", []):
                        if item["part_id"] == pid:
                            cc = {"before": item["unit_cost_usd"], "after": item["unit_cost_usd"], "delta": 0}
                            break
            bom_before_after.append({
                "part_id": pid, "part_name": p["name"],
                "weight_before": wc["before"], "weight_after": wc["after"], "weight_delta": wc["delta"],
                "cost_before": cc["before"], "cost_after": cc["after"], "cost_delta": cc["delta"],
                "changed": pid in weight_changes
            })
            total_weight_before += wc["before"]
            total_weight_after += wc["after"]
            total_cost_before += cc["before"]
            total_cost_after += cc["after"]

        for asm in affected_assemblies:
            bid = asm.get("bom_id")
            if bid and bid in bom:
                b = bom[bid]
                bom_impact.append({"bom_id": bid, "assembly_id": b["assembly_id"],
                                    "total_cost_usd": b["total_cost_usd"],
                                    "action": "Update weight, cost, lead time"})

        # Cost analysis with NET BENEFIT
        material_saving = round(total_cost_before - total_cost_after, 2)
        annual_units = 500
        annual_saving = round(material_saving * annual_units, 2)

        cost_analysis = {
            "material_cost_before": total_cost_before,
            "material_cost_after": total_cost_after,
            "material_saving_per_unit": material_saving,
            "annual_units": annual_units,
            "annual_material_saving": annual_saving,
            "weight_before": round(total_weight_before, 2),
            "weight_after": round(total_weight_after, 2),
            "weight_saving": round(total_weight_before - total_weight_after, 2)
        }

        # Inspection Before/After with exact values
        inspection_before_after = []
        for pid in all_ids:
            part = parts.get(pid, {})
            plan_id = part.get("inspection_plan_id")
            if not plan_id or plan_id not in inspection: continue
            for step in inspection[plan_id]["steps"]:
                kws = [k.lower() for k in step.get("keywords", [])]
                matched = any(kw in kws for kw in changed_params) or any(tok in step["description"].lower() for tok in tokens)
                old_nom = step.get("nominal_mm")
                old_tol = step.get("tolerance_mm", 0)
                new_nom = old_nom
                status = "NO CHANGE"

                if matched and old_nom:
                    for c in changes:
                        if c.get("part_id") == pid:
                            param = c.get("parameter", "").lower()
                            step_kws = [k.lower() for k in step.get("keywords", [])]
                            if any(kw in param for kw in step_kws):
                                # If it's a direct match for this dimensional parameter
                                new_nom = c.get("new_value", old_nom)
                                status = "UPDATE"
                                break
                            elif step.get("type") == "pressure" and "wall" in param:
                                status = "RE-CALCULATE"
                            elif "wall" in param and any(kw in "inner_diameter" for kw in step_kws):
                                # Wall thickness change implicitly impacts inner diameter
                                delta = c.get("delta", 0)
                                new_nom = old_nom - (2 * delta) if delta != 0 else old_nom
                                status = "UPDATE"
                                break

                inspection_before_after.append({
                    "part_name": part["name"], "step": step["step"],
                    "description": step["description"],
                    "tool": step.get("tool", ""),
                    "type": step.get("type", ""),
                    "nominal_before": round(old_nom, 2) if old_nom else None,
                    "tolerance": old_tol,
                    "nominal_after": round(new_nom, 2) if new_nom else (round(old_nom, 2) if old_nom else None),
                    "accept_before": f"{old_nom - old_tol:.2f}-{old_nom + old_tol:.2f}" if old_nom else "-",
                    "accept_after": f"{new_nom - old_tol:.2f}-{new_nom + old_tol:.2f}" if new_nom and status == "UPDATE" else ("-" if not old_nom else f"{old_nom - old_tol:.2f}-{old_nom + old_tol:.2f}"),
                    "status": status
                })

        # Barlow calculation details
        barlow_details = []
        v = rules["validation"]
        for c in changes:
            if "wall_thickness" in c.get("parameter", ""):
                pid = c.get("part_id")
                part = parts.get(pid, {})
                if part.get("category") == "pressure_retaining":
                    S = v["ss316_allowable_mpa"]
                    t_old = c.get("current_value", 12) / 1000
                    t_new = c.get("new_value", 10) / 1000
                    D = part["dimensions"].get("outer_diameter_mm", 150) / 1000
                    dp = part.get("design_pressure_bar", 150)
                    pmax_old = (2 * S * t_old) / D * 10
                    pmax_new = (2 * S * t_new) / D * 10
                    sf_old = pmax_old / dp
                    sf_new = pmax_new / dp
                    barlow_details.append({
                        "part_id": pid, "part_name": part["name"],
                        "S_mpa": S, "t_old_m": t_old, "t_new_m": t_new, "D_m": D,
                        "design_pressure_bar": dp,
                        "pmax_old_bar": round(pmax_old, 1), "pmax_new_bar": round(pmax_new, 1),
                        "sf_old": round(sf_old, 2), "sf_new": round(sf_new, 2),
                        "min_sf": v["min_safety_factor"],
                        "result": "PASS" if sf_new >= v["min_safety_factor"] else "FAIL"
                    })

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
        for c in changes:
            if "wall_thickness" in c.get("parameter", ""):
                new_val = c.get("new_value", 0)
                pct = abs(c.get("delta_pct", 0))
                pid = c.get("part_id")
                part = parts.get(pid, {})
                if new_val < v["min_wall_thickness_mm"]:
                    safety.append({"severity": "CRITICAL", "part_id": pid,
                                    "message": f"New wall {new_val}mm below minimum {v['min_wall_thickness_mm']}mm",
                                    "action": "STOP -- Principal Engineer review required"})
                elif pct > v["max_wall_reduction_pct"]:
                    safety.append({"severity": "WARNING", "part_id": pid,
                                    "message": f"Wall reduction {pct:.1f}% exceeds {v['max_wall_reduction_pct']}% guideline",
                                    "action": "Mandatory FEA pressure re-analysis required"})
                if part.get("category") == "pressure_retaining" and c.get("new_value"):
                    S_val = v["ss316_allowable_mpa"]
                    od = part["dimensions"].get("outer_diameter_mm", 150)
                    sf = (2 * S_val * (new_val / 1000)) / (od / 1000) * 10 / part.get("design_pressure_bar", 150)
                    if sf < v["min_safety_factor"]:
                        safety.append({"severity": "CRITICAL", "part_id": pid,
                                       "message": f"Barlow safety factor {sf:.2f} < {v['min_safety_factor']} minimum",
                                       "action": "Change rejected -- wall too thin for design pressure"})

        s = {"total_parts_affected": len(affected_parts),
             "total_assemblies_affected": len(affected_assemblies),
             "total_inspection_steps_to_update": len(insp_steps),
             "total_documents_to_update": len(docs),
             "high_priority_documents": sum(1 for d in docs if d["priority"] == "high"),
             "safety_critical_assemblies": sum(1 for a in affected_assemblies if a["criticality"] == "safety_critical"),
             "has_safety_violations": any(w["severity"] == "CRITICAL" for w in safety),
             "has_warnings": len(safety) > 0}

        result = {"affected_parts": affected_parts, "affected_assemblies": affected_assemblies,
                "affected_inspection_steps": insp_steps, "bom_impact": bom_impact,
                "bom_before_after": bom_before_after, "cost_analysis": cost_analysis,
                "inspection_before_after": inspection_before_after, "barlow_details": barlow_details,
                "document_impacts": docs, "safety_warnings": safety, "summary": s}
        result["_agent"] = self.name
        result["_time_seconds"] = round(time.time() - start, 2)
        return result
