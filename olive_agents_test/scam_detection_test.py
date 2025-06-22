import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta
import re
from collections import defaultdict
import whois
from threading import Lock

# Configuration
TOGETHER_API_KEY = "78623dc87eba15873654310f371ee2c5f8b4f5b732276ae5204a45bd1a60c107"  # Replace with your Together.ai API key
GOOGLE_SAFE_BROWSING_API_KEY = "AIzaSyAkl0pEOyKB04Tli0CoJICjfLAS6xcG31M"  # Replace with your Google Safe Browsing API key

TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

class RateLimiter:
    """Rate limiter to ensure we don't exceed 60 RPM for Together.ai API"""
    def __init__(self, max_requests=58, time_window=60):  # Buffer of 2 requests
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = Lock()
    
    def wait_if_needed(self):
        with self.lock:
            now = datetime.now()
            # Remove requests older than time_window
            self.requests = [req_time for req_time in self.requests 
                           if (now - req_time).total_seconds() < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    print(f"⏳ Rate limit approaching, waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time + 1)  # Add 1 second buffer
            
            self.requests.append(now)

class ScamInvestigator:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.investigation_results = {}
        self.risk_score = 0
        self.risk_factors = []
        
    def check_safe_browsing(self, url):
        """Check Google Safe Browsing API"""
        if not GOOGLE_SAFE_BROWSING_API_KEY:
            return {"status": "API key missing", "threats": []}
            
        try:
            response = requests.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}",
                json={
                    "client": {"clientId": "scam-investigator", "clientVersion": "1.0"},
                    "threatInfo": {
                        "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                        "platformTypes": ["ANY_PLATFORM"],
                        "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": url}]
                    }
                },
                timeout=10
            )
            result = response.json()
            threats = result.get('matches', [])
            return {"status": "success", "threats": threats}
        except Exception as e:
            return {"status": f"error: {str(e)}", "threats": []}

    def analyze_domain(self, url):
        """Analyze domain characteristics"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            analysis = {
                "domain": domain,
                "suspicious_keywords": [],
                "character_analysis": {},
                "whois_info": {}
            }
            
            # Check for suspicious keywords
            suspicious_keywords = [
                'paypal', 'apple', 'microsoft', 'amazon', 'google', 'facebook',
                'login', 'verify', 'secure', 'account', 'update', 'suspended',
                'urgent', 'immediate', 'confirm', 'banking', 'security'
            ]
            
            for keyword in suspicious_keywords:
                if keyword in domain and not domain.startswith(keyword + '.'):
                    analysis["suspicious_keywords"].append(keyword)
            
            # Character analysis
            analysis["character_analysis"] = {
                "has_hyphens": '-' in domain,
                "has_numbers": any(c.isdigit() for c in domain),
                "length": len(domain),
                "subdomain_count": len(domain.split('.')) - 2
            }
            
            # Try to get WHOIS info
            try:
                w = whois.whois(domain)
                if w:
                    analysis["whois_info"] = {
                        "creation_date": str(w.creation_date) if w.creation_date else None,
                        "registrar": str(w.registrar) if w.registrar else None,
                        "country": str(w.country) if w.country else None
                    }
            except:
                analysis["whois_info"] = {"error": "WHOIS lookup failed"}
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}

    def fetch_and_parse_content(self, url):
        """Fetch and parse website content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = {
                "title": soup.title.string if soup.title else "",
                "text_content": soup.get_text()[:2000],  # Limit text for API
                "forms": [],
                "links": [],
                "images": [],
                "meta_info": {}
            }
            
            # Analyze forms (common in phishing)
            for form in soup.find_all('form'):
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', ''),
                    "inputs": [inp.get('type', 'text') for inp in form.find_all('input')]
                }
                content["forms"].append(form_data)
            
            # Get external links
            for link in soup.find_all('a', href=True)[:10]:  # Limit to 10 links
                href = link['href']
                if href.startswith('http'):
                    content["links"].append(href)
            
            # Get images
            for img in soup.find_all('img', src=True)[:5]:  # Limit to 5 images
                content["images"].append(img['src'])
            
            # Meta information
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                if name and meta.get('content'):
                    content["meta_info"][name] = meta.get('content')
            
            return content
            
        except Exception as e:
            return {"error": str(e)}

    def ai_analysis(self, prompt, max_retries=3):
        """Analyze using Together.ai API with rate limiting"""
        self.rate_limiter.wait_if_needed()
        
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": TOGETHER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cybersecurity expert specializing in scam and phishing detection. Analyze the provided information and give a detailed assessment."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"AI Analysis failed: {str(e)}"
                time.sleep(2 ** attempt)  # Exponential backoff

    def calculate_risk_score(self):
        """Calculate overall risk score based on findings"""
        score = 0
        factors = []
        
        # Safe Browsing threats
        if self.investigation_results.get('safe_browsing', {}).get('threats'):
            score += 80
            factors.append("Google Safe Browsing detected threats")
        
        # Domain analysis
        domain_analysis = self.investigation_results.get('domain_analysis', {})
        if domain_analysis.get('suspicious_keywords'):
            score += len(domain_analysis['suspicious_keywords']) * 15
            factors.append(f"Suspicious keywords in domain: {', '.join(domain_analysis['suspicious_keywords'])}")
        
        char_analysis = domain_analysis.get('character_analysis', {})
        if char_analysis.get('has_hyphens') and char_analysis.get('has_numbers'):
            score += 10
            factors.append("Domain contains both hyphens and numbers")
        
        if char_analysis.get('length', 0) > 30:
            score += 15
            factors.append("Unusually long domain name")
        
        # Content analysis
        content = self.investigation_results.get('content', {})
        if content.get('forms'):
            login_forms = any('password' in str(form.get('inputs', [])) for form in content['forms'])
            if login_forms:
                score += 25
                factors.append("Contains login/password forms")
        
        # WHOIS analysis
        whois_info = domain_analysis.get('whois_info', {})
        if whois_info.get('creation_date'):
            try:
                # Check if domain is very new (less than 30 days)
                creation_date = whois_info['creation_date']
                # This is a simplified check, you'd want more robust date parsing
                if 'days ago' in str(creation_date) or '2024' in str(creation_date):
                    score += 20
                    factors.append("Recently registered domain")
            except:
                pass
        
        self.risk_score = min(score, 100)  # Cap at 100
        self.risk_factors = factors
        
        return self.risk_score, factors

    def investigate(self, url):
        """Main investigation method"""
        print(f"🕵️ Starting investigation of: {url}")
        print("=" * 60)
        
        # 1. Google Safe Browsing Check
        print("🔍 Checking Google Safe Browsing...")
        safe_browsing = self.check_safe_browsing(url)
        self.investigation_results['safe_browsing'] = safe_browsing
        
        if safe_browsing['threats']:
            print(f"⛔ THREATS DETECTED: {len(safe_browsing['threats'])} threat(s)")
            for threat in safe_browsing['threats']:
                print(f"   - {threat.get('threatType', 'Unknown threat')}")
        else:
            print("✅ No threats found in Safe Browsing database")
        
        # 2. Domain Analysis
        print("\n🌐 Analyzing domain...")
        domain_analysis = self.analyze_domain(url)
        self.investigation_results['domain_analysis'] = domain_analysis
        
        if domain_analysis.get('suspicious_keywords'):
            print(f"⚠️ Suspicious keywords found: {', '.join(domain_analysis['suspicious_keywords'])}")
        
        # 3. Content Analysis
        print("\n📄 Fetching and analyzing website content...")
        content = self.fetch_and_parse_content(url)
        self.investigation_results['content'] = content
        
        if content.get('error'):
            print(f"❌ Failed to fetch content: {content['error']}")
        else:
            print(f"✅ Content analyzed - Title: {content.get('title', 'No title')[:50]}...")
            if content.get('forms'):
                print(f"📝 Found {len(content['forms'])} form(s)")
        
        # 4. AI-Powered Analysis
        if not content.get('error') and TOGETHER_API_KEY:
            print("\n🤖 Running AI analysis...")
            
            # Prepare data for AI analysis
            ai_prompt = f"""
            Analyze this website for potential scam indicators:
            
            URL: {url}
            Domain: {domain_analysis.get('domain', 'Unknown')}
            
            Domain Analysis:
            - Suspicious keywords: {domain_analysis.get('suspicious_keywords', [])}
            - Has hyphens: {domain_analysis.get('character_analysis', {}).get('has_hyphens', False)}
            - Domain length: {domain_analysis.get('character_analysis', {}).get('length', 0)}
            
            Website Content:
            - Title: {content.get('title', 'No title')}
            - Text preview: {content.get('text_content', '')[:500]}...
            - Number of forms: {len(content.get('forms', []))}
            - External links: {len(content.get('links', []))}
            
            Safe Browsing Status: {safe_browsing.get('status', 'Unknown')}
            
            Please provide:
            1. Scam likelihood (Low/Medium/High)
            2. Key red flags identified
            3. Legitimate reasons it might not be a scam
            4. Specific recommendations for users
            """
            
            ai_analysis = self.ai_analysis(ai_prompt)
            self.investigation_results['ai_analysis'] = ai_analysis
            print("🤖 AI Analysis completed")
        
        # 5. Calculate Risk Score
        risk_score, risk_factors = self.calculate_risk_score()
        
        # 6. Generate Report
        self.generate_report(url, risk_score, risk_factors)
        
        return self.investigation_results

    def generate_report(self, url, risk_score, risk_factors):
        """Generate final investigation report"""
        print("\n" + "=" * 60)
        print("📊 INVESTIGATION REPORT")
        print("=" * 60)
        
        # Risk Assessment
        if risk_score >= 70:
            risk_level = "🔴 HIGH RISK"
            recommendation = "⛔ AVOID - This website shows strong indicators of being a scam"
        elif risk_score >= 40:
            risk_level = "🟡 MEDIUM RISK"
            recommendation = "⚠️ CAUTION - Exercise extreme caution, verify independently"
        else:
            risk_level = "🟢 LOW RISK"
            recommendation = "✅ LIKELY SAFE - No major red flags detected"
        
        print(f"URL: {url}")
        print(f"Risk Score: {risk_score}/100")
        print(f"Risk Level: {risk_level}")
        print(f"Recommendation: {recommendation}")
        
        if risk_factors:
            print("\n🚨 Risk Factors Identified:")
            for i, factor in enumerate(risk_factors, 1):
                print(f"   {i}. {factor}")
        
        # Safe Browsing Results
        safe_browsing = self.investigation_results.get('safe_browsing', {})
        if safe_browsing.get('threats'):
            print(f"\n⛔ Google Safe Browsing: {len(safe_browsing['threats'])} threat(s) detected")
        else:
            print("\n✅ Google Safe Browsing: Clean")
        
        # AI Analysis Summary
        if self.investigation_results.get('ai_analysis'):
            print("\n🤖 AI Analysis:")
            print(self.investigation_results['ai_analysis'])
        
        print("\n" + "=" * 60)

def main():
    if not TOGETHER_API_KEY:
        print("⚠️ Warning: TOGETHER_API_KEY not set. AI analysis will be skipped.")
    
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        print("⚠️ Warning: GOOGLE_SAFE_BROWSING_API_KEY not set. Safe Browsing check will be skipped.")
    
    print("🕵️ Scam Investigation Agent")
    print("Enter URLs to investigate (type 'quit' to exit)")
    
    investigator = ScamInvestigator()
    
    while True:
        url = input("\n🔗 Enter URL to investigate: ").strip()
        
        if url.lower() in ['quit', 'exit', 'q']:
            break
        
        if not url:
            continue
            
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            results = investigator.investigate(url)
            
            # Reset for next investigation
            investigator = ScamInvestigator()
            
        except KeyboardInterrupt:
            print("\n⏹️ Investigation interrupted by user")
            break
        except Exception as e:
            print(f"❌ Investigation failed: {str(e)}")

if __name__ == "__main__":
    main()