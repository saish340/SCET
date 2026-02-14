"""
Metadata Source Connectors
==========================
Individual connectors for each metadata source.

Each connector:
- Fetches metadata from a specific source
- Returns raw metadata dict
- Handles errors gracefully
- Respects rate limits and timeouts
"""

from .copyright_gov import search_copyright_gov_in, search_copyright_gov_us
from .wikipedia import search_wikipedia
from .openlibrary import search_openlibrary
from .publishers import search_publishers

__all__ = [
    "search_copyright_gov_in",
    "search_copyright_gov_us", 
    "search_wikipedia",
    "search_openlibrary",
    "search_publishers"
]
