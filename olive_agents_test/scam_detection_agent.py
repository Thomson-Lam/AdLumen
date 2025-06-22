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
import io
from PIL import Image
import hashlib

# Configuration
TOGETHER_API_KEY = ""  # Replace with your Together.ai API key
GOOGLE_SAFE_BROWSING_API_KEY = ""  # Replace with your Google Safe Browsing API key

TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
ORCHESTRATOR_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
DEEPFAKE_MODEL = "microsoft/DialoGPT-medium"  # Placeholder - replace with actual deepfake detection model

class RateLimiter:
    """Rate limiter to ensure we don't exceed 60 RPM for Together.ai API"""
    def __init__(self, max_requests=55, time_window=60):  # Buffer of 5 requests
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = Lock()
        self.request_count = 0
    
    def wait_if_needed(self):
        with self.lock:
            now = datetime.now()
            # Remove requests older than time_window
            self.requests = [req_time for req_time in self.requests 
                           if (now - req_time).total_seconds() < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request).total_seconds()
                if wait_time > 0:
                    print(f"⏳ Rate limit approaching, waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time + 1)
            
            self.requests.append(now)
            self.request_count += 1

class InvestigationTool:
    """Base class for investigation tools"""
    def __init__(self, name, description, cost=1):
        self.name = name
        self.description = description
        self.cost = cost  # API call cost (for rate limiting)
    
    def execute(self, *args, **kwargs):
        raise NotImplementedError

class SafeBrowsingTool(InvestigationTool):
    def __init__(self):
        super().__init__(
            "safe_browsing",
            "Check URL against Google Safe Browsing database for known threats",
            cost=0  # External API, no Together.ai cost
        )
    
    def execute(self, url):
        """Check Google Safe Browsing API"""
        if not GOOGLE_SAFE_BROWSING_API_KEY:
            return {
                "status": "error",
                "message": "API key missing",
                "threats": [],
                "confidence": 0
            }
            
        try:
            response = requests.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}",
                json={
                    "client": {"clientId": "scam-investigator", "clientVersion": "2.0"},
                    "threatInfo": {
                        "threatTypes": [
                            "MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", 
                            "POTENTIALLY_HARMFUL_APPLICATION"
                        ],
                        "platformTypes": ["ANY_PLATFORM"],
                        "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": url}]
                    }
                },
                timeout=10
            )
            result = response.json()
            threats = result.get('matches', [])
            
            return {
                "status": "success",
                "threats": threats,
                "threat_count": len(threats),
                "confidence": 95 if threats else 10,
                "details": {threat.get('threatType'): threat for threat in threats}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "threats": [],
                "confidence": 0
            }

class DomainAnalysisTool(InvestigationTool):
    def __init__(self):
        super().__init__(
            "domain_analysis",
            "Analyze domain characteristics, WHOIS data, and suspicious patterns",
            cost=0
        )
    
    def execute(self, url):
        """Comprehensive domain analysis"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            analysis = {
                "status": "success",
                "domain": domain,
                "suspicious_keywords": [],
                "character_analysis": {},
                "whois_info": {},
                "risk_indicators": [],
                "confidence": 50
            }
            
            # Enhanced suspicious keyword detection
            brand_keywords = [
                'paypal', 'apple', 'microsoft', 'amazon', 'google', 'facebook',
                'instagram', 'twitter', 'netflix', 'spotify', 'adobe', 'dropbox'
            ]
            
            action_keywords = [
                'login', 'verify', 'secure', 'account', 'update', 'suspended',
                'urgent', 'immediate', 'confirm', 'banking', 'security', 'warning'
            ]
            
            all_keywords = brand_keywords + action_keywords
            
            for keyword in all_keywords:
                if keyword in domain:
                    # Check if it's not the legitimate domain
                    if not (domain == keyword + '.com' or domain.startswith(keyword + '.')):
                        analysis["suspicious_keywords"].append({
                            "keyword": keyword,
                            "type": "brand" if keyword in brand_keywords else "action",
                            "position": domain.find(keyword)
                        })
            
            # Enhanced character analysis
            char_analysis = {
                "has_hyphens": '-' in domain,
                "hyphen_count": domain.count('-'),
                "has_numbers": any(c.isdigit() for c in domain),
                "number_count": sum(1 for c in domain if c.isdigit()),
                "length": len(domain),
                "subdomain_count": len(domain.split('.')) - 2,
                "has_mixed_case": domain != domain.lower(),
                "special_chars": len([c for c in domain if not c.isalnum() and c not in '.-'])
            }
            analysis["character_analysis"] = char_analysis
            
            # Risk indicators based on domain structure
            if char_analysis["hyphen_count"] > 2:
                analysis["risk_indicators"].append("Multiple hyphens in domain")
            
            if char_analysis["length"] > 25:
                analysis["risk_indicators"].append("Unusually long domain")
            
            if char_analysis["subdomain_count"] > 2:
                analysis["risk_indicators"].append("Multiple subdomains")
            
            # WHOIS analysis
            try:
                w = whois.whois(domain)
                if w:
                    whois_data = {
                        "creation_date": str(w.creation_date) if w.creation_date else None,
                        "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                        "registrar": str(w.registrar) if w.registrar else None,
                        "country": str(w.country) if w.country else None,
                        "name_servers": w.name_servers if w.name_servers else []
                    }
                    analysis["whois_info"] = whois_data
                    
                    # Check domain age
                    if w.creation_date:
                        try:
                            if isinstance(w.creation_date, list):
                                creation_date = w.creation_date[0]
                            else:
                                creation_date = w.creation_date
                            
                            days_old = (datetime.now() - creation_date).days
                            if days_old < 30:
                                analysis["risk_indicators"].append(f"Very new domain ({days_old} days old)")
                            elif days_old < 90:
                                analysis["risk_indicators"].append(f"Recently created domain ({days_old} days old)")
                        except:
                            pass
            except Exception as e:
                analysis["whois_info"] = {"error": f"WHOIS lookup failed: {str(e)}"}
            
            # Calculate confidence based on findings
            confidence = 50
            if analysis["suspicious_keywords"]:
                confidence += len(analysis["suspicious_keywords"]) * 15
            if analysis["risk_indicators"]:
                confidence += len(analysis["risk_indicators"]) * 10
            
            analysis["confidence"] = min(confidence, 95)
            
            return analysis
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "confidence": 0
            }

class ContentAnalysisTool(InvestigationTool):
    def __init__(self):
        super().__init__(
            "content_analysis",
            "Fetch and analyze website content, structure, and behavior",
            cost=0
        )
    
    def execute(self, url):
        """Comprehensive content analysis"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            # Track redirects
            redirect_chain = [resp.url for resp in response.history] + [response.url]
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements for text analysis
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = {
                "status": "success",
                "url": response.url,
                "status_code": response.status_code,
                "redirect_chain": redirect_chain,
                "title": soup.title.string.strip() if soup.title else "",
                "text_content": soup.get_text()[:3000],  # Increased limit
                "forms": [],
                "links": [],
                "images": [],
                "meta_info": {},
                "security_headers": {},
                "suspicious_elements": [],
                "confidence": 70
            }
            
            # Analyze security headers
            security_headers = {
                "https": response.url.startswith('https://'),
                "strict_transport_security": 'strict-transport-security' in response.headers,
                "content_security_policy": 'content-security-policy' in response.headers,
                "x_frame_options": 'x-frame-options' in response.headers
            }
            content["security_headers"] = security_headers
            
            # Enhanced form analysis
            for form in soup.find_all('form'):
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', 'get').lower(),
                    "inputs": [],
                    "suspicious": False
                }
                
                for inp in form.find_all('input'):
                    input_type = inp.get('type', 'text').lower()
                    input_name = inp.get('name', '').lower()
                    form_data["inputs"].append({
                        "type": input_type,
                        "name": input_name,
                        "required": inp.get('required') is not None
                    })
                    
                    # Check for suspicious patterns
                    if input_type in ['password', 'email'] or 'password' in input_name:
                        form_data["suspicious"] = True
                
                content["forms"].append(form_data)
            
            # Analyze links
            external_links = []
            internal_links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    if urlparse(href).netloc != urlparse(url).netloc:
                        external_links.append(href)
                    else:
                        internal_links.append(href)
            
            content["links"] = {
                "external": external_links[:10],
                "internal": internal_links[:10],
                "external_count": len(external_links),
                "internal_count": len(internal_links)
            }
            
            # Image analysis
            images = []
            for img in soup.find_all('img', src=True):
                img_src = img['src']
                if not img_src.startswith('data:'):  # Skip data URLs
                    images.append({
                        "src": img_src,
                        "alt": img.get('alt', ''),
                        "width": img.get('width'),
                        "height": img.get('height')
                    })
            content["images"] = images[:10]
            
            # Meta information
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                if name and meta.get('content'):
                    content["meta_info"][name] = meta.get('content')
            
            # Check for suspicious elements
            suspicious_patterns = [
                "urgent", "immediate", "suspended", "verify now", "click here",
                "limited time", "act now", "confirm identity", "update payment"
            ]
            
            text_lower = content["text_content"].lower()
            for pattern in suspicious_patterns:
                if pattern in text_lower:
                    content["suspicious_elements"].append(f"Suspicious text: '{pattern}'")
            
            # Check for multiple redirects (common in phishing)
            if len(redirect_chain) > 3:
                content["suspicious_elements"].append(f"Multiple redirects: {len(redirect_chain)}")
            
            # Adjust confidence based on findings
            if content["suspicious_elements"]:
                content["confidence"] += len(content["suspicious_elements"]) * 5
            if any(form["suspicious"] for form in content["forms"]):
                content["confidence"] += 20
            
            content["confidence"] = min(content["confidence"], 95)
            
            return content
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "confidence": 0
            }

# Also enhance the DeepfakeDetectionTool to analyze more images
class DeepfakeDetectionTool(InvestigationTool):
    def __init__(self):
        super().__init__(
            "deepfake_detection",
            "Analyze images and videos for deepfake/AI-generated content",
            cost=1  # Uses Together.ai API
        )
    
    def execute(self, images_data, rate_limiter):
        """Detect deepfakes in images - enhanced version"""
        if not images_data or not TOGETHER_API_KEY:
            return {
                "status": "skipped",
                "message": "No images provided or API key missing",
                "confidence": 0
            }
        
        results = {
            "status": "success",
            "analyzed_images": 0,
            "deepfake_detected": False,
            "suspicious_images": [],
            "confidence": 30,
            "analysis_details": []
        }
        
        try:
            # Analyze up to 5 images instead of 3
            max_images = min(5, len(images_data))
            print(f"   📊 Analyzing {max_images} images for deepfake content...")
            
            for i, image_info in enumerate(images_data[:max_images]):
                rate_limiter.wait_if_needed()
                
                # Download and analyze image
                img_url = image_info.get('src', '')
                if not img_url.startswith('http'):
                    continue
                
                try:
                    print(f"   🖼️ Analyzing image {i+1}/{max_images}: {img_url[:50]}...")
                    img_response = requests.get(img_url, timeout=10)
                    img_response.raise_for_status()
                    
                    # Enhanced analysis with URL context
                    analysis_result = self._analyze_image_for_deepfake(
                        img_response.content, 
                        rate_limiter, 
                        img_url,
                        image_info.get('alt', '')
                    )
                    
                    results["analysis_details"].append({
                        "url": img_url,
                        "result": analysis_result
                    })
                    
                    if analysis_result.get('suspicious', False):
                        results["suspicious_images"].append({
                            "url": img_url,
                            "reason": analysis_result.get('reason', 'Unknown'),
                            "confidence": analysis_result.get('confidence', 50),
                            "alt_text": image_info.get('alt', '')
                        })
                        results["deepfake_detected"] = True
                    
                    results["analyzed_images"] += 1
                    
                except Exception as e:
                    print(f"   ❌ Failed to analyze image {i+1}: {str(e)}")
                    continue
            
            # Adjust overall confidence based on results
            if results["deepfake_detected"]:
                results["confidence"] = 85
                print(f"   🚨 Potential deepfakes detected in {len(results['suspicious_images'])} images")
            elif results["analyzed_images"] > 0:
                results["confidence"] = 60
                print(f"   ✅ No deepfakes detected in {results['analyzed_images']} images")
            else:
                print(f"   ⚠️ No images could be analyzed")
            
            return results
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "confidence": 0
            }
    
    def _analyze_image_for_deepfake(self, image_data, rate_limiter, img_url="", alt_text=""):
        """Enhanced deepfake detection with context"""
        try:
            # Enhanced prompt with more specific deepfake indicators
            prompt = f"""
            Analyze this image for potential deepfake or AI-generated characteristics.
            
            Context:
            - Image URL: {img_url}
            - Alt text: {alt_text}
            
            Look for specific deepfake indicators:
            1. Facial inconsistencies: asymmetrical features, unnatural eye alignment
            2. Temporal inconsistencies: lighting that doesn't match across face
            3. Artifacts: pixelation around face edges, unnatural skin texture
            4. Eye anomalies: unnatural reflections, inconsistent gaze direction
            5. Hair/background blending issues
            6. Compression artifacts typical of GAN-generated images
            7. Unnatural facial expressions or micro-expressions
            8. Inconsistent aging markers across the face
            
            Consider the context - if this is from an article about deepfakes, it may contain examples.
            
            Respond with JSON:
            {{
                "suspicious": true/false,
                "confidence": 0-100,
                "reason": "specific explanation if suspicious",
                "deepfake_indicators": ["list of specific indicators found"],
                "likely_ai_generated": true/false
            }}
            """
            
            headers = {
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": ORCHESTRATOR_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert in deepfake detection with extensive knowledge of AI-generated image artifacts and inconsistencies. Be thorough in your analysis."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.1
            }
            
            response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # Try to parse JSON response
                try:
                    parsed_result = json.loads(ai_response)
                    return parsed_result
                except:
                    # Fallback if JSON parsing fails
                    suspicious_keywords = ['suspicious', 'artificial', 'generated', 'fake', 'deepfake', 'synthetic']
                    is_suspicious = any(keyword in ai_response.lower() for keyword in suspicious_keywords)
                    
                    return {
                        "suspicious": is_suspicious,
                        "confidence": 60 if is_suspicious else 40,
                        "reason": ai_response[:100] if is_suspicious else "Analysis completed, no clear indicators",
                        "deepfake_indicators": [],
                        "likely_ai_generated": is_suspicious
                    }
            
        except Exception as e:
            print(f"   ⚠️ AI analysis failed: {str(e)}")
            pass
        
        return {
            "suspicious": False,
            "confidence": 30,
            "reason": "Analysis failed - could not determine",
            "deepfake_indicators": [],
            "likely_ai_generated": False
        }

class TextAnalysisTool(InvestigationTool):
    def __init__(self):
        super().__init__(
            "text_analysis",
            "Analyze website text for scam patterns, social engineering, and deceptive language",
            cost=1
        )
    
    def execute(self, text_content, rate_limiter):
        """AI-powered text analysis for scam indicators"""
        if not text_content or not TOGETHER_API_KEY:
            return {
                "status": "skipped",
                "message": "No text content or API key missing",
                "confidence": 0
            }
        
        rate_limiter.wait_if_needed()
        
        prompt = f"""
        Analyze this website text for scam and phishing indicators:
        
        TEXT: {text_content[:1500]}
        
        Look for:
        1. Urgency tactics ("act now", "limited time")
        2. Fear tactics ("account suspended", "security breach")
        3. Social engineering techniques
        4. Grammar/spelling errors indicating non-native speakers
        5. Too-good-to-be-true offers
        6. Requests for personal/financial information
        7. Impersonation of legitimate brands
        
        Respond with JSON:
        {{
            "scam_likelihood": "low/medium/high",
            "confidence": 0-100,
            "red_flags": ["list of specific issues found"],
            "social_engineering_tactics": ["list of tactics used"],
            "overall_assessment": "brief summary"
        }}
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": ORCHESTRATOR_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a cybersecurity expert specializing in scam and phishing detection through text analysis."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 400,
                "temperature": 0.1
            }
            
            response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            try:
                parsed_result = json.loads(ai_response)
                parsed_result["status"] = "success"
                return parsed_result
            except json.JSONDecodeError:
                # Fallback parsing
                return {
                    "status": "success",
                    "scam_likelihood": "medium",
                    "confidence": 60,
                    "red_flags": ["AI analysis completed but format unclear"],
                    "social_engineering_tactics": [],
                    "overall_assessment": ai_response[:200],
                    "raw_response": ai_response
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "confidence": 0
            }

class InvestigationOrchestrator:
    """AI orchestrator that decides which tools to use based on initial analysis"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.tools = {
            "safe_browsing": SafeBrowsingTool(),
            "domain_analysis": DomainAnalysisTool(),
            "content_analysis": ContentAnalysisTool(),
            "deepfake_detection": DeepfakeDetectionTool(),
            "text_analysis": TextAnalysisTool()
        }
        self.investigation_results = {}
      
    # Add this method to the InvestigationOrchestrator class

    def plan_investigation(self, url, initial_scan=None):
        """AI decides which tools to use based on initial analysis"""
        if not TOGETHER_API_KEY:
            # Enhanced fallback plan
            return {
                "tools_to_use": ["safe_browsing", "domain_analysis", "content_analysis", "deepfake_detection", "text_analysis"],
                "reasoning": "Default comprehensive investigation plan (no AI orchestrator)",
                "priority": "medium"
            }
        
        self.rate_limiter.wait_if_needed()
        
        # Enhanced context with deepfake-specific triggers
        deepfake_triggers = [
            'deepfake', 'ai-generated', 'synthetic', 'face-swap', 'fake-video',
            'artificial', 'generated', 'manipulated', 'synthetic-media'
        ]
        
        url_lower = url.lower()
        has_deepfake_keywords = any(trigger in url_lower for trigger in deepfake_triggers)
        
        context = f"""
        URL to investigate: {url}
        
        IMPORTANT: This URL contains deepfake-related keywords: {has_deepfake_keywords}
        Deepfake triggers found: {[t for t in deepfake_triggers if t in url_lower]}
        
        Available investigation tools:
        1. safe_browsing: Check against Google's threat database (fast, free)
        2. domain_analysis: Analyze domain structure and WHOIS data (fast, free) 
        3. content_analysis: Fetch and analyze website content (medium speed, free)
        4. deepfake_detection: Analyze images for AI-generated content (slow, costs API calls) - CRITICAL for deepfake-related URLs
        5. text_analysis: AI analysis of website text for scam patterns (medium speed, costs API calls)
        
        PRIORITY RULES:
        - If URL contains deepfake-related terms, ALWAYS include 'deepfake_detection'
        - Educational/news sites about deepfakes should still be analyzed for actual deepfake content
        - Creative/design sites may contain examples that need verification
        
        Consider:
        - Budget: We have limited API calls but deepfake detection is important for relevant URLs
        - Speed: Some tools are faster than others
        - Relevance: Deepfake detection is highly relevant for this URL type
        
        Based on the URL, decide which tools to use and in what order.
        """
        
        if initial_scan:
            context += f"\nInitial scan results: {json.dumps(initial_scan, indent=2)}"
        
        prompt = f"""
        {context}
        
        Respond with JSON:
        {{
            "tools_to_use": ["list", "of", "tool", "names"],
            "reasoning": "explanation of why these tools were chosen",
            "priority": "low/medium/high", 
            "estimated_api_calls": number,
            "deepfake_analysis_warranted": true/false
        }}
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": ORCHESTRATOR_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an AI investigation orchestrator. For URLs containing deepfake-related terms, ALWAYS include deepfake_detection tool regardless of the site's legitimacy. Educational content about deepfakes should still be analyzed."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.2
            }
            
            response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            try:
                plan = json.loads(ai_response)
                # Validate the plan
                valid_tools = [tool for tool in plan.get("tools_to_use", []) if tool in self.tools]
                
                # Force include deepfake detection if URL suggests it
                if has_deepfake_keywords and "deepfake_detection" not in valid_tools:
                    valid_tools.append("deepfake_detection")
                    plan["reasoning"] += " [Auto-added deepfake detection due to URL keywords]"
                
                # Ensure content_analysis is included if deepfake_detection is used
                if "deepfake_detection" in valid_tools and "content_analysis" not in valid_tools:
                    valid_tools.insert(-1, "content_analysis")  # Add before deepfake_detection
                
                plan["tools_to_use"] = valid_tools
                return plan
            except json.JSONDecodeError:
                # Enhanced fallback plan for deepfake URLs
                if has_deepfake_keywords:
                    return {
                        "tools_to_use": ["safe_browsing", "domain_analysis", "content_analysis", "deepfake_detection", "text_analysis"],
                        "reasoning": "AI response parsing failed, using comprehensive deepfake investigation plan",
                        "priority": "high",
                        "estimated_api_calls": 4
                    }
                else:
                    return {
                        "tools_to_use": ["safe_browsing", "domain_analysis", "content_analysis"],
                        "reasoning": "AI response parsing failed, using default plan",
                        "priority": "medium",
                        "estimated_api_calls": 2
                    }
                    
        except Exception as e:
            # Enhanced fallback for deepfake URLs
            if has_deepfake_keywords:
                return {
                    "tools_to_use": ["safe_browsing", "domain_analysis", "content_analysis", "deepfake_detection", "text_analysis"],
                    "reasoning": f"AI orchestrator failed ({str(e)}), using comprehensive deepfake plan",
                    "priority": "high",
                    "estimated_api_calls": 4
                }
            else:
                return {
                    "tools_to_use": ["safe_browsing", "domain_analysis", "content_analysis"],
                    "reasoning": f"AI orchestrator failed ({str(e)}), using default plan",
                    "priority": "medium",
                    "estimated_api_calls": 2
                }
      
    def execute_investigation(self, url):
        """Main investigation pipeline"""
        print(f"🚀 Starting AI-orchestrated investigation of: {url}")
        print("=" * 70)
        
        # Step 1: Quick initial scan
        print("📊 Phase 1: Initial Assessment")
        parsed_url = urlparse(url)
        initial_scan = {
            "domain": parsed_url.netloc,
            "scheme": parsed_url.scheme,
            "has_path": bool(parsed_url.path and parsed_url.path != '/'),
            "has_query": bool(parsed_url.query)
        }
        
        # Step 2: AI decides investigation plan
        print("🤖 Phase 2: AI Planning Investigation Strategy")
        plan = self.plan_investigation(url, initial_scan)
        print(f"🎯 Investigation Plan: {plan['reasoning']}")
        print(f"🔧 Tools selected: {', '.join(plan['tools_to_use'])}")
        print(f"⚡ Priority: {plan['priority']}")
        print(f"💰 Estimated API calls: {plan.get('estimated_api_calls', 'unknown')}")
        
        # Step 3: Execute planned tools
        print("\n🔍 Phase 3: Executing Investigation Tools")
        
        for tool_name in plan["tools_to_use"]:
            tool = self.tools[tool_name]
            print(f"\n🛠️ Running {tool.name}...")
            
            try:
                if tool_name == "safe_browsing":
                    result = tool.execute(url)
                elif tool_name == "domain_analysis":
                    result = tool.execute(url)
                elif tool_name == "content_analysis":
                    result = tool.execute(url)
                elif tool_name == "deepfake_detection":
                    # Need content analysis results first
                    if "content_analysis" in self.investigation_results:
                        images = self.investigation_results["content_analysis"].get("images", [])
                        result = tool.execute(images, self.rate_limiter)
                    else:
                        result = {"status": "skipped", "message": "No content analysis available"}
                elif tool_name == "text_analysis":
                    # Need content analysis results first
                    if "content_analysis" in self.investigation_results:
                        text = self.investigation_results["content_analysis"].get("text_content", "")
                        result = tool.execute(text, self.rate_limiter)
                    else:
                        result = {"status": "skipped", "message": "No content analysis available"}
                
                self.investigation_results[tool_name] = result
                
                # Quick status update
                if result.get("status") == "success":
                    confidence = result.get("confidence", 0)
                    print(f"   ✅ Completed (confidence: {confidence}%)")
                else:
                    print(f"   ⚠️ {result.get('status', 'unknown')}: {result.get('message', 'No details')}")
                    
            except Exception as e:
                print(f"   ❌ Failed: {str(e)}")
                self.investigation_results[tool_name] = {
                    "status": "error",
                    "message": str(e),
                    "confidence": 0
                }
        
        # Step 4: Final AI analysis and risk assessment
        print("\n🧠 Phase 4: Final AI Risk Assessment")
        final_assessment = self.generate_final_assessment(url, plan)
        
        # Step 5: Generate comprehensive report
        print("\n📋 Phase 5: Generating Report")
        self.generate_comprehensive_report(url, plan, final_assessment)
        
        return {
            "url": url,
            "plan": plan,
            "results": self.investigation_results,
            "final_assessment": final_assessment
        }
    
    def generate_final_assessment(self, url, plan):
        """AI-powered final risk assessment"""
        if not TOGETHER_API_KEY:
            return self.calculate_basic_risk_score()
        
        self.rate_limiter.wait_if_needed()
        
        # Prepare comprehensive data for AI analysis
        analysis_data = {
            "url": url,
            "investigation_plan": plan,
            "tool_results": {}
        }
        
        # Summarize key findings from each tool
        for tool_name, result in self.investigation_results.items():
            if result.get("status") == "success":
                if tool_name == "safe_browsing":
                    analysis_data["tool_results"][tool_name] = {
                        "threats_found": len(result.get("threats", [])),
                        "threat_types": [t.get("threatType") for t in result.get("threats", [])],
                        "confidence": result.get("confidence", 0)
                    }
                elif tool_name == "domain_analysis":
                    analysis_data["tool_results"][tool_name] = {
                        "suspicious_keywords": result.get("suspicious_keywords", []),
                        "risk_indicators": result.get("risk_indicators", []),
                        "confidence": result.get("confidence", 0)
                    }
                elif tool_name == "content_analysis":
                    analysis_data["tool_results"][tool_name] = {
                        "suspicious_elements": result.get("suspicious_elements", []),
                        "forms_count": len(result.get("forms", [])),
                        "suspicious_forms": sum(1 for form in result.get("forms", []) if form.get("suspicious")),
                        "security_headers": result.get("security_headers", {}),
                        "confidence": result.get("confidence", 0)
                    }
                elif tool_name == "deepfake_detection":
                    analysis_data["tool_results"][tool_name] = {
                        "deepfake_detected": result.get("deepfake_detected", False),
                        "suspicious_images": len(result.get("suspicious_images", [])),
                        "confidence": result.get("confidence", 0)
                    }
                elif tool_name == "text_analysis":
                    analysis_data["tool_results"][tool_name] = {
                        "scam_likelihood": result.get("scam_likelihood", "unknown"),
                        "red_flags": result.get("red_flags", []),
                        "social_engineering_tactics": result.get("social_engineering_tactics", []),
                        "confidence": result.get("confidence", 0)
                    }
        
        prompt = f"""
        Analyze the comprehensive investigation results and provide a final risk assessment:
        
        Investigation Data:
        {json.dumps(analysis_data, indent=2)}
        
        Based on all available evidence, provide a comprehensive risk assessment:
        
        1. Calculate an overall risk score (0-100)
        2. Determine risk level (low/medium/high/critical)
        3. Identify the most significant risk factors
        4. Provide specific recommendations for users
        5. Assess the reliability of this assessment based on available data
        
        Respond with JSON:
        {{
            "overall_risk_score": 0-100,
            "risk_level": "low/medium/high/critical",
            "confidence_in_assessment": 0-100,
            "primary_risk_factors": ["list of main concerns"],
            "secondary_risk_factors": ["list of minor concerns"],
            "user_recommendation": "clear recommendation for users",
            "technical_summary": "brief technical summary for experts",
            "false_positive_likelihood": 0-100
        }}
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": ORCHESTRATOR_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a senior cybersecurity analyst providing final risk assessments. Be thorough, accurate, and consider both false positives and negatives."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }
            
            response = requests.post(TOGETHER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            try:
                assessment = json.loads(ai_response)
                assessment["method"] = "ai_powered"
                return assessment
            except json.JSONDecodeError:
                # Fallback to basic calculation with AI summary
                basic_assessment = self.calculate_basic_risk_score()
                basic_assessment["ai_summary"] = ai_response[:300]
                basic_assessment["method"] = "hybrid"
                return basic_assessment
                
        except Exception as e:
            basic_assessment = self.calculate_basic_risk_score()
            basic_assessment["ai_error"] = str(e)
            basic_assessment["method"] = "basic"
            return basic_assessment
    
    def calculate_basic_risk_score(self):
        """Fallback risk calculation when AI is unavailable"""
        score = 0
        primary_factors = []
        secondary_factors = []
        
        # Safe Browsing analysis
        if "safe_browsing" in self.investigation_results:
            sb_result = self.investigation_results["safe_browsing"]
            if sb_result.get("threats"):
                score += 80
                primary_factors.append(f"Google Safe Browsing: {len(sb_result['threats'])} threats detected")
        
        # Domain analysis
        if "domain_analysis" in self.investigation_results:
            domain_result = self.investigation_results["domain_analysis"]
            if domain_result.get("suspicious_keywords"):
                score += len(domain_result["suspicious_keywords"]) * 15
                primary_factors.append(f"Suspicious domain keywords: {len(domain_result['suspicious_keywords'])}")
            
            if domain_result.get("risk_indicators"):
                score += len(domain_result["risk_indicators"]) * 10
                secondary_factors.extend(domain_result["risk_indicators"])
        
        # Content analysis
        if "content_analysis" in self.investigation_results:
            content_result = self.investigation_results["content_analysis"]
            if content_result.get("suspicious_elements"):
                score += len(content_result["suspicious_elements"]) * 8
                secondary_factors.extend(content_result["suspicious_elements"])
            
            suspicious_forms = sum(1 for form in content_result.get("forms", []) if form.get("suspicious"))
            if suspicious_forms:
                score += suspicious_forms * 20
                primary_factors.append(f"Suspicious forms detected: {suspicious_forms}")
        
        # Text analysis
        if "text_analysis" in self.investigation_results:
            text_result = self.investigation_results["text_analysis"]
            if text_result.get("scam_likelihood") == "high":
                score += 30
                primary_factors.append("High scam likelihood from text analysis")
            elif text_result.get("scam_likelihood") == "medium":
                score += 15
                secondary_factors.append("Medium scam likelihood from text analysis")
        
        # Deepfake detection
        if "deepfake_detection" in self.investigation_results:
            deepfake_result = self.investigation_results["deepfake_detection"]
            if deepfake_result.get("deepfake_detected"):
                score += 25
                primary_factors.append("Potential deepfake/AI-generated images detected")
        
        # Determine risk level
        if score >= 80:
            risk_level = "critical"
            recommendation = "🚨 DO NOT INTERACT - This website shows multiple strong indicators of being a scam"
        elif score >= 60:
            risk_level = "high"
            recommendation = "⛔ AVOID - High risk of scam, do not provide personal information"
        elif score >= 35:
            risk_level = "medium"
            recommendation = "⚠️ CAUTION - Exercise extreme caution and verify independently"
        else:
            risk_level = "low"
            recommendation = "✅ PROCEED WITH NORMAL CAUTION - No major red flags detected"
        
        return {
            "overall_risk_score": min(score, 100),
            "risk_level": risk_level,
            "confidence_in_assessment": 75,
            "primary_risk_factors": primary_factors,
            "secondary_risk_factors": secondary_factors,
            "user_recommendation": recommendation,
            "technical_summary": f"Basic risk calculation based on {len(self.investigation_results)} tools",
            "false_positive_likelihood": 15,
            "method": "basic"
        }
    
    def generate_comprehensive_report(self, url, plan, final_assessment):
        """Generate detailed investigation report"""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE INVESTIGATION REPORT")
        print("=" * 70)
        
        # Header
        print(f"🔗 URL: {url}")
        print(f"🕐 Investigation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🤖 AI Orchestrator: {'Enabled' if TOGETHER_API_KEY else 'Disabled'}")
        print(f"📈 API Calls Used: {self.rate_limiter.request_count}")
        
        # Executive Summary
        print(f"\n🎯 EXECUTIVE SUMMARY")
        print(f"Risk Score: {final_assessment['overall_risk_score']}/100")
        print(f"Risk Level: {self._format_risk_level(final_assessment['risk_level'])}")
        print(f"Assessment Confidence: {final_assessment['confidence_in_assessment']}%")
        print(f"Recommendation: {final_assessment['user_recommendation']}")
        
        # Primary Risk Factors
        if final_assessment.get('primary_risk_factors'):
            print(f"\n🚨 PRIMARY RISK FACTORS:")
            for i, factor in enumerate(final_assessment['primary_risk_factors'], 1):
                print(f"   {i}. {factor}")
        
        # Secondary Risk Factors
        if final_assessment.get('secondary_risk_factors'):
            print(f"\n⚠️ SECONDARY RISK FACTORS:")
            for i, factor in enumerate(final_assessment['secondary_risk_factors'], 1):
                print(f"   {i}. {factor}")
        
        # Detailed Tool Results
        print(f"\n🔍 DETAILED TOOL RESULTS")
        print("-" * 50)
        
        for tool_name, result in self.investigation_results.items():
            tool = self.tools[tool_name]
            print(f"\n🛠️ {tool.name.upper()}")
            print(f"Description: {tool.description}")
            print(f"Status: {result.get('status', 'unknown')}")
            
            if result.get('status') == 'success':
                confidence = result.get('confidence', 0)
                print(f"Confidence: {confidence}%")
                
                # Tool-specific details
                if tool_name == "safe_browsing":
                    threats = result.get('threats', [])
                    if threats:
                        print(f"⛔ Threats detected: {len(threats)}")
                        for threat in threats:
                            print(f"   - {threat.get('threatType', 'Unknown')}")
                    else:
                        print("✅ No threats detected")
                
                elif tool_name == "domain_analysis":
                    keywords = result.get('suspicious_keywords', [])
                    if keywords:
                        print(f"🔍 Suspicious keywords: {len(keywords)}")
                        for kw in keywords[:3]:  # Show first 3
                            print(f"   - {kw.get('keyword', 'Unknown')} ({kw.get('type', 'unknown')} keyword)")
                    
                    risk_indicators = result.get('risk_indicators', [])
                    if risk_indicators:
                        print(f"⚠️ Risk indicators: {', '.join(risk_indicators[:3])}")
                
                elif tool_name == "content_analysis":
                    forms = result.get('forms', [])
                    suspicious_forms = sum(1 for form in forms if form.get('suspicious'))
                    if suspicious_forms:
                        print(f"📝 Suspicious forms: {suspicious_forms}/{len(forms)}")
                    
                    suspicious_elements = result.get('suspicious_elements', [])
                    if suspicious_elements:
                        print(f"🚩 Suspicious elements: {len(suspicious_elements)}")
                
                elif tool_name == "deepfake_detection":
                    if result.get('deepfake_detected'):
                        suspicious_imgs = result.get('suspicious_images', [])
                        print(f"🖼️ Suspicious images: {len(suspicious_imgs)}")
                    else:
                        print("✅ No deepfakes detected")
                
                elif tool_name == "text_analysis":
                    scam_likelihood = result.get('scam_likelihood', 'unknown')
                    print(f"📝 Scam likelihood: {scam_likelihood}")
                    red_flags = result.get('red_flags', [])
                    if red_flags:
                        print(f"🚩 Red flags: {len(red_flags)}")
            
            elif result.get('status') == 'error':
                print(f"❌ Error: {result.get('message', 'Unknown error')}")
            else:
                print(f"⏭️ Skipped: {result.get('message', 'No details')}")
        
        # Technical Summary
        print(f"\n🔬 TECHNICAL SUMMARY")
        print(f"Assessment Method: {final_assessment.get('method', 'unknown')}")
        print(f"False Positive Likelihood: {final_assessment.get('false_positive_likelihood', 'unknown')}%")
        print(f"Tools Executed: {len([r for r in self.investigation_results.values() if r.get('status') == 'success'])}/{len(plan['tools_to_use'])}")
        
        if final_assessment.get('technical_summary'):
            print(f"Expert Summary: {final_assessment['technical_summary']}")
        
        # Investigation Strategy
        print(f"\n📋 INVESTIGATION STRATEGY")
        print(f"AI Planning: {plan['reasoning']}")
        print(f"Priority Level: {plan['priority']}")
        print(f"Estimated API Calls: {plan.get('estimated_api_calls', 'unknown')}")
        print(f"Actual API Calls: {self.rate_limiter.request_count}")
        
        print("\n" + "=" * 70)
        print("Investigation Complete ✅")
        print("=" * 70)
    
    def _format_risk_level(self, risk_level):
        """Format risk level with appropriate emoji"""
        formats = {
            "low": "🟢 LOW",
            "medium": "🟡 MEDIUM", 
            "high": "🔴 HIGH",
            "critical": "🚨 CRITICAL"
        }
        return formats.get(risk_level, f"❓ {risk_level.upper()}")

def main():
    """Main application entry point"""
    print("🕵️ Advanced AI-Orchestrated Scam Investigation Agent")
    print("=" * 60)
    
    # Configuration check
    if not TOGETHER_API_KEY:
        print("⚠️ Warning: TOGETHER_API_KEY not set. AI orchestration and analysis will be limited.")
    
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        print("⚠️ Warning: GOOGLE_SAFE_BROWSING_API_KEY not set. Safe Browsing checks will be skipped.")
    
    print("\nAvailable Investigation Tools:")
    orchestrator = InvestigationOrchestrator()
    for name, tool in orchestrator.tools.items():
        cost_indicator = "💰" if tool.cost > 0 else "🆓"
        print(f"  {cost_indicator} {name}: {tool.description}")
    
    print(f"\nRate Limit: {orchestrator.rate_limiter.max_requests} requests per {orchestrator.rate_limiter.time_window} seconds")
    print("\nEnter URLs to investigate (type 'quit' to exit)")
    
    while True:
        try:
            url = input("\n🔗 Enter URL to investigate: ").strip()
            
            if url.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not url:
                continue
                
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Create new orchestrator for each investigation
            orchestrator = InvestigationOrchestrator()
            
            # Run investigation
            investigation_result = orchestrator.execute_investigation(url)
            
            # Option to save results
            save_option = input("\n💾 Save detailed results to JSON file? (y/n): ").strip().lower()
            if save_option == 'y':
                filename = f"investigation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(investigation_result, f, indent=2, default=str)
                print(f"📁 Results saved to {filename}")
            
        except KeyboardInterrupt:
            print("\n⏹️ Investigation interrupted by user")
            break
        except Exception as e:
            print(f"❌ Investigation failed: {str(e)}")
            print("Please try again with a different URL.")

if __name__ == "__main__":
    main()