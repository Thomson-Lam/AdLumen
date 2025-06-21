from fastapi import FastAPI
import requests
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware 
from google import genai
<<<<<<< HEAD
from pymongo import MongoClient

# Connect to your database
client = genai.Client(api_key="***REMOVED***")
client = MongoClient("***REMOVED***")  # or your Atlas URI

db = client["ai_analysis_db"]
collection = db["results"]
=======
from google.genai import types 
import os 
from dotenv import load_dotenv 
>>>>>>> c724143 (using backend with dotenv)

app = FastAPI()

# CORS middleware to allow requests from the Astro frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],  # Astro frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    url: str = None

# Endpoint to analyze a URL for AI-generated content
@app.post("/analyze")
async def analyze_url(request: AnalysisRequest):
    load_dotenv()
    API_KEY = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=API_KEY)
    url = request.url
    is_ai_generated = False
    confidence_score = 0.0
    explanation = "Pending AI detection"

    source = requests.get(url)

    if source.status_code == 200:
        html_content = source.text
        prompt = f"""
        {html_content}

        INSERT PROMPT HERE """

        res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt,
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
        ),)

        return {
            "url": url,
            "response": res.text,
        }

    else:
        return {
            "url": url,
            "response": "failed to get HTML."
        }
        


@app.get("/connection")
async def connection():
    return {"status": "connected"}

@app.get("/results")
async def results():
    return {
        "results": [
            {"url": "https://example.com/ad1", "score": 0.85},
            {"url": "https://example.com/ad2", "score": 0.90},
        ]
    }


