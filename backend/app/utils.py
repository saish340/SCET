"""
Utility functions for SCET
Text processing, normalization, and helper functions
"""

import re
import unicodedata
from typing import Optional, List, Tuple
from datetime import datetime
import hashlib


def normalize_title(title: str) -> str:
    """
    Normalize title for consistent searching and matching
    - Lowercase
    - Remove special characters
    - Normalize unicode
    - Remove extra whitespace
    """
    if not title:
        return ""
    
    # Unicode normalization
    title = unicodedata.normalize('NFKD', title)
    
    # Lowercase
    title = title.lower()
    
    # Remove special characters but keep spaces and basic punctuation
    title = re.sub(r'[^\w\s\-\']', '', title)
    
    # Normalize whitespace
    title = ' '.join(title.split())
    
    return title.strip()


def normalize_creator_name(name: str) -> str:
    """Normalize creator/author name"""
    if not name:
        return ""
    
    name = unicodedata.normalize('NFKD', name)
    name = name.lower()
    
    # Remove titles like Dr., Mr., Mrs., etc.
    titles = ['dr.', 'mr.', 'mrs.', 'ms.', 'prof.', 'sir', 'dame']
    for title in titles:
        name = name.replace(title, '')
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name.strip()


def extract_year_from_text(text: str) -> Optional[int]:
    """Extract publication year from text"""
    if not text:
        return None
    
    # Look for 4-digit years between 1000 and current year + 1
    current_year = datetime.now().year
    year_pattern = r'\b(1[0-9]{3}|20[0-2][0-9])\b'
    
    matches = re.findall(year_pattern, text)
    
    if matches:
        # Return the most likely publication year (usually the first reasonable one)
        for match in matches:
            year = int(match)
            if 1400 <= year <= current_year + 1:
                return year
    
    return None


def calculate_text_hash(text: str) -> str:
    """Calculate hash for text deduplication"""
    normalized = normalize_title(text)
    return hashlib.md5(normalized.encode()).hexdigest()


def parse_date_flexible(date_string: str) -> Optional[datetime]:
    """Parse dates in various formats"""
    if not date_string:
        return None
    
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%B %d, %Y',
        '%b %d, %Y',
        '%Y',
        '%m/%d/%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    
    # Try to extract just the year
    year = extract_year_from_text(date_string)
    if year:
        return datetime(year, 1, 1)
    
    return None


def estimate_death_year(birth_year: Optional[int], known_active_year: Optional[int] = None) -> Optional[int]:
    """
    Estimate author death year if unknown
    Used for copyright calculation when death year is not available
    Returns None if estimation is too uncertain
    """
    current_year = datetime.now().year
    
    if birth_year:
        # Assume average lifespan of 75 years
        estimated_death = birth_year + 75
        
        # If the person would be over 120, they're likely deceased
        if current_year - birth_year > 120:
            return min(estimated_death, birth_year + 100)
        
        # If they would be a reasonable age, return None (might still be alive)
        if current_year - birth_year < 100:
            return None
    
    if known_active_year:
        # If we know they were active in a certain year, estimate from there
        if current_year - known_active_year > 100:
            return known_active_year + 50  # Rough estimate
    
    return None


def format_years_duration(years: int) -> str:
    """Format years into human-readable duration"""
    if years < 0:
        abs_years = abs(years)
        if abs_years == 1:
            return "1 year ago"
        return f"{abs_years} years ago"
    elif years == 0:
        return "this year"
    elif years == 1:
        return "in 1 year"
    else:
        return f"in {years} years"


def clean_html(html_text: str) -> str:
    """Remove HTML tags and clean text"""
    if not html_text:
        return ""
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', html_text)
    
    # Decode common HTML entities
    entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
    }
    for entity, char in entities.items():
        clean = clean.replace(entity, char)
    
    # Normalize whitespace
    clean = ' '.join(clean.split())
    
    return clean.strip()


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if not text or len(text) <= max_length:
        return text or ""
    
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix


def generate_session_id() -> str:
    """Generate unique session ID"""
    import uuid
    return str(uuid.uuid4())


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings (0-1)"""
    if not s1 or not s2:
        return 0.0
    
    s1 = normalize_title(s1)
    s2 = normalize_title(s2)
    
    if s1 == s2:
        return 1.0
    
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    
    return 1 - (distance / max_len)


def detect_content_type(text: str, title: str = "") -> Optional[str]:
    """Attempt to detect content type from text clues"""
    combined = f"{title} {text}".lower()
    
    indicators = {
        'book': ['book', 'novel', 'author', 'publisher', 'isbn', 'chapter', 'edition', 'paperback', 'hardcover', 'literary'],
        'music': ['song', 'album', 'artist', 'track', 'music', 'composer', 'lyrics', 'record', 'single', 'band', 'musician'],
        'film': ['film', 'movie', 'director', 'starring', 'cinema', 'screenplay', 'runtime', 'box office', 'actor', 'actress'],
        'article': ['article', 'journal', 'published in', 'doi', 'abstract', 'citation'],
        'image': ['photograph', 'photo', 'image', 'painting', 'artwork', 'illustration', 'gallery'],
        'software': ['software', 'program', 'application', 'code', 'license', 'version', 'github', 'repository', 'library', 'framework', 'api', 'npm', 'pip', 'package'],
        'patent': ['patent', 'invention', 'inventor', 'claims', 'apparatus', 'method', 'device', 'system', 'utility', 'granted', 'filing', 'assignee', 'prior art'],
        'trademark': ['trademark', 'brand', 'registered', 'logo', 'service mark', 'trade name', 'corporation', 'company'],
        'academic_paper': ['research', 'study', 'paper', 'thesis', 'dissertation', 'peer-reviewed', 'academic', 'university', 'professor', 'phd'],
    }
    
    scores = {}
    for content_type, keywords in indicators.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[content_type] = score
    
    if scores:
        return max(scores, key=scores.get)
    
    return None
