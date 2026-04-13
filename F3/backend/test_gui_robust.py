import FreeCAD
import FreeCADGui
import Part
import time

def run_live_demo():
    print("Initializing FreeCAD Live Viewer...")
    doc = FreeCAD.newDocument("ValveBody")
    
    outer = doc.addObject("Part::Cylinder", "OuterCylinder")
    outer.Radius = FreeCAD.Units.Quantity("75 mm")
    outer.Height = FreeCAD.Units.Quantity("300 mm")
    
    inner = doc.addObject("Part::Cylinder", "InnerCylinder")
    inner.Radius = FreeCAD.Units.Quantity("63 mm")  # Wall is 12mm
    inner.Height = FreeCAD.Units.Quantity("302 mm")
    inner.Placement.Base.z = -1
    
    cut = doc.addObject("Part::Cut", "ValveBody")
    cut.Base = outer
    cut.Tool = inner
    
    doc.recompute()
    
    view = FreeCADGui.ActiveDocument.ActiveView
    view.viewIsometric()
    view.fitAll()
    view.setDrawStyle("As is")
    
    print("SHOWING BEFORE STATE (12mm wall) for 5 seconds...")
    FreeCADGui.updateGui()
    time.sleep(5)
    
    print("UPDATING MODEL...")
    inner.Radius = FreeCAD.Units.Quantity("65 mm")  # Wall is 10mm
    doc.recompute()
    view.fitAll()
    
    print("SHOWING AFTER STATE (10mm wall) for 5 seconds...")
    FreeCADGui.updateGui()
    time.sleep(5)

# Delay execution slightly so the GUI can finish setting up
import threading
def delayed_start():
    time.sleep(1)
    try:
        run_live_demo()
    except Exception as e:
        print(f"Error: {e}")

threading.Thread(target=delayed_start).start()
