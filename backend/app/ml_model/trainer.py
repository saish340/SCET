"""
Incremental Trainer
Manages the continuous learning process for the ML model
"""

import asyncio
import logging
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .predictor import get_predictor, CopyrightPredictor
from ..database.models import WorkMetadata, SearchLog, MLModelState
from ..database.connection import get_db_context
from ..config import get_settings
from ..schemas import CopyrightStatus

settings = get_settings()
logger = logging.getLogger(__name__)

settings = get_settings()
logger = logging.getLogger(__name__)


class IncrementalTrainer:
    """
    Manages incremental training of the ML model
    - Trains from verified examples
    - Learns from user feedback
    - Automatically retrains when threshold reached
    """
    
    def __init__(self):
        self.predictor = get_predictor()
        self._pending_samples: List[Dict[str, Any]] = []
        self._training_threshold = settings.RETRAIN_THRESHOLD
        self._last_training_run: Optional[datetime] = None
        self._is_training = False
    
    def add_training_sample(
        self,
        title: str,
        actual_status: CopyrightStatus,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US",
        source: str = "user_feedback"
    ):
        """Add a new training sample"""
        sample = {
            'title': title,
            'status': actual_status,
            'creator': creator,
            'publication_year': publication_year,
            'creator_death_year': creator_death_year,
            'content_type': content_type,
            'jurisdiction': jurisdiction,
            'source': source,
            'added_at': datetime.utcnow()
        }
        
        self._pending_samples.append(sample)
        
        # Check if we should trigger training
        if len(self._pending_samples) >= self._training_threshold:
            asyncio.create_task(self.run_training())
    
    async def run_training(self):
        """Run training on pending samples"""
        if self._is_training:
            logger.warning("Training already in progress")
            return
        
        if not self._pending_samples:
            logger.info("No pending samples to train on")
            return
        
        self._is_training = True
        
        try:
            logger.info(f"Starting training on {len(self._pending_samples)} samples")
            
            # Train on all pending samples
            self.predictor.batch_train(self._pending_samples)
            
            # Clear processed samples
            trained_count = len(self._pending_samples)
            self._pending_samples = []
            
            self._last_training_run = datetime.utcnow()
            
            # Save model state to database
            await self._save_model_state()
            
            logger.info(f"Training completed. Processed {trained_count} samples.")
            
        except Exception as e:
            logger.error(f"Training error: {e}")
        finally:
            self._is_training = False
    
    async def train_from_verified_works(self, db: Session):
        """
        Train from works with verified copyright status
        Uses works that have been manually verified or are certain
        """
        # Find works with high confidence or known public domain status
        verified_works = db.query(WorkMetadata).filter(
            WorkMetadata.data_confidence >= 0.9,
            WorkMetadata.copyright_status.in_(['public_domain', 'expired', 'active'])
        ).limit(100).all()
        
        for work in verified_works:
            status = CopyrightStatus(work.copyright_status)
            self.add_training_sample(
                title=work.title,
                actual_status=status,
                creator=work.creator,
                publication_year=work.publication_year,
                creator_death_year=work.creator_death_year,
                content_type=work.content_type,
                jurisdiction=work.jurisdiction or "US",
                source="verified_data"
            )
    
    async def train_from_search_feedback(self, db: Session):
        """
        Train from user search feedback
        Uses searches where users provided feedback
        """
        # Find searches with feedback
        feedback_logs = db.query(SearchLog).filter(
            SearchLog.feedback_score.isnot(None),
            SearchLog.user_selected_id.isnot(None)
        ).order_by(SearchLog.timestamp.desc()).limit(50).all()
        
        for log in feedback_logs:
            if log.user_selected_id:
                work = db.query(WorkMetadata).filter(
                    WorkMetadata.id == log.user_selected_id
                ).first()
                
                if work and work.copyright_status:
                    try:
                        status = CopyrightStatus(work.copyright_status)
                        self.add_training_sample(
                            title=work.title,
                            actual_status=status,
                            creator=work.creator,
                            publication_year=work.publication_year,
                            content_type=work.content_type,
                            source="user_feedback"
                        )
                    except ValueError:
                        pass  # Invalid status, skip
    
    def generate_training_data_from_rules(self) -> List[Dict[str, Any]]:
        """
        Generate synthetic training data based on copyright rules
        This helps bootstrap the model with known legal principles
        """
        samples = []
        current_year = datetime.now().year
        
        # Known public domain examples (rule-based certainties)
        # Works published before 1928 in US are public domain
        old_works = [
            {"title": "Pride and Prejudice", "creator": "Jane Austen", 
             "publication_year": 1813, "creator_death_year": 1817, "content_type": "book"},
            {"title": "Romeo and Juliet", "creator": "William Shakespeare",
             "publication_year": 1597, "creator_death_year": 1616, "content_type": "book"},
            {"title": "Symphony No. 5", "creator": "Ludwig van Beethoven",
             "publication_year": 1808, "creator_death_year": 1827, "content_type": "music"},
            {"title": "The Adventures of Sherlock Holmes", "creator": "Arthur Conan Doyle",
             "publication_year": 1892, "creator_death_year": 1930, "content_type": "book"},
            {"title": "A Tale of Two Cities", "creator": "Charles Dickens",
             "publication_year": 1859, "creator_death_year": 1870, "content_type": "book"},
        ]
        
        for work in old_works:
            work['status'] = CopyrightStatus.PUBLIC_DOMAIN
            samples.append(work)
        
        # Recent works that are still under copyright
        recent_works = [
            {"title": "Recent Fiction Novel", "publication_year": 2015, 
             "content_type": "book"},
            {"title": "Modern Pop Song", "publication_year": 2020,
             "content_type": "music"},
            {"title": "Contemporary Film", "publication_year": 2018,
             "content_type": "film"},
        ]
        
        for work in recent_works:
            work['status'] = CopyrightStatus.ACTIVE
            samples.append(work)
        
        return samples
    
    async def bootstrap_model(self):
        """Bootstrap the model with rule-based training data"""
        logger.info("Bootstrapping model with rule-based data")
        
        synthetic_samples = self.generate_training_data_from_rules()
        
        for sample in synthetic_samples:
            self.add_training_sample(
                title=sample['title'],
                actual_status=sample['status'],
                creator=sample.get('creator'),
                publication_year=sample.get('publication_year'),
                creator_death_year=sample.get('creator_death_year'),
                content_type=sample.get('content_type'),
                source="rule_based"
            )
        
        # Run immediate training
        await self.run_training()
    
    async def train_from_csv(self, csv_path: str = None) -> Dict[str, Any]:
        """
        Train the model from a CSV dataset file
        Expected columns: content_id, content_type, owner_type, license_type,
        allow_view, allow_download, allow_share, allow_modify, allow_commercial,
        copyright_start_year, copyright_duration_years, current_year, 
        copyright_expired, usage_context, detected_usage, misuse_flag, legal_summary_label
        """
        if csv_path is None:
            csv_path = Path(settings.DATA_PATH) / "training_data.csv"
        else:
            csv_path = Path(csv_path)
        
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return {"success": False, "error": "CSV file not found"}
        
        logger.info(f"Loading training data from {csv_path}")
        
        samples_processed = 0
        samples_skipped = 0
        
        # Content type mapping from CSV to our types
        content_type_map = {
            'audio': 'music',
            'video': 'film',
            'pdf': 'book',
            'image': 'image',
            'article': 'book'
        }
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Determine copyright status from the CSV
                        copyright_expired = int(row.get('copyright_expired', 0))
                        status = CopyrightStatus.PUBLIC_DOMAIN if copyright_expired == 1 else CopyrightStatus.ACTIVE
                        
                        # Map content type
                        csv_content_type = row.get('content_type', '').lower()
                        content_type = content_type_map.get(csv_content_type, 'book')
                        
                        # Get years
                        pub_year = int(row.get('copyright_start_year', 2000))
                        duration = int(row.get('copyright_duration_years', 70))
                        
                        # Calculate estimated death year (approximation based on pub year and duration)
                        # For individual owners, estimate death year for life + years calculation
                        owner_type = row.get('owner_type', 'individual')
                        creator_death_year = None
                        if owner_type == 'individual':
                            # Estimate death: assume author was 35 at publication, died 40 years later
                            creator_death_year = pub_year + 35
                        
                        # Create a synthetic title from content_id
                        content_id = row.get('content_id', f'work_{samples_processed}')
                        title = f"Work {content_id}"
                        
                        # Add license type to influence the model
                        license_type = row.get('license_type', 'all_rights_reserved')
                        if license_type == 'public_domain':
                            status = CopyrightStatus.PUBLIC_DOMAIN
                        
                        # Add training sample
                        self.add_training_sample(
                            title=title,
                            actual_status=status,
                            creator=f"{owner_type.title()} Creator",
                            publication_year=pub_year,
                            creator_death_year=creator_death_year,
                            content_type=content_type,
                            jurisdiction="US",
                            source="csv_dataset"
                        )
                        
                        samples_processed += 1
                        
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping row due to error: {e}")
                        samples_skipped += 1
                        continue
            
            logger.info(f"Loaded {samples_processed} samples from CSV ({samples_skipped} skipped)")
            
            # Run training immediately
            await self.run_training()
            
            return {
                "success": True,
                "samples_processed": samples_processed,
                "samples_skipped": samples_skipped,
                "model_stats": self.predictor.get_model_stats()
            }
            
        except Exception as e:
            logger.error(f"Error training from CSV: {e}")
            return {"success": False, "error": str(e)}

    async def _save_model_state(self):
        """Save model state to database"""
        try:
            with get_db_context() as db:
                stats = self.predictor.get_model_stats()
                
                # Find or create model state record
                model_state = db.query(MLModelState).filter(
                    MLModelState.model_name == "copyright_predictor"
                ).first()
                
                if model_state:
                    model_state.training_samples_count = stats['training_samples']
                    model_state.last_trained_at = datetime.utcnow()
                    model_state.accuracy = stats.get('rolling_accuracy')
                else:
                    model_state = MLModelState(
                        model_name="copyright_predictor",
                        model_type="binary_classifier",
                        version="1.0",
                        training_samples_count=stats['training_samples'],
                        last_trained_at=datetime.utcnow(),
                        accuracy=stats.get('rolling_accuracy'),
                        model_path=str(settings.MODEL_PATH / "copyright_predictor.pkl"),
                        is_active=True
                    )
                    db.add(model_state)
                
                db.commit()
        except Exception as e:
            logger.error(f"Error saving model state: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get trainer status"""
        return {
            'pending_samples': len(self._pending_samples),
            'training_threshold': self._training_threshold,
            'is_training': self._is_training,
            'last_training_run': self._last_training_run.isoformat() if self._last_training_run else None,
            'model_stats': self.predictor.get_model_stats()
        }


# Singleton instance
_trainer_instance: Optional[IncrementalTrainer] = None


def get_trainer() -> IncrementalTrainer:
    """Get or create trainer instance"""
    global _trainer_instance
    if _trainer_instance is None:
        _trainer_instance = IncrementalTrainer()
    return _trainer_instance
