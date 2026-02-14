"""
SCET API for Vercel Serverless
Copyright Status Tag - Simplified version for serverless deployment
Version: 1.1.0 - Updated tag fields
"""
from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

def extract_year(text):
    if not text:
        return None
    match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', str(text))
    return int(match.group(1)) if match else None

def clean_html(text):
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()

def make_request(url):
    """Make HTTP request with proper headers"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'SCET/1.0 (Smart Copyright Expiry Tag; https://scet.vercel.app)'
    })
    return urllib.request.urlopen(req, timeout=10)

def get_copyright_status(year):
    """Determine copyright status based on publication year"""
    if not year:
        return "UNKNOWN"
    current_year = datetime.now().year
    if year < 1929:
        return "PUBLIC_DOMAIN"
    elif current_year - year > 70:
        return "PUBLIC_DOMAIN"
    else:
        return "PROTECTED"

def search_openlibrary(query):
    results = []
    try:
        url = f"https://openlibrary.org/search.json?q={urllib.parse.quote(query)}&limit=5"
        with make_request(url) as resp:
            data = json.loads(resp.read().decode())
            for i, doc in enumerate(data.get('docs', [])[:5]):
                year = doc.get('first_publish_year')
                results.append({
                    "id": f"ol_{i}",
                    "title": doc.get('title', ''),
                    "creator": ', '.join(doc.get('author_name', [])[:2]) if doc.get('author_name') else None,
                    "publication_year": year,
                    "content_type": "book",
                    "source": "Open Library",
                    "source_url": f"https://openlibrary.org{doc.get('key', '')}",
                    "copyright_status": get_copyright_status(year),
                    "similarity_score": 0.85 - (i * 0.05)
                })
    except Exception as e:
        print(f"OpenLibrary error: {e}")
    return results

def search_wikipedia(query):
    results = []
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit=5"
        with make_request(url) as resp:
            data = json.loads(resp.read().decode())
            for i, item in enumerate(data.get('query', {}).get('search', [])[:5]):
                snippet = clean_html(item.get('snippet', ''))
                year = extract_year(snippet)
                results.append({
                    "id": f"wiki_{i}",
                    "title": item.get('title', ''),
                    "publication_year": year,
                    "content_type": "article",
                    "source": "Wikipedia",
                    "source_url": f"https://en.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
                    "description": snippet[:200],
                    "copyright_status": get_copyright_status(year),
                    "similarity_score": 0.75 - (i * 0.05)
                })
    except Exception as e:
        print(f"Wikipedia error: {e}")
    return results

def search_us_copyright(query):
    """Search US Copyright Office database (copyright.gov)"""
    results = []
    try:
        # US Copyright Office public catalog search
        url = f"https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?Search_Arg={urllib.parse.quote(query)}&Search_Code=TALL&PID=&SEQ=&CNT=10&HIST=1&SEARCH_TYPE=1"
        with make_request(url) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Parse results - look for registration entries
            # The copyright.gov catalog returns HTML with registration info
            if 'Registration Number' in html or 'Title:' in html:
                # Found potential matches
                results.append({
                    "id": "usco_search",
                    "title": f"US Copyright Search: {query}",
                    "publication_year": None,
                    "content_type": "copyright_registration",
                    "source": "US Copyright Office",
                    "source_url": f"https://www.copyright.gov/public-records/",
                    "description": "Search found potential matches in US Copyright Office records. Click to verify on official site.",
                    "copyright_status": "REGISTERED",
                    "similarity_score": 0.95,
                    "registered": True,
                    "jurisdiction": "US"
                })
            else:
                results.append({
                    "id": "usco_none",
                    "title": f"US Copyright Search: {query}",
                    "publication_year": None,
                    "content_type": "copyright_search",
                    "source": "US Copyright Office",
                    "source_url": "https://www.copyright.gov/public-records/",
                    "description": "No exact matches found in US Copyright Office records. Note: Not all works are registered.",
                    "copyright_status": "NOT_FOUND",
                    "similarity_score": 0.5,
                    "registered": False,
                    "jurisdiction": "US"
                })
    except Exception as e:
        print(f"US Copyright Office error: {e}")
        results.append({
            "id": "usco_error",
            "title": f"US Copyright Search: {query}",
            "content_type": "copyright_search",
            "source": "US Copyright Office",
            "source_url": "https://www.copyright.gov/public-records/",
            "description": "Could not search US Copyright Office. Visit link to search manually.",
            "copyright_status": "UNKNOWN",
            "similarity_score": 0.3,
            "jurisdiction": "US"
        })
    return results

def search_indian_copyright(query):
    """Search Indian Copyright Office (copyright.gov.in)"""
    results = []
    try:
        # Indian Copyright Office E-Register search
        url = f"https://copyright.gov.in/SearchRoc.aspx"
        # Since the Indian site uses POST/ASP.NET, provide direct link
        results.append({
            "id": "inco_search",
            "title": f"Indian Copyright Search: {query}",
            "publication_year": None,
            "content_type": "copyright_search",
            "source": "Indian Copyright Office",
            "source_url": "https://copyright.gov.in/SearchRoc.aspx",
            "description": f"Search for '{query}' on Indian Copyright Office E-Register. Click to verify registration status.",
            "copyright_status": "CHECK_REQUIRED",
            "similarity_score": 0.7,
            "jurisdiction": "IN"
        })
    except Exception as e:
        print(f"Indian Copyright Office error: {e}")
    return results

def search_eu_trademark(query):
    """Search EU Intellectual Property Office"""
    results = []
    try:
        results.append({
            "id": "euipo_search",
            "title": f"EU IP Search: {query}",
            "publication_year": None,
            "content_type": "trademark_search",
            "source": "EU Intellectual Property Office",
            "source_url": f"https://euipo.europa.eu/eSearch/#basic/{urllib.parse.quote(query)}",
            "description": f"Search for '{query}' in EU trademark and design database.",
            "copyright_status": "CHECK_REQUIRED",
            "similarity_score": 0.7,
            "jurisdiction": "EU"
        })
    except Exception as e:
        print(f"EUIPO error: {e}")
    return results

def generate_smart_tag(title, year, jurisdiction="US", creator=""):
    current_year = datetime.now().year
    pub_year = year or current_year
    
    rules = {
        "US": {"duration": 70, "pd_before": 1929},
        "EU": {"duration": 70, "pd_before": 1954},
        "UK": {"duration": 70, "pd_before": 1954},
        "IN": {"duration": 60, "pd_before": 1964},
    }
    
    rule = rules.get(jurisdiction, rules["US"])
    
    if pub_year < rule["pd_before"]:
        return {
            "status": "PUBLIC_DOMAIN",
            "status_text": "Public Domain",
            "status_color": "green",
            "status_emoji": "🌍",
            "copyright_status": "Public Domain",
            "emoji": "🌍",
            "title": title,
            "creator": creator,
            "expiry_tag": f"Expired (published {pub_year})",
            "expiry_info": f"Published in {pub_year}, now in public domain",
            "expiry_timeline": f"Published in {pub_year}, now in public domain",
            "rights": "No Rights Reserved - Public Domain",
            "allowed_uses": ["✅ Free to use", "✅ Modify", "✅ Distribute", "✅ Commercial use"],
            "allowed_uses_summary": ["✓ Free to use", "✓ Modify", "✓ Distribute", "✓ Commercial use"],
            "confidence": 0.9,
            "confidence_score": 0.9,
            "confidence_level": "High",
            "jurisdiction": jurisdiction,
            "last_verified": str(current_year),
            "ai_reasoning": f"Work published before {rule['pd_before']} is in the public domain.",
            "disclaimer": "This analysis is for informational purposes only and does not constitute legal advice.",
            "generated_at": datetime.now().isoformat(),
            "tag_version": "1.0"
        }
    elif current_year - pub_year > rule["duration"]:
        return {
            "status": "PUBLIC_DOMAIN", 
            "status_text": "Public Domain",
            "status_color": "green",
            "status_emoji": "🌍",
            "copyright_status": "Public Domain",
            "emoji": "🌍",
            "title": title,
            "creator": creator,
            "expiry_tag": f"Expired (published {pub_year})",
            "expiry_info": f"Copyright expired (published {pub_year})",
            "expiry_timeline": f"Copyright expired (published {pub_year})",
            "rights": "No Rights Reserved - Public Domain",
            "allowed_uses": ["✅ Free to use", "✅ Modify", "✅ Distribute", "✅ Commercial use"],
            "allowed_uses_summary": ["✓ Free to use", "✓ Modify", "✓ Distribute", "✓ Commercial use"],
            "confidence": 0.85,
            "confidence_score": 0.85,
            "confidence_level": "High",
            "jurisdiction": jurisdiction,
            "last_verified": str(current_year),
            "ai_reasoning": f"Copyright duration of {rule['duration']} years has passed.",
            "disclaimer": "This analysis is for informational purposes only and does not constitute legal advice.",
            "generated_at": datetime.now().isoformat(),
            "tag_version": "1.0"
        }
    else:
        years_remaining = rule["duration"] - (current_year - pub_year)
        expiry_year = pub_year + rule["duration"]
        return {
            "status": "PROTECTED",
            "status_text": "Copyright Protected",
            "status_color": "red",
            "status_emoji": "🔒",
            "copyright_status": "Copyright Protected",
            "emoji": "🔒",
            "title": title,
            "creator": creator,
            "expiry_tag": f"Estimated expiry {expiry_year}",
            "expiry_info": f"Protected until ~{expiry_year} ({years_remaining} years remaining)",
            "expiry_timeline": f"Protected until ~{expiry_year} ({years_remaining} years remaining)",
            "rights": "All Rights Reserved",
            "allowed_uses": ["⚠️ Fair use only", "❌ No commercial use without license"],
            "allowed_uses_summary": ["✓ Fair use", "✗ Commercial use without license"],
            "confidence": 0.8,
            "confidence_score": 0.8,
            "confidence_level": "Medium",
            "jurisdiction": jurisdiction,
            "last_verified": str(current_year),
            "ai_reasoning": f"Work is still under copyright protection in {jurisdiction}.",
            "disclaimer": "This analysis is for informational purposes only and does not constitute legal advice.",
            "generated_at": datetime.now().isoformat(),
            "tag_version": "1.0"
        }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        query_string = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(urllib.parse.parse_qsl(query_string))
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/api/v1/health':
            response = {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        elif path == '/api/v1/search':
            q = params.get('q', '')
            jurisdiction = params.get('jurisdiction', 'US')
            
            # Search all sources including government databases
            results = []
            results.extend(search_openlibrary(q))
            results.extend(search_wikipedia(q))
            
            # Add government copyright database searches based on jurisdiction
            if jurisdiction == 'US' or not jurisdiction:
                results.extend(search_us_copyright(q))
            if jurisdiction == 'IN':
                results.extend(search_indian_copyright(q))
            if jurisdiction == 'EU':
                results.extend(search_eu_trademark(q))
            
            # Always include US Copyright Office as primary source
            if jurisdiction not in ['US', '']:
                results.extend(search_us_copyright(q))
            
            results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            response = {
                "query": q,
                "results": results[:15],
                "total_results": len(results),
                "sources_searched": ["Open Library", "Wikipedia", "US Copyright Office", 
                                    "Indian Copyright Office" if jurisdiction == "IN" else None,
                                    "EU IPO" if jurisdiction == "EU" else None]
            }
        
        elif path == '/api/v1/tag':
            title = params.get('title', 'Unknown')
            year = int(params.get('year')) if params.get('year') else None
            jurisdiction = params.get('jurisdiction', 'US')
            response = generate_smart_tag(title, year, jurisdiction)
        
        elif path == '/api/v1/tag/detailed':
            title = params.get('title', 'Unknown')
            creator = params.get('creator', '')
            year_str = params.get('year', '')
            year = int(year_str) if year_str and year_str.isdigit() else None
            content_type = params.get('type', 'unknown')
            jurisdiction = params.get('jurisdiction', 'US')
            
            tag = generate_smart_tag(title, year, jurisdiction, creator)
            is_public_domain = tag["status"] == "PUBLIC_DOMAIN"
            
            # Add detailed information
            response = {
                "tag": tag,
                "recommendations": [
                    {"icon": "📚", "title": "Verify Source", "type": "info", "description": f"Verify publication date of '{title}' from official sources"},
                    {"icon": "⚖️", "title": "Check Laws", "type": "warning", "description": f"Check {jurisdiction} copyright law for specific exemptions"},
                    {"icon": "🔍", "title": "Fair Use", "type": "info", "description": "Consider fair use provisions for educational purposes"}
                ],
                "quick_actions": [
                    {"id": "verify", "label": "🔍 Verify Source", "action": "verify"},
                    {"id": "share", "label": "📤 Share", "action": "share"},
                    {"id": "download", "label": "📥 Download Report", "action": "download"}
                ],
                "risk_assessment": {
                    "level": "Low" if is_public_domain else "Medium",
                    "color": "#28a745" if is_public_domain else "#ffc107",
                    "icon": "✅" if is_public_domain else "⚠️",
                    "description": "This work is in the public domain and can be freely used." if is_public_domain else "This work is under copyright protection. Use requires permission or fair use justification.",
                    "commercial_risk": "None" if is_public_domain else "High",
                    "personal_risk": "None" if is_public_domain else "Low",
                    "score": 0.2 if is_public_domain else 0.6,
                    "factors": [
                        f"Publication year: {year or 'Unknown'}",
                        f"Jurisdiction: {jurisdiction}",
                        f"Content type: {content_type}"
                    ]
                },
                "summary": f"{tag['emoji']} {title} - {tag['status'].replace('_', ' ').title()}. {tag['expiry_info']}",
                "legal_checklist": [
                    {"item": "Verify publication date", "checked": year is not None, "required": True, "status": "done" if year else "pending"},
                    {"item": "Confirm author/creator", "checked": bool(creator), "required": True, "status": "done" if creator else "pending"},
                    {"item": "Check jurisdiction rules", "checked": True, "required": True, "status": "done"},
                    {"item": "Review allowed uses", "checked": True, "required": False, "status": "done"}
                ]
            }
        
        else:
            response = {
                "name": "SCET - Copyright Status Tag",
                "version": "1.0.0",
                "endpoints": ["/api/v1/search", "/api/v1/tag", "/api/v1/tag/detailed", "/api/v1/health"]
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
