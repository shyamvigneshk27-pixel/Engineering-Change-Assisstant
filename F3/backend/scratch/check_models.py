import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
raw = os.getenv("GEMINI_API_KEYS", "")
api_key = raw.split(",")[0] if raw else os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No API key found")
else:
    genai.configure(api_key=api_key)
    try:
        print("Available models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error: {e}")
