import requests
from bs4 import BeautifulSoup
import json
import os

# --- Configuration ---
HF_API_TOKEN = "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"  # Replace with your HF token
TEXT_MODEL = "typeform/distilbert-base-uncased-mnli"
IMAGE_MODEL = "google/vit-base-patch16-224"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# --- 1. Fetch HTML ---
def fetch_html(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[ERROR] Failed to fetch URL: {e}")
        return None

# --- 2. Parse HTML content ---
def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))[:1000]
    images = [img['src'] for img in soup.find_all("img") if img.get("src")]
    return {"text": text, "images": images[:3]}

# --- 3. Analyze Text via Zero-Shot Classification ---
def analyze_text_with_hf(text):
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["scam", "legitimate", "marketing", "phishing"]
        }
    }
    try:
        res = requests.post(
            f"https://api-inference.huggingface.co/models/{TEXT_MODEL}",
            headers=HEADERS,
            json=payload
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[ERROR] Text classification failed: {e}")
        return None

# --- 4. Image Classification (optional) ---
def analyze_image_url(image_url):
    try:
        image_bytes = requests.get(image_url, timeout=5).content
        res = requests.post(
            f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}",
            headers=HEADERS,
            data=image_bytes
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"[WARN] Image analysis failed for {image_url}: {e}")
        return None

# --- 5. Main Pipeline ---
def run_pipeline(url):
    print(f"[INFO] Scanning {url}")
    html = fetch_html(url)
    if not html:
        return

    parsed = parse_html(html)

    print("\n--- TEXT ANALYSIS ---")
    if parsed["text"].strip():
        text_result = analyze_text_with_hf(parsed["text"])
        print(json.dumps(text_result, indent=2))
    else:
        print("[INFO] No text found on page.")

    print("\n--- IMAGE ANALYSIS ---")
    for img_url in parsed["images"]:
        if not img_url.startswith("http"):
            continue
        img_result = analyze_image_url(img_url)
        if img_result:
            print(f"\nImage: {img_url}")
            print(json.dumps(img_result, indent=2))

# --- Entry Point ---
if __name__ == "__main__":
    url = input("Enter a URL: ").strip()
    run_pipeline(url)
