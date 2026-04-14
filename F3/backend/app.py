"""
ECA — Engineering Change Orchestrator
5-Agent Pipeline Backend with SSE Progress Streaming
"""
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import json, io, os, traceback, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

from agents.agent1_interpreter import Agent1Interpreter
from agents.agent2_tracer import Agent2Tracer
from agents.agent3_cad_executor import Agent3CADExecutor
from agents.agent4_validator import Agent4Validator
from agents.agent5_reporter import Agent5Reporter
from security.ot_security import log_access, get_ot_status
import db_manager as database

app = Flask(__name__, static_folder="../frontend")
CORS(app)

DB_PATH = Path(__file__).parent / "database"
sessions = {}

def load_parts():
    return json.load(open(DB_PATH / "parts.json"))

# Instantiate agents once
agent1 = Agent1Interpreter()
agent2 = Agent2Tracer()
agent3 = Agent3CADExecutor()
agent4 = Agent4Validator()
agent5 = Agent5Reporter()

@app.route("/health")
def health():
    fc = os.path.isfile(os.getenv("FREECAD_CMD", ""))
    return jsonify({
        "status": "online",
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "freecad": fc,
        "freecad_path": os.getenv("FREECAD_CMD", "not set"),
        "agents": 5
    })

@app.route("/parts")
def get_parts():
    p = load_parts()
    return jsonify([{"id": k, "name": v["name"]} for k, v in p.items()])

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Run the full 5-agent pipeline and return all results."""
    nl = (request.get_json() or {}).get("request", "").strip()
    if not nl: return jsonify({"error": "No request provided"}), 400
    if not os.getenv("GEMINI_API_KEY"): return jsonify({"error": "GEMINI_API_KEY not set"}), 500

    try:
        parts = load_parts()
        timings = {}

        # Agent 1: Interpreter
        t0 = time.time()
        parsed = agent1.run(nl, parts)
        timings["agent1"] = round(time.time() - t0, 2)

        # Agent 2: Impact Tracer
        t0 = time.time()
        impact = agent2.run(parsed)
        timings["agent2"] = round(time.time() - t0, 2)

        # Agent 3: CAD Executor
        t0 = time.time()
        cad_result = agent3.run(parsed, parts)
        timings["agent3"] = round(time.time() - t0, 2)

        # Agent 4: Validator
        t0 = time.time()
        validation = agent4.run(parsed, impact, cad_result)
        timings["agent4"] = round(time.time() - t0, 2)

        # Store session for report generation
        sid = f"s{abs(hash(nl)) % 99999}"
        sessions[sid] = {
            "parsed_request": parsed,
            "impact_data": impact,
            "cad_result": cad_result,
            "validation": validation
        }

        # 💾 Supabase Storage — upload modified .FCStd and .step models
        cad_storage_path = None
        step_storage_path = None
        try:
            changes = parsed.get("changes", [])
            if changes:
                pid = changes[0].get("part_id", "PART-001")
                # Asset 1: FCStd
                local_f = (Path(__file__).parent / "cad_models" / f"{pid}.FCStd").resolve()
                if not local_f.exists():
                    local_f = (DB_PATH.parent / "cad_models" / f"{pid}.FCStd").resolve()
                
                print(f"  [DB] FCStd local path: {local_f} (Exists: {local_f.exists()})")
                if local_f.exists():
                    s_path = f"sessions/{sid}/model_{pid}.FCStd"
                    cad_storage_path = database.upload_cad_model(str(local_f), s_path)
                
                # Asset 2: STEP
                step_f = cad_result.get("step_file")
                print(f"  [DB] STEP path from Agent 3: {step_f}")
                if step_f:
                    local_step = Path(step_f).resolve()
                    print(f"  [DB] STEP local path: {local_step} (Exists: {local_step.exists()})")
                    if local_step.exists():
                        step_s_path = f"sessions/{sid}/model_{pid}.step"
                        step_storage_path = database.upload_cad_model(str(local_step), step_s_path)
        except Exception as e:
            print(f"  [⚠️ DB] CAD upload failed (non-fatal): {e}")

        # 💾 Supabase Version Control — save full session
        try:
            # Agent 5 report (needed for PDF + narrative)
            report_data = agent5.run(parsed, impact, cad_result, validation)
            sessions[sid]["report"] = report_data
            database.save_session(
                session_id=sid,
                prompt=nl,
                parsed=parsed,
                impact=impact,
                validation=validation,
                report=report_data,
                cad_result=cad_result,
                cad_storage_path=cad_storage_path,
                step_storage_path=step_storage_path
            )
            # Legacy per-change row
            for c in parsed.get("changes", []):
                database.save_version(
                    part_id=c.get("part_id"),
                    parameter=c.get("parameter"),
                    old_val=c.get("current_value"),
                    new_val=c.get("new_value"),
                    session_id=sid
                )
        except Exception as db_err:
            print(f"  [⚠️ DB] Session save failed: {db_err}")

        return jsonify(
            status="success",
            session_id=sid,
            parsed_request=parsed,
            impact_data=impact,
            cad_result={k: v for k, v in cad_result.items() if k != "render_base64"},
            cad_render=cad_result.get("render_base64"),
            validation_checks=validation["validation_checks"],
            revision_data=validation["revision_data"],
            effort_data=validation["effort_data"],
            cad_method=cad_result.get("cad_method", "simulation"),
            timings=timings
        )
    except Exception as e:
        err_msg = str(e)
        status_code = 429 if "GEMINI_API_EXHAUSTED" in err_msg else 500
        return jsonify(error=err_msg, trace=traceback.format_exc()), status_code


@app.route("/analyze-stream", methods=["GET", "POST"])
@app.route("/api/analyze-stream", methods=["GET", "POST"])
def analyze_stream():
    """SSE endpoint that streams agent progress in real-time."""
    if request.method == "POST":
        nl = (request.get_json() or {}).get("request", "").strip()
    else:
        nl = request.args.get("request", "").strip()

    if not nl:
        return jsonify({"error": "No request provided"}), 400

    print(f"  [STREAM] Analysis started for: {nl[:30]}...")


    def generate():
        try:
            # Send 2KB padding to bypass browser/proxy buffering
            yield ":" + " " * 2048 + "\n\n"
            
            # Send immediate start signal
            yield f"data: {json.dumps({'agent': 1, 'name': 'INTERPRETER', 'status': 'running'})}\n\n"
            
            parts = load_parts()
            parsed = agent1.run(nl, parts)
            yield f"data: {json.dumps({'agent': 1, 'name': 'INTERPRETER', 'status': 'done', 'time': parsed.get('_time_seconds', 0), 'confidence': parsed.get('confidence','')})}\n\n"

            # Agent 2
            yield f"data: {json.dumps({'agent': 2, 'name': 'IMPACT TRACER', 'status': 'running'})}\n\n"
            impact = agent2.run(parsed)
            yield f"data: {json.dumps({'agent': 2, 'name': 'IMPACT TRACER', 'status': 'done', 'time': impact.get('_time_seconds', 0), 'parts': impact['summary']['total_parts_affected'], 'assemblies': impact['summary']['total_assemblies_affected']})}\n\n"

            # Agent 3
            yield f"data: {json.dumps({'agent': 3, 'name': 'CAD EXECUTOR', 'status': 'running'})}\n\n"
            cad_result = agent3.run(parsed, parts)
            yield f"data: {json.dumps({'agent': 3, 'name': 'CAD EXECUTOR', 'status': 'done', 'time': cad_result.get('_time_seconds', 0), 'method': cad_result.get('cad_method','')})}\n\n"

            # Agent 4
            yield f"data: {json.dumps({'agent': 4, 'name': 'VALIDATOR', 'status': 'running'})}\n\n"
            validation = agent4.run(parsed, impact, cad_result)
            yield f"data: {json.dumps({'agent': 4, 'name': 'VALIDATOR', 'status': 'done', 'time': validation.get('_time_seconds', 0), 'safe': validation['overall_safe']})}\n\n"

            # Agent 5
            yield f"data: {json.dumps({'agent': 5, 'name': 'REPORTER', 'status': 'running'})}\n\n"
            report = agent5.run(parsed, impact, cad_result, validation)
            yield f"data: {json.dumps({'agent': 5, 'name': 'REPORTER', 'status': 'done', 'time': report.get('_time_seconds', 0)})}\n\n"

            # Store session
            sid = f"s{abs(hash(nl)) % 99999}"
            sessions[sid] = {
                "parsed_request": parsed,
                "impact_data": impact,
                "cad_result": cad_result,
                "validation": validation,
                "report": report
            }

            # 💾 Supabase Storage — upload modified .FCStd and .step models
            cad_storage_path = None
            step_storage_path = None
            try:
                changes = parsed.get("changes", [])
                if changes:
                    pid = changes[0].get("part_id", "PART-001")
                    # Asset 1: FCStd
                    local_f = (Path(__file__).parent / "cad_models" / f"{pid}.FCStd").resolve()
                    if not local_f.exists():
                        local_f = (DB_PATH.parent / "cad_models" / f"{pid}.FCStd").resolve()
                    
                    print(f"  [DB] FCStd local path: {local_f} (Exists: {local_f.exists()})")
                    if local_f.exists():
                        s_path = f"sessions/{sid}/model_{pid}.FCStd"
                        cad_storage_path = database.upload_cad_model(str(local_f), s_path)

                    # Asset 2: STEP
                    step_f = cad_result.get("step_file")
                    print(f"  [DB] STEP path from Agent 3: {step_f}")
                    if step_f:
                        local_step = Path(step_f).resolve()
                        print(f"  [DB] STEP local path: {local_step} (Exists: {local_step.exists()})")
                        if local_step.exists():
                            step_s_path = f"sessions/{sid}/model_{pid}.step"
                            step_storage_path = database.upload_cad_model(str(local_step), step_s_path)
            except Exception as e:
                print(f"  [⚠️ DB] CAD upload failed (non-fatal): {e}")

            # 💾 Supabase Version Control — save full session + per-change rows
            try:
                database.save_session(
                    session_id=sid,
                    prompt=nl,
                    parsed=parsed,
                    impact=impact,
                    validation=validation,
                    report=report,
                    cad_result=cad_result,
                    cad_storage_path=cad_storage_path,
                    step_storage_path=step_storage_path
                )
                for c in parsed.get("changes", []):
                    database.save_version(
                        part_id=c.get("part_id"),
                        parameter=c.get("parameter"),
                        old_val=c.get("current_value"),
                        new_val=c.get("new_value"),
                        session_id=sid
                    )
            except Exception as db_err:
                print(f"  [⚠️ DB] Supabase save failed (non-fatal): {db_err}")

            # Final result
            final = {
                "agent": "complete",
                "session_id": sid,
                "parsed_request": parsed,
                "impact_data": impact,
                "cad_render": cad_result.get("render_base64"),
                "cad_method": cad_result.get("cad_method", "simulation"),
                "validation_checks": validation["validation_checks"],
                "revision_data": validation["revision_data"],
                "effort_data": validation["effort_data"],
                "narrative": report.get("narrative", ""),
                "step_files": report.get("step_files", []),
                "bom_before_after": impact.get("bom_before_after", []),
                "cost_analysis": impact.get("cost_analysis", {}),
                "inspection_before_after": impact.get("inspection_before_after", []),
                "barlow_details": impact.get("barlow_details", []),
                "error": cad_result.get("error"),
                "vol_removed_mm3": cad_result.get("vol_removed_mm3"),
                "mass_reduction_pct": cad_result.get("mass_reduction_pct")
            }
            yield f"data: {json.dumps(final)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'agent': 'error', 'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/report", methods=["POST"])
def report():
    d = request.get_json() or {}
    sid = d.get("session_id")
    if not sid or sid not in sessions:
        return jsonify({"error": "Session not found. Run analysis first."}), 404

    s = sessions[sid]
    try:
        # If report already generated, use cached
        if "report" in s and s["report"].get("pdf_bytes"):
            pdf = s["report"]["pdf_bytes"]
        else:
            r = agent5.run(s["parsed_request"], s["impact_data"], s["cad_result"], s["validation"])
            pdf = r["pdf_bytes"]
            s["report"] = r

        return send_file(io.BytesIO(pdf), mimetype="application/pdf",
                         as_attachment=True, download_name="ECA_Change_Impact_Report.pdf")
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/download-step/<session_id>")
def download_step(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    s = sessions[session_id]
    step_files = s.get("cad_result", {}).get("step_files", [])
    if not step_files:
        return jsonify({"error": "No STEP file available"}), 404
    return send_file(step_files[0], as_attachment=True, download_name="ECA_modified_part.step")


@app.route("/preview-model")
def preview_model():
    """Open the base valve assembly in FreeCAD GUI (non-blocking) for judge viewing."""
    import subprocess as sp
    cad_dir = Path(__file__).parent / "cad_models"
    model = cad_dir / "valve_assembly.FCStd"
    # Also check for PART-001.FCStd
    if not model.exists():
        model = cad_dir / "PART-001.FCStd"
    if not model.exists():
        return jsonify({"error": "No base model found. Run the pipeline first."}), 404

    freecad_gui = r"C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe"
    if not os.path.isfile(freecad_gui):
        return jsonify({"error": f"FreeCAD GUI not found at {freecad_gui}"}), 500

    sp.Popen([freecad_gui, str(model)], cwd=str(cad_dir))
    return jsonify({"status": "opened", "file": str(model)})


@app.route("/preview-modified")
def preview_modified():
    """Open the modified model in FreeCAD GUI (non-blocking) to show changes."""
    import subprocess as sp
    cad_dir = Path(__file__).parent / "cad_models"
    # Find most recent modified model
    modified = cad_dir / "PART-001.FCStd"
    if not modified.exists():
        return jsonify({"error": "No modified model found. Run the pipeline first."}), 404

    freecad_gui = r"C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe"
    if not os.path.isfile(freecad_gui):
        return jsonify({"error": f"FreeCAD GUI not found at {freecad_gui}"}), 500

    sp.Popen([freecad_gui, str(modified)], cwd=str(cad_dir))
    return jsonify({"status": "opened", "file": str(modified)})


@app.route("/audit-log")
def audit_log():
    """View audit trail of all system interactions."""
    log_access("System", "view_audit", "audit_log", "GRANTED")
    return jsonify(get_ot_status())


@app.route("/ot-dashboard")
def ot_dashboard():
    """Centralized OT monitoring dashboard data."""
    return jsonify(get_ot_status())


@app.route("/api/history")
def history():
    """Retrieve version control history from Supabase (newest first, light fields only)."""
    data = database.get_history(limit=100)
    return jsonify(data)


@app.route("/api/session/<session_id>")
def get_session(session_id):
    """Retrieve full session record including PDF base64 and all JSON blobs."""
    data = database.get_session(session_id)
    if not data:
        return jsonify({"error": "Session not found in Supabase"}), 404
    return jsonify(data)


@app.route("/api/cad-url/<session_id>")
def get_cad_url(session_id):
    """Generate a public (or signed) URL for archived model. ?format=step|fcstd"""
    fmt = request.args.get("format", "fcstd").lower()
    data = database.get_session(session_id)
    if not data:
        return jsonify({"error": "Session not found"}), 404
    
    path = data.get("step_storage_path") if fmt == "step" else data.get("cad_storage_path")
    if not path:
        return jsonify({"error": f"{fmt.upper()} model not found for this session"}), 404
    
    # We assume the bucket is public for simplicity in this demo.
    url = f"{database.SUPABASE_URL}/storage/v1/object/public/eca-cad-models/{path}"
    return jsonify({"url": url})


@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ECA -- Engineering Change Orchestrator v3.0")
    print("  5-Agent Pipeline | STARK-X | SLB Hackathon 2026")
    print("  Gemini:", "YES" if os.getenv("GEMINI_API_KEY") else "NO")
    print("  FreeCAD:", "YES" if os.path.isfile(os.getenv("FREECAD_CMD","")) else "NO (simulation mode)")
    print("="*60)
    print("  http://localhost:5000\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)
    