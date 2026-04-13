
import FreeCAD, os
from pathlib import Path

cad_dir = Path('backend/cad_models')
model_path = str(cad_dir / 'valve_assembly.FCStd').replace('\\', '/')
output_path = 'backend/scratch/cad_info.txt'

with open(output_path, 'w') as f:
    f.write("--- CAD INFO ---\n")
    try:
        doc = FreeCAD.openDocument(model_path)
        f.write(f"Document: {doc.Name}\n")
        f.write("Objects:\n")
        for obj in doc.Objects:
            f.write(f"  - {obj.Name} | {obj.Label} | {obj.TypeId}\n")
            props = []
            if hasattr(obj, "Radius"): props.append(f"Radius={float(obj.Radius)}")
            if hasattr(obj, "Height"): props.append(f"Height={float(obj.Height)}")
            if hasattr(obj, "Length"): props.append(f"Length={float(obj.Length)}")
            if props: f.write(f"    PROPS: {', '.join(props)}\n")
    except Exception as e:
        f.write(f"ERROR: {str(e)}\n")

os._exit(0)
