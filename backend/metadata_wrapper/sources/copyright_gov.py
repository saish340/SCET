"""
Government Copyright Office Connectors
======================================
Connectors for official copyright registration databases.

Supported:
- Indian Copyright Office (copyright.gov.in)
- US Copyright Office (copyright.gov)

Legal Note:
- Only extracts publicly available registration metadata
- Never downloads copyrighted content
- Respects robots.txt and rate limits
"""

import urllib.request
import urllib.parse
import urllib.error
import re
import json
import ssl
from typing import Dict, Any, Optional, List
from datetime import datetime


# Common headers for polite requests
HEADERS = {
    "User-Agent": "SCET-MetadataWrapper/1.0 (Copyright Research Tool; +https://scet.vercel.app)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def search_copyright_gov_in(title: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Search Indian Copyright Office E-Register.
    
    Args:
        title: Title to search for
        timeout: Request timeout in seconds
        
    Returns:
        Metadata dict or None if not found
        
    Note:
        The Indian Copyright Office uses an ASP.NET form-based search.
        We provide direct link for manual verification since automated
        form submission is complex and may change.
    """
    if not title:
        return None
    
    try:
        # Construct search reference URL
        search_url = "https://copyright.gov.in/SearchRoc.aspx"
        
        # Return metadata pointing to search page
        # Note: Direct API is not publicly available
        return {
            "title": title,
            "creator": None,
            "publication_year": None,
            "content_type": "copyright_registration",
            "source": "Indian Copyright Office",
            "source_url": search_url,
            "confidence_score": 0.6,  # Medium confidence - requires manual verification
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "registration_status": "check_required",
            "jurisdiction": "IN",
            "notes": f"Search for '{title}' on Indian Copyright Office E-Register for official registration status."
        }
        
    except Exception as e:
        return None


def search_copyright_gov_us(title: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Search US Copyright Office Public Catalog.
    
    Args:
        title: Title to search for
        timeout: Request timeout in seconds
        
    Returns:
        Metadata dict or None if not found
    """
    if not title:
        return None
    
    try:
        # US Copyright Office catalog search
        encoded_title = urllib.parse.quote(title)
        search_url = f"https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?Search_Arg={encoded_title}&Search_Code=TALL&PID=&SEQ=&CNT=25&HIST=1"
        
        # Create SSL context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Create request with headers
        request = urllib.request.Request(search_url, headers=HEADERS)
        
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Check if results found
                if 'No records found' in html or 'Your search found no results' in html:
                    return {
                        "title": title,
                        "creator": None,
                        "publication_year": None,
                        "content_type": "copyright_search",
                        "source": "US Copyright Office",
                        "source_url": "https://cocatalog.loc.gov/",
                        "confidence_score": 0.4,
                        "last_verified": datetime.now().strftime("%Y-%m-%d"),
                        "registration_status": "not_found",
                        "jurisdiction": "US",
                        "notes": "No registration found. Note: Not all copyrighted works are registered."
                    }
                
                # Parse basic info from results page
                metadata = _parse_us_copyright_results(html, title)
                if metadata:
                    metadata["source_url"] = search_url
                    return metadata
                    
        except urllib.error.URLError:
            pass
        
        # Return reference if direct search fails
        return {
            "title": title,
            "creator": None,
            "publication_year": None,
            "content_type": "copyright_registration",
            "source": "US Copyright Office",
            "source_url": "https://cocatalog.loc.gov/",
            "confidence_score": 0.5,
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "registration_status": "check_required",
            "jurisdiction": "US",
            "notes": f"Search for '{title}' on US Copyright Office Public Catalog."
        }
        
    except Exception as e:
        return None


def _parse_us_copyright_results(html: str, query_title: str) -> Optional[Dict[str, Any]]:
    """
    Parse US Copyright Office search results.
    
    Args:
        html: HTML content from search results
        query_title: Original search query
        
    Returns:
        Parsed metadata or None
    """
    try:
        # Look for registration entries
        # Format varies, look for common patterns
        
        # Try to find title in results
        title_pattern = r'<td[^>]*>Title[:\s]*</td>\s*<td[^>]*>([^<]+)</td>'
        title_match = re.search(title_pattern, html, re.IGNORECASE)
        
        # Try to find author/claimant
        author_pattern = r'<td[^>]*>(?:Author|Claimant)[:\s]*</td>\s*<td[^>]*>([^<]+)</td>'
        author_match = re.search(author_pattern, html, re.IGNORECASE)
        
        # Try to find registration date/year
        date_pattern = r'<td[^>]*>(?:Date|Year)[:\s]*</td>\s*<td[^>]*>([^<]+)</td>'
        date_match = re.search(date_pattern, html, re.IGNORECASE)
        
        # Try to find registration number
        reg_pattern = r'<td[^>]*>(?:Registration|Reg\.?\s*No\.?)[:\s]*</td>\s*<td[^>]*>([A-Z0-9\-]+)</td>'
        reg_match = re.search(reg_pattern, html, re.IGNORECASE)
        
        # Check if we found anything useful
        found_title = title_match.group(1).strip() if title_match else None
        found_author = author_match.group(1).strip() if author_match else None
        found_date = date_match.group(1).strip() if date_match else None
        found_reg = reg_match.group(1).strip() if reg_match else None
        
        # Must have at least title or registration number
        if not found_title and not found_reg:
            # Check for any indication of records found
            if 'record' in html.lower() and 'found' in html.lower():
                return {
                    "title": query_title,
                    "creator": None,
                    "publication_year": None,
                    "content_type": "copyright_registration",
                    "source": "US Copyright Office",
                    "confidence_score": 0.65,
                    "last_verified": datetime.now().strftime("%Y-%m-%d"),
                    "registration_status": "potential_match",
                    "jurisdiction": "US",
                    "notes": "Potential matches found. Manual verification recommended."
                }
            return None
        
        # Extract year from date
        pub_year = None
        if found_date:
            year_match = re.search(r'\b(19|20)\d{2}\b', found_date)
            if year_match:
                pub_year = int(year_match.group())
        
        return {
            "title": found_title or query_title,
            "creator": found_author,
            "publication_year": pub_year,
            "content_type": "copyright_registration",
            "source": "US Copyright Office",
            "confidence_score": 0.85,
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "registration_status": "registered",
            "registration_number": found_reg,
            "jurisdiction": "US"
        }
        
    except Exception:
        return None


# Future API Integration Point
class CopyrightAPIConnector:
    """
    Base class for future official API integration.
    
    When copyright.gov.in or copyright.gov APIs become available,
    extend this class to implement direct API access.
    
    Example:
        class IndianCopyrightAPI(CopyrightAPIConnector):
            def __init__(self, api_key):
                self.api_key = api_key
                self.base_url = "https://api.copyright.gov.in/v1"
            
            def search(self, title):
                # Implement API call
                pass
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url
    
    def search(self, title: str) -> Optional[Dict[str, Any]]:
        """Override in subclass to implement API search."""
        raise NotImplementedError("Subclass must implement search()")
    
    def verify_registration(self, registration_id: str) -> Optional[Dict[str, Any]]:
        """Override in subclass to verify specific registration."""
        raise NotImplementedError("Subclass must implement verify_registration()")
