import os
import json
from dotenv import load_dotenv
from agents.agent1_interpreter import Agent1Interpreter
from agents.agent3_cad_executor import Agent3CADExecutor

load_dotenv(override=True)

def test_assembly_fix():
    print("--- STARTING ASSEMBLY FIX VERIFICATION ---")
    
    # Setup
    interpreter = Agent1Interpreter()
    cad = Agent3CADExecutor()

    # Database
    parts_db = json.load(open("database/parts.json"))
    
    # Request: Reduce wall thickness of Valve Body by 2mm for weight reduction
    request = "Reduce wall thickness of Valve Body by 2mm for weight reduction"
    print(f"Request: {request}")

    # Step 1: Interpreter
    parsed = interpreter.run(request, parts_db)
    print(f"Parsed Change: {parsed['changes']}")

    # Step 2: CAD Executor
    cad_result = cad.run(parsed, parts_db)
    mp = cad_result['modified_parts'][0]
    print(f"CAD Status: {mp.get('status')}")
    print(f"FreeCAD Log Tail:\n{mp.get('freecad_log', 'N/A')}")
    print(f"Volume Removed: {mp.get('vol_removed_mm3')} mm3")

    print("--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    test_assembly_fix()
