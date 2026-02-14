"""
Metadata Wrapper Controller
===========================
Main controller for fetching and aggregating metadata from multiple sources.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .normalizer import normalize_metadata
from .validator import validate_metadata
from .sources import (
    search_copyright_gov_in,
    search_copyright_gov_us,
    search_wikipedia,
    search_openlibrary,
    search_publishers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataWrapper:
    """
    Main Metadata Wrapper class for fetching and aggregating copyright metadata.
    
    Features:
    - Multi-source metadata fetching
    - Priority-based source selection
    - Automatic normalization and validation
    - Graceful failure handling
    - Rate limiting and timeout protection
    """
    
    # Source priority (higher = more authoritative)
    SOURCE_PRIORITIES = {
        "Indian Copyright Office": 100,
        "US Copyright Office": 95,
        "Official Publisher": 85,
        "Open Library": 75,
        "Wikipedia": 60,
        "Other": 30
    }
    
    # Configuration
    DEFAULT_TIMEOUT = 10  # seconds per source
    MAX_WORKERS = 5  # concurrent source queries
    MIN_CONFIDENCE_THRESHOLD = 0.3
    
    def __init__(self, timeout: int = None, max_workers: int = None):
        """
        Initialize the Metadata Wrapper.
        
        Args:
            timeout: Request timeout in seconds (default: 10)
            max_workers: Max concurrent source queries (default: 5)
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_workers = max_workers or self.MAX_WORKERS
        self._last_request_time = {}
        self._rate_limit_delay = 1.0  # seconds between requests to same source
    
    def _get_source_priority(self, source: str) -> int:
        """Get priority score for a metadata source."""
        for key, priority in self.SOURCE_PRIORITIES.items():
            if key.lower() in source.lower():
                return priority
        return self.SOURCE_PRIORITIES["Other"]
    
    def _rate_limit(self, source: str):
        """Apply rate limiting for polite requests."""
        now = time.time()
        if source in self._last_request_time:
            elapsed = now - self._last_request_time[source]
            if elapsed < self._rate_limit_delay:
                time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time[source] = time.time()
    
    def _fetch_from_source(self, source_func, title: str, source_name: str) -> Optional[Dict]:
        """
        Fetch metadata from a single source with error handling.
        
        Args:
            source_func: The source connector function
            title: Title to search for
            source_name: Name of the source for logging
            
        Returns:
            Normalized metadata dict or None on failure
        """
        try:
            self._rate_limit(source_name)
            logger.info(f"Fetching metadata from {source_name} for: {title}")
            
            raw_data = source_func(title, timeout=self.timeout)
            
            if not raw_data:
                logger.debug(f"No data from {source_name}")
                return None
            
            # Handle list of results
            if isinstance(raw_data, list):
                results = []
                for item in raw_data[:5]:  # Limit to top 5 results
                    normalized = normalize_metadata(item)
                    if validate_metadata(normalized):
                        results.append(normalized)
                return results if results else None
            
            # Handle single result
            normalized = normalize_metadata(raw_data)
            if validate_metadata(normalized):
                return normalized
            
            logger.debug(f"Validation failed for {source_name} data")
            return None
            
        except Exception as e:
            logger.warning(f"Error fetching from {source_name}: {str(e)}")
            return None
    
    def fetch_metadata(self, title: str, content_type: str = None, 
                       jurisdiction: str = None) -> Dict[str, Any]:
        """
        Fetch metadata from multiple sources and return best match.
        
        Args:
            title: The title to search for
            content_type: Optional content type filter (book, music, film, etc.)
            jurisdiction: Optional jurisdiction (US, IN, EU, etc.)
            
        Returns:
            Best metadata match with confidence score
        """
        if not title or not title.strip():
            return self._empty_result("Empty title provided")
        
        title = title.strip()
        all_results = []
        
        # Define sources to query based on jurisdiction
        sources = [
            (search_openlibrary, "Open Library"),
            (search_wikipedia, "Wikipedia"),
        ]
        
        # Add jurisdiction-specific sources
        if jurisdiction == "IN" or not jurisdiction:
            sources.append((search_copyright_gov_in, "Indian Copyright Office"))
        if jurisdiction == "US" or not jurisdiction:
            sources.append((search_copyright_gov_us, "US Copyright Office"))
        
        # Add publisher search
        sources.append((search_publishers, "Official Publisher"))
        
        # Fetch from all sources concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {
                executor.submit(self._fetch_from_source, func, title, name): name
                for func, name in sources
            }
            
            for future in as_completed(future_to_source, timeout=self.timeout * 2):
                source_name = future_to_source[future]
                try:
                    result = future.result()
                    if result:
                        if isinstance(result, list):
                            all_results.extend(result)
                        else:
                            all_results.append(result)
                except Exception as e:
                    logger.warning(f"Source {source_name} failed: {e}")
        
        if not all_results:
            return self._empty_result("No metadata found from any source")
        
        # Score and rank results
        scored_results = self._score_results(all_results, title, content_type)
        
        # Return best match
        best_match = scored_results[0] if scored_results else None
        
        if best_match and best_match.get("confidence_score", 0) >= self.MIN_CONFIDENCE_THRESHOLD:
            best_match["last_verified"] = datetime.now().strftime("%Y-%m-%d")
            return {
                "success": True,
                "metadata": best_match,
                "alternatives": scored_results[1:5] if len(scored_results) > 1 else [],
                "sources_checked": len(sources)
            }
        
        return self._empty_result("No confident matches found")
    
    def _score_results(self, results: List[Dict], query_title: str, 
                       content_type: str = None) -> List[Dict]:
        """
        Score and rank metadata results.
        
        Args:
            results: List of normalized metadata dicts
            query_title: Original query title
            content_type: Optional content type filter
            
        Returns:
            Sorted list of results by score (descending)
        """
        scored = []
        query_lower = query_title.lower()
        
        for result in results:
            score = result.get("confidence_score", 0.5)
            
            # Boost for source priority
            source_priority = self._get_source_priority(result.get("source", ""))
            score += source_priority / 200  # Max +0.5 boost
            
            # Boost for title match
            result_title = result.get("title", "").lower()
            if query_lower == result_title:
                score += 0.3  # Exact match
            elif query_lower in result_title or result_title in query_lower:
                score += 0.15  # Partial match
            
            # Boost for content type match
            if content_type and result.get("content_type", "").lower() == content_type.lower():
                score += 0.1
            
            # Boost for having creator info
            if result.get("creator"):
                score += 0.05
            
            # Boost for having publication year
            if result.get("publication_year"):
                score += 0.05
            
            # Cap at 1.0
            result["confidence_score"] = min(score, 1.0)
            scored.append(result)
        
        # Sort by score descending
        return sorted(scored, key=lambda x: x.get("confidence_score", 0), reverse=True)
    
    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return empty result with reason."""
        return {
            "success": False,
            "metadata": None,
            "alternatives": [],
            "reason": reason,
            "sources_checked": 0
        }


# Module-level convenience functions

_wrapper_instance = None

def _get_wrapper() -> MetadataWrapper:
    """Get or create singleton wrapper instance."""
    global _wrapper_instance
    if _wrapper_instance is None:
        _wrapper_instance = MetadataWrapper()
    return _wrapper_instance


def fetch_metadata(title: str, content_type: str = None, 
                   jurisdiction: str = None) -> Dict[str, Any]:
    """
    Fetch metadata for a title from multiple sources.
    
    Args:
        title: The title to search for
        content_type: Optional content type (book, music, film, etc.)
        jurisdiction: Optional jurisdiction (US, IN, EU, etc.)
        
    Returns:
        Dict with metadata and alternatives
    """
    return _get_wrapper().fetch_metadata(title, content_type, jurisdiction)


def get_enriched_metadata(title: str, content_type: str = None,
                          jurisdiction: str = None) -> Dict[str, Any]:
    """
    Get enriched metadata in standard SCET format.
    
    This is the main integration point for existing SCET pipeline.
    
    Args:
        title: The title to search for
        content_type: Optional content type
        jurisdiction: Optional jurisdiction
        
    Returns:
        Standardized metadata dict or None if not found
        
    Example output:
        {
            "title": "Harry Potter and the Philosopher's Stone",
            "creator": "J.K. Rowling",
            "publication_year": 1997,
            "content_type": "book",
            "source": "Open Library",
            "source_url": "https://openlibrary.org/...",
            "confidence_score": 0.94,
            "last_verified": "2026-02-14"
        }
    """
    result = fetch_metadata(title, content_type, jurisdiction)
    
    if result.get("success") and result.get("metadata"):
        return result["metadata"]
    
    # Return minimal fallback if no metadata found
    return {
        "title": title,
        "creator": None,
        "publication_year": None,
        "content_type": content_type or "unknown",
        "source": "user_input",
        "source_url": None,
        "confidence_score": 0.1,
        "last_verified": datetime.now().strftime("%Y-%m-%d")
    }
