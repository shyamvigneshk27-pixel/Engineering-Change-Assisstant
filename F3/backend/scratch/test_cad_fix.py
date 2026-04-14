import sys
import os
from pathlib import Path

# Add backend to path so we can import agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.agent3_cad_executor import Agent3CADExecutor
import json

parts_db = {
  "PART-001": {
    "name": "Valve Body",
    "cad_feature_map": {
      "outer_diameter_mm": "OuterDiameter"
    },
    "dimensions": {
      "outer_diameter_mm": 150
    }
  }
}

parsed_request = {
  "changes": [
    {
      "part_id": "PART-001",
      "parameter": "outer_diameter_mm",
      "new_value": 170.0,
      "current_value": 150.0
    }
  ]
}

agent = Agent3CADExecutor()
result = agent.run(parsed_request, parts_db)
print("Result success:", result["cad_method"] == "freecad")
print("Modified parts:", json.dumps(result["modified_parts"], indent=2))
print("Step files:", result["step_files"])
