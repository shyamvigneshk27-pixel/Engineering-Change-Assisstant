
import FreeCAD, os, sys
from pathlib import Path

# Paths
cad_dir = Path('backend/cad_models')
model_path = str(cad_dir / 'valve_assembly.FCStd').replace('\\', '/')

print("--- FREECAD INSPECTION START ---")
try:
    doc = FreeCAD.openDocument(model_path)
    print(f"Document Loaded: {doc.Name}")
    
    print("\nOBJECT LIST:")
    for obj in doc.Objects:
        print(f"  - {obj.Name} | {obj.Label} | {obj.TypeId}")
        # Log properties to see if Height/Length exists
        props = []
        if hasattr(obj, "Radius"): props.append(f"Radius={float(obj.Radius)}")
        if hasattr(obj, "Height"): props.append(f"Height={float(obj.Height)}")
        if hasattr(obj, "Length"): props.append(f"Length={float(obj.Length)}")
        if props: print(f"    PROPS: {', '.join(props)}")

    print("\nVERIFYING TARGETS:")
    targets = ["PipeRight", "PipeLeft", "ValveBody", "Bonnet", "Stem", "Cap", "Cylinder"]
    for t in targets:
        found = [o for o in doc.Objects if t.lower() in o.Name.lower() or t.lower() in o.Label.lower()]
        print(f"  Target '{t}': {'FOUND' if found else 'NOT FOUND'}")

except Exception as e:
    print(f"ERROR: {e}")

print("--- FREECAD INSPECTION END ---")
os._exit(0)
