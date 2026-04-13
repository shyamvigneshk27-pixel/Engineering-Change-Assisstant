"""
PROOF: Real FreeCAD CAD File Modification (Fixed for FreeCAD 1.1 Quantity API)
"""
import subprocess, os, tempfile

FREECAD_CMD = r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe"
CAD_DIR = os.path.join(os.path.dirname(__file__), "cad_models")
os.makedirs(CAD_DIR, exist_ok=True)
model_path = os.path.join(CAD_DIR, "PART-001.FCStd").replace("\\", "/")
step_path = os.path.join(CAD_DIR, "PART-001_modified.step").replace("\\", "/")

# STEP 1: Create parametric model
create_script = f'''
import FreeCAD, Part

doc = FreeCAD.newDocument("ValveBody")

outer = doc.addObject("Part::Cylinder", "OuterCylinder")
outer.Radius = FreeCAD.Units.Quantity("75 mm")
outer.Height = FreeCAD.Units.Quantity("300 mm")
outer.Label = "OuterDiameter"

inner = doc.addObject("Part::Cylinder", "InnerCylinder")
inner.Radius = FreeCAD.Units.Quantity("63 mm")
inner.Height = FreeCAD.Units.Quantity("302 mm")
inner.Placement.Base.z = -1
inner.Label = "InnerDiameter"

cut = doc.addObject("Part::Cut", "ValveBody")
cut.Base = outer
cut.Tool = inner

doc.recompute()
doc.saveCopy("{model_path}")

print("=== MODEL CREATED ===")
print(f"  OD = {{float(outer.Radius)*2}} mm")
print(f"  ID = {{float(inner.Radius)*2}} mm")
print(f"  Wall = {{float(outer.Radius) - float(inner.Radius)}} mm")
print("CREATE_OK")
'''

# STEP 2: Modify wall thickness from 12mm to 10mm
modify_script = f'''
import FreeCAD, Part

doc = FreeCAD.openDocument("{model_path}")

outer = doc.getObject("OuterCylinder")
inner = doc.getObject("InnerCylinder")

print("\\n=== BEFORE ===")
print(f"  OD = {{float(outer.Radius)*2}} mm")
print(f"  ID = {{float(inner.Radius)*2}} mm")
print(f"  Wall = {{float(outer.Radius) - float(inner.Radius)}} mm")

# ACTUAL MODIFICATION: Reduce wall from 12mm to 10mm
# Wall = 10mm -> Inner Radius = Outer Radius - Wall = 75 - 10 = 65mm
inner.Radius = FreeCAD.Units.Quantity("65 mm")

doc.recompute()

print("\\n=== AFTER (wall reduced to 10mm) ===")
print(f"  OD = {{float(outer.Radius)*2}} mm")
print(f"  ID = {{float(inner.Radius)*2}} mm")
print(f"  Wall = {{float(outer.Radius) - float(inner.Radius)}} mm")

doc.save()

# Export real STEP file
valve = doc.getObject("ValveBody")
Part.export([valve], "{step_path}")
print(f"\\n=== STEP EXPORTED ===")
print(f"  {{valve.Shape.Volume / 1000:.1f}} cm3 volume")
print("MODIFY_OK")
'''

def run(label, script):
    print(f"\n{label}")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=CAD_DIR) as f:
        f.write(script); sp = f.name
    r = subprocess.run([FREECAD_CMD, sp], capture_output=True, text=True, timeout=30)
    print(r.stdout)
    if r.stderr and "Error" in r.stderr: print("STDERR:", r.stderr[:300])
    os.unlink(sp)

print("="*60)
print("  PROOF: FreeCAD Real CAD Modification")
print("="*60)

run("[1] Creating 3D valve body...", create_script)
run("[2] Modifying wall 12mm -> 10mm & exporting STEP...", modify_script)

print("\n[3] Verifying output files:")
for f in ["PART-001.FCStd", "PART-001_modified.step"]:
    fp = os.path.join(CAD_DIR, f)
    if os.path.exists(fp):
        print(f"  OK: {f} ({os.path.getsize(fp):,} bytes)")
    else:
        print(f"  MISSING: {f}")
print("="*60)
