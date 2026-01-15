"""
Data Update Scheduler
Handles periodic re-verification and updates of stored metadata
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from ..database.models import WorkMetadata
from ..database.connection import get_db_context
from ..config import get_settings
from .collector import get_collector

settings = get_settings()
logger = logging.getLogger(__name__)


class DataUpdateScheduler:
    """
    Scheduler for automatic data updates
    - Periodically re-verifies stored metadata
    - Updates stale entries
    - Maintains data freshness
    """
    
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_check = None
        self._entries_updated = 0
    
    async def start(self, interval_hours: Optional[int] = None):
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        interval = interval_hours or settings.DATA_UPDATE_INTERVAL_HOURS
        self._running = True
        
        logger.info(f"Starting data update scheduler with {interval}h interval")
        self._task = asyncio.create_task(self._run_loop(interval))
    
    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Data update scheduler stopped")
    
    async def _run_loop(self, interval_hours: int):
        """Main scheduler loop"""
        while self._running:
            try:
                await self._check_and_update_stale_entries()
                self._last_check = datetime.utcnow()
                
                # Sleep until next interval
                await asyncio.sleep(interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait a bit before retrying
    
    async def _check_and_update_stale_entries(self):
        """Find and update stale entries"""
        collector = get_collector()
        threshold = datetime.utcnow() - timedelta(hours=settings.DATA_UPDATE_INTERVAL_HOURS * 7)
        
        with get_db_context() as db:
            # Find entries that haven't been verified recently
            stale_entries = db.query(WorkMetadata).filter(
                (WorkMetadata.last_verified_at == None) | 
                (WorkMetadata.last_verified_at < threshold)
            ).limit(50).all()  # Process in batches
            
            for entry in stale_entries:
                try:
                    await collector.verify_and_update(entry.id, db)
                    self._entries_updated += 1
                except Exception as e:
                    logger.error(f"Error updating entry {entry.id}: {e}")
                
                # Rate limiting
                await asyncio.sleep(1)
        
        logger.info(f"Updated {len(stale_entries)} stale entries")
    
    async def force_update(self, work_id: int) -> bool:
        """Force update a specific work"""
        collector = get_collector()
        
        with get_db_context() as db:
            result = await collector.verify_and_update(work_id, db)
            return result is not None
    
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            'running': self._running,
            'last_check': self._last_check.isoformat() if self._last_check else None,
            'entries_updated': self._entries_updated,
            'next_check': (self._last_check + timedelta(hours=settings.DATA_UPDATE_INTERVAL_HOURS)).isoformat() 
                         if self._last_check else None
        }


# Singleton instance
_scheduler_instance: Optional[DataUpdateScheduler] = None


def get_scheduler() -> DataUpdateScheduler:
    """Get or create scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DataUpdateScheduler()
    return _scheduler_instance
