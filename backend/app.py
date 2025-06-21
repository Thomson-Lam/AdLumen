from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware 
from google import genai
client = genai.Client(api_key="AIzaSyDZZ2FUI5Gm493WRJ0u8uCZqhpXlD07Nv0")

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
        Extract all relevant information and return the result as a JSON object.
        """
        # 5️⃣ Call Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disables thinking
            ),
        )
        result = response.text

        # 6️⃣ Return the result
        return {
            "url": url,
            "results": result
        }
    else:
        return {
            "url": url,
            "error": "failed to get HTML",
            "status_code": source.status_code
        }
