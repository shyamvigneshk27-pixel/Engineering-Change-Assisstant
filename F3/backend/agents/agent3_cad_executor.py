"""
AGENT 3 — CAD EXECUTOR
Modifies real FreeCAD .FCStd model files via headless subprocess.
Exports updated STEP. Falls back to matplotlib render if FreeCAD unavailable.
"""
import subprocess, json, os, time, tempfile, base64, io, shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DB = Path(__file__).parent.parent / "database"
CAD_DIR = Path(__file__).parent.parent / "cad_models"
CAD_DIR.mkdir(exist_ok=True)

class Agent3CADExecutor:
    name = "CAD EXECUTOR"
    description = "Modifies FreeCAD model, exports STEP, renders before/after"

    def __init__(self):
        if os.name == "nt":  # Windows
            default_cmd = r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"
        else:  # Linux/Docker
            default_cmd = "FreeCADCmd"
            
        self.freecad_cmd = os.getenv("FREECAD_CMD", default_cmd)

    def run(self, parsed: dict, parts_db: dict) -> dict:
        start = time.time()
        changes = parsed.get("changes", [])
        if not changes:
            return {"modified_parts": [], "cad_method": "none", "render_base64": None,
                    "_agent": self.name, "_time_seconds": 0}

        results = []
        step_files = []
        freecad_available = os.path.isfile(self.freecad_cmd)
        cad_method = "freecad" if freecad_available else "simulation"

        # --- 🛡️ GEOMETRIC INTEGRITY GUARDRAIL ---
        for c in changes:
            pid = c.get("part_id", "PART-001")
            part = parts_db.get(pid, {})
            dims = part.get("dimensions", {})
            od = dims.get("outer_diameter_mm", 150)
            id_ = dims.get("inner_diameter_mm", 126)
            if "outer_diameter" in c["parameter"]: od = c["new_value"]
            if "inner_diameter" in c["parameter"]: id_ = c["new_value"]
            if id_ >= od:
                return {
                    "success": False, "overall_safe": False,
                    "error": f"CRITICAL GEOMETRY ERROR: Inner Diameter ({id_}mm) cannot be >= Outer Diameter ({od}mm).",
                    "modified_parts": [], "cad_method": "aborted_safety_fail",
                    "render_base64": None, "_agent": self.name, "_time_seconds": 0
                }

        for c in changes:
            pid = c.get("part_id", "PART-001")
            part = parts_db.get(pid, {})
            param = c.get("parameter", "")
            new_val = c.get("new_value")
            cur_val = c.get("current_value")
            feature_map = part.get("cad_feature_map", {})
            cad_feature = feature_map.get(param, c.get("cad_feature", param))

            model_file = CAD_DIR / f"{pid}.FCStd"
            step_file = CAD_DIR / f"{pid}_updated.step"

            cad_result = {"part_id": pid, "part_name": part.get("name", pid),
                          "parameter": param, "cad_feature": cad_feature,
                           "original_value": cur_val, "new_value": new_val,
                          "cad_method": cad_method}

            if freecad_available:
                # First ensure parametric model exists
                if not model_file.exists():
                    self._create_parametric_model(pid, part, model_file)

                # Run FreeCAD headless modification
                fc_result = self._run_freecad(model_file, cad_feature, new_val, step_file, pid)
                cad_result.update(fc_result)
                if step_file.exists():
                    step_files.append(str(step_file))
            else:
                # Simulation fallback for lightning-fast demo
                cad_result["status"] = "simulated"
                cad_result["message"] = f"Simulated: {cad_feature} = {cur_val} -> {new_val}"
                
                # Auto-copy the valve assembly to PART-001 so the "View Modified Model" button shows the assembly instead of a broken cylinder
                import shutil
                assembly_src = CAD_DIR / "valve_assembly.FCStd"
                if assembly_src.exists():
                    shutil.copy2(str(assembly_src), str(model_file))

            # --- 📦 VOLUMETRIC DELTA CALCULATION ---
            # Pipe volume V = pi * (R^2 - r^2) * h
            # For simplicity in 2D-centered demo, we assume a standard 100mm length segment
            h = 100.0
            import math
            # Calculate updated OD and ID based on the specific change
            od_u = new_val if "outer_diameter" in param else od
            id_u = new_val if "inner_diameter" in param else id_
            if "wall_thickness" in param:
                 id_u = od_u - (2 * new_val)

            vol_o = math.pi * ((od/2)**2 - (id_/2)**2) * h
            vol_u = math.pi * ((od_u/2)**2 - (id_u/2)**2) * h
            vol_delta = vol_o - vol_u # Positive means material was REMOVED

            cad_result.update({
                "vol_removed_mm3": round(vol_delta, 1),
                "mass_reduction_pct": round((vol_delta / vol_o) * 100, 1) if vol_o > 0 else 0
            })

            # Validation checks
            checks = self._validate(c, part)
            cad_result["validation"] = {
                "overall": "PASS" if all(ch["status"] == "PASS" for ch in checks) else "FAIL",
                "checks": checks
            }
            results.append(cad_result)

        # Generate side-by-side render
        render_b64 = self._generate_render(parsed, parts_db)

        return {
            "modified_parts": results,
            "step_files": step_files,
            "cad_method": cad_method,
            "render_base64": f"data:image/png;base64,{render_b64}" if render_b64 else None,
            "_agent": self.name,
            "_time_seconds": round(time.time() - start, 2)
        }

    def _create_parametric_model(self, pid, part, model_file):
        """Copy the pre-built valve assembly as the base model."""
        assembly_src = CAD_DIR / "valve_assembly.FCStd"
        if assembly_src.exists():
            shutil.copy2(str(assembly_src), str(model_file))
            print(f"  [CAD] Copied valve assembly -> {model_file}")
        else:
            # Fallback: build simple model if assembly doesn't exist
            dims = part.get("dimensions", {})
            od = dims.get("outer_diameter_mm", 150)
            wall = dims.get("wall_thickness_mm", 12)
            length = dims.get("length_mm", 300)
            script = f'''
import FreeCAD, Part, os
doc = FreeCAD.newDocument("{pid}")
outer = doc.addObject("Part::Cylinder", "OuterCylinder")
outer.Radius = FreeCAD.Units.Quantity("{od/2} mm")
outer.Height = FreeCAD.Units.Quantity("{length} mm")
inner = doc.addObject("Part::Cylinder", "InnerCylinder")
inner.Radius = FreeCAD.Units.Quantity("{(od/2) - wall} mm")
inner.Height = FreeCAD.Units.Quantity("{length + 2} mm")
inner.Placement.Base.z = -1
cut = doc.addObject("Part::Cut", "ValveBody")
cut.Base = outer; cut.Tool = inner
doc.recompute()
doc.saveCopy("{str(model_file).replace(chr(92), '/')}")
print("MODEL_CREATED_OK")
os._exit(0)
'''
            self._exec_freecad_script(script)

    def _run_freecad(self, model_file, feature_name, new_value, step_file, pid):
        """Run FreeCAD headlessly to modify valve assembly and export STEP."""
        model_path = str(model_file).replace("\\", "/")
        step_path = str(step_file).replace("\\", "/")

        script = f'''
import FreeCAD
import Part
import os

doc = FreeCAD.openDocument("{model_path}")

print("Objects in model:")
for obj in doc.Objects:
    r_str = ""
    if hasattr(obj, "Radius"):
        r_str = f" Radius={{float(obj.Radius)}}"
    print(f"  {{obj.Name}} ({{obj.Label}}) {{obj.TypeId}}{{r_str}}")

# Find valve body inner cylinder (bore)
vb_inner = doc.getObject("ValveBody_Inner")
vb_outer = doc.getObject("ValveBody_Outer")
pL_inner = doc.getObject("PipeLeft_Inner")
pR_inner = doc.getObject("PipeRight_Inner")
pL_outer = doc.getObject("PipeLeft_Outer")
pR_outer = doc.getObject("PipeRight_Outer")
bonnet   = doc.getObject("Bonnet")
disc     = doc.getObject("ButterflyDisc")
stem     = doc.getObject("ValveStem")
handle   = doc.getObject("Handle")

    # Also check for simple model fallback
if not vb_inner:
    vb_inner = doc.getObject("InnerDiameter") or doc.getObject("InnerCylinder")
    vb_outer = doc.getObject("OuterDiameter") or doc.getObject("OuterCylinder")

feat = "{feature_name}".lower()
try:
    val = float({new_value})
except:
    val = 0.0

# --- SECTION A: Universal Property Sync (Height/Length) ---
# This runs even if vb_inner/outer are not the main focus
if "height" in feat or "length" in feat:
    print(f"  MODE: Height/Length Adjustment -> {{val}}")
    targets = ["PipeRight", "PipeLeft", "ValveBody", "Bonnet", "Stem", "Cap", "Cylinder"]
    for obj in doc.Objects:
        if any(t.lower() in obj.Name.lower() or t.lower() in obj.Label.lower() for t in targets):
            for attr in ["Height", "Length"]:
                if hasattr(obj, attr):
                    try:
                        setattr(obj, attr, FreeCAD.Units.Quantity(f"{{val}} mm"))
                        print(f"    Synced {{obj.Name}}.{{attr}} -> {{val}}mm")
                    except: pass

# --- SECTION B: Radius/Diameter Logic ---
elif vb_outer and vb_inner:
    inner_r = float(vb_inner.Radius)
    outer_r = float(vb_outer.Radius)
    new_inner_r, new_outer_r = inner_r, outer_r

    if "wall" in feat or "thickness" in feat:
        new_outer_r = inner_r + val
        print(f"  MODE: Smart Wall Thickness -> {{val}}")
    elif "stem" in feat and stem:
        stem.Radius = FreeCAD.Units.Quantity(f"{{val / 2}} mm")
    elif "inner" in feat or "id" in feat or "bore" in feat:
        new_inner_r = val / 2
    elif "outer" in feat or "od" in feat:
        new_outer_r = val / 2
    else:
        if val > (outer_r * 0.8) and val < (outer_r * 1.5): new_outer_r = val / 2
        elif val < 50: new_inner_r = outer_r - val
        else: new_inner_r = val / 2

    if new_inner_r <= 0: new_inner_r = inner_r
    if new_outer_r <= new_inner_r: new_outer_r = new_inner_r + 5.0

    for o_name in ["ValveBody_Outer", "PipeLeft_Outer", "PipeRight_Outer", "OuterDiameter", "OuterCylinder"]:
        o = doc.getObject(o_name)
        if o and hasattr(o, "Radius"): o.Radius = FreeCAD.Units.Quantity(f"{{new_outer_r}} mm")
    for o_name in ["InnerDiameter", "ValveBody_Inner", "PipeLeft_Inner", "PipeRight_Inner", "InnerCylinder", "Bore"]:
        o = doc.getObject(o_name)
        if o and hasattr(o, "Radius"): o.Radius = FreeCAD.Units.Quantity(f"{{new_inner_r}} mm")
    if disc: disc.Radius = FreeCAD.Units.Quantity(f"{{max(5.0, new_inner_r - 1.5)}} mm")
    if stem:
        stem.Height = (new_outer_r * 2) + 60
        stem.Placement.Base.y = -(new_outer_r + 30)
    if handle:
        handle.Placement.Base.y = new_outer_r + 25

doc.recompute()

# Export
shapes = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()
          and o.TypeId not in ("Part::Cylinder", "Part::Box")]
if not shapes: shapes = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
if shapes:
    Part.export(shapes, "{step_path}")
    print("STEP_EXPORTED_OK")

doc.save()
print("FREECAD_COMPLETE")
os._exit(0)

print("FREECAD_COMPLETE")
os._exit(0)
'''
        stdout = self._exec_freecad_script(script)
        
        # FreeCAD swallows prints on some OS, so rely on file creation
        step_exported = os.path.exists(step_path)
        success = step_exported

        return {
            "status": "success" if success else "error",
            "cad_method": "freecad",
            "step_exported": step_exported,
            "step_file": step_path if step_exported else None,
            "freecad_log": stdout[-500:] if stdout else ""
        }

    def _exec_freecad_script(self, script_content):
        """Execute a FreeCAD script via subprocess."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=str(CAD_DIR)) as f:
            f.write(script_content)
            script_path = f.name

        try:
            result = subprocess.run(
                [self.freecad_cmd, script_path],
                capture_output=True, text=True, timeout=15,
                cwd=str(CAD_DIR)
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        except Exception as e:
            return f"ERROR: {str(e)}"
        finally:
            try: os.unlink(script_path)
            except: pass

    def _validate(self, change, part):
        """Engineering validation checks."""
        checks = []
        param = change.get("parameter", "")
        new_val = change.get("new_value")

        if new_val is None:
            return []

        if "wall_thickness" in param and new_val and part.get("category") == "pressure_retaining":
            od = part["dimensions"].get("outer_diameter_mm", 150)
            dp = part.get("design_pressure_bar", 150)
            S = 138  # SS316 allowable stress MPa
            pmax = (2 * S * (new_val / 1000)) / (od / 1000) * 10
            sf = pmax / dp
            checks.append({
                "check": "Barlow Pressure Analysis (P=2St/D)",
                "status": "PASS" if sf >= 2.5 else "FAIL",
                "detail": f"Pmax={pmax:.0f} bar, SF={sf:.2f} ({'>=' if sf >= 2.5 else '<'} 2.5 ASME VIII)"
            })
            checks.append({
                "check": "Minimum Wall Thickness (ASME VIII)",
                "status": "PASS" if new_val >= 6.0 else "FAIL",
                "detail": f"{new_val}mm {'>=' if new_val >= 6 else '<'} 6mm minimum"
            })

            # OD/ID consistency
            new_id = od - 2 * new_val
            checks.append({
                "check": "OD/ID Geometric Consistency",
                "status": "PASS" if new_id > 0 else "FAIL",
                "detail": f"OD={od}mm, new_wall={new_val}mm, new_ID={new_id:.1f}mm"
            })

        return checks

    def _generate_render(self, parsed, parts_db):
        """Generate high-fidelity side-by-side comparison with ghost overlay."""
        changes = parsed.get("changes", [])
        if not changes: return None

        pid = changes[0].get("part_id", "PART-001")
        part = parts_db.get(pid, {})
        orig = part.get("dimensions", {}).copy()
        updated = orig.copy()
        for c in changes:
            if c.get("part_id") == pid and c.get("parameter") and c.get("new_value") is not None:
                updated[c["parameter"]] = c["new_value"]

        fig, axes = plt.subplots(1, 2, figsize=(16, 8), facecolor="#0D1117")
        fig.suptitle(f"CAD IMPACT ANALYSIS — {part.get('name', pid)} ({pid})",
                     color="#58a6ff", fontsize=16, fontweight="bold", fontfamily="monospace", y=0.98)

        # Common scaling
        od_max = max(orig.get("outer_diameter_mm", 150), updated.get("outer_diameter_mm", 150))
        id_max = max(orig.get("inner_diameter_mm", 126), updated.get("inner_diameter_mm", 126))
        
        # Consistent scaling: Use the physical dimensions directly in the plot, 
        # and just set the limits based on the OD.
        limit = (od_max / 2) * 1.5  # 50% padding for labels
        scale = 1.0 # Remove arbitrary scaling factor to prevent "off-screen" circles

        # Baseline dimensions for comparison
        od_o = orig.get("outer_diameter_mm", 150)
        if "wall_thickness_mm" in orig:
             id_o = od_o - (2 * orig["wall_thickness_mm"])
        else:
             id_o = orig.get("inner_diameter_mm", 126)
        wall_o = (od_o - id_o) / 2

        for ax, dims, label, color in zip(axes,
                [orig, updated], ["BASELINE (Before)", "MODIFIED (After)"], ["#3a86ff", "#00f5d4"]):
            ax.set_facecolor("#161b22")
            ax.set_aspect("equal")
            ax.set_xlim(-limit, limit); ax.set_ylim(-limit, limit)
            ax.axis("off")

            # Calc dimensions (ID can be changed independently of wall)
            od_u = dims.get("outer_diameter_mm", 150)
            if "wall_thickness_mm" in dims:
                 id_u = od_u - (2 * dims["wall_thickness_mm"])
            else:
                 id_u = dims.get("inner_diameter_mm", 126)
            
            wall_u = (od_u - id_u) / 2

            # 👻 GHOST OVERLAY (Only on the Adjusted side)
            if label == "MODIFIED (After)":
                # Draw the original ID as a ghost line to show the gap
                ghost_ri = (id_o / 2) * scale
                ax.add_patch(plt.Circle((0, 0), ghost_ri, fill=False, color="#f85149", alpha=0.4, 
                                        linestyle="--", linewidth=1.5, label="Original Bore"))
                
                # Highlight the 2mm gap if thickness changed
                if wall_u != wall_o:
                    ri_u = (id_u / 2) * scale
                    ri_o = (id_o / 2) * scale
                    diff_rect = plt.Rectangle((min(ri_u, ri_o), -10), abs(ri_u - ri_o), 20, 
                                            color="#ffd60a", alpha=0.6, label="Delta Area")
                    ax.add_patch(diff_rect)

            # Main Outlines
            ro, ri = (od_u / 2) * scale, (id_u / 2) * scale
            ax.add_patch(plt.Circle((0, 0), ro, fill=True, facecolor=color, alpha=0.15, edgecolor=color, linewidth=3))
            ax.add_patch(plt.Circle((0, 0), ri, fill=True, facecolor="#0D1117", alpha=1.0, edgecolor="#8b949e", linewidth=1.5, linestyle="--"))

            # Labels and Callouts
            ax.set_title(label, color=color, fontsize=14, fontfamily="monospace", fontweight="bold", pad=20)
            
            # Wall thickness arrow
            ax.annotate("", xy=(ro, 40), xytext=(ri, 40), arrowprops=dict(arrowstyle="<->", color="#ffd60a", lw=2.5))
            ax.text((ro + ri) / 2, 55, f"t = {wall_u:.1f}mm", color="#ffd60a", ha="center", fontsize=12, fontweight="bold")

            # Diameter label
            ax.annotate("", xy=(-ro, -50), xytext=(ro, -50), arrowprops=dict(arrowstyle="<->", color=color, lw=1.5))
            ax.text(0, -75, f"OD = {od_u:.1f}mm", color=color, ha="center", fontsize=11)

            # Bore label
            ax.annotate("", xy=(-ri, -110), xytext=(ri, -110), arrowprops=dict(arrowstyle="<->", color="#8b949e", lw=1.5))
            ax.text(0, -135, f"ID = {id_u:.1f}mm", color="#8b949e", ha="center", fontsize=11)

            # Change indicator
            if label == "MODIFIED (After)" and wall_u != wall_o:
                delta = wall_u - wall_o
                ax.text(0, 180, f"DISPLACEMENT: {delta:+.1f}mm", color="#ffd60a", 
                        ha="center", fontsize=14, fontweight="bold", bbox=dict(facecolor="#161b22", alpha=0.8, edgecolor="#ffd60a"))

        plt.tight_layout(rect=[0, 0, 1, 0.94])
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=160, bbox_inches="tight", facecolor="#0D1117")
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
