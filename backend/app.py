from fastapi import FastAPI, HTTPException
# import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from google import genai
import os
from dotenv import load_dotenv
import requests
import json

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

    # Fetch the URL content
    url = request.url
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch URL content")
        html_content = response.text
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching URL: {str(e)}")

    # Build the prompt
    prompt = f"""
    {html_content}

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

