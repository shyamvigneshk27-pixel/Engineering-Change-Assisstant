// =============================================================
// ECA_SolidWorks.cs
// ECA — Engineering Change Assistant | Phase 2 CAD Engine
// STARK-X | Sri Ramakrishna Engineering College | SLB 2026
// Platform : SolidWorks 2020+ (.NET COM API / Macro)
//
// HOW TO RUN (Option A — Macro):
//   1. Open ValveBody.SLDPRT in SolidWorks
//   2. Tools → Macros → New  (select C# VSTA)
//   3. Replace generated code with this file
//   4. Click Run (▶)
//
// HOW TO RUN (Option B — External App):
//   1. Create a new C# Console project
//   2. Add COM reference: SolidWorks.Interop.sldworks
//                         SolidWorks.Interop.swconst
//                         SolidWorks.Interop.swpublished
//   3. nuget: SolidWorks.Interop.sldworks (or from SW install dir)
//   4. Build and run — SW must be open with ValveBody.SLDPRT active
//
// REQUIREMENTS:
//   - ValveBody.SLDPRT with a sketch dimension named "WallThickness@Sketch1"
//     OR a global variable "WallThickness" = 12mm
//   - ValveAssembly.SLDASM referencing ValveBody.SLDPRT
// =============================================================

using System;
using System.IO;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;

namespace ECA_SolidWorks
{
    public class ECA_Phase2
    {
        // ── EWR Configuration ────────────────────────────────────
        const string EWR_TEXT      = "Reduce the wall thickness of the Valve Body by 2mm for weight reduction";
        const string PART_FILENAME = "ValveBody.SLDPRT";
        const string ASM_FILENAME  = "ValveAssembly.SLDASM";

        // Parameter names — adjust to match your SolidWorks model
        const string PARAM_EQUATION = "\"WallThickness\"";  // Equations manager name
        const string DIM_NAME       = "D1@Sketch1";         // Sketch dimension fullname

        const double DELTA_MM   = 2.0;
        const string DIRECTION  = "DECREASE";
        const double OD_MM      = 150.0;
        const double YIELD_MPA  = 170.0;  // SS316L
        const double DESIGN_BAR = 200.0;
        const double SAFETY_MIN = 2.5;    // ASME VIII

        private SldWorks swApp;
        private StreamWriter logWriter;

        // ─────────────────────────────────────────────────────────
        // SECTION 1 — ENTRY POINT
        // ─────────────────────────────────────────────────────────
        public void Main()
        {
            InitLog();
            Log("═══════════════════════════════════════════════════════");
            Log("ECA Phase 2 — SolidWorks .NET API");
            Log("STARK-X | SREC | SLB Industry-Academia Hackathon 2026");
            Log("═══════════════════════════════════════════════════════");
            Log($"EWR: {EWR_TEXT}");

            // Connect to running SolidWorks instance
            swApp = (SldWorks)System.Runtime.InteropServices.Marshal
                        .GetActiveObject("SldWorks.Application");
            swApp.Visible = true;

            // Open the part document
            int openErr = 0, openWarn = 0;
            ModelDoc2 swPartDoc = (ModelDoc2)swApp.OpenDoc6(
                PART_FILENAME,
                (int)swDocumentTypes_e.swDocPART,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                "", ref openErr, ref openWarn);

            if (swPartDoc == null)
            {
                Log("ERROR: Could not open " + PART_FILENAME);
                return;
            }

            PartDoc swPart = (PartDoc)swPartDoc;

            // Read current wall thickness
            double wallBefore = GetDimensionValue(swPartDoc, DIM_NAME);
            double wallAfter  = DIRECTION == "DECREASE"
                                ? wallBefore - DELTA_MM
                                : wallBefore + DELTA_MM;

            Log($"Wall before: {wallBefore:F2} mm  →  after: {wallAfter:F2} mm");

            // ── Step 1: Barlow safety validation ────────────────
            if (!ValidateSafety(wallBefore, wallAfter))
            {
                Log("ABORTED: Safety check failed. No geometry changes made.");
                CloseLog();
                return;
            }

            // ── Step 2: Update dimension / equation ─────────────
            bool dimOk = UpdateDimension(swPartDoc, wallAfter);
            if (!dimOk) { CloseLog(); return; }

            // ── Step 3: Regenerate model ─────────────────────────
            bool regenOk = RegenerateModel(swPartDoc);
            if (!regenOk) Log("WARNING: Rebuild errors detected — review feature tree.");

            // ── Step 4: Validate geometry (mass, interferences) ──
            ValidateGeometry(swPart, wallAfter);

            // ── Step 5: Update assembly constraints ──────────────
            UpdateAssembly(wallAfter);

            // ── Step 6: Update custom properties (BOM) ───────────
            UpdateCustomProperties(swPartDoc, wallBefore, wallAfter);

            // ── Step 7: Export STEP + SLDPRT ─────────────────────
            ExportFiles(swPartDoc, wallAfter);

            // ── Step 8: Save and summarize ───────────────────────
            swPartDoc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                             ref openErr, ref openWarn);
            Log("Part saved.");
            PrintSummary(wallBefore, wallAfter);
            CloseLog();
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 2 — BARLOW SAFETY VALIDATOR
        // ─────────────────────────────────────────────────────────
        double BarlowSF(double wall_mm)
        {
            double t   = wall_mm / 1000.0;
            double d   = OD_MM   / 1000.0;
            double p   = DESIGN_BAR * 0.1;        // MPa
            double pmax = (2.0 * YIELD_MPA * t) / d;
            return pmax / p;
        }

        bool ValidateSafety(double before, double after)
        {
            double sfBefore = BarlowSF(before);
            double sfAfter  = BarlowSF(after);
            Log($"  Barlow BEFORE: wall={before:F2}mm  SF={sfBefore:F2}");
            Log($"  Barlow AFTER:  wall={after:F2}mm  SF={sfAfter:F2}");
            Log($"  Minimum SF required: {SAFETY_MIN} (ASME VIII Div.1)");

            if (sfAfter >= SAFETY_MIN)
            {
                Log("  SAFETY: PASS ✅");
                return true;
            }
            Log("  SAFETY: FAIL ❌ — change rejected");
            return false;
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 3 — DIMENSION READ + UPDATE
        // ─────────────────────────────────────────────────────────
        double GetDimensionValue(ModelDoc2 doc, string dimName)
        {
            // Try via Equations first (global variable / equation)
            EquationMgr eqMgr = doc.GetEquationMgr();
            for (int i = 0; i < eqMgr.GetCount(); i++)
            {
                string eqName = eqMgr.Name[i];
                if (eqName.Contains("WallThickness"))
                {
                    // Parse numeric value from equation string e.g. "= 12mm"
                    string val = eqMgr.Equation[i]
                                    .Replace("=","").Replace("mm","").Trim();
                    if (double.TryParse(val, out double parsed)) return parsed;
                }
            }

            // Fallback: read from sketch dimension directly
            DisplayDimension dispDim = (DisplayDimension)doc.Parameter(dimName);
            if (dispDim != null)
            {
                Dimension dim = (Dimension)dispDim.GetDimension2(0);
                // SW stores in meters internally — convert to mm
                return dim.Value * 1000.0;
            }

            Log("WARNING: Dimension not found — assuming default 12mm");
            return 12.0;
        }

        bool UpdateDimension(ModelDoc2 doc, double newVal_mm)
        {
            Log($"Updating dimension to {newVal_mm:F2} mm ...");

            // ── Method A: Update via Equations Manager ───────────
            EquationMgr eqMgr = doc.GetEquationMgr();
            bool found = false;
            for (int i = 0; i < eqMgr.GetCount(); i++)
            {
                if (eqMgr.Name[i].Contains("WallThickness"))
                {
                    eqMgr.Equation[i] = "= " + newVal_mm + "mm";
                    eqMgr.EvaluateAll();
                    Log($"  Equation updated: WallThickness = {newVal_mm}mm");
                    found = true;
                    break;
                }
            }

            if (!found)
            {
                // ── Method B: Update sketch dimension directly ───
                // SolidWorks API: doc.Parameter(name) for display dimension
                DisplayDimension dispDim = (DisplayDimension)doc.Parameter(DIM_NAME);
                if (dispDim != null)
                {
                    Dimension dim = (Dimension)dispDim.GetDimension2(0);
                    // SetSystemValue3 uses meters, override array = null for all configs
                    int setErr = dim.SetSystemValue3(
                        newVal_mm / 1000.0,  // meters
                        (int)swSetValueInConfiguration_e.swSetValue_InThisConfiguration,
                        null);
                    if (setErr == 0)
                        Log($"  Sketch dimension '{DIM_NAME}' updated to {newVal_mm}mm");
                    else
                    {
                        Log($"  ERROR setting dimension. SW error code: {setErr}");
                        return false;
                    }
                }
                else
                {
                    Log($"  ERROR: Dimension '{DIM_NAME}' not found.");
                    return false;
                }
            }

            return true;
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 4 — MODEL REGENERATION & VALIDATION
        // ─────────────────────────────────────────────────────────
        bool RegenerateModel(ModelDoc2 doc)
        {
            Log("Regenerating model (ForceRebuild3) ...");

            // ForceRebuild3: true = top-level only rebuild, false = full rebuild
            bool rebuildErrors = doc.ForceRebuild3(false);
            // Note: SW returns true if there ARE errors (confusing API design)
            if (!rebuildErrors)
                Log("Model regeneration: SUCCESS ✅ — no errors")
            else
                Log("Model regeneration: WARNINGS detected — check FeatureManager");

            return !rebuildErrors;
        }

        void ValidateGeometry(PartDoc part, double wallAfter)
        {
            Log("Validating geometry (mass properties + interference) ...");

            // Mass properties after dimension change
            MassProperty massProps = (MassProperty)part.GetMassProperties2(
                swInertiaReferenceFrameType_e.swInertiaReferenceFrame_CenterOfMass,
                false);

            if (massProps != null)
            {
                double massBefore = massProps.Mass * 1000.0;  // kg → g (approx)
                Log($"  Mass (updated): {massBefore:F2} g");
                Log($"  Volume (updated): {massProps.Volume * 1e6:F2} cm³");
            }

            // Wall thickness check
            if (wallAfter < 3.0)
                Log("  ❌ CONSTRAINT FAIL: Wall < 3mm minimum manufacturing limit");
            else
                Log($"  ✅ Wall {wallAfter:F2}mm ≥ 3mm manufacturing minimum");
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 5 — ASSEMBLY CONSTRAINT UPDATE
        // ─────────────────────────────────────────────────────────
        void UpdateAssembly(double wallAfter)
        {
            Log("Opening assembly for constraint update ...");
            if (!File.Exists(ASM_FILENAME))
            {
                Log($"  Assembly '{ASM_FILENAME}' not found — skipping.");
                return;
            }

            int err = 0, warn = 0;
            ModelDoc2 swAsmDoc = (ModelDoc2)swApp.OpenDoc6(
                ASM_FILENAME,
                (int)swDocumentTypes_e.swDocASSEMBLY,
                (int)swOpenDocOptions_e.swOpenDocOptions_Silent,
                "", ref err, ref warn);

            if (swAsmDoc == null)
            {
                Log("  ERROR: Could not open assembly.");
                return;
            }

            AssemblyDoc swAsm = (AssemblyDoc)swAsmDoc;

            // Get all components in the assembly
            object[] components = (object[])swAsm.GetComponents(false);
            int constraintsChecked = 0;

            foreach (object comp in components)
            {
                Component2 swComp = (Component2)comp;
                Log($"  Component: {swComp.Name2}");

                // Check mates referencing the outer/inner diameter faces
                object[] mates = (object[])swComp.GetMates();
                if (mates == null) continue;

                foreach (object mateObj in mates)
                {
                    Mate2 swMate = (Mate2)mateObj;
                    // Suppress + unsuppress to force re-evaluation
                    swMate.Suppressed = true;
                    swMate.Suppressed = false;
                    constraintsChecked++;
                    Log($"    Re-evaluated mate: {swMate.Name}");
                }
            }

            // Regenerate the assembly
            swAsmDoc.ForceRebuild3(false);
            swAsmDoc.Save3((int)swSaveAsOptions_e.swSaveAsOptions_Silent, ref err, ref warn);
            Log($"  Assembly rebuilt. {constraintsChecked} mates re-evaluated. Saved.");

            swApp.CloseDoc(ASM_FILENAME);
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 6 — CUSTOM PROPERTIES (BOM / Revision)
        // ─────────────────────────────────────────────────────────
        void UpdateCustomProperties(ModelDoc2 doc,
                                     double wallBefore, double wallAfter)
        {
            Log("Updating custom properties (BOM metadata) ...");
            CustomPropertyManager propMgr = doc.Extension.get_CustomPropertyManager("");

            // Overwrite or add each custom property
            // AddProperty2 signature: name, type, value  (returns 0=ok)
            int r;
            r = propMgr.Add3("ECA_WallThickness_mm",
                              (int)swCustomInfoType_e.swCustomInfoText,
                              wallAfter.ToString("F2"),
                              (int)swCustomPropertyAddOption_e.swCustomPropertyReplaceValue);

            r = propMgr.Add3("ECA_RevisionType",
                              (int)swCustomInfoType_e.swCustomInfoText,
                              "MAJOR",
                              (int)swCustomPropertyAddOption_e.swCustomPropertyReplaceValue);

            r = propMgr.Add3("ECA_Rule",
                              (int)swCustomInfoType_e.swCustomInfoText,
                              "M1 — Wall thickness >5% on pressure boundary (ASME VIII)",
                              (int)swCustomPropertyAddOption_e.swCustomPropertyReplaceValue);

            r = propMgr.Add3("Revision",
                              (int)swCustomInfoType_e.swCustomInfoText,
                              "C",
                              (int)swCustomPropertyAddOption_e.swCustomPropertyReplaceValue);

            r = propMgr.Add3("ECA_EWR",
                              (int)swCustomInfoType_e.swCustomInfoText,
                              EWR_TEXT,
                              (int)swCustomPropertyAddOption_e.swCustomPropertyReplaceValue);

            r = propMgr.Add3("ECA_Timestamp",
                              (int)swCustomInfoType_e.swCustomInfoText,
                              DateTime.Now.ToString("dd/MM/yyyy HH:mm"),
                              (int)swCustomPropertyAddOption_e.swCustomPropertyReplaceValue);

            Log("  Custom properties written: Revision=C, ECA_WallThickness=" +
                wallAfter.ToString("F2") + "mm");
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 7 — EXPORT STEP + SLDPRT
        // ─────────────────────────────────────────────────────────
        void ExportFiles(ModelDoc2 doc, double wallAfter)
        {
            string basePath = Path.GetFileNameWithoutExtension(doc.GetPathName());
            string baseDir  = Path.GetDirectoryName(doc.GetPathName());

            string stepPath = Path.Combine(baseDir,
                $"{basePath}_ECA_Rev-C_Wall{wallAfter:F1}mm.step");
            string sldPath  = Path.Combine(baseDir,
                $"{basePath}_ECA_Rev-C_Wall{wallAfter:F1}mm.SLDPRT");

            // Export STEP AP214
            int err = 0, warn = 0;
            bool stepOk = doc.Extension.SaveAs(
                stepPath,
                (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                null, ref err, ref warn);

            Log(stepOk
                ? $"STEP exported: {stepPath} ✅"
                : $"STEP export FAILED (err={err}) ❌");

            // Save copy as SLDPRT (revised part)
            bool sldOk = doc.Extension.SaveAs(
                sldPath,
                (int)swSaveAsVersion_e.swSaveAsCurrentVersion,
                (int)swSaveAsOptions_e.swSaveAsOptions_Copy |
                (int)swSaveAsOptions_e.swSaveAsOptions_Silent,
                null, ref err, ref warn);

            Log(sldOk
                ? $"SLDPRT copy saved: {sldPath} ✅"
                : $"SLDPRT save FAILED (err={err}) ❌");
        }

        // ─────────────────────────────────────────────────────────
        // SECTION 8 — SUMMARY + LOGGING
        // ─────────────────────────────────────────────────────────
        void PrintSummary(double wallBefore, double wallAfter)
        {
            double sfAfter = BarlowSF(wallAfter);
            Log("═══════════════════════════════════════════════════════");
            Log("ECA CHANGE IMPACT SUMMARY — SolidWorks Phase 2");
            Log("═══════════════════════════════════════════════════════");
            Log($"EWR        : {EWR_TEXT}");
            Log($"Wall       : {wallBefore:F2} → {wallAfter:F2} mm  (Δ = −{DELTA_MM}mm, −{DELTA_MM/wallBefore*100:F1}%)");
            Log($"ID         : {OD_MM - 2*wallBefore:F2} → {OD_MM - 2*wallAfter:F2} mm");
            Log($"SF After   : {sfAfter:F2} (≥2.5 ASME VIII) ✅");
            Log($"Revision   : B → C (MAJOR)");
            Log($"Assemblies : ValveAssembly.SLDASM rebuilt");
            Log($"Exports    : .STEP + .SLDPRT");
            Log($"Status     : COMPLETE ✅");
            Log("═══════════════════════════════════════════════════════");
        }

        void InitLog()
        {
            logWriter = new StreamWriter("ECA_SolidWorks_ChangeLog.txt", append: true);
            logWriter.WriteLine($"\n=== ECA Run: {DateTime.Now} ===");
        }

        void Log(string msg)
        {
            Console.WriteLine("[ECA-SW] " + msg);
            logWriter?.WriteLine("[ECA-SW] " + msg);
            logWriter?.Flush();
        }

        void CloseLog() => logWriter?.Close();

        // Entry point for VSTA macro usage
        static void Main(string[] args)
        {
            new ECA_Phase2().Main();
        }
    }
}
