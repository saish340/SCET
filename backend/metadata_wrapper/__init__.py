"""
SCET Metadata Wrapper Module
============================
A modular metadata acquisition layer for enhancing copyright status accuracy.

This module:
- Fetches copyright metadata from official and public sources
- Extracts ONLY metadata (never copyrighted content)
- Normalizes metadata into standard internal format
- Integrates safely with existing SCET search pipeline

Legal Compliance:
- Only extracts factual metadata
- Never stores copyrighted content
- Respects robots.txt and rate limits
"""

from .wrapper import MetadataWrapper, fetch_metadata, get_enriched_metadata
from .normalizer import normalize_metadata
from .validator import validate_metadata

__version__ = "1.0.0"
__all__ = [
    "MetadataWrapper",
    "fetch_metadata", 
    "get_enriched_metadata",
    "normalize_metadata",
    "validate_metadata"
]
