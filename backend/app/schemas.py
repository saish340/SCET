"""
Pydantic Schemas for API Request/Response validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    # Creative Works (Traditional Copyright)
    BOOK = "book"
    MUSIC = "music"
    FILM = "film"
    ARTICLE = "article"
    IMAGE = "image"
    ARTWORK = "artwork"
    
    # Software & Code (Open Source Licenses)
    SOFTWARE = "software"
    CODE = "code"
    LIBRARY = "library"
    
    # Intellectual Property (Different Legal Systems)
    PATENT = "patent"
    TRADEMARK = "trademark"
    DESIGN = "design"  # Industrial design
    
    # Other
    PERSONAL_PROJECT = "personal_project"
    ACADEMIC_PAPER = "academic_paper"
    DATASET = "dataset"
    VIDEO_GAME = "video_game"


class LicenseType(str, Enum):
    """License types for software and open source"""
    MIT = "MIT"
    GPL_V2 = "GPL-2.0"
    GPL_V3 = "GPL-3.0"
    APACHE_2 = "Apache-2.0"
    BSD_2 = "BSD-2-Clause"
    BSD_3 = "BSD-3-Clause"
    LGPL = "LGPL"
    MPL = "MPL-2.0"
    UNLICENSE = "Unlicense"
    CC0 = "CC0-1.0"
    CC_BY = "CC-BY-4.0"
    CC_BY_SA = "CC-BY-SA-4.0"
    CC_BY_NC = "CC-BY-NC-4.0"
    PROPRIETARY = "Proprietary"
    UNKNOWN = "Unknown"


class IPStatus(str, Enum):
    """Status for patents and trademarks"""
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    REGISTERED = "registered"
    UNKNOWN = "unknown"


class CopyrightStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PUBLIC_DOMAIN = "public_domain"
    UNKNOWN = "unknown"
    LIKELY_ACTIVE = "likely_active"
    LIKELY_EXPIRED = "likely_expired"


class AllowedUse(str, Enum):
    PERSONAL = "personal"
    EDUCATIONAL = "educational"
    COMMERCIAL = "commercial"
    REMIX = "remix"
    DERIVATIVE = "derivative"
    DISTRIBUTION = "distribution"


# ============ Search Schemas ============

class SearchRequest(BaseModel):
    """Request for AI-based title search"""
    query: str = Field(..., min_length=1, max_length=500, description="Title or partial title to search")
    content_type: Optional[ContentType] = Field(None, description="Filter by content type")
    max_results: int = Field(10, ge=1, le=50, description="Maximum results to return")
    include_similar: bool = Field(True, description="Include semantically similar results")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class SearchResult(BaseModel):
    """Single search result"""
    id: int
    title: str
    creator: Optional[str]
    publication_year: Optional[int]
    content_type: Optional[str]
    copyright_status: str
    similarity_score: float = Field(..., ge=0, le=1)
    source: Optional[str]
    
    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Response containing search results"""
    query: str
    corrected_query: Optional[str] = None  # After spell correction
    results: List[SearchResult]
    total_found: int
    search_time_ms: int
    ai_explanation: str  # AI reasoning about results
    suggestions: List[str] = []  # Related searches


# ============ Copyright Analysis Schemas ============

class CopyrightAnalysisRequest(BaseModel):
    """Request for copyright analysis"""
    work_id: Optional[int] = None
    title: Optional[str] = None
    creator: Optional[str] = None
    publication_year: Optional[int] = None
    content_type: Optional[ContentType] = None
    jurisdiction: str = Field("US", description="Jurisdiction for copyright rules")


class AllowedUsage(BaseModel):
    """Details about allowed usage"""
    use_type: AllowedUse
    is_allowed: bool
    conditions: Optional[str] = None
    confidence: float


class CopyrightAnalysisResponse(BaseModel):
    """Detailed copyright analysis response"""
    work_title: str
    creator: Optional[str]
    publication_year: Optional[int]
    content_type: Optional[str]
    
    # Copyright status
    status: CopyrightStatus
    expiry_date: Optional[datetime]
    years_until_expiry: Optional[int]
    
    # Allowed uses
    allowed_uses: List[AllowedUsage]
    
    # AI Analysis
    confidence_score: float = Field(..., ge=0, le=1)
    reasoning: str  # Explanation of how status was determined
    uncertainties: List[str]  # Factors that reduce confidence
    
    # Legal disclaimer
    disclaimer: str
    jurisdiction: str


# ============ Smart Copyright Expiry Tag ============

class SmartTag(BaseModel):
    """The Smart Copyright Expiry Tag output"""
    # Basic Info
    title: str
    creator: Optional[str]
    publication_year: Optional[int]
    content_type: Optional[str]
    
    # Copyright Status (emoji-based for readability)
    status_emoji: str  # ❌, ✅, 🔁, 🌍
    status_text: str
    status_color: str  # red, green, yellow, blue
    
    # Timeline
    expiry_date: Optional[str]
    expiry_timeline: str  # "Expired 20 years ago", "Expires in 30 years"
    
    # Allowed Uses Summary
    allowed_uses_summary: List[str]
    
    # Confidence
    confidence_score: float
    confidence_level: str  # High, Medium, Low
    
    # AI Explanation
    ai_reasoning: str
    data_sources: List[str]
    
    # Metadata
    generated_at: datetime
    tag_version: str
    auto_update_enabled: bool
    next_verification_date: Optional[datetime]
    
    # Legal
    disclaimer: str
    jurisdiction: str


class SmartTagRequest(BaseModel):
    """Request to generate Smart Tag"""
    query: str = Field(..., description="Title to generate tag for")
    content_type: Optional[ContentType] = None
    jurisdiction: str = Field("US", description="Jurisdiction for copyright rules")
    include_ai_reasoning: bool = True


# ============ Data Collection Schemas ============

class DataCollectionStatus(BaseModel):
    """Status of data collection process"""
    is_running: bool
    total_sources_checked: int
    new_entries_found: int
    last_run_at: Optional[datetime]
    next_scheduled_run: Optional[datetime]
    current_source: Optional[str]


class CollectedWorkData(BaseModel):
    """Data collected from web sources"""
    title: str
    creator: Optional[str]
    publication_year: Optional[int]
    content_type: Optional[str]
    source_url: str
    source_name: str
    raw_data: Dict[str, Any]
    extraction_confidence: float


# ============ ML Model Schemas ============

class ModelStatus(BaseModel):
    """ML Model status information"""
    model_name: str
    model_type: str
    version: str
    is_active: bool
    training_samples: int
    accuracy: Optional[float]
    last_trained: Optional[datetime]
    next_retrain_at: Optional[int]  # After N more samples


class TrainingFeedback(BaseModel):
    """User feedback for model improvement"""
    search_id: int
    selected_result_id: int
    was_correct: bool
    correct_answer: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)


# ============ System Schemas ============

class HealthCheck(BaseModel):
    """System health check response"""
    status: str
    version: str
    database_connected: bool
    ml_models_loaded: bool
    data_collection_active: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str]
    code: str
    timestamp: datetime
