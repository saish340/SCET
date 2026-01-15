"""
Database Models for SCET
Stores metadata only - NO copyrighted content
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, 
    Boolean, JSON, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class WorkMetadata(Base):
    """
    Stores metadata about creative works (books, music, films, etc.)
    This is dynamically collected from web sources - NOT a static dataset
    """
    __tablename__ = "work_metadata"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core metadata
    title = Column(String(500), nullable=False, index=True)
    title_normalized = Column(String(500), index=True)  # Lowercase, cleaned for search
    creator = Column(String(300))  # Author, artist, director, etc.
    creator_death_year = Column(Integer, nullable=True)  # For copyright calculation
    publication_year = Column(Integer, nullable=True)
    content_type = Column(String(50))  # book, music, film, article, image
    
    # Source tracking
    source_url = Column(String(1000))  # Where we found this info
    source_name = Column(String(200))  # Wikipedia, OpenLibrary, etc.
    
    # Copyright analysis (ML-predicted + rule-based)
    copyright_status = Column(String(100))  # active, expired, public_domain, unknown
    expiry_date = Column(DateTime, nullable=True)
    jurisdiction = Column(String(50), default="US")
    
    # AI confidence scores
    data_confidence = Column(Float, default=0.5)  # How reliable is source data
    prediction_confidence = Column(Float, default=0.5)  # ML model confidence
    
    # Allowed uses (derived from copyright status)
    allowed_uses = Column(JSON, default=list)  # ['educational', 'personal', 'commercial', 'remix']
    
    # Embedding for semantic search (stored as JSON array)
    title_embedding = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_verified_at = Column(DateTime, nullable=True)  # Last time we re-checked source
    
    # Indexes for fast searching
    __table_args__ = (
        Index('idx_title_type', 'title_normalized', 'content_type'),
        Index('idx_creator', 'creator'),
        Index('idx_year', 'publication_year'),
    )


class SearchLog(Base):
    """
    Logs all searches for ML training and improvement
    Used for incremental learning
    """
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Search details
    query_text = Column(String(500), nullable=False)
    query_normalized = Column(String(500))
    corrected_query = Column(String(500), nullable=True)  # After spell correction
    
    # Results
    result_count = Column(Integer, default=0)
    top_result_id = Column(Integer, ForeignKey("work_metadata.id"), nullable=True)
    user_selected_id = Column(Integer, ForeignKey("work_metadata.id"), nullable=True)
    
    # For learning
    was_successful = Column(Boolean, default=True)
    feedback_score = Column(Integer, nullable=True)  # 1-5 rating if provided
    
    # Timing
    search_time_ms = Column(Integer)  # Response time
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Session tracking
    session_id = Column(String(100))


class MLModelState(Base):
    """
    Tracks ML model versions and training state
    For incremental learning management
    """
    __tablename__ = "ml_model_state"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    model_name = Column(String(100), nullable=False)
    model_type = Column(String(50))  # 'search', 'copyright_predictor', 'embeddings'
    
    # Version tracking
    version = Column(String(50))
    training_samples_count = Column(Integer, default=0)
    last_trained_at = Column(DateTime)
    
    # Performance metrics
    accuracy = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    
    # Model state (serialized)
    model_path = Column(String(500))
    hyperparameters = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CopyrightRule(Base):
    """
    Stores copyright rules by jurisdiction
    Used by the rule engine
    """
    __tablename__ = "copyright_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    jurisdiction = Column(String(50), nullable=False, unique=True)
    jurisdiction_name = Column(String(200))
    
    # Duration rules
    standard_duration_years = Column(Integer, default=70)  # After author death
    corporate_duration_years = Column(Integer, default=95)  # For corporate works
    anonymous_duration_years = Column(Integer, default=95)
    
    # Special rules
    public_domain_before_year = Column(Integer, nullable=True)  # Works before this are PD
    requires_registration = Column(Boolean, default=False)
    
    # Rule details
    rule_description = Column(Text)
    source_url = Column(String(500))
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataSource(Base):
    """
    Tracks data sources and their reliability
    """
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    name = Column(String(200), nullable=False)
    base_url = Column(String(500))
    source_type = Column(String(50))  # 'api', 'scrape', 'manual'
    
    # Reliability tracking
    reliability_score = Column(Float, default=0.7)
    total_fetches = Column(Integer, default=0)
    successful_fetches = Column(Integer, default=0)
    
    # Rate limiting
    requests_per_minute = Column(Integer, default=10)
    last_accessed = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
