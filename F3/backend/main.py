import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from schemas import EwrAnalysisResponse

# Load environment variables (can fall back to frontend's .env.local if needed)
load_dotenv(dotenv_path="../frontend/.env.local")
load_dotenv()

app = FastAPI(title="Engineering Change Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # We won't crash here so the server can start, but logging it is useful
    print("Warning: GEMINI_API_KEY not found in environment")
client = genai.Client(api_key=api_key)

class AnalyzeRequest(BaseModel):
    ewrText: str

@app.post("/api/analyze", response_model=EwrAnalysisResponse)
async def analyze_ewr(request: AnalyzeRequest):
    if not request.ewrText:
        raise HTTPException(status_code=400, detail="ewrText is required")

    prompt = f"""You are an AI Engineering Change Assistant (ECA). Analyze the following Engineering Work Request (EWR) and provide a detailed structured impact analysis.

EWR: "{request.ewrText}"

Provide plausible, realistic engineering data based on the request (e.g., impact on assemblies, wall thickness changes, Barlow formula validation, affected documents, inspection procedures, and effort estimate in hours). Include a brief narrative (1-2 paragraphs) summarizing the change and its implications. Make sure to populate the color fields using CSS vars (e.g. "var(--color-accent)", "var(--color-danger)")."""

    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': EwrAnalysisResponse,
            },
        )
        # response.parsed contains the Pydantic model populated by the SDK
        return response.parsed
    except Exception as e:
        print(f"AI Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze EWR")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
