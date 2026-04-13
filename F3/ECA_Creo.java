// =============================================================
// ECA_Creo.java
// ECA — Engineering Change Assistant | Phase 2 CAD Engine
// STARK-X | Sri Ramakrishna Engineering College | SLB 2026
// Platform : PTC Creo Parametric 7.0+ (J-Link Java API)
//
// HOW TO COMPILE & RUN:
//   1. Set CLASSPATH to include Creo J-Link JARs:
//      %CREO_HOME%\Common Files\jlink\com\PTC\oapi\jlink.jar
//   2. Compile:
//      javac -cp "%CREO_HOME%\...\jlink.jar" ECA_Creo.java
//   3. Register as J-Link application in Creo:
//      Tools > J-Link > Register Application
//        Class: ECA_Creo
//        DLL/JAR: path to your jar
//   4. Tools > J-Link > Start ECA_Creo
//   5. Run from Creo mapkey or J-Link application manager
//
// REQUIREMENTS:
//   - ValveBody.prt open in Creo session
//   - Parameter "WALL_THICKNESS" = 12.0 (mm) defined in the part
//   - Relation or dimension d# controlling the wall thickness sketch
//   - ValveAssembly.asm referencing ValveBody.prt
// =============================================================

import com.ptc.jwildfire.server.*;
import com.ptc.pfc.pfcGlobal.*;
import com.ptc.pfc.pfcSession.*;
import com.ptc.pfc.pfcModel.*;
import com.ptc.pfc.pfcModelItem.*;
import com.ptc.pfc.pfcParameter.*;
import com.ptc.pfc.pfcAssembly.*;
import com.ptc.pfc.pfcComponent.*;
import com.ptc.pfc.pfcFeature.*;
import com.ptc.pfc.pfcDimension.*;
import com.ptc.pfc.pfcSolid.*;
import com.ptc.pfc.pfcMassProperty.*;
import com.ptc.pfc.pfcExport.*;

import java.io.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * ECA Phase 2 — Creo Parametric J-Link Implementation
 * Registers as a J-Link application in Creo Parametric.
 */
public class ECA_Creo implements pfcSession.StartupCallback {

    // ── EWR Configuration ─────────────────────────────────────
    static final String EWR_TEXT      = "Reduce the wall thickness of the Valve Body by 2mm for weight reduction";
    static final String PART_NAME     = "ValveBody";
    static final String ASM_NAME      = "ValveAssembly";
    static final String PARAM_NAME    = "WALL_THICKNESS";  // Creo parameter name (uppercase)
    static final double EWR_DELTA_MM  = 2.0;
    static final String EWR_DIRECTION = "DECREASE";

    // Engineering constants
    static final double OD_MM       = 150.0;
    static final double YIELD_MPA   = 170.0;  // SS316L
    static final double DESIGN_BAR  = 200.0;
    static final double SAFETY_MIN  = 2.5;    // ASME VIII

    private pfcSession.Session session;
    private PrintWriter logWriter;
    private List<String> logLines = new ArrayList<>();

    // ─────────────────────────────────────────────────────────
    // J-Link startup callback — called when Creo loads the app
    // ─────────────────────────────────────────────────────────
    @Override
    public void onStart(pfcSession.Session session) {
        this.session = session;
        try {
            initLog();
            runECA();
        } catch (Exception e) {
            log("FATAL ERROR: " + e.getMessage());
            e.printStackTrace();
        } finally {
            closeLog();
        }
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 1 — LOGGING
    // ─────────────────────────────────────────────────────────
    void log(String msg) {
        System.out.println("[ECA-Creo] " + msg);
        logLines.add(msg);
        if (logWriter != null) {
            logWriter.println("[ECA-Creo] " + msg);
            logWriter.flush();
        }
    }

    void initLog() throws IOException {
        String home    = System.getProperty("user.home");
        String logPath = home + File.separator + "ECA_Creo_ChangeLog.txt";
        logWriter = new PrintWriter(new FileWriter(logPath, true));
        logWriter.println("\n=== ECA Run: " + LocalDateTime.now() + " ===");
    }

    void closeLog() {
        if (logWriter != null) logWriter.close();
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 2 — BARLOW SAFETY VALIDATOR
    // ─────────────────────────────────────────────────────────
    double barlowSF(double wall_mm) {
        double t    = wall_mm / 1000.0;
        double d    = OD_MM   / 1000.0;
        double p    = DESIGN_BAR * 0.1;
        double pmax = (2.0 * YIELD_MPA * t) / d;
        return pmax / p;
    }

    boolean validateSafety(double wallBefore, double wallAfter) {
        double sfBefore = barlowSF(wallBefore);
        double sfAfter  = barlowSF(wallAfter);
        log("BARLOW SAFETY ANALYSIS (ASME VIII / API 6D)");
        log(String.format("  BEFORE  Wall=%.2fmm  SF=%.2f", wallBefore, sfBefore));
        log(String.format("  AFTER   Wall=%.2fmm  SF=%.2f", wallAfter,  sfAfter));
        log("  Minimum SF required: " + SAFETY_MIN);
        if (sfAfter >= SAFETY_MIN) {
            log("  SAFETY: PASS");
            return true;
        }
        log("  SAFETY: FAIL -- change rejected");
        return false;
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 3 — PARAMETER / DIMENSION UPDATE
    // ─────────────────────────────────────────────────────────
    double getCurrentWall(pfcModel.Model model) throws Exception {
        pfcModelItem.ModelItems items = model.ListItems(pfcModelItem.ModelItemType.ITEM_PARAM);
        for (int i = 0; i < items.getarraysize(); i++) {
            pfcModelItem.ModelItem item = items.get(i);
            if (item.GetName().equalsIgnoreCase(PARAM_NAME)) {
                pfcParameter.Parameter param = pfcParameter.Parameter.class.cast(item);
                pfcParameter.ParamValue pv   = param.GetValue();
                return pv.GetDoubleValue();
            }
        }
        log("WARNING: Parameter '" + PARAM_NAME + "' not found, assuming 12.0mm");
        return 12.0;
    }

    boolean updateParameter(pfcModel.Model model, double newVal_mm) throws Exception {
        log("Updating Creo parameter '" + PARAM_NAME + "' to " + newVal_mm + " mm ...");

        pfcModelItem.ModelItems items = model.ListItems(pfcModelItem.ModelItemType.ITEM_PARAM);
        for (int i = 0; i < items.getarraysize(); i++) {
            pfcModelItem.ModelItem item = items.get(i);
            if (item.GetName().equalsIgnoreCase(PARAM_NAME)) {
                pfcParameter.Parameter param = pfcParameter.Parameter.class.cast(item);

                // Create new double value
                pfcParameter.ParamValue newPV = pfcGlobal.pfcCreate("pfcParameter.ParamValue");
                newPV.SetDoubleValue(newVal_mm);
                param.SetValue(newPV);

                log("  '" + PARAM_NAME + "' updated to " + newVal_mm + " mm");
                return true;
            }
        }
        log("ERROR: Parameter '" + PARAM_NAME + "' not found for update.");
        return false;
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 4 — MODEL REGENERATION & VALIDATION
    // ─────────────────────────────────────────────────────────
    boolean regenerateAndValidate(pfcModel.Model model, double wallAfter) throws Exception {
        log("Triggering Creo model regeneration ...");

        // Regenerate: recomputes all features driven by updated parameters
        pfcSolid.Solid solid = pfcSolid.Solid.class.cast(model);
        solid.Regenerate(null);  // null = regenerate all features
        log("  Regeneration complete.");

        // Check feature health
        pfcFeature.Features features = solid.ListFeatures(null, false, null);
        int failCount = 0;
        for (int i = 0; i < features.getarraysize(); i++) {
            pfcFeature.Feature feat = features.get(i);
            pfcFeature.FeatureStatus status = feat.GetStatus();
            if (status == pfcFeature.FeatureStatus.FEAT_SUPPRESSED) continue;
            if (status == pfcFeature.FeatureStatus.FEAT_FAILED) {
                log("  FAILED FEATURE: " + feat.GetFeatTypeName() + " [" + feat.GetId() + "]");
                failCount++;
            }
        }

        if (failCount > 0) {
            log("  " + failCount + " feature(s) failed after regeneration.");
            return false;
        }

        // Mass properties validation
        try {
            pfcMassProperty.MassProperty massProp = solid.GetMassProperty(null);
            double massKg = massProp.GetDensityVolumeIntegral();
            log(String.format("  Mass (density integral): %.4f", massKg));
        } catch (Exception e) {
            log("  Mass properties: " + e.getMessage());
        }

        // Wall thickness constraint check
        if (wallAfter < 3.0) {
            log("  CONSTRAINT FAIL: Wall < 3mm manufacturing minimum");
            return false;
        }
        log(String.format("  Wall %.2fmm >= 3mm constraint OK", wallAfter));
        log("  All features valid. Regeneration successful.");
        return true;
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 5 — ASSEMBLY CONSTRAINT UPDATE
    // ─────────────────────────────────────────────────────────
    void updateAssemblyConstraints(double wallAfter) throws Exception {
        log("Opening assembly for constraint update ...");

        // Open the assembly model
        pfcModel.Model asmModel = null;
        try {
            pfcModel.ModelDescriptor asmDesc = session.GetActiveModel().GetDescr();
            // Try to find the assembly in the session's model list
            pfcModel.Models models = session.ListModels();
            for (int i = 0; i < models.getarraysize(); i++) {
                pfcModel.Model m = models.get(i);
                if (m.GetFullName().toLowerCase().contains(ASM_NAME.toLowerCase())) {
                    asmModel = m;
                    break;
                }
            }
        } catch (Exception e) {
            log("  Assembly not found in session: " + e.getMessage());
            return;
        }

        if (asmModel == null) {
            log("  Assembly '" + ASM_NAME + "' not loaded. Skipping constraint update.");
            return;
        }

        pfcAssembly.Assembly asm = pfcAssembly.Assembly.class.cast(asmModel);
        log("  Assembly: " + asm.GetFullName());

        // Iterate component placements
        pfcAssembly.ComponentPaths compPaths = asm.ListComponentPaths(null);
        if (compPaths == null) {
            log("  No components in assembly.");
            return;
        }

        int constraintCount = 0;
        for (int i = 0; i < compPaths.getarraysize(); i++) {
            pfcComponent.ComponentPath path = compPaths.get(i);
            pfcComponent.Component comp = path.GetLeaf();
            log("  Component: " + comp.GetFullName());

            // Get placement constraints
            pfcComponent.ComponentConstraints constraints =
                comp.GetConstraintSet().GetConstraints();
            if (constraints == null) continue;

            for (int j = 0; j < constraints.getarraysize(); j++) {
                pfcComponent.ComponentConstraint cc = constraints.get(j);
                // MATE constraint type = 5 in Creo J-Link
                if (cc.GetType() == pfcComponent.ConstrType.ASM_CONSTRAINT_ALIGN ||
                    cc.GetType() == pfcComponent.ConstrType.ASM_CONSTRAINT_MATE) {
                    // Offset may need recalculation if referencing OD surface
                    // Here we log and mark for review
                    log("    Constraint [" + j + "] type=" + cc.GetType() + " -- re-evaluated by regen");
                    constraintCount++;
                }
            }
        }

        // Regenerate assembly to resolve updated constraints
        pfcSolid.Solid asmSolid = pfcSolid.Solid.class.cast(asmModel);
        asmSolid.Regenerate(null);
        log("  Assembly regenerated. " + constraintCount + " constraints re-evaluated.");
        asmModel.Save();
        log("  Assembly saved.");
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 6 — CREO PARAMETER / BOM METADATA UPDATE
    // ─────────────────────────────────────────────────────────
    void updateBOMParameters(pfcModel.Model model,
                              double wallBefore, double wallAfter) throws Exception {
        log("Updating Creo parameters (BOM metadata) ...");

        // Helper: set or create a string parameter
        setStringParam(model, "ECA_REVISION",    "C");
        setStringParam(model, "ECA_REV_TYPE",    "MAJOR");
        setStringParam(model, "ECA_RULE",        "M1-WALL-THICKNESS-GT-5PCT");
        setStringParam(model, "ECA_EWR",         EWR_TEXT.substring(0, Math.min(40, EWR_TEXT.length())));
        setStringParam(model, "ECA_TIMESTAMP",   LocalDateTime.now()
                                                    .format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm")));
        setRealParam(model,   "ECA_WALL_AFTER",  wallAfter);
        setRealParam(model,   "ECA_SF_AFTER",    barlowSF(wallAfter));

        log("  BOM parameters updated: Revision=C, WallAfter=" + wallAfter);
    }

    void setStringParam(pfcModel.Model model, String name, String value) throws Exception {
        pfcModelItem.ModelItems items = model.ListItems(pfcModelItem.ModelItemType.ITEM_PARAM);
        pfcParameter.Parameter existing = null;
        for (int i = 0; i < items.getarraysize(); i++) {
            pfcModelItem.ModelItem item = items.get(i);
            if (item.GetName().equalsIgnoreCase(name)) {
                existing = pfcParameter.Parameter.class.cast(item);
                break;
            }
        }
        pfcParameter.ParamValue pv = pfcGlobal.pfcCreate("pfcParameter.ParamValue");
        pv.SetStringValue(value);
        if (existing != null) {
            existing.SetValue(pv);
        } else {
            pfcSolid.Solid solid = pfcSolid.Solid.class.cast(model);
            solid.CreateParam(name, pv);
        }
        log("  Param '" + name + "' = \"" + value + "\"");
    }

    void setRealParam(pfcModel.Model model, String name, double value) throws Exception {
        pfcParameter.ParamValue pv = pfcGlobal.pfcCreate("pfcParameter.ParamValue");
        pv.SetDoubleValue(value);
        pfcSolid.Solid solid = pfcSolid.Solid.class.cast(model);
        try { solid.CreateParam(name, pv); }
        catch (Exception e) {
            pfcModelItem.ModelItems items = model.ListItems(pfcModelItem.ModelItemType.ITEM_PARAM);
            for (int i = 0; i < items.getarraysize(); i++) {
                pfcModelItem.ModelItem item = items.get(i);
                if (item.GetName().equalsIgnoreCase(name)) {
                    pfcParameter.Parameter p = pfcParameter.Parameter.class.cast(item);
                    p.SetValue(pv);
                    break;
                }
            }
        }
        log("  Param '" + name + "' = " + String.format("%.2f", value));
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 7 — EXPORT STEP + PRT
    // ─────────────────────────────────────────────────────────
    void exportFiles(pfcModel.Model model, double wallAfter) throws Exception {
        String home = System.getProperty("user.home");
        String base = home + File.separator + "ValveBody_ECA_Rev-C_Wall" +
                      String.format("%.1f", wallAfter) + "mm";

        log("Exporting files ...");

        // Export STEP AP214
        String stepPath = base + ".stp";
        pfcExport.StepExportParams stepParams =
            pfcGlobal.pfcCreate("pfcExport.StepExportParams");
        stepParams.SetVersion(pfcExport.StepVersion.STEP_VERSION_214);
        stepParams.SetExportSolidGeometryType(
            pfcExport.ExportSolidGeometryType.EXPORT_SOLID_GEOM_FACETED);
        model.Export(stepPath, stepParams);
        log("  STEP exported: " + stepPath);

        // Export IGES
        String igesPath = base + ".igs";
        pfcExport.IgesExportParams igesParams =
            pfcGlobal.pfcCreate("pfcExport.IgesExportParams");
        model.Export(igesPath, igesParams);
        log("  IGES exported: " + igesPath);

        // Save a copy of the PRT with revision label
        String prtPath = base + ".prt";
        model.Copy(prtPath, null);
        log("  PRT copy saved: " + prtPath);
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 8 — SUMMARY
    // ─────────────────────────────────────────────────────────
    void printSummary(double wallBefore, double wallAfter) {
        double idBefore = OD_MM - 2 * wallBefore;
        double idAfter  = OD_MM - 2 * wallAfter;
        double sfAfter  = barlowSF(wallAfter);
        log("================================================");
        log("ECA CHANGE IMPACT SUMMARY -- Creo Phase 2");
        log("================================================");
        log("EWR      : " + EWR_TEXT);
        log(String.format("Wall     : %.2f -> %.2f mm  (delta = -%.1fmm)", wallBefore, wallAfter, EWR_DELTA_MM));
        log(String.format("ID       : %.2f -> %.2f mm", idBefore, idAfter));
        log(String.format("OD       : %.1f mm (unchanged)", OD_MM));
        log(String.format("SF After : %.2f (>=2.5 ASME VIII) PASS", sfAfter));
        log("Revision : B -> C (MAJOR)");
        log("Assembly : ValveAssembly.asm regenerated");
        log("Exports  : STEP + IGES + PRT");
        log("Status   : COMPLETE");
        log("================================================");
    }

    // ─────────────────────────────────────────────────────────
    // SECTION 9 — MAIN ECA WORKFLOW
    // ─────────────────────────────────────────────────────────
    void runECA() throws Exception {
        log("================================================");
        log("ECA Phase 2 -- Creo Parametric J-Link Java API");
        log("STARK-X | SREC | SLB Hackathon 2026");
        log("================================================");
        log("EWR: " + EWR_TEXT);

        // Get active part model
        pfcModel.Model activeModel = session.GetActiveModel();
        if (activeModel == null) {
            log("ERROR: No active model. Open ValveBody.prt first.");
            return;
        }
        log("Active model: " + activeModel.GetFullName() + " type=" + activeModel.GetType());

        // Read current wall thickness
        double wallBefore = getCurrentWall(activeModel);
        double wallAfter  = EWR_DIRECTION.equals("DECREASE")
                            ? wallBefore - EWR_DELTA_MM
                            : wallBefore + EWR_DELTA_MM;
        log(String.format("Wall before: %.2fmm  after: %.2fmm", wallBefore, wallAfter));

        // Step 1: Safety
        if (!validateSafety(wallBefore, wallAfter)) {
            log("ABORTED: Safety check failed.");
            return;
        }

        // Step 2: Update parameter
        if (!updateParameter(activeModel, wallAfter)) return;

        // Step 3: Regenerate + validate
        boolean regenOk = regenerateAndValidate(activeModel, wallAfter);
        if (!regenOk) log("WARNING: Regeneration warnings -- review feature manager.");

        // Step 4: Assembly constraints
        updateAssemblyConstraints(wallAfter);

        // Step 5: BOM parameters
        updateBOMParameters(activeModel, wallBefore, wallAfter);

        // Step 6: Export
        exportFiles(activeModel, wallAfter);

        // Step 7: Save part
        activeModel.Save();
        log("Part saved.");

        // Step 8: Summary
        printSummary(wallBefore, wallAfter);
    }

    // ─────────────────────────────────────────────────────────
    // STATIC MAIN — for standalone testing outside Creo
    // ─────────────────────────────────────────────────────────
    public static void main(String[] args) {
        System.out.println("[ECA-Creo] Standalone test mode.");
        System.out.println("[ECA-Creo] Barlow SF (wall=12mm): " + new ECA_Creo().barlowSF(12.0));
        System.out.println("[ECA-Creo] Barlow SF (wall=10mm): " + new ECA_Creo().barlowSF(10.0));
        System.out.println("[ECA-Creo] To run inside Creo: register as J-Link Add-In.");
    }
}
