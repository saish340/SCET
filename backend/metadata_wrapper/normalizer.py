"""
Metadata Normalizer
===================
Converts raw metadata from various sources into standard SCET format.
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime


# Standard metadata schema
STANDARD_SCHEMA = {
    "title": str,
    "creator": str,
    "publication_year": int,
    "content_type": str,
    "source": str,
    "source_url": str,
    "last_verified": str,
    "confidence_score": float
}

# Content type mapping
CONTENT_TYPE_MAP = {
    # Books
    "book": "book",
    "books": "book",
    "literary work": "book",
    "novel": "book",
    "ebook": "book",
    "textbook": "book",
    "publication": "book",
    
    # Music
    "music": "music",
    "song": "music",
    "album": "music",
    "sound recording": "music",
    "musical work": "music",
    "audio": "music",
    
    # Film
    "film": "film",
    "movie": "film",
    "motion picture": "film",
    "video": "film",
    "documentary": "film",
    
    # Software
    "software": "software",
    "code": "software",
    "program": "software",
    "application": "software",
    "library": "software",
    
    # Art
    "artwork": "artwork",
    "art": "artwork",
    "painting": "artwork",
    "photograph": "artwork",
    "image": "artwork",
    "visual art": "artwork",
    
    # Articles
    "article": "article",
    "paper": "article",
    "journal": "article",
    "academic": "article",
    
    # Trademark
    "trademark": "trademark",
    "brand": "trademark",
    
    # Patent
    "patent": "patent",
    "invention": "patent",
}


def normalize_metadata(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw metadata into standard SCET format.
    
    Args:
        raw_data: Raw metadata dict from any source
        
    Returns:
        Normalized metadata dict with standard fields
    """
    if not raw_data or not isinstance(raw_data, dict):
        return _empty_metadata()
    
    normalized = {
        "title": _normalize_title(raw_data),
        "creator": _normalize_creator(raw_data),
        "publication_year": _normalize_year(raw_data),
        "content_type": _normalize_content_type(raw_data),
        "source": _normalize_source(raw_data),
        "source_url": _normalize_url(raw_data),
        "last_verified": _normalize_date(raw_data),
        "confidence_score": _normalize_confidence(raw_data)
    }
    
    return normalized


def _empty_metadata() -> Dict[str, Any]:
    """Return empty metadata structure."""
    return {
        "title": None,
        "creator": None,
        "publication_year": None,
        "content_type": "unknown",
        "source": "unknown",
        "source_url": None,
        "last_verified": datetime.now().strftime("%Y-%m-%d"),
        "confidence_score": 0.0
    }


def _normalize_title(data: Dict) -> Optional[str]:
    """Extract and normalize title."""
    # Try common field names
    title_fields = ["title", "name", "work_title", "book_title", "Title", "Name"]
    
    for field in title_fields:
        if field in data and data[field]:
            title = str(data[field]).strip()
            # Remove excessive whitespace
            title = re.sub(r'\s+', ' ', title)
            # Limit length
            return title[:500] if title else None
    
    return None


def _normalize_creator(data: Dict) -> Optional[str]:
    """Extract and normalize creator/author."""
    # Try common field names
    creator_fields = [
        "creator", "author", "authors", "artist", "composer",
        "Creator", "Author", "writer", "by", "created_by",
        "author_name", "creator_name"
    ]
    
    for field in creator_fields:
        if field in data and data[field]:
            value = data[field]
            
            # Handle list of authors
            if isinstance(value, list):
                if len(value) > 0:
                    # Join first 3 authors
                    authors = [str(a).strip() for a in value[:3] if a]
                    if len(value) > 3:
                        authors.append("et al.")
                    return ", ".join(authors)
            else:
                creator = str(value).strip()
                # Clean up common patterns
                creator = re.sub(r'\s+', ' ', creator)
                return creator[:200] if creator else None
    
    return None


def _normalize_year(data: Dict) -> Optional[int]:
    """Extract and normalize publication year."""
    # Try common field names
    year_fields = [
        "publication_year", "year", "publish_year", "pub_year",
        "date", "publish_date", "publication_date", "first_publish_year",
        "Year", "Date", "created_year", "release_year"
    ]
    
    for field in year_fields:
        if field in data and data[field]:
            year = _extract_year(data[field])
            if year:
                return year
    
    return None


def _extract_year(value: Any) -> Optional[int]:
    """Extract year from various formats."""
    if value is None:
        return None
    
    value_str = str(value).strip()
    
    # Try direct integer conversion
    if value_str.isdigit():
        year = int(value_str)
        if 1000 <= year <= datetime.now().year + 5:
            return year
    
    # Try to find 4-digit year in string
    match = re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', value_str)
    if match:
        year = int(match.group(1))
        if 1000 <= year <= datetime.now().year + 5:
            return year
    
    return None


def _normalize_content_type(data: Dict) -> str:
    """Extract and normalize content type."""
    # Try common field names
    type_fields = [
        "content_type", "type", "work_type", "media_type",
        "Type", "category", "format", "kind"
    ]
    
    for field in type_fields:
        if field in data and data[field]:
            raw_type = str(data[field]).lower().strip()
            
            # Map to standard type
            for key, standard_type in CONTENT_TYPE_MAP.items():
                if key in raw_type:
                    return standard_type
            
            # Return cleaned raw type if no mapping found
            return raw_type[:50]
    
    return "unknown"


def _normalize_source(data: Dict) -> str:
    """Extract and normalize source name."""
    source_fields = ["source", "Source", "provider", "database", "origin"]
    
    for field in source_fields:
        if field in data and data[field]:
            return str(data[field]).strip()[:100]
    
    return "unknown"


def _normalize_url(data: Dict) -> Optional[str]:
    """Extract and normalize source URL."""
    url_fields = [
        "source_url", "url", "link", "href", "source_link",
        "URL", "Source_URL", "web_url", "reference_url"
    ]
    
    for field in url_fields:
        if field in data and data[field]:
            url = str(data[field]).strip()
            # Basic URL validation
            if url.startswith(('http://', 'https://')):
                return url[:500]
    
    return None


def _normalize_date(data: Dict) -> str:
    """Extract or generate last verified date."""
    date_fields = ["last_verified", "verified_date", "last_updated", "updated_at"]
    
    for field in date_fields:
        if field in data and data[field]:
            # Try to parse and reformat date
            try:
                date_str = str(data[field])
                # Already in correct format
                if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    return date_str
            except:
                pass
    
    # Default to current date
    return datetime.now().strftime("%Y-%m-%d")


def _normalize_confidence(data: Dict) -> float:
    """Extract or calculate confidence score."""
    confidence_fields = [
        "confidence_score", "confidence", "score", "relevance",
        "similarity_score", "match_score"
    ]
    
    for field in confidence_fields:
        if field in data:
            try:
                score = float(data[field])
                # Ensure 0-1 range
                if score > 1:
                    score = score / 100  # Assume percentage
                return max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                pass
    
    # Calculate based on data completeness
    completeness = 0.0
    if data.get("title"):
        completeness += 0.3
    if data.get("creator") or data.get("author"):
        completeness += 0.25
    if data.get("publication_year") or data.get("year"):
        completeness += 0.2
    if data.get("source_url") or data.get("url"):
        completeness += 0.15
    if data.get("content_type") or data.get("type"):
        completeness += 0.1
    
    return completeness
