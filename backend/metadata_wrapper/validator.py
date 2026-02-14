"""
Metadata Validator
==================
Validates normalized metadata for quality and completeness.
"""

import re
from typing import Dict, Any, List, Tuple
from datetime import datetime


# Validation thresholds
MIN_TITLE_LENGTH = 2
MAX_TITLE_LENGTH = 500
MIN_CONFIDENCE_THRESHOLD = 0.1
CURRENT_YEAR = datetime.now().year


def validate_metadata(metadata: Dict[str, Any]) -> bool:
    """
    Validate metadata for minimum quality requirements.
    
    Args:
        metadata: Normalized metadata dict
        
    Returns:
        True if metadata passes validation, False otherwise
    """
    if not metadata or not isinstance(metadata, dict):
        return False
    
    # Must have title
    if not _validate_title(metadata.get("title")):
        return False
    
    # Must have minimum confidence
    confidence = metadata.get("confidence_score", 0)
    if not isinstance(confidence, (int, float)) or confidence < MIN_CONFIDENCE_THRESHOLD:
        return False
    
    # Validate optional fields if present
    if metadata.get("publication_year"):
        if not _validate_year(metadata["publication_year"]):
            return False
    
    if metadata.get("source_url"):
        if not _validate_url(metadata["source_url"]):
            return False
    
    return True


def validate_metadata_strict(metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Perform strict validation with detailed error reporting.
    
    Args:
        metadata: Normalized metadata dict
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not metadata or not isinstance(metadata, dict):
        return False, ["Invalid metadata format"]
    
    # Title validation
    title = metadata.get("title")
    if not title:
        errors.append("Missing title")
    elif not _validate_title(title):
        errors.append(f"Invalid title: too short or too long")
    
    # Creator validation (warning only)
    creator = metadata.get("creator")
    if not creator:
        errors.append("Warning: Missing creator/author information")
    
    # Year validation
    year = metadata.get("publication_year")
    if year and not _validate_year(year):
        errors.append(f"Invalid publication year: {year}")
    
    # Content type validation
    content_type = metadata.get("content_type")
    if not content_type or content_type == "unknown":
        errors.append("Warning: Unknown content type")
    
    # Source validation
    source = metadata.get("source")
    if not source or source == "unknown":
        errors.append("Warning: Unknown source")
    
    # URL validation
    url = metadata.get("source_url")
    if url and not _validate_url(url):
        errors.append(f"Invalid source URL format")
    
    # Confidence validation
    confidence = metadata.get("confidence_score", 0)
    if not isinstance(confidence, (int, float)):
        errors.append("Invalid confidence score format")
    elif confidence < MIN_CONFIDENCE_THRESHOLD:
        errors.append(f"Confidence score too low: {confidence}")
    
    # Date validation
    last_verified = metadata.get("last_verified")
    if last_verified and not _validate_date(last_verified):
        errors.append(f"Invalid date format: {last_verified}")
    
    # Filter out warnings for strict validation result
    critical_errors = [e for e in errors if not e.startswith("Warning:")]
    
    return len(critical_errors) == 0, errors


def _validate_title(title: Any) -> bool:
    """Validate title field."""
    if not title or not isinstance(title, str):
        return False
    
    title = title.strip()
    
    if len(title) < MIN_TITLE_LENGTH:
        return False
    
    if len(title) > MAX_TITLE_LENGTH:
        return False
    
    # Check for obviously invalid titles
    invalid_patterns = [
        r'^[0-9]+$',  # Only numbers
        r'^[^a-zA-Z0-9]+$',  # Only special chars
        r'^(null|none|undefined|n/a)$',  # Null values
    ]
    
    title_lower = title.lower()
    for pattern in invalid_patterns:
        if re.match(pattern, title_lower):
            return False
    
    return True


def _validate_year(year: Any) -> bool:
    """Validate publication year."""
    try:
        year_int = int(year)
        # Reasonable year range: 1000 AD to 5 years in future
        return 1000 <= year_int <= CURRENT_YEAR + 5
    except (ValueError, TypeError):
        return False


def _validate_url(url: Any) -> bool:
    """Validate URL format."""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    # Must start with http:// or https://
    if not url.startswith(('http://', 'https://')):
        return False
    
    # Basic URL pattern check
    url_pattern = r'^https?://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+.*$'
    return bool(re.match(url_pattern, url))


def _validate_date(date_str: Any) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    if not date_str or not isinstance(date_str, str):
        return False
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def calculate_quality_score(metadata: Dict[str, Any]) -> float:
    """
    Calculate overall quality score for metadata.
    
    Args:
        metadata: Normalized metadata dict
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    if not metadata:
        return 0.0
    
    score = 0.0
    
    # Title (30%)
    if _validate_title(metadata.get("title")):
        score += 0.30
    
    # Creator (20%)
    creator = metadata.get("creator")
    if creator and isinstance(creator, str) and len(creator.strip()) > 1:
        score += 0.20
    
    # Publication year (15%)
    if _validate_year(metadata.get("publication_year")):
        score += 0.15
    
    # Content type (10%)
    content_type = metadata.get("content_type")
    if content_type and content_type != "unknown":
        score += 0.10
    
    # Source (10%)
    source = metadata.get("source")
    if source and source != "unknown":
        score += 0.10
    
    # Source URL (10%)
    if _validate_url(metadata.get("source_url")):
        score += 0.10
    
    # Confidence already set (5%)
    confidence = metadata.get("confidence_score", 0)
    if isinstance(confidence, (int, float)) and confidence > 0:
        score += 0.05
    
    return min(score, 1.0)
