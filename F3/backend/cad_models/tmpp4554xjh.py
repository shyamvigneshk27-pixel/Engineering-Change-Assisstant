
import FreeCAD
import Part
import os

doc = FreeCAD.openDocument("D:/MyData/downloads/ECA-main/ECA-main/backend/cad_models/PART-001.FCStd")

print("Objects in model:")
for obj in doc.Objects:
    r_str = ""
    if hasattr(obj, "Radius"):
        r_str = f" Radius={float(obj.Radius)}"
    print(f"  {obj.Name} ({obj.Label}) {obj.TypeId}{r_str}")

# Find valve body inner cylinder (bore)
vb_inner = doc.getObject("ValveBody_Inner")
vb_outer = doc.getObject("ValveBody_Outer")
pL_inner = doc.getObject("PipeLeft_Inner")
pR_inner = doc.getObject("PipeRight_Inner")
disc     = doc.getObject("ButterflyDisc")

# Also check for simple model fallback
if not vb_inner:
    vb_inner = doc.getObject("InnerCylinder")
    vb_outer = doc.getObject("OuterCylinder")

if vb_outer and vb_inner:
    outer_r = float(vb_outer.Radius)
    inner_r = float(vb_inner.Radius)
    wall_before = outer_r - inner_r
    print(f"\nBEFORE: OD={outer_r*2}, ID={inner_r*2}, Wall={wall_before}")

    feat = "WallThickness".lower()

    if "wall" in feat or "thickness" in feat:
        new_inner_r = outer_r - -188.0
        # Update ALL inner bores across the assembly
        for obj_name in ["ValveBody_Inner", "PipeLeft_Inner", "PipeRight_Inner",
                         "FlangeLeft_Inner", "FlangeRight_Inner", "InnerCylinder"]:
            obj = doc.getObject(obj_name)
            if obj and hasattr(obj, "Radius"):
                obj.Radius = FreeCAD.Units.Quantity(f"{new_inner_r} mm")
                print(f"  UPDATED {obj_name}: Radius -> {new_inner_r}")
        # Update butterfly disc to match new bore
        if disc:
            disc.Radius = FreeCAD.Units.Quantity(f"{new_inner_r - 1} mm")
            print(f"  UPDATED ButterflyDisc: Radius -> {new_inner_r - 1}")
        print(f"MODIFIED: wall=-188.0mm, new_bore_r={new_inner_r}")

    elif "outer" in feat or "od" in feat:
        new_outer_r = -188.0 / 2
        vb_outer.Radius = FreeCAD.Units.Quantity(f"{new_outer_r} mm")
        for obj_name in ["PipeLeft_Outer", "PipeRight_Outer"]:
            obj = doc.getObject(obj_name)
            if obj and hasattr(obj, "Radius"):
                obj.Radius = FreeCAD.Units.Quantity(f"{new_outer_r} mm")
        print(f"MODIFIED: OD -> -188.0mm")

    elif "inner" in feat or "id" in feat or "bore" in feat:
        new_inner_r = -188.0 / 2
        for obj_name in ["ValveBody_Inner", "PipeLeft_Inner", "PipeRight_Inner",
                         "FlangeLeft_Inner", "FlangeRight_Inner"]:
            obj = doc.getObject(obj_name)
            if obj and hasattr(obj, "Radius"):
                obj.Radius = FreeCAD.Units.Quantity(f"{new_inner_r} mm")
        if disc:
            disc.Radius = FreeCAD.Units.Quantity(f"{new_inner_r - 1} mm")
        print(f"MODIFIED: ID -> -188.0mm")
    else:
        # Fallback: treat as wall thickness
        new_inner_r = outer_r - -188.0
        vb_inner.Radius = FreeCAD.Units.Quantity(f"{new_inner_r} mm")
        print(f"MODIFIED (fallback): InnerRadius -> {new_inner_r}")

    doc.recompute()

    wall_after = float(vb_outer.Radius) - float(vb_inner.Radius)
    print(f"AFTER: OD={float(vb_outer.Radius)*2}, ID={float(vb_inner.Radius)*2}, Wall={wall_after}")

    # Export ALL visible shapes as complete assembly STEP
    shapes = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()
              and o.TypeId not in ("Part::Cylinder", "Part::Box")]
    if not shapes:
        shapes = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
    if shapes:
        Part.export(shapes, "D:/MyData/downloads/ECA-main/ECA-main/backend/cad_models/PART-001_updated.step")
        print("STEP_EXPORTED_OK")

    doc.save()
    print("FREECAD_COMPLETE")
else:
    print("ERROR: Could not find valve body objects")

os._exit(0)
