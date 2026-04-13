import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv(override=True)

key = os.getenv("GEMINI_API_KEY")
print(f"Key: {key[:10]}...{key[-4:]}")

models_to_try = ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"]

for m in models_to_try:
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(m)
        resp = model.generate_content("Say OK")
        print(f"  {m}: WORKS! Response: {resp.text.strip()[:30]}")
        break
    except Exception as e:
        err = str(e)[:120]
        print(f"  {m}: FAILED - {err}")
