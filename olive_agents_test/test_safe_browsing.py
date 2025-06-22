import requests
from urllib.parse import urlparse

API_KEY = "AIzaSyAkl0pEOyKB04Tli0CoJICjfLAS6xcG31M"

def check_safe_browsing(url):
    try:
        response = requests.post(
            f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={API_KEY}",
            json={
                "client": {"clientId": "yourcompany", "clientVersion": "1.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url}]
                }
            },
            timeout=5
        )
        result = response.json()
        return result.get('matches', [])
    except Exception as e:
        print(f"⚠️ API Error: {str(e)}")
        return []

def is_suspicious_domain(url):
    domain = urlparse(url).netloc.lower()
    red_flags = ['paypal', 'apple', 'microsoft', 'login', 'verify']
    return any(flag in domain for flag in red_flags)

if __name__ == "__main__":
    TEST_URLS = [
        "http://malware.testing.google.test/testing/malware/",
        "https://www.google.com",
        "http://paypal-com.login.security.update.com",
        "http://microsoft-office365.com.verify-login.org"
    ]
    
    for url in TEST_URLS:
        print(f"\n🔎 Checking: {url}")
        
        threats = check_safe_browsing(url)
        if threats:
            for threat in threats:
                print(f"⛔ Safe Browsing Threat: {threat['threatType']}")
        elif is_suspicious_domain(url):
            print("⚠️ Suspicious Domain (Not in Safe Browsing yet)")
        else:
            print("✅ No threats detected")