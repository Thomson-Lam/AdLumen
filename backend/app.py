from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from google import genai
import os
from dotenv import load_dotenv
import requests
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import json

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    url: str

@app.post("/analyze")
async def analyze_url(request: AnalysisRequest):
    # Get Gemini API key
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set.")
    client = genai.Client(api_key=API_KEY)

    # Setup requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9",
    })
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Get page
    time.sleep(random.uniform(1, 3))
    try:
        response = session.get(request.url, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch URL.")
    except requests.RequestException:
        raise HTTPException(status_code=500, detail="Error fetching the URL.")

    # Extract text
    soup = BeautifulSoup(response.text, "html.parser")
    clean_text = soup.get_text(separator='\n')[:7500]

    # Build Gemini prompt
    prompt = f"""
    {clean_text}

    Based on the text above, rate the likelihood this page was AI-generated on a scale from 0 (entirely human-written) to 10(entirely AI-written). 
    Respond with only the number (no text).
    """
    try:
        gemini_response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        score = gemini_response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

    return {"url": request.url, "score": score}

@app.get("/connection")
async def connection():
    return {"status": "connected"}
