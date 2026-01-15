"""
Semantic Search Module
Uses embeddings and vector similarity for intelligent search
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import logging
import json
from pathlib import Path
from datetime import datetime

from ..config import get_settings
from ..utils import normalize_title

settings = get_settings()
logger = logging.getLogger(__name__)


class SemanticMatcher:
    """
    Semantic similarity search using embeddings
    - Computes text embeddings for titles
    - Finds semantically similar works
    - Supports incremental learning
    """
    
    def __init__(self):
        self._embeddings_cache: Dict[str, np.ndarray] = {}
        self._model = None
        self._model_loaded = False
        self._use_simple_mode = False  # Fallback if transformers not available
        
        # TF-IDF components for simple mode
        self._vocabulary: Dict[str, int] = {}
        self._idf_scores: Dict[str, float] = {}
        self._doc_count = 0
        
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self._model_loaded = True
            logger.info("Embedding model loaded successfully")
            
        except ImportError:
            logger.warning("sentence-transformers not available, using TF-IDF fallback")
            self._use_simple_mode = True
            self._model_loaded = True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._use_simple_mode = True
            self._model_loaded = True
    
    def compute_embedding(self, text: str) -> np.ndarray:
        """Compute embedding for text"""
        if not text:
            return np.zeros(384)  # Default embedding size
        
        normalized = normalize_title(text)
        
        # Check cache
        if normalized in self._embeddings_cache:
            return self._embeddings_cache[normalized]
        
        if self._use_simple_mode:
            embedding = self._compute_tfidf_vector(normalized)
        else:
            embedding = self._model.encode(normalized, convert_to_numpy=True)
        
        # Cache the embedding
        self._embeddings_cache[normalized] = embedding
        
        return embedding
    
    def _compute_tfidf_vector(self, text: str) -> np.ndarray:
        """Compute TF-IDF vector for text (fallback mode)"""
        words = text.lower().split()
        
        # Update vocabulary
        for word in words:
            if word not in self._vocabulary:
                self._vocabulary[word] = len(self._vocabulary)
        
        # Compute TF-IDF
        vector_size = max(len(self._vocabulary), 384)
        vector = np.zeros(vector_size)
        
        word_count = len(words)
        tf = {}
        for word in words:
            tf[word] = tf.get(word, 0) + 1
        
        for word, count in tf.items():
            if word in self._vocabulary:
                idx = self._vocabulary[word]
                if idx < vector_size:
                    # TF * IDF
                    tf_score = count / word_count
                    idf_score = self._idf_scores.get(word, 1.0)
                    vector[idx] = tf_score * idf_score
        
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector[:384]  # Keep consistent size
    
    def update_idf(self, documents: List[str]):
        """Update IDF scores with new documents"""
        import math
        
        self._doc_count += len(documents)
        
        # Count document frequency for each word
        doc_freq: Dict[str, int] = {}
        
        for doc in documents:
            words = set(doc.lower().split())
            for word in words:
                doc_freq[word] = doc_freq.get(word, 0) + 1
        
        # Update IDF scores
        for word, freq in doc_freq.items():
            self._idf_scores[word] = math.log(self._doc_count / (1 + freq))
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        emb1 = self.compute_embedding(text1)
        emb2 = self.compute_embedding(text2)
        
        return self._cosine_similarity(emb1, emb2)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between vectors"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def find_similar(
        self, 
        query: str, 
        candidates: List[Tuple[int, str]],  # (id, title) pairs
        top_k: int = 10,
        min_similarity: float = None
    ) -> List[Tuple[int, str, float]]:
        """
        Find most similar candidates to query
        Returns list of (id, title, similarity_score)
        """
        if not candidates:
            return []
        
        min_sim = min_similarity or settings.MIN_SIMILARITY_THRESHOLD
        query_embedding = self.compute_embedding(query)
        
        # Compute similarities
        results = []
        for cand_id, title in candidates:
            cand_embedding = self.compute_embedding(title)
            similarity = self._cosine_similarity(query_embedding, cand_embedding)
            
            if similarity >= min_sim:
                results.append((cand_id, title, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results[:top_k]
    
    def batch_compute_embeddings(self, texts: List[str]) -> Dict[str, np.ndarray]:
        """Compute embeddings for multiple texts efficiently"""
        if self._use_simple_mode:
            return {text: self.compute_embedding(text) for text in texts}
        
        # Batch encoding with transformer model
        normalized = [normalize_title(t) for t in texts]
        
        # Filter out cached
        to_encode = [n for n in normalized if n not in self._embeddings_cache]
        
        if to_encode:
            embeddings = self._model.encode(to_encode, convert_to_numpy=True, show_progress_bar=False)
            
            for text, emb in zip(to_encode, embeddings):
                self._embeddings_cache[text] = emb
        
        return {text: self._embeddings_cache[normalize_title(text)] for text in texts}
    
    def store_embedding(self, work_id: int, title: str, embedding: Optional[np.ndarray] = None):
        """Store embedding for a work (for later retrieval)"""
        if embedding is None:
            embedding = self.compute_embedding(title)
        
        normalized = normalize_title(title)
        self._embeddings_cache[normalized] = embedding
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embeddings_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_embeddings': len(self._embeddings_cache),
            'vocabulary_size': len(self._vocabulary),
            'model_loaded': self._model_loaded,
            'using_simple_mode': self._use_simple_mode,
        }


class FuzzyMatcher:
    """
    Fuzzy string matching using multiple algorithms
    """
    
    @staticmethod
    def levenshtein_ratio(s1: str, s2: str) -> float:
        """Calculate Levenshtein similarity ratio (0-1)"""
        if not s1 or not s2:
            return 0.0
        
        s1 = s1.lower()
        s2 = s2.lower()
        
        if s1 == s2:
            return 1.0
        
        len1, len2 = len(s1), len(s2)
        
        # Create distance matrix
        distances = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            distances[i][0] = i
        for j in range(len2 + 1):
            distances[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                distances[i][j] = min(
                    distances[i-1][j] + 1,      # deletion
                    distances[i][j-1] + 1,      # insertion
                    distances[i-1][j-1] + cost  # substitution
                )
        
        distance = distances[len1][len2]
        max_len = max(len1, len2)
        
        return 1 - (distance / max_len)
    
    @staticmethod
    def token_set_ratio(s1: str, s2: str) -> float:
        """
        Token set ratio - handles word reordering
        e.g., "Harry Potter" vs "Potter Harry" = 1.0
        """
        if not s1 or not s2:
            return 0.0
        
        tokens1 = set(s1.lower().split())
        tokens2 = set(s2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
    
    @staticmethod
    def partial_ratio(s1: str, s2: str) -> float:
        """
        Partial matching - finds best substring match
        Useful for partial title searches
        """
        if not s1 or not s2:
            return 0.0
        
        s1 = s1.lower()
        s2 = s2.lower()
        
        # Ensure s1 is shorter
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        
        best_ratio = 0.0
        
        # Slide s1 over s2
        for i in range(len(s2) - len(s1) + 1):
            substring = s2[i:i+len(s1)]
            ratio = FuzzyMatcher.levenshtein_ratio(s1, substring)
            best_ratio = max(best_ratio, ratio)
        
        return best_ratio
    
    @staticmethod
    def combined_score(s1: str, s2: str) -> float:
        """Combine multiple fuzzy matching scores"""
        lev = FuzzyMatcher.levenshtein_ratio(s1, s2)
        token = FuzzyMatcher.token_set_ratio(s1, s2)
        partial = FuzzyMatcher.partial_ratio(s1, s2)
        
        # Weighted combination
        return 0.4 * lev + 0.3 * token + 0.3 * partial
