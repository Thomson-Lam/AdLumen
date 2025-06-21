from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware 
from google import genai
from pymongo import MongoClient

# Connect to your database
client = genai.Client(api_key="***REMOVED***")
client = MongoClient("***REMOVED***")  # or your Atlas URI

db = client["ai_analysis_db"]
collection = db["results"]

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
    url: str


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


#### this is the same as above but merged see if u can make ot work or i will do later 

import requests

class AnalysisRequest(BaseModel):
    url: str


# 2️⃣ POST Route
@app.post("/analyze")
async def analyze_url(request: AnalysisRequest):
    url = request.url

    # 3️⃣ Get the page
    source = requests.get(url)

    if source.status_code == 200:
        html_content = source.text

        # 4️⃣ Build the prompt
        prompt = f"""
        {html_content}
        
        Extract all relevant information and return the result should be a JSON object with the following keys:
        - url: the URL of the page
        - results: the extracted information from the page
        - image : the URL of the image on the page
        """
        # call Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disables thinking
            ),
        )
        result = response.text
        response = model.generate_content(prompt)
        try:
            results = json.loads(response.text)  # Parse Gemini's reply
        except json.JSONDecodeError:
            results = {"error": "failed to parse JSON", "raw": response.text}

       # Save results
    inserted_id = collection.insert_one({
        "url": url,
        "results": results
    }).inserted_id

    # ✅ Final return goes INSIDE the async method
    return {
        "url": url,
        "results": results,
        "database_id": str(inserted_id)
    }
