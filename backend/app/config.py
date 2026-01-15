"""
SCET Configuration Module
Contains all system configurations, API keys placeholders, and settings
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "SCET - Smart Copyright Expiry Tag"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./scet_database.db"
    
    # ML Model Settings
    MODEL_PATH: Path = Path("./models")
    DATA_PATH: Path = Path("./data")
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    MIN_SIMILARITY_THRESHOLD: float = 0.6
    FUZZY_MATCH_THRESHOLD: int = 70
    
    # Data Collection Settings
    SCRAPING_DELAY: float = 1.0  # Delay between requests (be respectful)
    MAX_SEARCH_RESULTS: int = 20
    DATA_UPDATE_INTERVAL_HOURS: int = 24
    USER_AGENT: str = "SCET-Research-Bot/1.0 (Educational Research Project)"
    
    # Copyright Rules (Default: US-based, 70 years after author death)
    DEFAULT_COPYRIGHT_DURATION_YEARS: int = 70
    CORPORATE_COPYRIGHT_DURATION_YEARS: int = 95
    DEFAULT_JURISDICTION: str = "US"
    
    # Supported content types
    CONTENT_TYPES: List[str] = ["book", "music", "film", "article", "image", "software", "artwork"]
    
    # Incremental Learning
    RETRAIN_THRESHOLD: int = 100  # Retrain after N new entries
    MIN_CONFIDENCE_SCORE: float = 0.5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create models and data directories if not exists
settings = get_settings()
settings.MODEL_PATH.mkdir(parents=True, exist_ok=True)
settings.DATA_PATH.mkdir(parents=True, exist_ok=True)
