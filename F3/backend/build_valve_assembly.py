"""
Build a realistic butterfly valve assembly in FreeCAD.
Components: Pipe sections, valve body, flanges, butterfly disc, stem, bolts.
All parametric so Agent 3 can modify dimensions.
"""
import FreeCAD
import Part
import math
import os

doc = FreeCAD.newDocument("ValveAssembly")

# ============================================================
# PARAMETERS (all in mm) — Agent 3 modifies these objects
# ============================================================
PIPE_OD       = 150.0    # Outer diameter
PIPE_WALL     = 12.0     # Wall thickness
PIPE_ID       = PIPE_OD - 2 * PIPE_WALL
PIPE_LEN      = 200.0    # Length of each pipe section

VALVE_OD      = 190.0    # Valve body outer diameter
VALVE_LEN     = 80.0     # Valve body length

FLANGE_OD     = 230.0    # Flange outer diameter
FLANGE_THK    = 22.0     # Flange thickness
BOLT_R        = 95.0     # Bolt circle radius
BOLT_D        = 16.0     # Bolt diameter
BOLT_LEN      = 50.0     # Bolt length
NUM_BOLTS     = 8

DISC_THICK    = 6.0      # Butterfly disc thickness
STEM_D        = 22.0     # Stem diameter

# ============================================================
# LEFT PIPE SECTION
# ============================================================
pL_out = doc.addObject("Part::Cylinder", "PipeLeft_Outer")
pL_out.Radius = PIPE_OD / 2
pL_out.Height = PIPE_LEN
pL_out.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -PIPE_LEN - VALVE_LEN/2), FreeCAD.Rotation())

pL_in = doc.addObject("Part::Cylinder", "PipeLeft_Inner")
pL_in.Radius = PIPE_ID / 2
pL_in.Height = PIPE_LEN + 2
pL_in.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -PIPE_LEN - VALVE_LEN/2 - 1), FreeCAD.Rotation())

pL = doc.addObject("Part::Cut", "PipeLeft")
pL.Base = pL_out
pL.Tool = pL_in

# ============================================================
# RIGHT PIPE SECTION
# ============================================================
pR_out = doc.addObject("Part::Cylinder", "PipeRight_Outer")
pR_out.Radius = PIPE_OD / 2
pR_out.Height = PIPE_LEN
pR_out.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, VALVE_LEN/2), FreeCAD.Rotation())

pR_in = doc.addObject("Part::Cylinder", "PipeRight_Inner")
pR_in.Radius = PIPE_ID / 2
pR_in.Height = PIPE_LEN + 2
pR_in.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, VALVE_LEN/2 - 1), FreeCAD.Rotation())

pR = doc.addObject("Part::Cut", "PipeRight")
pR.Base = pR_out
pR.Tool = pR_in

# ============================================================
# VALVE BODY (wider section in the middle)
# ============================================================
vb_out = doc.addObject("Part::Cylinder", "ValveBody_Outer")
vb_out.Radius = VALVE_OD / 2
vb_out.Height = VALVE_LEN
vb_out.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -VALVE_LEN/2), FreeCAD.Rotation())
vb_out.Label = "OuterDiameter"

vb_in = doc.addObject("Part::Cylinder", "ValveBody_Inner")
vb_in.Radius = PIPE_ID / 2
vb_in.Height = VALVE_LEN + 2
vb_in.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -VALVE_LEN/2 - 1), FreeCAD.Rotation())
vb_in.Label = "InnerDiameter"

vb = doc.addObject("Part::Cut", "ValveBody")
vb.Base = vb_out
vb.Tool = vb_in

# ============================================================
# LEFT FLANGE
# ============================================================
fl1_out = doc.addObject("Part::Cylinder", "FlangeLeft_Outer")
fl1_out.Radius = FLANGE_OD / 2
fl1_out.Height = FLANGE_THK
fl1_out.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -VALVE_LEN/2 - FLANGE_THK), FreeCAD.Rotation())

fl1_in = doc.addObject("Part::Cylinder", "FlangeLeft_Inner")
fl1_in.Radius = PIPE_ID / 2
fl1_in.Height = FLANGE_THK + 2
fl1_in.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -VALVE_LEN/2 - FLANGE_THK - 1), FreeCAD.Rotation())

fl1 = doc.addObject("Part::Cut", "FlangeLeft")
fl1.Base = fl1_out
fl1.Tool = fl1_in

# ============================================================
# RIGHT FLANGE
# ============================================================
fl2_out = doc.addObject("Part::Cylinder", "FlangeRight_Outer")
fl2_out.Radius = FLANGE_OD / 2
fl2_out.Height = FLANGE_THK
fl2_out.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, VALVE_LEN/2), FreeCAD.Rotation())

fl2_in = doc.addObject("Part::Cylinder", "FlangeRight_Inner")
fl2_in.Radius = PIPE_ID / 2
fl2_in.Height = FLANGE_THK + 2
fl2_in.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, VALVE_LEN/2 - 1), FreeCAD.Rotation())

fl2 = doc.addObject("Part::Cut", "FlangeRight")
fl2.Base = fl2_out
fl2.Tool = fl2_in

# ============================================================
# BOLTS (8 bolts on each flange)
# ============================================================
for i in range(NUM_BOLTS):
    angle = i * (360.0 / NUM_BOLTS)
    rad = math.radians(angle)
    x = BOLT_R * math.cos(rad)
    y = BOLT_R * math.sin(rad)

    # Left flange bolts
    bL = doc.addObject("Part::Cylinder", f"BoltLeft_{i+1}")
    bL.Radius = BOLT_D / 2
    bL.Height = BOLT_LEN
    bL.Placement = FreeCAD.Placement(
        FreeCAD.Vector(x, y, -VALVE_LEN/2 - BOLT_LEN), FreeCAD.Rotation())

    # Right flange bolts
    bR = doc.addObject("Part::Cylinder", f"BoltRight_{i+1}")
    bR.Radius = BOLT_D / 2
    bR.Height = BOLT_LEN
    bR.Placement = FreeCAD.Placement(
        FreeCAD.Vector(x, y, VALVE_LEN/2), FreeCAD.Rotation())

# ============================================================
# BUTTERFLY DISC (tilted at 30° to show it's a butterfly valve)
# ============================================================
disc = doc.addObject("Part::Cylinder", "ButterflyDisc")
disc.Radius = PIPE_ID / 2 - 1
disc.Height = DISC_THICK
disc.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, -DISC_THICK/2),
    FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 30))  # 30° tilt

# ============================================================
# VALVE STEM (vertical shaft through center)
# ============================================================
stem = doc.addObject("Part::Cylinder", "ValveStem")
stem.Radius = STEM_D / 2
stem.Height = VALVE_OD + 60
stem.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, -(VALVE_OD/2 + 30), 0),
    FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90))  # Vertical

# ============================================================
# HANDLE (on top of stem)
# ============================================================
handle = doc.addObject("Part::Box", "Handle")
handle.Length = 120
handle.Width = 20
handle.Height = 12
handle.Placement = FreeCAD.Placement(
    FreeCAD.Vector(-60, VALVE_OD/2 + 25, -6),
    FreeCAD.Rotation())

# ============================================================
doc.recompute()

# Save
save_dir = os.path.dirname(os.path.abspath(__file__))
cad_dir = os.path.join(save_dir, "cad_models")
os.makedirs(cad_dir, exist_ok=True)
save_path = os.path.join(cad_dir, "valve_assembly.FCStd").replace("\\", "/")
doc.saveCopy(save_path)
print(f"MODEL_SAVED: {save_path}")
print("ASSEMBLY_COMPLETE")

os._exit(0)
