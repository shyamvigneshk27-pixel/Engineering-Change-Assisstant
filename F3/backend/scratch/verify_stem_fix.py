import os
import json
from dotenv import load_dotenv
from agents.agent1_interpreter import Agent1Interpreter
from agents.agent3_cad_executor import Agent3CADExecutor

load_dotenv(override=True)

def test_stem_fix():
    print("--- STARTING STEM FIX VERIFICATION ---")
    
    # Setup
    interpreter = Agent1Interpreter()
    cad = Agent3CADExecutor()

    # Database
    parts_db = json.load(open("database/parts.json"))
    
    # Request: Increase Gate Stem diameter to 28mm
    request = "Increase Gate Stem diameter to 28mm"
    print(f"Request: {request}")

    # Step 1: Interpreter
    parsed = interpreter.run(request, parts_db)
    print(f"Parsed Change: {parsed['changes']}")

    # Step 2: CAD Executor
    cad_result = cad.run(parsed, parts_db)
    if not cad_result.get("success", True):
        print(f"CAD Error: {cad_result.get('error')}")
        return
    
    mp = cad_result['modified_parts'][0]
    print(f"CAD Status: {mp.get('status')}")
    print(f"FreeCAD Log Tail:\n{mp.get('freecad_log')}")

    print("--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    test_stem_fix()
