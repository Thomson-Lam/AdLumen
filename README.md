# AdLumen: An URL Safety Scanner  

Welcome! Good to see you here. This is the GitHub repo for AdLumen's submission to SpurHacks. 
Using a single agent workflow with Human-In-the-Loop, AdLumen takes a URL and scans the credibility of the site based on the site's images, domain name and content, then gives the user an assessment on whether the site contains deceptive or fraudulent content or not.

# Running locally

## frontend 
cd frontend, `npm i`,  `npm run dev`

## backend 
cd backend, use a venv of choice and run `uvicorn app:app --reload`
