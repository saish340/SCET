"""
Data Collector Module
Orchestrates data collection from multiple sources
Stores only metadata - NO copyrighted content
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from .scrapers import WebScraper, ScrapedWork
from ..database.models import WorkMetadata, DataSource
from ..database.connection import get_db_context
from ..utils import normalize_title, calculate_text_hash
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class DataCollector:
    """
    Main data collection orchestrator
    - Collects data dynamically from the internet
    - Stores only metadata
    - Supports incremental updates
    """
    
    def __init__(self):
        self.scraper = WebScraper()
        self._is_running = False
        self._last_run = None
        self._total_collected = 0
    
    async def collect_for_query(
        self, 
        query: str, 
        content_type: Optional[str] = None,
        db: Optional[Session] = None
    ) -> List[WorkMetadata]:
        """
        Collect data for a specific search query
        This is the primary method - triggered on-demand by user searches
        """
        logger.info(f"Collecting data for query: '{query}' (type: {content_type})")
        
        self._is_running = True
        collected = []
        
        try:
            # Scrape from all sources
            scraped_works = await self.scraper.search_all(query, content_type)
            
            if not scraped_works:
                logger.info(f"No results found for: {query}")
                return []
            
            # Process and store results
            if db is None:
                with get_db_context() as db:
                    collected = await self._process_and_store(scraped_works, db)
            else:
                collected = await self._process_and_store(scraped_works, db)
            
            self._total_collected += len(collected)
            logger.info(f"Collected {len(collected)} works for query: {query}")
            
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise
        finally:
            self._is_running = False
            self._last_run = datetime.utcnow()
        
        return collected
    
    async def _process_and_store(
        self, 
        scraped_works: List[ScrapedWork], 
        db: Session
    ) -> List[WorkMetadata]:
        """Process scraped works and store as metadata"""
        stored = []
        
        for work in scraped_works:
            try:
                # Check for duplicates using normalized title
                title_normalized = normalize_title(work.title)
                
                existing = db.query(WorkMetadata).filter(
                    WorkMetadata.title_normalized == title_normalized,
                    WorkMetadata.content_type == work.content_type
                ).first()
                
                if existing:
                    # Update existing record with new data if more confident
                    if work.confidence > existing.data_confidence:
                        existing = self._update_work(existing, work)
                        stored.append(existing)
                    continue
                
                # Create new metadata entry
                metadata = WorkMetadata(
                    title=work.title,
                    title_normalized=title_normalized,
                    creator=work.creator,
                    creator_death_year=work.creator_death_year,
                    publication_year=work.publication_year,
                    content_type=work.content_type or "unknown",
                    source_url=work.source_url,
                    source_name=work.source_name,
                    data_confidence=work.confidence,
                    copyright_status="unknown",  # Will be calculated by rule engine
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.add(metadata)
                db.flush()  # Get the ID
                stored.append(metadata)
                
            except Exception as e:
                logger.error(f"Error storing work {work.title}: {e}")
                continue
        
        db.commit()
        return stored
    
    def _update_work(self, existing: WorkMetadata, new_data: ScrapedWork) -> WorkMetadata:
        """Update existing work with new data"""
        # Update fields if new data is available
        if new_data.creator and not existing.creator:
            existing.creator = new_data.creator
        
        if new_data.creator_death_year and not existing.creator_death_year:
            existing.creator_death_year = new_data.creator_death_year
        
        if new_data.publication_year and not existing.publication_year:
            existing.publication_year = new_data.publication_year
        
        # Update confidence if higher
        if new_data.confidence > existing.data_confidence:
            existing.data_confidence = new_data.confidence
        
        existing.updated_at = datetime.utcnow()
        existing.last_verified_at = datetime.utcnow()
        
        return existing
    
    async def verify_and_update(self, work_id: int, db: Session) -> Optional[WorkMetadata]:
        """
        Re-verify data for an existing work
        Used for periodic updates to keep data fresh
        """
        work = db.query(WorkMetadata).filter(WorkMetadata.id == work_id).first()
        if not work:
            return None
        
        # Re-search for this work
        scraped = await self.scraper.search_all(work.title, work.content_type)
        
        if scraped:
            # Find the best match
            best_match = None
            best_score = 0
            
            for item in scraped:
                title_sim = self._title_similarity(work.title, item.title)
                if title_sim > best_score:
                    best_score = title_sim
                    best_match = item
            
            if best_match and best_score > 0.8:
                work = self._update_work(work, best_match)
                work.last_verified_at = datetime.utcnow()
                db.commit()
        
        return work
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity"""
        from ..utils import similarity_ratio
        return similarity_ratio(title1, title2)
    
    async def batch_collect(
        self, 
        queries: List[str], 
        content_type: Optional[str] = None
    ) -> Dict[str, int]:
        """Collect data for multiple queries"""
        results = {}
        
        for query in queries:
            try:
                with get_db_context() as db:
                    collected = await self.collect_for_query(query, content_type, db)
                    results[query] = len(collected)
            except Exception as e:
                logger.error(f"Error in batch collection for {query}: {e}")
                results[query] = 0
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get current collection status"""
        return {
            'is_running': self._is_running,
            'last_run': self._last_run.isoformat() if self._last_run else None,
            'total_collected': self._total_collected,
        }
    
    async def close(self):
        """Clean up resources"""
        await self.scraper.close()


# Singleton instance
_collector_instance: Optional[DataCollector] = None


def get_collector() -> DataCollector:
    """Get or create collector instance"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = DataCollector()
    return _collector_instance
