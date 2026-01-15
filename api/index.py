"""
SCET API for Vercel Serverless
Simplified version for serverless deployment
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import aiohttp
import asyncio
import re
from datetime import datetime
from bs4 import BeautifulSoup

app = FastAPI(title="SCET API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class SearchResult(BaseModel):
    title: str
    creator: Optional[str] = None
    publication_year: Optional[int] = None
    content_type: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.5

class SearchResponse(BaseModel):
    query: str
    corrected_query: Optional[str] = None
    results: List[SearchResult]
    total_results: int

class SmartTag(BaseModel):
    status: str
    emoji: str
    title: str
    expiry_info: str
    allowed_uses: List[str]
    confidence: float
    jurisdiction: str
    ai_reasoning: str

# Helper functions
def extract_year(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', str(text))
    return int(match.group(1)) if match else None

def clean_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()

# Scrapers
async def search_openlibrary(query: str) -> List[SearchResult]:
    results = []
    url = f"https://openlibrary.org/search.json?q={query}&limit=5"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for doc in data.get('docs', [])[:5]:
                        results.append(SearchResult(
                            title=doc.get('title', ''),
                            creator=', '.join(doc.get('author_name', [])[:2]) if doc.get('author_name') else None,
                            publication_year=doc.get('first_publish_year'),
                            content_type='book',
                            source_url=f"https://openlibrary.org{doc.get('key', '')}",
                            source_name='Open Library',
                            confidence=0.85
                        ))
    except:
        pass
    return results

async def search_wikipedia(query: str) -> List[SearchResult]:
    results = []
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=5"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get('query', {}).get('search', [])[:5]:
                        snippet = clean_html(item.get('snippet', ''))
                        results.append(SearchResult(
                            title=item.get('title', ''),
                            publication_year=extract_year(snippet),
                            content_type='article',
                            source_url=f"https://en.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
                            source_name='Wikipedia',
                            description=snippet[:200],
                            confidence=0.7
                        ))
    except:
        pass
    return results

async def search_semantic_scholar(query: str) -> List[SearchResult]:
    results = []
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5&fields=title,year,authors,abstract"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for paper in data.get('data', [])[:5]:
                        authors = paper.get('authors', [])
                        author_names = ', '.join([a.get('name', '') for a in authors[:2]])
                        results.append(SearchResult(
                            title=paper.get('title', ''),
                            creator=author_names if author_names else None,
                            publication_year=paper.get('year'),
                            content_type='academic_paper',
                            source_url=f"https://www.semanticscholar.org/search?q={query}",
                            source_name='Semantic Scholar',
                            description=paper.get('abstract', '')[:200] if paper.get('abstract') else None,
                            confidence=0.8
                        ))
    except:
        pass
    return results

# Smart Tag Generator
def generate_smart_tag(result: SearchResult, jurisdiction: str = "US") -> SmartTag:
    current_year = datetime.now().year
    pub_year = result.publication_year or current_year
    
    # Copyright rules by jurisdiction
    rules = {
        "US": {"duration": 70, "pd_before": 1929},
        "EU": {"duration": 70, "pd_before": 1954},
        "UK": {"duration": 70, "pd_before": 1954},
        "IN": {"duration": 60, "pd_before": 1964},
        "JP": {"duration": 70, "pd_before": 1954},
    }
    
    rule = rules.get(jurisdiction, rules["US"])
    
    # Determine status
    if pub_year < rule["pd_before"]:
        status = "PUBLIC_DOMAIN"
        emoji = "🌍"
        expiry_info = f"Published in {pub_year}, now in public domain"
        allowed_uses = ["✅ Free to use", "✅ Modify", "✅ Distribute", "✅ Commercial use"]
        reasoning = f"Work published before {rule['pd_before']} is in the public domain in {jurisdiction}."
    elif current_year - pub_year > rule["duration"]:
        status = "PUBLIC_DOMAIN"
        emoji = "🌍"
        expiry_info = f"Copyright expired (published {pub_year})"
        allowed_uses = ["✅ Free to use", "✅ Modify", "✅ Distribute", "✅ Commercial use"]
        reasoning = f"Copyright duration of {rule['duration']} years has passed."
    else:
        years_remaining = rule["duration"] - (current_year - pub_year)
        status = "PROTECTED"
        emoji = "🔒"
        expiry_info = f"Protected until ~{pub_year + rule['duration']} ({years_remaining} years remaining)"
        allowed_uses = ["⚠️ Fair use only", "❌ No commercial use without license"]
        reasoning = f"Work is still under copyright protection in {jurisdiction}."
    
    return SmartTag(
        status=status,
        emoji=emoji,
        title=result.title,
        expiry_info=expiry_info,
        allowed_uses=allowed_uses,
        confidence=result.confidence,
        jurisdiction=jurisdiction,
        ai_reasoning=reasoning
    )

# API Routes
@app.get("/")
async def root():
    return {
        "name": "SCET - Smart Copyright Expiry Tag",
        "version": "1.0.0",
        "description": "AI-powered copyright status checker",
        "docs": "/docs"
    }

@app.get("/api/v1/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    jurisdiction: Optional[str] = Query("US", description="Jurisdiction")
):
    # Run searches concurrently
    tasks = [
        search_openlibrary(q),
        search_wikipedia(q),
        search_semantic_scholar(q)
    ]
    
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_results = []
    for result_list in results_lists:
        if isinstance(result_list, list):
            all_results.extend(result_list)
    
    # Filter by content type if specified
    if content_type:
        all_results = [r for r in all_results if r.content_type == content_type]
    
    # Sort by confidence
    all_results.sort(key=lambda x: x.confidence, reverse=True)
    
    return SearchResponse(
        query=q,
        results=all_results[:10],
        total_results=len(all_results)
    )

@app.get("/api/v1/tag")
async def get_tag(
    title: str = Query(...),
    year: Optional[int] = Query(None),
    content_type: Optional[str] = Query(None),
    jurisdiction: str = Query("US")
):
    result = SearchResult(
        title=title,
        publication_year=year,
        content_type=content_type,
        confidence=0.75
    )
    tag = generate_smart_tag(result, jurisdiction)
    return tag

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Vercel handler
handler = app
