"""
Copyright Predictor - ML Model
Predicts copyright status and expiry using machine learning
Supports incremental learning without pre-built datasets
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
import pickle
from pathlib import Path

from .features import FeatureExtractor
from ..config import get_settings
from ..schemas import CopyrightStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class CopyrightPredictor:
    """
    ML model for predicting copyright status
    - Uses feature-based prediction
    - Supports incremental learning
    - Improves with more searches
    """
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.model_path = settings.MODEL_PATH / "copyright_predictor.pkl"
        
        # Model parameters (learned)
        self._weights: Optional[np.ndarray] = None
        self._bias: float = 0.0
        
        # Training state
        self._training_samples = 0
        self._last_trained = None
        self._accuracy_history: List[float] = []
        
        # Learning rate for incremental updates
        self._learning_rate = 0.01
        
        # Initialize or load model
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize model weights or load from disk"""
        feature_count = self.feature_extractor.get_feature_count()
        
        if self.model_path.exists():
            try:
                self._load_model()
                logger.info("Loaded existing copyright predictor model")
                return
            except Exception as e:
                logger.warning(f"Could not load model: {e}")
        
        # Initialize with smart defaults based on domain knowledge
        self._weights = self._get_initial_weights(feature_count)
        self._bias = 0.0
        logger.info("Initialized new copyright predictor model")
    
    def _get_initial_weights(self, feature_count: int) -> np.ndarray:
        """
        Initialize weights with domain knowledge
        This is NOT a pre-trained model - it's using logical defaults
        that the model will adjust through learning
        """
        weights = np.zeros(feature_count)
        
        # Feature indices (from feature extractor)
        # These weights encode basic copyright logic
        # They will be refined through incremental learning
        
        # Year-based features have strong influence
        weights[0] = 0.3   # normalized_age - older = more likely PD
        weights[1] = 0.2   # decades_since_pub
        weights[2] = 0.5   # before_pd_threshold - strong indicator
        weights[3] = 0.4   # pre_1900 - very likely PD
        weights[4] = 0.3   # year_1900_1950
        weights[5] = -0.1  # year_1950_1980 - less likely PD
        weights[6] = -0.2  # year_1980_2000
        weights[7] = -0.3  # post_2000 - unlikely PD
        
        # Death-based features
        weights[8] = 0.3   # years_since_death_normalized
        weights[9] = 0.4   # death_70_plus
        weights[10] = 0.5  # death_95_plus
        
        # Title features (weak signals)
        weights[11:17] = [0.0, 0.0, 0.0, 0.0, 0.05, 0.0]
        
        # Creator features
        weights[17] = -0.1  # is_corporate - corporate works have different rules
        weights[18] = 0.0   # creator_word_count
        weights[19] = 0.4   # is_classical - historical figures = PD
        weights[20] = -0.1  # creator_alive_prob
        
        # Content type (varying rules)
        weights[21:29] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0]
        
        # Likelihood features (strong signals)
        weights[29] = 0.4  # pd_probability
        weights[30] = 0.3  # death_pd_probability
        weights[31] = 0.5  # combined_probability
        weights[32] = 0.1  # type_adjustment
        
        return weights
    
    def predict(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US"
    ) -> Dict[str, Any]:
        """
        Predict copyright status for a work
        Returns probability and predicted status
        """
        # Extract features
        features = self.feature_extractor.extract_features(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction
        )
        
        # Compute raw score
        raw_score = np.dot(features, self._weights) + self._bias
        
        # Apply sigmoid to get probability
        probability = self._sigmoid(raw_score)
        
        # Determine status and confidence
        status, confidence = self._interpret_probability(probability, features)
        
        # Calculate expiry estimation
        expiry_info = self._estimate_expiry(
            publication_year, creator_death_year, 
            content_type, jurisdiction, probability
        )
        
        return {
            'status': status,
            'probability_public_domain': float(probability),
            'confidence': float(confidence),
            'expiry_date': expiry_info.get('expiry_date'),
            'years_until_expiry': expiry_info.get('years_until_expiry'),
            'reasoning': self._generate_reasoning(features, probability, status),
            'feature_importance': self._get_feature_importance(features),
        }
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation function"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def _interpret_probability(
        self, 
        probability: float,
        features: np.ndarray
    ) -> Tuple[CopyrightStatus, float]:
        """Interpret probability into status and confidence"""
        
        # Determine status
        if probability >= 0.85:
            status = CopyrightStatus.PUBLIC_DOMAIN
            confidence = probability
        elif probability >= 0.65:
            status = CopyrightStatus.LIKELY_EXPIRED
            confidence = probability
        elif probability >= 0.35:
            status = CopyrightStatus.UNKNOWN
            confidence = 0.5 - abs(probability - 0.5)  # Lower confidence near boundary
        elif probability >= 0.15:
            status = CopyrightStatus.LIKELY_ACTIVE
            confidence = 1 - probability
        else:
            status = CopyrightStatus.ACTIVE
            confidence = 1 - probability
        
        # Adjust confidence based on data completeness
        data_completeness = self._assess_data_completeness(features)
        confidence = confidence * data_completeness
        
        return status, confidence
    
    def _assess_data_completeness(self, features: np.ndarray) -> float:
        """Assess how complete the input data is"""
        completeness = 1.0
        
        # Check for missing year (feature index 0 would be 0.5 for unknown)
        if features[0] == 0.5:  # normalized_age unknown
            completeness *= 0.7
        
        # Check for missing death year
        if features[8] == 0.5:  # years_since_death unknown
            completeness *= 0.8
        
        return completeness
    
    def _estimate_expiry(
        self,
        publication_year: Optional[int],
        creator_death_year: Optional[int],
        content_type: Optional[str],
        jurisdiction: str,
        probability: float
    ) -> Dict[str, Any]:
        """Estimate copyright expiry date"""
        current_year = datetime.now().year
        
        # Already public domain
        if probability >= 0.85:
            return {
                'expiry_date': None,
                'years_until_expiry': 0,
                'expired': True
            }
        
        # Calculate based on death year (life + 70 rule)
        if creator_death_year:
            duration = settings.DEFAULT_COPYRIGHT_DURATION_YEARS
            expiry_year = creator_death_year + duration
            years_until = expiry_year - current_year
            
            return {
                'expiry_date': datetime(expiry_year, 1, 1) if years_until > 0 else None,
                'years_until_expiry': max(0, years_until),
                'expired': years_until <= 0
            }
        
        # Calculate based on publication year (95 years for corporate works)
        if publication_year:
            duration = settings.CORPORATE_COPYRIGHT_DURATION_YEARS
            expiry_year = publication_year + duration
            years_until = expiry_year - current_year
            
            return {
                'expiry_date': datetime(expiry_year, 1, 1) if years_until > 0 else None,
                'years_until_expiry': max(0, years_until),
                'expired': years_until <= 0
            }
        
        # Unknown
        return {
            'expiry_date': None,
            'years_until_expiry': None,
            'expired': False
        }
    
    def _generate_reasoning(
        self,
        features: np.ndarray,
        probability: float,
        status: CopyrightStatus
    ) -> str:
        """Generate human-readable reasoning for the prediction"""
        reasons = []
        
        # Check key indicators
        if features[2] > 0.5:  # before_pd_threshold
            reasons.append("Published before the public domain threshold date")
        
        if features[3] > 0.5:  # pre_1900
            reasons.append("Published before 1900 (very likely public domain)")
        
        if features[9] > 0.5:  # death_70_plus
            reasons.append("Creator deceased for 70+ years")
        
        if features[10] > 0.5:  # death_95_plus
            reasons.append("Creator deceased for 95+ years")
        
        if features[19] > 0.5:  # is_classical
            reasons.append("Creator is a historical/classical figure")
        
        if features[7] > 0.5:  # post_2000
            reasons.append("Published after 2000 (likely still protected)")
        
        if features[17] > 0.5:  # is_corporate
            reasons.append("Work appears to have corporate authorship")
        
        if not reasons:
            if probability > 0.5:
                reasons.append("Based on available metadata, work appears to be in or near public domain")
            else:
                reasons.append("Based on available metadata, work appears to be under copyright protection")
        
        return "; ".join(reasons) + "."
    
    def _get_feature_importance(self, features: np.ndarray) -> Dict[str, float]:
        """Get importance of each feature for this prediction"""
        feature_names = self.feature_extractor.get_feature_names()
        
        # Calculate contribution of each feature
        contributions = features * self._weights
        
        # Get top contributing features
        importance = {}
        for i, (name, contrib) in enumerate(zip(feature_names, contributions)):
            if abs(contrib) > 0.01:  # Only significant contributions
                importance[name] = float(contrib)
        
        # Sort by absolute importance
        sorted_importance = dict(sorted(
            importance.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        )[:5])  # Top 5
        
        return sorted_importance
    
    def train_incremental(
        self,
        title: str,
        actual_status: CopyrightStatus,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US"
    ):
        """
        Train model incrementally with a new labeled example
        This is how the model learns and improves over time
        """
        # Extract features
        features = self.feature_extractor.extract_features(
            title=title,
            creator=creator,
            publication_year=publication_year,
            creator_death_year=creator_death_year,
            content_type=content_type,
            jurisdiction=jurisdiction
        )
        
        # Convert status to target
        if actual_status in [CopyrightStatus.PUBLIC_DOMAIN, CopyrightStatus.EXPIRED]:
            target = 1.0
        elif actual_status in [CopyrightStatus.ACTIVE, CopyrightStatus.LIKELY_ACTIVE]:
            target = 0.0
        else:
            return  # Don't train on uncertain examples
        
        # Get current prediction
        raw_score = np.dot(features, self._weights) + self._bias
        prediction = self._sigmoid(raw_score)
        
        # Calculate error
        error = target - prediction
        
        # Update weights using gradient descent
        gradient = error * prediction * (1 - prediction) * features
        self._weights += self._learning_rate * gradient
        self._bias += self._learning_rate * error
        
        # Update training state
        self._training_samples += 1
        self._last_trained = datetime.utcnow()
        
        # Record accuracy
        is_correct = (prediction > 0.5) == (target > 0.5)
        self._accuracy_history.append(1.0 if is_correct else 0.0)
        
        # Keep only last 100 for rolling accuracy
        self._accuracy_history = self._accuracy_history[-100:]
        
        # Save model periodically
        if self._training_samples % 10 == 0:
            self._save_model()
        
        logger.info(f"Trained on sample {self._training_samples}, error: {error:.4f}")
    
    def batch_train(
        self,
        samples: List[Dict[str, Any]]
    ):
        """Train on multiple samples at once"""
        for sample in samples:
            self.train_incremental(
                title=sample.get('title', ''),
                actual_status=sample.get('status'),
                creator=sample.get('creator'),
                publication_year=sample.get('publication_year'),
                creator_death_year=sample.get('creator_death_year'),
                content_type=sample.get('content_type'),
                jurisdiction=sample.get('jurisdiction', 'US')
            )
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model statistics"""
        return {
            'training_samples': self._training_samples,
            'last_trained': self._last_trained.isoformat() if self._last_trained else None,
            'rolling_accuracy': np.mean(self._accuracy_history) if self._accuracy_history else None,
            'accuracy_samples': len(self._accuracy_history),
            'feature_count': len(self._weights) if self._weights is not None else 0,
        }
    
    def _save_model(self):
        """Save model to disk"""
        try:
            model_data = {
                'weights': self._weights,
                'bias': self._bias,
                'training_samples': self._training_samples,
                'last_trained': self._last_trained,
                'accuracy_history': self._accuracy_history,
            }
            
            settings.MODEL_PATH.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _load_model(self):
        """Load model from disk"""
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self._weights = model_data['weights']
        self._bias = model_data['bias']
        self._training_samples = model_data.get('training_samples', 0)
        self._last_trained = model_data.get('last_trained')
        self._accuracy_history = model_data.get('accuracy_history', [])


# Singleton instance
_predictor_instance: Optional[CopyrightPredictor] = None


def get_predictor() -> CopyrightPredictor:
    """Get or create predictor instance"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = CopyrightPredictor()
    return _predictor_instance
