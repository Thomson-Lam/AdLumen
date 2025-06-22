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
import base64
from io import BytesIO
from PIL import Image
import hashlib

# Configuration
TOGETHER_API_KEY = "78623dc87eba15873654310f371ee2c5f8b4f5b732276ae5204a45bd1a60c107"  # Replace with your Together.ai API key
GOOGLE_SAFE_BROWSING_API_KEY = "AIzaSyAkl0pEOyKB04Tli0CoJICjfLAS6xcG31M"  # Replace with your Google Safe Browsing API key

TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

class RateLimiter:
    """Enhanced rate limiter to ensure we don't exceed 60 RPM for Together.ai API"""
    def __init__(self, max_requests=55, time_window=60):  # Buffer of 5 requests for safety
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = Lock()
        self.total_requests = 0
    
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
                    print(f"⏳ Rate limit protection: waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time + 2)  # Add 2 second buffer
            
            self.requests.append(now)
            self.total_requests += 1
            print(f"📊 API Request #{self.total_requests} (Current window: {len(self.requests)}/{self.max_requests})")

class ScamInvestigationAgent:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.investigation_data = {}
        self.tools_used = []
        self.decision_factors = {}
        self.final_scam_probability = 0
        
    def parse_gemini_response(self, gemini_response_text):
        """Parse the JSON response from Gemini LLM"""
        try:
            print("🔍 Parsing Gemini response...")
            data = json.loads(gemini_response_text)
            
            required_keys = ['url', 'results', 'image']
            for key in required_keys:
                if key not in data:
                    print(f"⚠️ Missing key in Gemini response: {key}")
            
            print(f"✅ Parsed Gemini data - URL: {data.get('url', 'N/A')}")
            return data
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Gemini response: {e}")
            return None

    def ai_analysis(self, prompt, context="general", max_retries=3):
        """Enhanced AI analysis with context awareness and rate limiting"""
        self.rate_limiter.wait_if_needed()
        
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompts = {
            "general": "You are a cybersecurity expert specializing in scam and phishing detection. Analyze the provided information and give a detailed assessment.",
            "deepfake": "You are an AI-generated content detection expert. Analyze images for signs of AI generation or deepfake manipulation. Focus on technical artifacts, inconsistencies, and tell-tale signs.",
            "ai_generated": "You are an expert in detecting AI-generated images. Look for common AI artifacts like inconsistent lighting, unnatural textures, impossible geometry, or other generation artifacts.",
            "content_analysis": "You are a web content analysis expert. Examine website content for scam patterns, social engineering tactics, and deceptive practices."
        }
        
        payload = {
            "model": TOGETHER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompts.get(context, system_prompts["general"])
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 600,
            "temperature": 0.1
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
            except Exception as e:
                print(f"🔄 AI Analysis attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    return f"AI Analysis failed after {max_retries} attempts: {str(e)}"
                time.sleep(2 ** attempt)  # Exponential backoff

    def tool_google_safe_browsing(self, url):
        """Tool: Google Safe Browsing API Check"""
        print("\n🛡️ TOOL: Google Safe Browsing Check")
        self.tools_used.append("Google Safe Browsing")
        
        if not GOOGLE_SAFE_BROWSING_API_KEY:
            print("❌ API key missing")
            return {"status": "API key missing", "threats": [], "score": 0}
            
        try:
            response = requests.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}",
                json={
                    "client": {"clientId": "scam-investigator", "clientVersion": "2.0"},
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
            
            score = 90 if threats else 0  # High score if threats found
            
            if threats:
                print(f"⛔ THREATS DETECTED: {len(threats)} threat(s)")
                for threat in threats:
                    print(f"   - {threat.get('threatType', 'Unknown threat')}")
            else:
                print("✅ No threats found")
                
            return {"status": "success", "threats": threats, "score": score}
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"status": f"error: {str(e)}", "threats": [], "score": 0}

    def tool_domain_analysis(self, url):
        """Tool: Advanced Domain Analysis"""
        print("\n🌐 TOOL: Domain Analysis")
        self.tools_used.append("Domain Analysis")
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            analysis = {
                "domain": domain,
                "suspicious_keywords": [],
                "character_analysis": {},
                "whois_info": {},
                "score": 0
            }
            
            # Enhanced suspicious keywords
            suspicious_keywords = [
                'paypal', 'apple', 'microsoft', 'amazon', 'google', 'facebook', 'instagram',
                'login', 'verify', 'secure', 'account', 'update', 'suspended', 'blocked',
                'urgent', 'immediate', 'confirm', 'banking', 'security', 'validation',
                'support', 'service', 'official', 'customer', 'help', 'team'
            ]
            
            # Brand impersonation detection
            brand_keywords = ['paypal', 'apple', 'microsoft', 'amazon', 'google', 'facebook']
            for keyword in suspicious_keywords:
                if keyword in domain:
                    # Check if it's legitimate (exact match or proper subdomain)
                    if not (domain == keyword + '.com' or domain.startswith(keyword + '.') or domain.endswith('.' + keyword + '.com')):
                        analysis["suspicious_keywords"].append(keyword)
                        if keyword in brand_keywords:
                            analysis["score"] += 25  # High score for brand impersonation
                        else:
                            analysis["score"] += 10
            
            # Character analysis
            char_analysis = {
                "has_hyphens": '-' in domain,
                "hyphen_count": domain.count('-'),
                "has_numbers": any(c.isdigit() for c in domain),
                "number_count": sum(1 for c in domain if c.isdigit()),
                "length": len(domain),
                "subdomain_count": len(domain.split('.')) - 2,
                "has_suspicious_tld": domain.split('.')[-1] in ['tk', 'ml', 'ga', 'cf', 'click', 'download']
            }
            
            analysis["character_analysis"] = char_analysis
            
            # Scoring based on character analysis
            if char_analysis["has_hyphens"] and char_analysis["has_numbers"]:
                analysis["score"] += 15
            if char_analysis["hyphen_count"] > 2:
                analysis["score"] += 10
            if char_analysis["length"] > 25:
                analysis["score"] += 10
            if char_analysis["subdomain_count"] > 2:
                analysis["score"] += 15
            if char_analysis["has_suspicious_tld"]:
                analysis["score"] += 20
            
            # WHOIS analysis
            try:
                print("🔍 Performing WHOIS lookup...")
                w = whois.whois(domain)
                if w:
                    whois_data = {
                        "creation_date": str(w.creation_date) if w.creation_date else None,
                        "registrar": str(w.registrar) if w.registrar else None,
                        "country": str(w.country) if w.country else None,
                        "name_servers": w.name_servers if w.name_servers else None
                    }
                    analysis["whois_info"] = whois_data
                    
                    # Check if domain is very new (less than 30 days)
                    if w.creation_date:
                        try:
                            if isinstance(w.creation_date, list):
                                creation_date = w.creation_date[0]
                            else:
                                creation_date = w.creation_date
                            
                            days_old = (datetime.now() - creation_date).days
                            if days_old < 30:
                                analysis["score"] += 25
                                print(f"⚠️ Domain is only {days_old} days old")
                            elif days_old < 90:
                                analysis["score"] += 15
                                print(f"⚠️ Domain is {days_old} days old (relatively new)")
                        except:
                            pass
            except Exception as e:
                analysis["whois_info"] = {"error": f"WHOIS lookup failed: {str(e)}"}
            
            print(f"📊 Domain Analysis Score: {analysis['score']}/100")
            return analysis
            
        except Exception as e:
            return {"error": str(e), "score": 0}

    def tool_content_analysis(self, url, extracted_results=None):
        """Tool: Website Content Analysis"""
        print("\n📄 TOOL: Content Analysis")
        self.tools_used.append("Content Analysis")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = {
                "title": soup.title.string if soup.title else "",
                "text_content": soup.get_text()[:3000],  # Increased limit
                "forms": [],
                "links": [],
                "images": [],
                "meta_info": {},
                "score": 0
            }
            
            # Enhanced form analysis
            for form in soup.find_all('form'):
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', ''),
                    "inputs": []
                }
                
                for inp in form.find_all('input'):
                    input_type = inp.get('type', 'text')
                    input_name = inp.get('name', '')
                    form_data["inputs"].append({"type": input_type, "name": input_name})
                
                content["forms"].append(form_data)
                
                # Score based on form content
                if any(inp["type"] == "password" for inp in form_data["inputs"]):
                    content["score"] += 20
                    print("⚠️ Password input form detected")
                
                # Look for credit card or personal info fields
                sensitive_fields = ['credit', 'card', 'ssn', 'social', 'passport', 'license']
                for inp in form_data["inputs"]:
                    if any(field in inp["name"].lower() for field in sensitive_fields):
                        content["score"] += 15
                        print(f"⚠️ Sensitive field detected: {inp['name']}")
            
            # Analyze text content for scam indicators
            text_lower = content["text_content"].lower()
            scam_phrases = [
                'verify your account', 'suspended', 'urgent action required',
                'click here immediately', 'limited time offer', 'act now',
                'congratulations you have won', 'claim your prize',
                'update your information', 'confirm your identity',
                'unusual activity', 'security alert', 'account locked'
            ]
            
            phrase_count = 0
            for phrase in scam_phrases:
                if phrase in text_lower:
                    phrase_count += 1
                    print(f"⚠️ Scam phrase detected: '{phrase}'")
            
            content["score"] += phrase_count * 8
            
            # Use AI for advanced content analysis
            if TOGETHER_API_KEY and content["text_content"]:
                ai_prompt = f"""
                Analyze this website content for scam indicators:
                
                Title: {content['title']}
                Content Preview: {content['text_content'][:1000]}
                Number of forms: {len(content['forms'])}
                
                Rate the likelihood this is a scam based on:
                1. Language patterns (urgency, fear tactics, too-good-to-be-true claims)
                2. Grammar and spelling quality
                3. Legitimacy of offers or claims
                4. Professional presentation vs amateur appearance
                
                Provide a score from 0-100 and explain key findings.
                """
                
                ai_analysis = self.ai_analysis(ai_prompt, "content_analysis")
                content["ai_analysis"] = ai_analysis
                
                # Extract score from AI analysis if possible
                try:
                    import re
                    score_match = re.search(r'score[:\s]*(\d+)', ai_analysis.lower())
                    if score_match:
                        ai_score = int(score_match.group(1))
                        content["score"] += min(ai_score // 2, 30)  # Add up to 30 points from AI
                except:
                    pass
            
            print(f"📊 Content Analysis Score: {content['score']}/100")
            return content
            
        except Exception as e:
            print(f"❌ Content analysis failed: {str(e)}")
            return {"error": str(e), "score": 0}

    def tool_image_ai_detection(self, image_url):
        """Tool: AI-Generated Image Detection"""
        print("\n🖼️ TOOL: AI-Generated Image Detection")
        self.tools_used.append("AI Image Detection")
        
        if not image_url:
            return {"status": "No image URL provided", "score": 0}
        
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Basic image analysis
            image_analysis = {
                "url": image_url,
                "size": len(response.content),
                "content_type": response.headers.get('content-type', ''),
                "score": 0,
                "findings": []
            }
            
            # Use AI to analyze the image for generation artifacts
            if TOGETHER_API_KEY:
                ai_prompt = f"""
                Analyze this image for signs of AI generation or manipulation:
                
                Image URL: {image_url}
                File size: {image_analysis['size']} bytes
                Content type: {image_analysis['content_type']}
                
                Look for common AI-generated image artifacts:
                1. Unnatural skin textures or lighting
                2. Inconsistent background elements
                3. Impossible geometry or perspectives
                4. Repetitive patterns or textures
                5. Artificial-looking eyes or facial features
                6. Inconsistent shadows or reflections
                
                Rate the likelihood this image is AI-generated (0-100) and explain your reasoning.
                Focus on technical artifacts rather than content appropriateness.
                """
                
                ai_result = self.ai_analysis(ai_prompt, "ai_generated")
                image_analysis["ai_analysis"] = ai_result
                
                # Extract confidence score
                try:
                    import re
                    confidence_match = re.search(r'(\d+)(?:%|\s*out\s*of\s*100|\s*likelihood)', ai_result.lower())
                    if confidence_match:
                        confidence = int(confidence_match.group(1))
                        if confidence > 70:
                            image_analysis["score"] = 25
                            image_analysis["findings"].append(f"High AI generation likelihood: {confidence}%")
                        elif confidence > 40:
                            image_analysis["score"] = 15
                            image_analysis["findings"].append(f"Moderate AI generation likelihood: {confidence}%")
                except:
                    pass
            
            print(f"📊 AI Image Detection Score: {image_analysis['score']}/100")
            return image_analysis
            
        except Exception as e:
            print(f"❌ AI image detection failed: {str(e)}")
            return {"error": str(e), "score": 0}

    def tool_deepfake_detection(self, image_url):
        """Tool: Deepfake Detection"""
        print("\n🎭 TOOL: Deepfake Detection")
        self.tools_used.append("Deepfake Detection")
        
        if not image_url:
            return {"status": "No image URL provided", "score": 0}
        
        try:
            deepfake_analysis = {
                "url": image_url,
                "score": 0,
                "findings": []
            }
            
            if TOGETHER_API_KEY:
                ai_prompt = f"""
                Analyze this image for signs of deepfake manipulation or face swapping:
                
                Image URL: {image_url}
                
                Look for deepfake indicators:
                1. Inconsistent facial features or proportions
                2. Unnatural eye movements or blinking patterns
                3. Mismatched skin tones between face and neck/body
                4. Inconsistent lighting on facial features
                5. Artifacts around face edges or hairline
                6. Unnatural facial expressions or micro-expressions
                7. Inconsistent image quality between face and background
                
                Rate the likelihood this is a deepfake (0-100) and explain specific technical indicators you observe.
                """
                
                ai_result = self.ai_analysis(ai_prompt, "deepfake")
                deepfake_analysis["ai_analysis"] = ai_result
                
                # Extract confidence score
                try:
                    import re
                    confidence_match = re.search(r'(\d+)(?:%|\s*out\s*of\s*100|\s*likelihood)', ai_result.lower())
                    if confidence_match:
                        confidence = int(confidence_match.group(1))
                        if confidence > 80:
                            deepfake_analysis["score"] = 30
                            deepfake_analysis["findings"].append(f"High deepfake likelihood: {confidence}%")
                        elif confidence > 50:
                            deepfake_analysis["score"] = 20
                            deepfake_analysis["findings"].append(f"Moderate deepfake likelihood: {confidence}%")
                except:
                    pass
            
            print(f"📊 Deepfake Detection Score: {deepfake_analysis['score']}/100")
            return deepfake_analysis
            
        except Exception as e:
            print(f"❌ Deepfake detection failed: {str(e)}")
            return {"error": str(e), "score": 0}

    def conduct_investigation(self, gemini_response):
        """Main investigation orchestrator - accepts JSON dict or string"""
        print("🕵️ STARTING COMPREHENSIVE SCAM INVESTIGATION")
        print("=" * 70)
        
        # Handle both JSON dict and string inputs
        if isinstance(gemini_response, str):
            # Parse string to JSON
            gemini_data = self.parse_gemini_response(gemini_response)
            if not gemini_data:
                return {"error": "Failed to parse Gemini response", "probability": 0}
        elif isinstance(gemini_response, dict):
            # Already a dict, use directly
            gemini_data = gemini_response
        else:
            return {"error": "Invalid input type. Expected string or dict", "probability": 0}
        
        url = gemini_data.get('url')
        extracted_results = gemini_data.get('results')
        image_url = gemini_data.get('image')
        
        print(f"🎯 Target URL: {url}")
        print(f"📋 Extracted Results Available: {'Yes' if extracted_results else 'No'}")
        print(f"🖼️ Image URL Available: {'Yes' if image_url else 'No'}")
        
        # Decide which tools to use based on available data
        print("\n🧠 DECISION: Selecting appropriate investigation tools...")
        
        selected_tools = []
        if url:
            selected_tools.extend(["Google Safe Browsing", "Domain Analysis", "Content Analysis"])
        if image_url:
            selected_tools.extend(["AI Image Detection", "Deepfake Detection"])
        
        print(f"🔧 Selected Tools: {', '.join(selected_tools)}")
        
        # Execute tools
        tool_results = {}
        
        if "Google Safe Browsing" in selected_tools:
            tool_results["safe_browsing"] = self.tool_google_safe_browsing(url)
        
        if "Domain Analysis" in selected_tools:
            tool_results["domain_analysis"] = self.tool_domain_analysis(url)
        
        if "Content Analysis" in selected_tools:
            tool_results["content_analysis"] = self.tool_content_analysis(url, extracted_results)
        
        if "AI Image Detection" in selected_tools:
            tool_results["ai_image_detection"] = self.tool_image_ai_detection(image_url)
        
        if "Deepfake Detection" in selected_tools:
            tool_results["deepfake_detection"] = self.tool_deepfake_detection(image_url)
        
        # Store results
        self.investigation_data = {
            "gemini_data": gemini_data,
            "tool_results": tool_results,
            "tools_used": self.tools_used
        }
        
        # Calculate final probability
        final_probability = self.calculate_final_probability(tool_results)
        
        # Generate comprehensive report
        self.generate_final_report(url, final_probability, tool_results)
        
        return {
            "url": url,
            "probability": final_probability,
            "tools_used": self.tools_used,
            "investigation_data": self.investigation_data
        }

    def calculate_final_probability(self, tool_results):
        """Calculate final scam probability using weighted scoring"""
        print(f"\n🧮 CALCULATING FINAL SCAM PROBABILITY")
        print("-" * 50)
        
        total_score = 0
        max_possible_score = 0
        decision_factors = []
        
        # Weight different tools based on reliability
        tool_weights = {
            "safe_browsing": 0.35,      # Highest weight - authoritative source
            "domain_analysis": 0.25,    # High weight - strong indicators
            "content_analysis": 0.25,   # High weight - behavioral patterns
            "ai_image_detection": 0.10, # Lower weight - supplementary
            "deepfake_detection": 0.15  # Medium weight - trust indicator
        }
        
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "score" in result:
                score = result["score"]
                weight = tool_weights.get(tool_name, 0.1)
                weighted_score = score * weight
                total_score += weighted_score
                max_possible_score += 100 * weight
                
                print(f"📊 {tool_name.replace('_', ' ').title()}: {score}/100 (weight: {weight}) = {weighted_score:.1f}")
                
                if score > 0:
                    decision_factors.append(f"{tool_name}: {score} points")
        
        # Calculate percentage
        if max_possible_score > 0:
            probability = min(int((total_score / max_possible_score) * 100), 100)
        else:
            probability = 0
        
        print(f"\n🎯 TOTAL WEIGHTED SCORE: {total_score:.1f}/{max_possible_score:.1f}")
        print(f"🎯 FINAL SCAM PROBABILITY: {probability}%")
        
        self.final_scam_probability = probability
        self.decision_factors = decision_factors
        
        return probability

    def generate_final_report(self, url, probability, tool_results):
        """Generate comprehensive final report"""
        print("\n" + "=" * 70)
        print("📋 COMPREHENSIVE INVESTIGATION REPORT")
        print("=" * 70)
        
        # Risk categorization
        if probability >= 80:
            risk_level = "🔴 EXTREME RISK"
            recommendation = "⛔ DEFINITELY AVOID - Strong indicators of scam"
        elif probability >= 60:
            risk_level = "🟠 HIGH RISK"
            recommendation = "⚠️ LIKELY SCAM - Avoid and report"
        elif probability >= 40:
            risk_level = "🟡 MODERATE RISK"
            recommendation = "⚠️ SUSPICIOUS - Exercise extreme caution"
        elif probability >= 20:
            risk_level = "🟢 LOW RISK"
            recommendation = "✅ PROBABLY SAFE - Minor concerns detected"
        else:
            risk_level = "🟢 MINIMAL RISK"
            recommendation = "✅ LIKELY LEGITIMATE - No significant red flags"
        
        print(f"🌐 URL: {url}")
        print(f"🎯 SCAM PROBABILITY: {probability}% ")
        print(f"🚨 RISK LEVEL: {risk_level}")
        print(f"💡 RECOMMENDATION: {recommendation}")
        print(f"🔧 TOOLS USED: {', '.join(self.tools_used)}")
        
        # Tool-by-tool breakdown
        print(f"\n📊 DETAILED TOOL ANALYSIS:")
        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                score = result.get("score", 0)
                status = result.get("status", "Completed")
                print(f"   • {tool_name.replace('_', ' ').title()}: {score}/100 - {status}")
        
        # Key findings
        if self.decision_factors:
            print(f"\n🔍 KEY DECISION FACTORS:")
            for factor in self.decision_factors:
                print(f"   • {factor}")
        
        print("\n" + "=" * 70)

def scam_agent(gemini_response):
    """
    Scam investigation function that takes Gemini JSON response as parameter
    
    Args:
        gemini_response (str): JSON string from Gemini LLM
        
    Returns:
        dict: Investigation results with probability and analysis
    """
    if not TOGETHER_API_KEY:
        print("⚠️ Warning: TOGETHER_API_KEY not set. AI-powered analysis will be limited.")
    
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        print("⚠️ Warning: GOOGLE_SAFE_BROWSING_API_KEY not set. Safe Browsing check will be skipped.")
    
    print("🕵️ Advanced Scam Investigation Agent")
    print(f"📥 Processing Gemini response: {gemini_response.text[:100]}...")
    
    agent = ScamInvestigationAgent()
    
    try:
        result = agent.conduct_investigation(gemini_response)
        
        if result.get("error"):
            print(f"❌ Investigation failed: {result['error']}")
            return result
        else:
            print(f"\n🎯 INVESTIGATION COMPLETE")
            print(f"📊 Final Scam Probability: {result['probability']}%")
            return result
            
    except Exception as e:
        error_msg = f"Investigation failed: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg, "probability": 0}

if __name__ == "__main__":
    scam_agent()