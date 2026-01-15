"""
SCET API for Vercel Serverless
Simplified version for serverless deployment
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

def generate_smart_tag(title, year, jurisdiction="US"):
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
            "emoji": "🌍",
            "title": title,
            "expiry_info": f"Published in {pub_year}, now in public domain",
            "allowed_uses": ["✅ Free to use", "✅ Modify", "✅ Distribute", "✅ Commercial use"],
            "confidence": 0.9,
            "jurisdiction": jurisdiction,
            "ai_reasoning": f"Work published before {rule['pd_before']} is in the public domain."
        }
    elif current_year - pub_year > rule["duration"]:
        return {
            "status": "PUBLIC_DOMAIN", 
            "emoji": "🌍",
            "title": title,
            "expiry_info": f"Copyright expired (published {pub_year})",
            "allowed_uses": ["✅ Free to use", "✅ Modify", "✅ Distribute", "✅ Commercial use"],
            "confidence": 0.85,
            "jurisdiction": jurisdiction,
            "ai_reasoning": f"Copyright duration of {rule['duration']} years has passed."
        }
    else:
        years_remaining = rule["duration"] - (current_year - pub_year)
        return {
            "status": "PROTECTED",
            "emoji": "🔒",
            "title": title,
            "expiry_info": f"Protected until ~{pub_year + rule['duration']} ({years_remaining} years remaining)",
            "allowed_uses": ["⚠️ Fair use only", "❌ No commercial use without license"],
            "confidence": 0.8,
            "jurisdiction": jurisdiction,
            "ai_reasoning": f"Work is still under copyright protection in {jurisdiction}."
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
            results = search_openlibrary(q) + search_wikipedia(q)
            results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            response = {
                "query": q,
                "results": results[:10],
                "total_results": len(results)
            }
        
        elif path == '/api/v1/tag':
            title = params.get('title', 'Unknown')
            year = int(params.get('year')) if params.get('year') else None
            jurisdiction = params.get('jurisdiction', 'US')
            response = generate_smart_tag(title, year, jurisdiction)
        
        else:
            response = {
                "name": "SCET - Smart Copyright Expiry Tag",
                "version": "1.0.0",
                "endpoints": ["/api/v1/search", "/api/v1/tag", "/api/v1/health"]
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
