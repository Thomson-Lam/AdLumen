from fastapi import FastAPI, HTTPException
# import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from google import genai
import os
from dotenv import load_dotenv
import requests
import json
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS middleware to allow requests from the Astro frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],  # Astro frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class AnalysisRequest(BaseModel):
    url: str = None

# Endpoint to analyze a URL for AI-generated content
@app.post("/analyze")
async def analyze_url(request: AnalysisRequest):
    # Load API key
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set in environment variables")

    # Initialize Gemini client
    client = genai.Client(api_key=API_KEY)

    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive"
    }

    session.headers.update(headers)


    retry_strategy = Retry(
        total=5,
        backoff_factor=1,  # exponential backoff: 1s, 2s, 4s, etc.
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    time.sleep(random.uniform(1, 3))

    # Fetch the URL content
    url = request.url
    try:
        response = session.get(url, timeout=10)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch URL content")
        html_content = response.text
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL. Received HTTP 500 from server.")

    # Build the prompt
    soup = BeautifulSoup(html_content, "html.parser")
    clean_text = soup.get_text(separator='\n')

    # NOTE: truncate the text with a text limit
    max = 7500 # cut it safe for 8000

    clean_text = clean_text[:max]

    prompt = f"""
    {clean_text}

    Extract all relevant information and return the result as a JSON object with the following keys:
    - url: the URL of the page
    - results: the extracted information from the page
    - image: the URL of the image on the page
    """

    # Call Gemini API
    try:
        gemini_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        # results = json.loads(gemini_response.text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse Gemini API response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    # Return the response
    return {
        "url": url,
        "response": gemini_response.text,
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

##### JSON > LLM INVESTIGATOR #####

