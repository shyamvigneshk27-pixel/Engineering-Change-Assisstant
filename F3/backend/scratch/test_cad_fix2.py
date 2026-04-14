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
agent._exec_freecad_script_old = agent._exec_freecad_script
def wrapped_exec(script_content):
    out = agent._exec_freecad_script_old(script_content)
    with open("full_freecad_log.txt", "w") as f:
        f.write(out)
    return out

agent._exec_freecad_script = wrapped_exec
result = agent.run(parsed_request, parts_db)
print("Saved full log")
