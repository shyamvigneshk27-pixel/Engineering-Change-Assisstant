import google.generativeai as genai
import json, re, os

def parse_change_request(nl_request: str, parts_db: dict) -> dict:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)

    parts_summary = [
        {"id": pid, "name": p["name"], "material": p["material"],
         "dimensions": p["dimensions"]}
        for pid, p in parts_db.items()
    ]

    prompt = f"""You are a senior mechanical engineering AI in an industrial PDM system.

Parts database:
{json.dumps(parts_summary, indent=2)}

Change request: "{nl_request}"

Return ONLY valid JSON (no markdown, no explanation):
{{
  "understood_request": "professional restatement",
  "change_intent": "reduction|increase|replacement|cosmetic|structural",
  "affected_part_ids": ["PART-XXX"],
  "cascade_part_ids": ["parts impacted by interface dependency"],
  "changes": [
    {{
      "part_id": "PART-XXX",
      "parameter": "exact key from dimensions dict",
      "cad_feature": "CAD feature name",
      "current_value": 12.0,
      "new_value": 10.0,
      "delta": -2.0,
      "delta_pct": -16.67,
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

    response = model.generate_content(prompt)
    raw = response.text.strip()
    if "```" in raw:
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(raw)


def generate_narrative(parsed_request: dict, impact_data: dict) -> str:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)
    prompt = f"""You are a senior engineering change management specialist.

Change: {json.dumps(parsed_request, indent=2)}
Impact: {json.dumps(impact_data, indent=2)}

Write a 3-paragraph professional engineering impact narrative (150-200 words) for a formal Change Impact Summary Report. Cover: (1) what is changing and on which parts, (2) downstream system impacts, (3) risk summary and recommended action. Plain text only, no headers."""
    return model.generate_content(prompt).text.strip()
