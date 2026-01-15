"""
Feature Extraction for ML Model
Extracts meaningful features from work metadata for copyright prediction
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import re
import logging

from ..utils import normalize_title, normalize_creator_name
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Extracts features from work metadata for ML model
    Features used to predict copyright status and expiry
    """
    
    def __init__(self):
        self.current_year = datetime.now().year
        
        # Content type encoding
        self.content_type_map = {
            'book': 0,
            'music': 1,
            'film': 2,
            'article': 3,
            'image': 4,
            'software': 5,
            'artwork': 6,
            'unknown': 7
        }
        
        # Known historical markers
        self.public_domain_thresholds = {
            'US': 1928,  # Works published before 1928 are PD in US
            'EU': 1900,  # Very old works
        }
    
    def extract_features(
        self,
        title: str,
        creator: Optional[str] = None,
        publication_year: Optional[int] = None,
        creator_death_year: Optional[int] = None,
        content_type: Optional[str] = None,
        jurisdiction: str = "US"
    ) -> np.ndarray:
        """
        Extract feature vector from work metadata
        Returns a fixed-size numpy array
        """
        features = []
        
        # 1. Year-based features
        year_features = self._extract_year_features(
            publication_year, creator_death_year, jurisdiction
        )
        features.extend(year_features)
        
        # 2. Title-based features
        title_features = self._extract_title_features(title)
        features.extend(title_features)
        
        # 3. Creator-based features
        creator_features = self._extract_creator_features(creator, creator_death_year)
        features.extend(creator_features)
        
        # 4. Content type features
        type_features = self._extract_type_features(content_type)
        features.extend(type_features)
        
        # 5. Computed likelihood features
        likelihood_features = self._compute_likelihood_features(
            publication_year, creator_death_year, content_type, jurisdiction
        )
        features.extend(likelihood_features)
        
        return np.array(features, dtype=np.float32)
    
    def _extract_year_features(
        self,
        publication_year: Optional[int],
        creator_death_year: Optional[int],
        jurisdiction: str
    ) -> List[float]:
        """Extract year-related features"""
        features = []
        
        # Publication year
        if publication_year:
            # Normalized age (0-1 scale, 0 = new, 1 = very old)
            age = self.current_year - publication_year
            normalized_age = min(age / 200, 1.0)
            features.append(normalized_age)
            
            # Decades since publication
            decades = age / 10
            features.append(min(decades / 20, 1.0))
            
            # Is before public domain threshold?
            pd_threshold = self.public_domain_thresholds.get(jurisdiction, 1928)
            is_before_threshold = 1.0 if publication_year < pd_threshold else 0.0
            features.append(is_before_threshold)
            
            # Year ranges (one-hot-ish)
            features.append(1.0 if publication_year < 1900 else 0.0)
            features.append(1.0 if 1900 <= publication_year < 1950 else 0.0)
            features.append(1.0 if 1950 <= publication_year < 1980 else 0.0)
            features.append(1.0 if 1980 <= publication_year < 2000 else 0.0)
            features.append(1.0 if publication_year >= 2000 else 0.0)
        else:
            # Unknown publication year
            features.extend([0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
        # Creator death year features
        if creator_death_year:
            years_since_death = self.current_year - creator_death_year
            normalized_death = min(years_since_death / 150, 1.0)
            features.append(normalized_death)
            
            # Is 70+ years since death? (common copyright expiry)
            features.append(1.0 if years_since_death >= 70 else 0.0)
            features.append(1.0 if years_since_death >= 95 else 0.0)
        else:
            features.extend([0.5, 0.0, 0.0])  # Unknown
        
        return features
    
    def _extract_title_features(self, title: str) -> List[float]:
        """Extract title-based features"""
        features = []
        
        if not title:
            return [0.0] * 6
        
        normalized = normalize_title(title)
        
        # Title length (normalized)
        features.append(min(len(normalized) / 100, 1.0))
        
        # Word count
        word_count = len(normalized.split())
        features.append(min(word_count / 20, 1.0))
        
        # Contains edition/volume indicators (suggests multiple versions)
        edition_keywords = ['edition', 'volume', 'vol', 'ed', 'revised']
        has_edition = any(kw in normalized for kw in edition_keywords)
        features.append(1.0 if has_edition else 0.0)
        
        # Contains date in title
        has_year = bool(re.search(r'\b(19|20)\d{2}\b', title))
        features.append(1.0 if has_year else 0.0)
        
        # Contains "the" at start (common in older works)
        features.append(1.0 if normalized.startswith('the ') else 0.0)
        
        # Is in foreign language (simplified check)
        non_ascii = sum(1 for c in title if ord(c) > 127) / max(len(title), 1)
        features.append(non_ascii)
        
        return features
    
    def _extract_creator_features(
        self,
        creator: Optional[str],
        creator_death_year: Optional[int]
    ) -> List[float]:
        """Extract creator-based features"""
        features = []
        
        if not creator:
            return [0.0, 0.0, 0.0, 0.5]
        
        normalized = normalize_creator_name(creator)
        
        # Is corporate author?
        corporate_keywords = ['inc', 'corp', 'llc', 'ltd', 'company', 'studio', 'production']
        is_corporate = any(kw in normalized for kw in corporate_keywords)
        features.append(1.0 if is_corporate else 0.0)
        
        # Number of words in creator name
        word_count = len(normalized.split())
        features.append(min(word_count / 5, 1.0))
        
        # Is known classical creator (historical figures)
        classical_names = ['shakespeare', 'mozart', 'beethoven', 'bach', 'dickens', 
                          'austen', 'twain', 'poe', 'homer', 'plato', 'aristotle']
        is_classical = any(name in normalized for name in classical_names)
        features.append(1.0 if is_classical else 0.0)
        
        # Creator alive probability (if no death year)
        if creator_death_year:
            features.append(0.0)  # Confirmed deceased
        else:
            # Estimate based on common patterns
            # Most active creators are 20-80 years old
            features.append(0.5)  # Unknown
        
        return features
    
    def _extract_type_features(self, content_type: Optional[str]) -> List[float]:
        """Extract content type features (one-hot encoding)"""
        features = [0.0] * len(self.content_type_map)
        
        type_key = (content_type or 'unknown').lower()
        if type_key in self.content_type_map:
            features[self.content_type_map[type_key]] = 1.0
        else:
            features[self.content_type_map['unknown']] = 1.0
        
        return features
    
    def _compute_likelihood_features(
        self,
        publication_year: Optional[int],
        creator_death_year: Optional[int],
        content_type: Optional[str],
        jurisdiction: str
    ) -> List[float]:
        """Compute probability-based features"""
        features = []
        
        # Base probability of being in public domain
        pd_probability = 0.5  # Default unknown
        
        if publication_year:
            pd_threshold = self.public_domain_thresholds.get(jurisdiction, 1928)
            
            if publication_year < pd_threshold:
                pd_probability = 0.95
            elif publication_year < 1950:
                pd_probability = 0.7
            elif publication_year < 1980:
                pd_probability = 0.3
            else:
                pd_probability = 0.1
        
        features.append(pd_probability)
        
        # Probability based on creator death
        if creator_death_year:
            years_since_death = self.current_year - creator_death_year
            duration = settings.DEFAULT_COPYRIGHT_DURATION_YEARS
            
            if years_since_death >= duration:
                death_pd_prob = 0.9
            elif years_since_death >= duration - 10:
                death_pd_prob = 0.6
            else:
                death_pd_prob = 0.2
        else:
            death_pd_prob = 0.4  # Unknown
        
        features.append(death_pd_prob)
        
        # Combined probability
        if publication_year and creator_death_year:
            combined = (pd_probability + death_pd_prob) / 2
        elif publication_year:
            combined = pd_probability
        elif creator_death_year:
            combined = death_pd_prob
        else:
            combined = 0.5
        
        features.append(combined)
        
        # Content type adjustment
        # Software has shorter protection in some cases
        type_adjustment = 0.0
        if content_type == 'software':
            type_adjustment = 0.1  # Slightly more likely to be openly licensed
        elif content_type == 'book' and publication_year and publication_year < 1950:
            type_adjustment = 0.2  # Old books more likely PD
        
        features.append(type_adjustment)
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get names of all features for interpretability"""
        names = [
            # Year features
            'normalized_age', 'decades_since_pub', 'before_pd_threshold',
            'pre_1900', 'year_1900_1950', 'year_1950_1980', 'year_1980_2000', 'post_2000',
            'years_since_death_normalized', 'death_70_plus', 'death_95_plus',
            
            # Title features
            'title_length', 'word_count', 'has_edition', 'has_year_in_title',
            'starts_with_the', 'non_ascii_ratio',
            
            # Creator features
            'is_corporate', 'creator_word_count', 'is_classical', 'creator_alive_prob',
            
            # Content type features (one-hot)
            'type_book', 'type_music', 'type_film', 'type_article',
            'type_image', 'type_software', 'type_artwork', 'type_unknown',
            
            # Likelihood features
            'pd_probability', 'death_pd_probability', 'combined_probability', 'type_adjustment'
        ]
        return names
    
    def get_feature_count(self) -> int:
        """Get total number of features"""
        return len(self.get_feature_names())
