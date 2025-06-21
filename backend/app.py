from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# CORS middleware to allow requests from the Astro frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],  # Astro frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# schema for incomeing requests 
class AnalysisRequest(BaseModel):
    text: str = None       # Text extracted from the ad
    image: str = None      # Image data (can be base64 or URL)


# schema for outgoing responses
@@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    print("GOT IT:", request) # SANITY CHECK 
    return {
        "link": "https://example.com/ad",
        "is_ai_generated": False,
        "confidence_score": 0.0,
        "explanation": "Analysis not implemented yet."
    }
