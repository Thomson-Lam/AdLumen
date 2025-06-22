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
    
    ##
    try:
        print("Starting analyze endpoint")
        ##
        
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
        # prompt = f"""
        # {clean_text}

        # Based on the text above, rate the likelihood this page was AI-generated on a scale from 0 (entirely human-written) to 10(entirely AI-written). 
        # Respond with only the number (no text).
        # """
        
        ##
        prompt = f"""Task: Perform a fraud risk assessment of {request.url} and return ONLY a JSON object with the following structure:

            json
            {{
            "fraud_probability": [0.00–1.00],
            "confidence_level": [0.00–1.00],
            "justification": "Concise 1-2 sentence explanation."
            }}

            Rules:

            - No additional text before, after, or inside the JSON (e.g., no "Here’s the result:", disclaimers, or markdown formatting).
            - Strict compliance—if unable to generate valid JSON, return {{}}.
            - Precision: Use decimal percentages (e.g., 0.25, not 0.2).

            Analysis Requirements:

            Technical: WHOIS age, SSL/TLS, HTTPS, security headers (CSP/HSTS/X-Frame-Options).
            Content: Scam indicators, branding consistency, contact info.
            Threat Intel: Blacklists (Google Safe Browsing, PhishTank), historical scans (VirusTotal)."""
        ##
        
        try:
            gemini_response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            raw_response = gemini_response.text.strip()
            print(f"Raw Gemini response: {raw_response}")
            
            # Parse JSON response
            import json
            try:
                analysis_result = json.loads(raw_response)
                print(f"Parsed JSON: {analysis_result}")
                
                # Validate required fields
                if not all(key in analysis_result for key in ["fraud_probability", "confidence_level", "justification"]):
                    raise ValueError("Missing required fields in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parsing error: {e}")
                # Fallback response
                analysis_result = {
                    "fraud_probability": 0.0,
                    "confidence_level": 0.0,
                    "justification": "Unable to analyze due to parsing error."
                }
                
        except Exception as e:
            print(f"Gemini error: {e}")
            raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

        print("Analysis completed successfully")
        response_data = {
            "url": request.url,
            "fraud_probability": analysis_result["fraud_probability"],
            "confidence_level": analysis_result["confidence_level"],
            "justification": analysis_result["justification"]
        }
        print(f"About to return: {response_data}")
        return response_data
        
    except Exception as e:
        print(f"Error in analyze: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/connection")
async def connection():
    return {"status": "connected"}
