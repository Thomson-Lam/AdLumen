def build_prompt(url, clean_text):
    prompt = f"""# Cybersecurity Agent - Initial Analysis

    ## Role & Context
    You are the **initial analysis component** of a multi-stage fraud detection system. Your assessment will be combined with additional tool results to calculate a final averaged fraud score. Focus on providing your best independent assessment using cybersecurity expertise.

    ## Your Specific Task
    Perform comprehensive fraud risk analysis using ONLY the provided URL and content. Do NOT call external tools - your role is the foundational analysis that will be enhanced by specialized tools if needed.

    ## Input Data
    - **Target URL**: {url}
    - **Extracted Content**: {clean_text}

    ## Analysis Framework

    ### Primary Cybersecurity Assessment
    Analyze as an expert cybersecurity specialist:

    **Content Security Analysis:**
    - Phishing indicators (credential harvesting, urgent language, impersonation)
    - Social engineering tactics (false scarcity, fear appeals, unrealistic promises)
    - Legitimacy markers (professional copy, consistent branding, logical business model)
    - Contact verification (email domains, phone patterns, address consistency)

    **Technical Security Evaluation:**
    - Domain assessment (structure, TLD reputation, suspicious patterns)
    - Known threat signatures (compare against common fraud schemes)
    - Security implementation (HTTPS usage, redirect behavior)
    - Website functionality (normal business operations vs. suspicious requests)

    **Risk Indicators Checklist:**
    - Grammar/spelling errors in professional contexts
    - Mismatched branding or domain inconsistencies
    - Excessive urgency or pressure tactics
    - Requests for sensitive information
    - Suspicious payment methods or processes
    - Domain age implications (if determinable from content)

    ## Scoring Guidelines
    Your fraud_probability represents your independent assessment:
    - **0.00-0.25**: Strong legitimacy indicators, professional presentation
    - **0.26-0.50**: Minor concerns but likely legitimate
    - **0.51-0.75**: Significant red flags, probably fraudulent
    - **0.76-1.00**: Multiple fraud indicators, high confidence malicious

    ## Function Call Decision
    Based on your analysis, determine if additional validation would be valuable:

    **Available Tools:**
    - `google_safe_browsing_check(url)` - Check reputation databases
    - `whoami(url)` - Domain registration analysis

    **Call Functions When:**
    - Your confidence is medium (fraud_probability 0.25-0.75)
    - Conflicting indicators need external validation
    - Domain details would significantly impact assessment

    **Skip Functions When:**
    - High confidence in legitimacy (< 0.25 fraud probability)
    - High confidence in fraud (> 0.75 fraud probability)
    - Content provides overwhelming evidence either way

    ## Output Requirements
    Return ONLY this JSON object with no additional text:

    ```json
    {{
            "fraud_probability": final_fraud_score,
            "confidence_level": analysis_result["confidence_level"],
            "justification": analysis_result["justification"]
    }}
    ```

    ## Formatting Rules
    - **fraud_probability**: Your independent assessment (0.00-1.00, two decimals)
    - **confidence_level**: Certainty in your assessment (0.00-1.00, two decimals)
    - **justification**: 1-2 sentences explaining key determining factors
    - **call_google_safe_browsing**: Boolean - should this tool be called?
    - **call_whoami**: Boolean - should this tool be called?
    - **Error handling**: Return {{}} if analysis cannot be completed

    ## Important Notes
    - Your score will be averaged with tool results for the final fraud score
    - Focus on what you can determine from content and URL alone
    - Make function call decisions based on what would genuinely improve overall assessment accuracy
    - Higher confidence = less need for additional tools"""
        
    return prompt
    
def scam_agent(client, url, clean_text):
    # Get the prompt
    prompt = build_prompt(url, clean_text)
    
    try:
        # Call Gemini
        gemini_response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        raw_response = gemini_response.text.strip()
        print(f"Raw Gemini response: {raw_response}")
        
        # Clean the response by removing Markdown code blocks
        if raw_response.startswith('```json'):
            raw_response = raw_response[7:]  # Remove ```json
        if raw_response.endswith('```'):
            raw_response = raw_response[:-3]  # Remove ```
        raw_response = raw_response.strip()
        
        # Parse JSON response
        import json
        try:
            full_response = json.loads(raw_response)
            print(f"Parsed JSON: {full_response}")
            
            # Validate required fields
            required_fields = ["fraud_probability", "confidence_level", "justification"]
            if not all(key in full_response for key in required_fields):
                raise ValueError("Missing required fields in response")
                
            # Extract tool call flags
            call_google = full_response.pop("call_google_safe_browsing", False)
            call_whoami = full_response.pop("call_whoami", False)
            
            analysis_result = full_response
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {e}")
            analysis_result = {
                "fraud_probability": 0.0,
                "confidence_level": 0.0,
                "justification": "Unable to analyze due to parsing error"
            }
            call_google = False
            call_whoami = False
        
        # Call tools based on flags
        tool_results = []

        if call_google:
            tool_results.append(google_safe_browsing_check(url))

        if call_whoami:
            tool_results.append((whoami(url), True))  # whoami always returns includable score

        # Average scores
        final_fraud_score = average_score(analysis_result["fraud_probability"], tool_results)

        # Update analysis_result with final averaged score
        analysis_result = {
            "fraud_probability": final_fraud_score,
            "confidence_level": analysis_result["confidence_level"],
            "justification": analysis_result["justification"]
        }

        return analysis_result
        
    except Exception as e:
        print(f"Gemini error: {e}")
        # Error response
        return {
            "fraud_probability": 0.0,
            "confidence_level": 0.0,
            "justification": f"Analysis failed: {str(e)}"
        }
    
def google_safe_browsing_check(url):
    """Returns (score, should_include_in_average) tuple"""
    try:
        import requests
        import os
        from urllib.parse import urlparse
        
        # Skip check for certain domains
        domain = urlparse(url).netloc.lower()
        excluded_domains = ['.gov', '.mil', 'localhost']  # Add others as needed
        if any(domain.endswith(excluded) for excluded in excluded_domains):
            print(f"Skipping Safe Browsing check for excluded domain: {domain}")
            return (0.0, False)  # Neutral score, excluded from average
        
        api_key = os.getenv('GOOGLE_SAFE_BROWSING_API_KEY')
        if not api_key:
            print("Google Safe Browsing API key not found")
            return (0.0, False)
        
        # API request setup remains the same...
        api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
        payload = {
            "client": {
                "clientId": "fraud-detection-agent",
                "clientVersion": "1.0.0"
            },
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}]
            }
        }
        
        try:
            response = requests.post(api_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if "matches" in result and result["matches"]:
                threat_types = [match.get("threatType", "UNKNOWN") for match in result["matches"]]
                print(f"Threats found: {threat_types}")
                
                score = 0.0
                for threat in threat_types:
                    if threat == "MALWARE":
                        score = max(score, 0.9)
                    elif threat == "SOCIAL_ENGINEERING":
                        score = max(score, 0.8)
                    elif threat in ["UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"]:
                        score = max(score, 0.6)
                    else:
                        score = max(score, 0.5)
                
                return (min(score, 1.0), True)
            else:
                print("No threats found in Google Safe Browsing")
                return (0.0, True)
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print("Google Safe Browsing API access denied (possibly restricted domain)")
                return (0.0, False)
            raise
            
    except Exception as e:
        print(f"Google Safe Browsing check failed: {e}")
        return (0.0, False)  # Neutral score, excluded from average
    
def whoami(url):
    try:
        import whois
        from urllib.parse import urlparse
        from datetime import datetime
        
        # Extract domain from URL
        domain = urlparse(url).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        
        print(f"Performing WHOIS lookup for: {domain}")
        
        # Perform WHOIS lookup
        w = whois.whois(domain)
        
        score = 0.0
        factors = []
        
        # Check domain age
        if w.creation_date:
            if isinstance(w.creation_date, list):
                creation_date = w.creation_date[0]
            else:
                creation_date = w.creation_date
            
            age_days = (datetime.now() - creation_date).days
            
            if age_days < 30:
                score += 0.4  # Very new domain - high risk
                factors.append("very new domain")
            elif age_days < 365:
                score += 0.2  # Less than 1 year - moderate risk
                factors.append("domain less than 1 year old")
            else:
                factors.append(f"domain age: {age_days} days")
        
        # Check registrar
        if w.registrar:
            # Some registrars commonly used by scammers
            suspicious_registrars = ['namecheap', 'godaddy', 'namesilo']
            if any(sus in w.registrar.lower() for sus in suspicious_registrars):
                score += 0.1
                factors.append("registrar commonly used by fraudsters")
        
        # Check privacy protection
        if w.whois_server and 'privacy' in str(w.whois_server).lower():
            score += 0.1
            factors.append("privacy protection enabled")
        
        # Check expiration date
        if w.expiration_date:
            if isinstance(w.expiration_date, list):
                expiration_date = w.expiration_date[0]
            else:
                expiration_date = w.expiration_date
            
            days_until_expiry = (expiration_date - datetime.now()).days
            if days_until_expiry < 30:
                score += 0.2
                factors.append("expires soon")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        print(f"WHOIS analysis complete. Score: {score}, Factors: {factors}")
        return score
        
    except Exception as e:
        print(f"WHOIS lookup failed: {e}")
        return 0.0  # Return neutral score on failure

def average_score(gemini_score, tool_results):
    """
    Calculate weighted average of scores.
    tool_results should be list of (score, should_include) tuples
    """
    valid_scores = [gemini_score]
    
    for score, should_include in tool_results:
        if should_include:
            valid_scores.append(score)
    
    if valid_scores:
        average = sum(valid_scores) / len(valid_scores)
        print(f"Averaging {len(valid_scores)} scores: {valid_scores} = {average:.2f}")
        return round(average, 2)
    else:
        return round(gemini_score, 2)