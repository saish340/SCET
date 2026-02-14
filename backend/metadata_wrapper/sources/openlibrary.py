"""
Open Library Metadata Connector
===============================
Extracts book metadata from Open Library API.

Legal Note:
- Open Library provides free, public API for book metadata
- Only extracts metadata, never downloads books
- API is designed for this purpose
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime


# Open Library API endpoints
OPENLIBRARY_SEARCH = "https://openlibrary.org/search.json"
OPENLIBRARY_BASE = "https://openlibrary.org"

# Request headers
HEADERS = {
    "User-Agent": "SCET-MetadataWrapper/1.0 (Copyright Research Tool; +https://scet.vercel.app)",
    "Accept": "application/json",
}


def search_openlibrary(title: str, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    Search Open Library for book metadata.
    
    Args:
        title: Book title to search for
        timeout: Request timeout in seconds
        
    Returns:
        List of metadata dicts or None if not found
    """
    if not title:
        return None
    
    try:
        params = {
            "title": title,
            "limit": "5",
            "fields": "key,title,author_name,first_publish_year,publisher,subject,cover_i,isbn"
        }
        
        url = f"{OPENLIBRARY_SEARCH}?{urllib.parse.urlencode(params)}"
        
        request = urllib.request.Request(url, headers=HEADERS)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            docs = data.get("docs", [])
            
            if not docs:
                return None
            
            results = []
            
            for doc in docs[:5]:
                metadata = _parse_openlibrary_doc(doc)
                if metadata:
                    results.append(metadata)
            
            return results if results else None
            
    except Exception as e:
        return None


def _parse_openlibrary_doc(doc: Dict) -> Optional[Dict[str, Any]]:
    """
    Parse Open Library document into standard metadata format.
    
    Args:
        doc: Open Library document dict
        
    Returns:
        Standardized metadata dict
    """
    if not doc:
        return None
    
    title = doc.get("title")
    if not title:
        return None
    
    # Extract authors
    authors = doc.get("author_name", [])
    creator = None
    if authors:
        if len(authors) == 1:
            creator = authors[0]
        elif len(authors) <= 3:
            creator = ", ".join(authors)
        else:
            creator = f"{', '.join(authors[:3])}, et al."
    
    # Extract year
    year = doc.get("first_publish_year")
    if year:
        try:
            year = int(year)
        except (ValueError, TypeError):
            year = None
    
    # Build source URL
    key = doc.get("key", "")
    source_url = f"{OPENLIBRARY_BASE}{key}" if key else OPENLIBRARY_BASE
    
    # Extract subjects for better categorization
    subjects = doc.get("subject", [])[:5] if doc.get("subject") else []
    
    # Calculate confidence based on data completeness
    confidence = 0.6
    if creator:
        confidence += 0.15
    if year:
        confidence += 0.1
    if doc.get("isbn"):
        confidence += 0.1
    
    return {
        "title": title,
        "creator": creator,
        "publication_year": year,
        "content_type": "book",
        "source": "Open Library",
        "source_url": source_url,
        "confidence_score": min(confidence, 0.95),
        "last_verified": datetime.now().strftime("%Y-%m-%d"),
        "subjects": subjects,
        "isbn": doc.get("isbn", [None])[0] if doc.get("isbn") else None,
        "publishers": doc.get("publisher", [])[:3] if doc.get("publisher") else None
    }


def get_book_details(olid: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Get detailed metadata for a specific Open Library ID.
    
    Args:
        olid: Open Library ID (e.g., "OL123456W")
        timeout: Request timeout
        
    Returns:
        Detailed metadata dict
    """
    if not olid:
        return None
    
    try:
        url = f"{OPENLIBRARY_BASE}/works/{olid}.json"
        
        request = urllib.request.Request(url, headers=HEADERS)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            title = data.get("title")
            if not title:
                return None
            
            # Get author details
            authors = data.get("authors", [])
            creator = None
            if authors:
                author_keys = [a.get("author", {}).get("key") for a in authors if a.get("author")]
                # Would need additional API calls to resolve author names
                # For now, mark as available
                creator = f"{len(author_keys)} author(s)" if author_keys else None
            
            return {
                "title": title,
                "creator": creator,
                "publication_year": None,  # Need edition data
                "content_type": "book",
                "source": "Open Library",
                "source_url": f"{OPENLIBRARY_BASE}/works/{olid}",
                "confidence_score": 0.8,
                "last_verified": datetime.now().strftime("%Y-%m-%d"),
                "description": data.get("description", {}).get("value") if isinstance(data.get("description"), dict) else data.get("description"),
                "subjects": data.get("subjects", [])[:10]
            }
            
    except Exception:
        return None
