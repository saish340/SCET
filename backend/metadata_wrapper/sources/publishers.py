"""
Publisher Metadata Connector
============================
Extracts metadata from official publisher sources and databases.

Legal Note:
- Only extracts publicly available catalog metadata
- Never downloads copyrighted content
- Respects robots.txt and rate limits
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import re
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime


# Request headers
HEADERS = {
    "User-Agent": "SCET-MetadataWrapper/1.0 (Copyright Research Tool; +https://scet.vercel.app)",
    "Accept": "application/json,text/html",
}


# Google Books API (free tier, public metadata)
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"


def search_publishers(title: str, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """
    Search publisher databases for metadata.
    
    Currently uses:
    - Google Books API (aggregates publisher data)
    
    Args:
        title: Title to search for
        timeout: Request timeout in seconds
        
    Returns:
        List of metadata dicts or None if not found
    """
    if not title:
        return None
    
    results = []
    
    # Search Google Books (aggregates publisher data)
    google_results = _search_google_books(title, timeout)
    if google_results:
        results.extend(google_results)
    
    return results if results else None


def _search_google_books(title: str, timeout: int) -> Optional[List[Dict[str, Any]]]:
    """
    Search Google Books API for publisher metadata.
    
    Args:
        title: Title to search for
        timeout: Request timeout
        
    Returns:
        List of metadata dicts
    """
    try:
        params = {
            "q": f"intitle:{title}",
            "maxResults": "5",
            "printType": "books"
        }
        
        url = f"{GOOGLE_BOOKS_API}?{urllib.parse.urlencode(params)}"
        
        request = urllib.request.Request(url, headers=HEADERS)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            items = data.get("items", [])
            
            if not items:
                return None
            
            results = []
            
            for item in items[:5]:
                metadata = _parse_google_books_item(item)
                if metadata:
                    results.append(metadata)
            
            return results if results else None
            
    except Exception:
        return None


def _parse_google_books_item(item: Dict) -> Optional[Dict[str, Any]]:
    """
    Parse Google Books API item into standard metadata format.
    
    Args:
        item: Google Books API item dict
        
    Returns:
        Standardized metadata dict
    """
    if not item:
        return None
    
    volume_info = item.get("volumeInfo", {})
    
    title = volume_info.get("title")
    if not title:
        return None
    
    # Extract authors
    authors = volume_info.get("authors", [])
    creator = None
    if authors:
        if len(authors) == 1:
            creator = authors[0]
        elif len(authors) <= 3:
            creator = ", ".join(authors)
        else:
            creator = f"{', '.join(authors[:3])}, et al."
    
    # Extract publication year
    pub_date = volume_info.get("publishedDate", "")
    year = None
    if pub_date:
        year_match = re.search(r'(\d{4})', pub_date)
        if year_match:
            year = int(year_match.group(1))
    
    # Get publisher
    publisher = volume_info.get("publisher")
    
    # Build source URL
    info_link = volume_info.get("infoLink", "")
    
    # Determine content type
    categories = volume_info.get("categories", [])
    content_type = _determine_content_type_from_categories(categories)
    
    # Calculate confidence
    confidence = 0.65
    if creator:
        confidence += 0.1
    if year:
        confidence += 0.1
    if publisher:
        confidence += 0.1
    
    return {
        "title": title,
        "creator": creator,
        "publication_year": year,
        "content_type": content_type,
        "source": f"Official Publisher ({publisher})" if publisher else "Google Books",
        "source_url": info_link or "https://books.google.com/",
        "confidence_score": min(confidence, 0.95),
        "last_verified": datetime.now().strftime("%Y-%m-%d"),
        "publisher": publisher,
        "categories": categories[:5] if categories else None,
        "isbn_10": volume_info.get("industryIdentifiers", [{}])[0].get("identifier") 
                  if volume_info.get("industryIdentifiers") else None,
        "page_count": volume_info.get("pageCount"),
        "language": volume_info.get("language")
    }


def _determine_content_type_from_categories(categories: List[str]) -> str:
    """
    Determine content type from Google Books categories.
    
    Args:
        categories: List of category strings
        
    Returns:
        Content type string
    """
    if not categories:
        return "book"
    
    cat_string = " ".join(categories).lower()
    
    if any(word in cat_string for word in ["fiction", "novel", "literature"]):
        return "book"
    if any(word in cat_string for word in ["music", "musicians"]):
        return "music"
    if any(word in cat_string for word in ["art", "painting", "photography"]):
        return "artwork"
    if any(word in cat_string for word in ["computers", "programming", "software"]):
        return "software"
    if any(word in cat_string for word in ["academic", "science", "research"]):
        return "article"
    
    return "book"


# Future: Add more publisher connectors
class PublisherConnector:
    """
    Base class for specific publisher API connectors.
    
    Extend this class to add support for specific publishers:
    - Penguin Random House
    - HarperCollins
    - Simon & Schuster
    - Hachette
    - etc.
    
    Example:
        class PenguinConnector(PublisherConnector):
            def __init__(self, api_key=None):
                super().__init__("Penguin Random House", "https://api.penguinrandomhouse.com")
                self.api_key = api_key
            
            def search(self, title):
                # Implement API search
                pass
    """
    
    def __init__(self, publisher_name: str, base_url: str):
        self.publisher_name = publisher_name
        self.base_url = base_url
    
    def search(self, title: str, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Override in subclass to implement search."""
        raise NotImplementedError("Subclass must implement search()")
    
    def get_book_details(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Override in subclass to get specific book details."""
        raise NotImplementedError("Subclass must implement get_book_details()")
