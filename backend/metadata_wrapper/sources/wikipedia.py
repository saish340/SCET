"""
Wikipedia Metadata Connector
============================
Extracts metadata from Wikipedia for creative works.

Legal Note:
- Only extracts factual metadata (title, author, year, etc.)
- Never stores article content
- Uses Wikipedia API which is designed for this purpose
- Respects rate limits
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import re
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime


# Wikipedia API endpoint
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

# Request headers
HEADERS = {
    "User-Agent": "SCET-MetadataWrapper/1.0 (Copyright Research Tool; +https://scet.vercel.app)",
    "Accept": "application/json",
}


def search_wikipedia(title: str, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    Search Wikipedia for metadata about a creative work.
    
    Args:
        title: Title to search for
        timeout: Request timeout in seconds
        
    Returns:
        List of metadata dicts or None if not found
    """
    if not title:
        return None
    
    try:
        # Step 1: Search for pages matching the title
        search_results = _wikipedia_search(title, timeout)
        
        if not search_results:
            return None
        
        results = []
        
        # Step 2: Get metadata for top results (limit to 3 to avoid rate limiting)
        for page_title in search_results[:3]:
            metadata = _get_wikipedia_metadata(page_title, timeout)
            if metadata:
                results.append(metadata)
        
        return results if results else None
        
    except Exception as e:
        return None


def _wikipedia_search(query: str, timeout: int) -> Optional[List[str]]:
    """
    Search Wikipedia for page titles.
    
    Args:
        query: Search query
        timeout: Request timeout
        
    Returns:
        List of page titles or None
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": "5",
        "format": "json"
    }
    
    url = f"{WIKIPEDIA_API}?{urllib.parse.urlencode(params)}"
    
    try:
        request = urllib.request.Request(url, headers=HEADERS)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            search_results = data.get("query", {}).get("search", [])
            
            if search_results:
                return [r["title"] for r in search_results]
            
    except Exception:
        pass
    
    return None


def _get_wikipedia_metadata(page_title: str, timeout: int) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a specific Wikipedia page.
    
    Args:
        page_title: Wikipedia page title
        timeout: Request timeout
        
    Returns:
        Metadata dict or None
    """
    # Get page info and extract (first paragraph)
    params = {
        "action": "query",
        "titles": page_title,
        "prop": "extracts|info|categories",
        "exintro": "true",
        "explaintext": "true",
        "exsentences": "3",
        "inprop": "url",
        "format": "json"
    }
    
    url = f"{WIKIPEDIA_API}?{urllib.parse.urlencode(params)}"
    
    try:
        request = urllib.request.Request(url, headers=HEADERS)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page_data in pages.items():
                if page_id == "-1":  # Page not found
                    continue
                
                extract = page_data.get("extract", "")
                page_url = page_data.get("fullurl", "")
                categories = page_data.get("categories", [])
                
                # Extract metadata from extract
                metadata = _parse_wikipedia_extract(extract, page_title)
                
                # Determine content type from categories
                content_type = _determine_content_type(categories, extract)
                
                return {
                    "title": page_title,
                    "creator": metadata.get("creator"),
                    "publication_year": metadata.get("year"),
                    "content_type": content_type,
                    "source": "Wikipedia",
                    "source_url": page_url or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title)}",
                    "confidence_score": 0.7,
                    "last_verified": datetime.now().strftime("%Y-%m-%d"),
                    "description": extract[:200] if extract else None
                }
                
    except Exception:
        pass
    
    return None


def _parse_wikipedia_extract(extract: str, title: str) -> Dict[str, Any]:
    """
    Parse Wikipedia extract to find creator and year.
    
    Args:
        extract: Wikipedia page extract text
        title: Page title
        
    Returns:
        Dict with creator and year if found
    """
    result = {
        "creator": None,
        "year": None
    }
    
    if not extract:
        return result
    
    extract_lower = extract.lower()
    
    # Pattern for "by [Author]" or "written by [Author]"
    by_patterns = [
        r'(?:written|authored|created|composed|directed|developed)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
        r'by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
        r'is\s+a[n]?\s+\w+\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
    ]
    
    for pattern in by_patterns:
        match = re.search(pattern, extract)
        if match:
            result["creator"] = match.group(1).strip()
            break
    
    # Pattern for years
    year_patterns = [
        r'published\s+(?:in\s+)?(\d{4})',
        r'released\s+(?:in\s+)?(\d{4})',
        r'first\s+published\s+(?:in\s+)?(\d{4})',
        r'\((\d{4})\)',  # Year in parentheses
        r'in\s+(\d{4})',
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, extract_lower)
        if match:
            year = int(match.group(1))
            if 1000 <= year <= datetime.now().year + 5:
                result["year"] = year
                break
    
    return result


def _determine_content_type(categories: List[Dict], extract: str) -> str:
    """
    Determine content type from Wikipedia categories and extract.
    
    Args:
        categories: List of category dicts
        extract: Page extract text
        
    Returns:
        Content type string
    """
    # Build category string for matching
    cat_string = " ".join([c.get("title", "").lower() for c in categories])
    extract_lower = extract.lower() if extract else ""
    combined = cat_string + " " + extract_lower
    
    # Check for content type indicators
    type_indicators = {
        "book": ["novel", "book", "literature", "fiction", "non-fiction", "autobiography", "biography"],
        "film": ["film", "movie", "cinema", "motion picture"],
        "music": ["album", "song", "music", "musician", "band", "singer", "composer"],
        "software": ["software", "programming", "application", "video game", "computer game"],
        "artwork": ["painting", "sculpture", "artwork", "artist", "art"],
        "article": ["journal", "academic", "paper", "research", "publication"],
        "trademark": ["brand", "trademark", "company", "corporation"],
    }
    
    for content_type, indicators in type_indicators.items():
        for indicator in indicators:
            if indicator in combined:
                return content_type
    
    return "unknown"
