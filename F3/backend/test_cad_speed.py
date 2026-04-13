import time
start = time.time()

from agents.agent3_cad_executor import Agent3CADExecutor

a = Agent3CADExecutor()
parsed = {
    "changes": [{
        "part_id": "PART-001",
        "cad_feature": "wall_thickness",
        "new_value": 10
    }]
}
parts = {
    "PART-001": {
        "name": "Valve Body",
        "material": "SS316",
        "dimensions": {
            "outer_diameter_mm": 150,
            "wall_thickness_mm": 12,
            "length_mm": 300
        },
        "category": "pressure_retaining",
        "cad_feature_map": {
            "outer_diameter_mm": "OuterDiameter",
            "inner_diameter_mm": "InnerDiameter"
        }
    }
}

result = a.run(parsed, parts)
elapsed = time.time() - start

print(f"CAD TIME: {elapsed:.1f}s")
print(f"METHOD: {result.get('cad_method')}")
print(f"STATUS: {result.get('status')}")
print(f"STEP FILES: {result.get('step_files')}")
