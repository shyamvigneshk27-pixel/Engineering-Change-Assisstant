"""
AGENT 1 — INTERPRETER
Sends the EWR text + full parts database to Gemini.
Returns structured JSON: part_id, parameter, current_value, new_value, delta, confidence.
Auto-retries on 429 errors. Fails explicitly if all retries fail.
"""
import google.generativeai as genai
import json, re, os, time
from dotenv import load_dotenv

class Agent1Interpreter:
    name = "INTERPRETER"
    description = "Parses natural language EWR into structured change request"

    def run(self, nl_request: str, parts_db: dict) -> dict:
        start = time.time()
        load_dotenv(override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise Exception("GEMINI_API_KEY not set in environment or .env file.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        parts_summary = [
            {"id": pid, "name": p["name"], "material": p["material"],
             "dimensions": p["dimensions"], "category": p.get("category", ""),
             "cad_feature_map": p.get("cad_feature_map", {})}
            for pid, p in parts_db.items()
        ]

        prompt = f"""You are a senior mechanical engineering AI in an industrial PDM system.

Parts database:
{json.dumps(parts_summary, indent=2)}

Change request: "{nl_request}"

Extract the intent and parameters from the change request to construct a valid JSON response.
Return ONLY valid JSON matching this schema exactly. Do NOT use markdown. Do NOT use code blocks. Replace the placeholder values with the actual extracted variables.
IMPORTANT: The numerical values 0.0 in the schema are PLACEHOLDERS. You MUST replace them with ACTUAL extracted or calculated numbers based on the user's Change Request!

Schema:
{{
  "understood_request": "professional restatement",
  "change_intent": "reduction|increase|replacement|cosmetic|structural",
  "affected_part_ids": ["PART-XXX"],
  "cascade_part_ids": ["parts impacted by interface dependency"],
  "changes": [
    {{
      "part_id": "PART-XXX",
      "parameter": "exact key from dimensions dict. e.g outer_diameter_mm",
      "cad_feature": "matching key from cad_feature_map. e.g OuterDiameter",
      "current_value": 0.0,
      "new_value": 0.0,
      "delta": 0.0,
      "delta_pct": 0.0,
      "unit": "mm"
    }}
  ],
  "material_change": false,
  "new_material": null,
  "change_category": "dimensional|material|tolerance|cosmetic|structural",
  "affects_pressure_boundary": true,
  "affects_mating_interface": false,
  "confidence": "high|medium|low",
  "ambiguities": []
}}"""

        # Simple retry on 429 rate limit
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                raw = response.text.strip()
                if "```" in raw:
                    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
                result = json.loads(raw)
                result["_agent"] = self.name
                result["_mode"] = "gemini_ai"
                result["_time_seconds"] = round(time.time() - start, 2)
                return result
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    if attempt < max_retries - 1:
                        wait = (2 ** attempt) * 2 + 1
                        print(f"  [INTERPRETER] Rate limit hit (Attempt {attempt+1}/{max_retries}). Retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"  [INTERPRETER] API exhausted after {max_retries} attempts.")
                        raise Exception("GEMINI_API_EXHAUSTED")
                else:
                    print(f"  [INTERPRETER] Unexpected AI error: {err_str[:200]}")
                    raise Exception(f"AI_ERROR: {err_str[:100]}")

        raise Exception("GEMINI_API_EXHAUSTED")
