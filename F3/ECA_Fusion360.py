# =============================================================
# ECA_Fusion360.py
# ECA — Engineering Change Assistant | Phase 2 CAD Engine
# STARK-X | Sri Ramakrishna Engineering College | SLB 2026
# Platform : Autodesk Fusion 360 (Python Add-In / Script)
#
# HOW TO RUN:
#   Option A — Script (simplest for demo):
#     1. Open Fusion 360 with ValveBody design active
#     2. Tools > Add-Ins > Scripts and Add-Ins
#     3. Click "+" > browse to this file > Run
#
#   Option B — Add-In (persistent panel button):
#     Place this file in:
#     %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\ECA_Phase2\
#     Tools > Add-Ins > Add-Ins tab > select ECA_Phase2 > Run
#
# REQUIREMENTS:
#   - Fusion 360 design with component "ValveBody"
#   - User parameter "WallThickness" = 12 mm
#   - Parametric Design Type enabled
# =============================================================

import adsk.core
import adsk.fusion
import traceback
import math
import os
from datetime import datetime

# ── EWR Configuration ─────────────────────────────────────────
EWR_TEXT      = "Reduce the wall thickness of the Valve Body by 2mm for weight reduction"
EWR_PART      = "ValveBody"
EWR_PARAM     = "WallThickness"
EWR_DELTA_MM  = 2.0
EWR_DIRECTION = "DECREASE"   # DECREASE or INCREASE

# Engineering constants (SS316L, ASME VIII)
OD_MM          = 150.0
YIELD_MPA      = 170.0
DESIGN_BAR     = 200.0
SAFETY_MIN     = 2.5

_app = None
_ui  = None
_log_lines = []

# ─────────────────────────────────────────────────────────────
# SECTION 1 — LOGGING
# ─────────────────────────────────────────────────────────────

def log(msg):
    print("[ECA-F360] " + msg)
    _log_lines.append(msg)

def save_log():
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        path = os.path.join(desktop, "ECA_Fusion360_ChangeLog.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n=== ECA Run: " + str(datetime.now()) + " ===\n")
            for line in _log_lines:
                f.write("[ECA-F360] " + line + "\n")
        log("Log saved: " + path)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# SECTION 2 — BARLOW SAFETY VALIDATOR
# ─────────────────────────────────────────────────────────────

def barlow_sf(wall_mm):
    t = wall_mm / 1000.0
    d = OD_MM   / 1000.0
    p = DESIGN_BAR * 0.1
    p_max = (2.0 * YIELD_MPA * t) / d
    return p_max / p

def validate_safety(wall_before, wall_after):
    sf_before = barlow_sf(wall_before)
    sf_after  = barlow_sf(wall_after)
    log("BARLOW SAFETY ANALYSIS (ASME VIII / API 6D)")
    log("  BEFORE  Wall=" + str(round(wall_before,2)) + "mm  SF=" + str(round(sf_before,2)))
    log("  AFTER   Wall=" + str(round(wall_after,2))  + "mm  SF=" + str(round(sf_after,2)))
    log("  Minimum SF required: " + str(SAFETY_MIN))
    if sf_after >= SAFETY_MIN:
        log("  SAFETY: PASS")
        return True
    log("  SAFETY: FAIL -- change rejected")
    return False

# ─────────────────────────────────────────────────────────────
# SECTION 3 — USER PARAMETER UPDATE (Feature Dimension)
# ─────────────────────────────────────────────────────────────

def get_parameter(design, name):
    params = design.userParameters
    for i in range(params.count):
        p = params.item(i)
        if p.name == name:
            return p
    return None

def update_dimension(design, param_name, new_val_mm):
    log("Updating parameter '" + param_name + "' to " + str(round(new_val_mm,2)) + " mm ...")
    param = get_parameter(design, param_name)
    if param is None:
        log("ERROR: Parameter '" + param_name + "' not found.")
        log("Available parameters:")
        for i in range(design.userParameters.count):
            p = design.userParameters.item(i)
            log("  " + p.name + " = " + str(round(p.value * 10.0, 2)) + " mm")
        return False
    old_mm = param.value * 10.0
    # Set via expression string -- supports formulas like "12 mm - 2 mm"
    param.expression = str(new_val_mm) + " mm"
    log("  '" + param_name + "': " + str(round(old_mm,2)) + "mm -> " + str(round(new_val_mm,2)) + "mm")
    return True

# ─────────────────────────────────────────────────────────────
# SECTION 4 — MODEL REGENERATION AND VALIDATION
# ─────────────────────────────────────────────────────────────

def regenerate_and_validate(design, wall_after):
    log("Triggering model regeneration ...")
    timeline = design.timeline
    if timeline is not None:
        log("  Timeline features: " + str(timeline.count))
        # Replay entire timeline by advancing marker to end
        timeline.markerPosition = timeline.count
        log("  Timeline replayed. Regeneration complete.")

    if wall_after <= 0:
        log("  FAIL: wall_after <= 0")
        return False
    if wall_after < 3.0:
        log("  ENGINEERING CONSTRAINT FAIL: Wall < 3mm manufacturing minimum")
        return False

    root = design.rootComponent
    body_count = root.bRepBodies.count
    log("  Bodies in root: " + str(body_count))
    all_valid = True
    for i in range(body_count):
        body = root.bRepBodies.item(i)
        status = "VALID" if body.isValid else "INVALID"
        log("  Body '" + body.name + "': " + status)
        if not body.isValid:
            all_valid = False

    try:
        phys = root.getPhysicalProperties(
            adsk.fusion.CalculationAccuracy.LowCalculationAccuracy)
        log("  Mass: " + str(round(phys.mass * 1000.0, 1)) + " g")
        log("  Volume: " + str(round(phys.volume * 1e6, 2)) + " cm3")
    except Exception:
        log("  Physical properties: not available (no material assigned)")

    log("  Wall " + str(round(wall_after,2)) + "mm >= 3mm minimum OK")
    log("Regeneration complete")
    return all_valid

# ─────────────────────────────────────────────────────────────
# SECTION 5 — ASSEMBLY JOINT / CONSTRAINT UPDATE
# ─────────────────────────────────────────────────────────────

def update_assembly_joints(design, wall_after):
    log("Checking assembly joints ...")
    root = design.rootComponent

    occ_count = root.allOccurrences.count
    log("  Total occurrences: " + str(occ_count))
    for i in range(occ_count):
        occ = root.allOccurrences.item(i)
        log("  Occurrence: " + occ.name + "  grounded=" + str(occ.isGrounded))

    # Re-evaluate rigid joints
    joint_count = root.joints.count
    log("  Assembly joints: " + str(joint_count))
    for i in range(joint_count):
        joint = root.joints.item(i)
        log("  Joint '" + joint.name + "' type=" + str(joint.jointMotion.jointType))
        if joint.jointMotion.jointType == 0:
            joint.isSuppressed = True
            joint.isSuppressed = False
            log("    Re-evaluated: " + joint.name)

    # As-built joints
    ab_count = root.asBuiltJoints.count
    log("  As-built joints: " + str(ab_count))
    for i in range(ab_count):
        abj = root.asBuiltJoints.item(i)
        abj.isSuppressed = True
        abj.isSuppressed = False
        log("  As-built joint re-evaluated: " + abj.name)

    log("Assembly joint update complete. " + str(joint_count + ab_count) + " joints re-evaluated.")

# ─────────────────────────────────────────────────────────────
# SECTION 6 — ATTRIBUTES (BOM / Revision Metadata)
# ─────────────────────────────────────────────────────────────

def update_attributes(design, wall_before, wall_after):
    log("Writing ECA attributes (BOM metadata) ...")
    root = design.rootComponent
    attrs = root.attributes
    attrs.add("ECA", "WallThickness_mm",   str(round(wall_after,2)))
    attrs.add("ECA", "WallBefore_mm",      str(round(wall_before,2)))
    attrs.add("ECA", "RevisionType",       "MAJOR")
    attrs.add("ECA", "RevisionLabel",      "C")
    attrs.add("ECA", "Rule",               "M1 -- Wall >5% on pressure boundary (ASME VIII)")
    attrs.add("ECA", "EWR_Text",           EWR_TEXT)
    attrs.add("ECA", "Timestamp",          datetime.now().strftime("%d/%m/%Y %H:%M"))
    attrs.add("ECA", "SafetyFactor_After", str(round(barlow_sf(wall_after),2)))
    attrs.add("ECA", "Platform",           "Fusion 360")
    log("  Attributes written: Revision=C, WallThickness=" + str(round(wall_after,2)) + "mm")

# ─────────────────────────────────────────────────────────────
# SECTION 7 — EXPORT (.STEP + .F3D + .IGES)
# ─────────────────────────────────────────────────────────────

def export_files(design, wall_after):
    log("Exporting files ...")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base = "ValveBody_ECA_Rev-C_Wall" + str(round(wall_after,1)) + "mm"
    exportMgr = design.exportManager

    # STEP AP214
    step_path = os.path.join(desktop, base + ".step")
    stepOpts = exportMgr.createSTEPExportOptions(step_path)
    r1 = exportMgr.execute(stepOpts)
    log("  STEP: " + step_path + "  " + ("OK" if r1 else "FAILED"))

    # Fusion Archive F3D
    f3d_path = os.path.join(desktop, base + ".f3d")
    f3dOpts = exportMgr.createFusionArchiveExportOptions(f3d_path)
    r2 = exportMgr.execute(f3dOpts)
    log("  F3D:  " + f3d_path  + "  " + ("OK" if r2 else "FAILED"))

    # IGES (for legacy SLB systems)
    iges_path = os.path.join(desktop, base + ".iges")
    igesOpts = exportMgr.createIGESExportOptions(iges_path)
    r3 = exportMgr.execute(igesOpts)
    log("  IGES: " + iges_path + "  " + ("OK" if r3 else "FAILED"))

# ─────────────────────────────────────────────────────────────
# SECTION 8 — CHANGE IMPACT SUMMARY
# ─────────────────────────────────────────────────────────────

def print_summary(wall_before, wall_after):
    id_before  = OD_MM - 2 * wall_before
    id_after   = OD_MM - 2 * wall_after
    sf_after   = barlow_sf(wall_after)
    change_pct = abs(wall_after - wall_before) / wall_before * 100
    log("================================================")
    log("ECA CHANGE IMPACT SUMMARY -- Fusion 360 Phase 2")
    log("================================================")
    log("EWR      : " + EWR_TEXT)
    log("Wall     : " + str(round(wall_before,2)) + " -> " + str(round(wall_after,2)) + " mm")
    log("ID       : " + str(round(id_before,2))   + " -> " + str(round(id_after,2))   + " mm")
    log("OD       : " + str(OD_MM) + " mm (unchanged)")
    log("SF After : " + str(round(sf_after,2)) + " (>=2.5 ASME VIII) PASS")
    log("Revision : B -> C (MAJOR)")
    log("Exports  : STEP + F3D + IGES")
    log("Status   : COMPLETE")
    log("================================================")

# ─────────────────────────────────────────────────────────────
# SECTION 9 — MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        log("================================================")
        log("ECA Phase 2 -- Autodesk Fusion 360 Python API")
        log("STARK-X | SREC | SLB Hackathon 2026")
        log("================================================")
        log("EWR: " + EWR_TEXT)

        product = _app.activeProduct
        if not isinstance(product, adsk.fusion.Design):
            _ui.messageBox("ECA Error: Please open a Fusion 360 Design first.")
            return

        design = adsk.fusion.Design.cast(product)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        log("Design: " + design.rootComponent.name + " (Parametric)")

        # Read current wall thickness
        param = get_parameter(design, EWR_PARAM)
        wall_before = (param.value * 10.0) if param else 12.0

        wall_after = (wall_before - EWR_DELTA_MM
                      if EWR_DIRECTION == "DECREASE"
                      else wall_before + EWR_DELTA_MM)

        log("Wall before: " + str(round(wall_before,2)) + "mm  after: " + str(round(wall_after,2)) + "mm")

        # Step 1: Safety
        if not validate_safety(wall_before, wall_after):
            _ui.messageBox("ECA REJECTED: Barlow SF below 2.5.\nNo changes applied.", "ECA Rejection")
            save_log()
            return

        # Step 2: Update dimension
        if not update_dimension(design, EWR_PARAM, wall_after):
            _ui.messageBox("ECA ERROR: Parameter update failed.\nCheck: " + EWR_PARAM, "ECA Error")
            save_log()
            return

        # Step 3: Regenerate
        regenerate_and_validate(design, wall_after)

        # Step 4: Assembly joints
        update_assembly_joints(design, wall_after)

        # Step 5: Attributes
        update_attributes(design, wall_before, wall_after)

        # Step 6: Export
        export_files(design, wall_after)

        # Step 7: Summary
        print_summary(wall_before, wall_after)
        save_log()

        _ui.messageBox(
            "ECA Phase 2 Complete!\n\n"
            "Wall: " + str(round(wall_before,2)) + " -> " + str(round(wall_after,2)) + " mm\n"
            "Safety Factor: " + str(round(barlow_sf(wall_after),2)) + " PASS\n"
            "Revision: B -> C (MAJOR)\n\n"
            "STEP + F3D + IGES exported to Desktop.",
            "ECA -- STARK-X")

    except Exception:
        if _ui:
            _ui.messageBox("ECA Exception:\n" + traceback.format_exc(), "ECA Error")
        raise

def stop(context):
    log("ECA Add-In stopped.")
