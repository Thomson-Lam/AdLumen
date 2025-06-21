from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# schema for incomeing requests 
class AnalysisRequest(BaseModel):
    text: str = None       # Text extracted from the ad
    image: str = None      # Image data (can be base64 or URL)

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    #dummy data to check if the API is working
    response = {
        'link' : "https://example.com/ad",
        "is_ai_generated": False,
        "confidence_score": 0.0,
        "explanation": "Analysis not implemented yet."
    }
    return response
