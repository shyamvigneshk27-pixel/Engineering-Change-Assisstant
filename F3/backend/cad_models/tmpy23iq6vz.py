
import sys
import time
import FreeCAD
import Part

try:
    import FreeCADGui
    FreeCADGui.showMainWindow()
    from PySide import QtCore
    GUI_MODE = True
except:
    GUI_MODE = False

doc = FreeCAD.openDocument("D:/MyData/downloads/ECA-main/ECA-main/backend/cad_models/PART-001.FCStd")

if GUI_MODE:
    try:
        view = FreeCADGui.ActiveDocument.ActiveView
        view.viewIsometric()
        view.fitAll()
        view.setDrawStyle("As is")
        print("SHOWING BEFORE STATE...")
        for _ in range(8):
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.1)
    except:
        pass

print("Objects in model:")
for obj in doc.Objects:
    r_str = ""
    if hasattr(obj, "Radius"):
        r_str = f" Radius={float(obj.Radius)}"
    print(f"  {obj.Name} ({obj.Label}) {obj.TypeId}{r_str}")


outer = doc.getObject("OuterCylinder")
inner = doc.getObject("InnerCylinder")

if outer and inner:
    outer_r = float(outer.Radius)
    inner_r = float(inner.Radius)
    wall_before = outer_r - inner_r
    print(f"\nBEFORE: OD={outer_r*2}, ID={inner_r*2}, Wall={wall_before}")

    # Determine what to modify based on feature name
    feat = "WallThickness".lower()
    if "wall" in feat or "thickness" in feat:
        new_inner_r = outer_r - 10.0
        inner.Radius = FreeCAD.Units.Quantity(f"{new_inner_r} mm")
        print(f"MODIFIED: InnerRadius {inner_r} -> {new_inner_r} (wall=10.0mm)")
    elif "outer" in feat or "od" in feat:
        outer.Radius = FreeCAD.Units.Quantity(f"{10.0/2} mm")
        print(f"MODIFIED: OuterRadius {outer_r} -> {10.0/2}")
    elif "inner" in feat or "id" in feat or "bore" in feat:
        inner.Radius = FreeCAD.Units.Quantity(f"{10.0/2} mm")
        print(f"MODIFIED: InnerRadius {inner_r} -> {10.0/2}")
    else:
        new_inner_r = outer_r - 10.0
        inner.Radius = FreeCAD.Units.Quantity(f"{new_inner_r} mm")
        print(f"MODIFIED (fallback): InnerRadius -> {new_inner_r}")

    doc.recompute()

    wall_after = float(outer.Radius) - float(inner.Radius)
    print(f"AFTER: OD={float(outer.Radius)*2}, ID={float(inner.Radius)*2}, Wall={wall_after}")

    # Export STEP
    valve = doc.getObject("ValveBody")
    if valve and hasattr(valve, "Shape") and not valve.Shape.isNull():
        Part.export([valve], "D:/MyData/downloads/ECA-main/ECA-main/backend/cad_models/PART-001_updated.step")
        print("STEP_EXPORTED_OK")
    else:
        shapes = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
        if shapes:
            Part.export(shapes, "D:/MyData/downloads/ECA-main/ECA-main/backend/cad_models/PART-001_updated.step")
            print("STEP_EXPORTED_OK")

    doc.save()
    print("FREECAD_COMPLETE")
    
    if GUI_MODE:
        try:
            view.fitAll()
            print("SHOWING AFTER STATE...")
            for _ in range(10):
                QtCore.QCoreApplication.processEvents()
                time.sleep(0.1)
            FreeCADGui.getMainWindow().close()
            import os
            os._exit(0)
        except:
            pass

else:
    print("ERROR: Could not find OuterCylinder/InnerCylinder objects")
