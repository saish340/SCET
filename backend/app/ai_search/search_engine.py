"""
AI Search Engine
Main search orchestrator combining semantic search, spell correction, and fuzzy matching
Behaves like an AI assistant - infers, explains, and refines
"""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import asyncio

from .spell_corrector import SpellCorrector
from .semantic_search import SemanticMatcher, FuzzyMatcher
from ..database.models import WorkMetadata, SearchLog
from ..database.connection import get_db_context
from ..data_collection.collector import get_collector
from ..utils import normalize_title, generate_session_id
from ..config import get_settings
from ..schemas import SearchResult, SearchResponse
import re

settings = get_settings()
logger = logging.getLogger(__name__)

# Technology/Technical keywords that suggest patent/software search
TECH_KEYWORDS = {
    'system', 'device', 'apparatus', 'method', 'process', 'technology',
    'software', 'hardware', 'algorithm', 'machine', 'engine', 'sensor',
    'controller', 'network', 'protocol', 'interface', 'platform', 'framework',
    'autonomous', 'automated', 'smart', 'intelligent', 'ai', 'ml', 'iot',
    'electric', 'electronic', 'digital', 'wireless', 'bluetooth', 'wifi',
    'robot', 'robotic', 'automotive', 'vehicle', 'car', 'drone', 'camera',
    'battery', 'solar', 'renewable', 'energy', 'power', 'chip', 'processor',
    'computer', 'computing', 'cloud', 'database', 'server', 'api', 'mobile'
}

# Creative work keywords
CREATIVE_KEYWORDS = {
    'song', 'album', 'music', 'book', 'novel', 'story', 'poem', 'poetry',
    'film', 'movie', 'documentary', 'series', 'show', 'episode', 'symphony',
    'concerto', 'opera', 'play', 'drama', 'comedy', 'painting', 'artwork'
}


class AISearchEngine:
    """
    Intelligent search engine that:
    - Understands user intent (not just keyword matching)
    - Corrects spelling mistakes
    - Finds semantically similar results
    - Explains its reasoning
    - Learns from user interactions
    """
    
    def __init__(self):
        self.spell_corrector = SpellCorrector()
        self.semantic_matcher = SemanticMatcher()
        self.fuzzy_matcher = FuzzyMatcher()
        
        # Search configuration - adjusted for phrase matching
        self.exact_weight = 0.35      # Exact/phrase matches more important
        self.phrase_weight = 0.25     # Multi-word phrase matching
        self.semantic_weight = 0.25   # Semantic similarity
        self.fuzzy_weight = 0.15      # Fuzzy character matching
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine intent and optimal search strategy
        Returns: dict with query_type, is_technical, keywords, etc.
        """
        normalized = normalize_title(query).lower()
        words = set(normalized.split())
        
        tech_matches = words & TECH_KEYWORDS
        creative_matches = words & CREATIVE_KEYWORDS
        
        is_technical = len(tech_matches) > len(creative_matches)
        is_multi_word = len(words) > 1
        
        # Detect if query is a phrase (specific concept)
        is_phrase = is_multi_word and not any(w in ['the', 'a', 'an', 'of', 'for', 'and', 'or', 'in', 'on', 'at', 'to', 'by'] for w in words if len(w) < 4)
        
        # Suggest content type based on query analysis
        suggested_type = None
        if 'patent' in words or (is_technical and len(tech_matches) >= 2):
            suggested_type = 'patent'
        elif 'software' in words or 'code' in words or 'library' in words:
            suggested_type = 'software'
        elif 'trademark' in words or 'brand' in words:
            suggested_type = 'trademark'
        elif any(w in words for w in ['book', 'novel', 'author', 'story']):
            suggested_type = 'book'
        elif any(w in words for w in ['song', 'album', 'artist', 'band']):
            suggested_type = 'music'
        elif any(w in words for w in ['film', 'movie', 'director']):
            suggested_type = 'film'
        
        return {
            'is_technical': is_technical,
            'is_multi_word': is_multi_word,
            'is_phrase': is_phrase,
            'tech_keywords': tech_matches,
            'suggested_type': suggested_type,
            'word_count': len(words),
            'min_word_match_ratio': 0.7 if is_phrase else 0.3  # Require 70% word match for phrases
        }
    
    async def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        max_results: int = 10,
        include_web_results: bool = True,
        session_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> SearchResponse:
        """
        Main AI-powered search method
        Combines multiple search strategies for best results
        """
        start_time = time.time()
        session_id = session_id or generate_session_id()
        
        # Step 1: Spell correction
        corrected_query, was_corrected = self.spell_corrector.correct(query)
        
        logger.info(f"Search: '{query}' -> '{corrected_query}' (corrected: {was_corrected})")
        
        # Step 2: Search in local database
        if db is None:
            with get_db_context() as db:
                return await self._execute_search(
                    query, corrected_query, was_corrected,
                    content_type, max_results, include_web_results,
                    session_id, db, start_time
                )
        else:
            return await self._execute_search(
                query, corrected_query, was_corrected,
                content_type, max_results, include_web_results,
                session_id, db, start_time
            )
    
    async def _execute_search(
        self,
        original_query: str,
        corrected_query: str,
        was_corrected: bool,
        content_type: Optional[str],
        max_results: int,
        include_web_results: bool,
        session_id: str,
        db: Session,
        start_time: float
    ) -> SearchResponse:
        """Execute the full search pipeline"""
        
        search_query = corrected_query
        all_results: List[Tuple[WorkMetadata, float]] = []
        
        # Analyze query for intent and optimal search strategy
        query_analysis = self._analyze_query(search_query)
        
        # Auto-suggest content type if technical query and none specified
        if not content_type and query_analysis.get('suggested_type'):
            logger.info(f"Query suggests content type: {query_analysis['suggested_type']}")
        
        # Step 2: Database search (existing data)
        db_results = self._search_database(search_query, content_type, db, max_results * 2, query_analysis)
        all_results.extend(db_results)
        
        # Step 3: Web search if needed (collect new data)
        if include_web_results and len(all_results) < max_results:
            collector = get_collector()
            new_works = await collector.collect_for_query(search_query, content_type, db)
            
            # Score the new works with query analysis
            for work in new_works:
                score = self._calculate_relevance_score(search_query, work, query_analysis)
                all_results.append((work, score))
        
        # Step 4: Rank and deduplicate
        ranked_results = self._rank_and_deduplicate(all_results, max_results)
        
        # Step 5: Generate AI explanation
        ai_explanation = self._generate_explanation(
            original_query, corrected_query, was_corrected,
            ranked_results, content_type
        )
        
        # Step 6: Generate suggestions
        suggestions = self._generate_suggestions(search_query, ranked_results, db)
        
        # Step 7: Log search for learning
        search_time_ms = int((time.time() - start_time) * 1000)
        self._log_search(
            original_query, corrected_query, 
            len(ranked_results), session_id, 
            search_time_ms, db
        )
        
        # Convert to response format
        search_results = []
        for work, score in ranked_results:
            search_results.append(SearchResult(
                id=work.id,
                title=work.title,
                creator=work.creator,
                publication_year=work.publication_year,
                content_type=work.content_type,
                copyright_status=work.copyright_status or "unknown",
                similarity_score=round(score, 3),
                source=work.source_name
            ))
        
        return SearchResponse(
            query=original_query,
            corrected_query=corrected_query if was_corrected else None,
            results=search_results,
            total_found=len(search_results),
            search_time_ms=search_time_ms,
            ai_explanation=ai_explanation,
            suggestions=suggestions
        )
    
    def _search_database(
        self,
        query: str,
        content_type: Optional[str],
        db: Session,
        limit: int,
        query_analysis: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[WorkMetadata, float]]:
        """Search existing database entries with improved phrase matching"""
        
        normalized_query = normalize_title(query).lower()
        query_words = normalized_query.split()
        
        if query_analysis is None:
            query_analysis = self._analyze_query(query)
        
        min_word_ratio = query_analysis.get('min_word_match_ratio', 0.3)
        is_phrase = query_analysis.get('is_phrase', False)
        
        # Build base query
        base_query = db.query(WorkMetadata)
        
        if content_type:
            base_query = base_query.filter(WorkMetadata.content_type == content_type)
        
        # Get candidates using multiple strategies
        results: List[Tuple[WorkMetadata, float]] = []
        
        # Strategy 1: Exact match (highest priority)
        exact_matches = base_query.filter(
            func.lower(WorkMetadata.title_normalized) == normalized_query
        ).limit(5).all()
        
        for work in exact_matches:
            results.append((work, 1.0))
        
        # Strategy 2: Full phrase contains match
        contains_matches = base_query.filter(
            WorkMetadata.title_normalized.contains(normalized_query)
        ).limit(limit).all()
        
        for work in contains_matches:
            if work not in [r[0] for r in results]:
                score = self._calculate_relevance_score(query, work, query_analysis)
                results.append((work, score))
        
        # Strategy 3: Multi-word matching with minimum overlap requirement
        if len(query_words) > 1:
            # For phrases, require multiple words to match
            word_conditions = [
                WorkMetadata.title_normalized.contains(word)
                for word in query_words if len(word) > 2  # Skip short words
            ]
            
            if word_conditions:
                word_matches = base_query.filter(or_(*word_conditions)).limit(limit * 2).all()
                
                for work in word_matches:
                    if work not in [r[0] for r in results]:
                        # Check word overlap before adding
                        title_normalized = normalize_title(work.title).lower()
                        matching_words = sum(1 for w in query_words if w in title_normalized)
                        overlap_ratio = matching_words / len(query_words)
                        
                        # Only include if meets minimum word overlap
                        if overlap_ratio >= min_word_ratio or not is_phrase:
                            score = self._calculate_relevance_score(query, work, query_analysis)
                            # Apply penalty if low overlap
                            if overlap_ratio < 0.5 and is_phrase:
                                score *= 0.5
                            results.append((work, score))
        else:
            # Single word query - standard matching
            word_conditions = [
                WorkMetadata.title_normalized.contains(word)
                for word in query_words
            ]
            word_matches = base_query.filter(or_(*word_conditions)).limit(limit).all()
            
            for work in word_matches:
                if work not in [r[0] for r in results]:
                    score = self._calculate_relevance_score(query, work, query_analysis)
                    results.append((work, score))
        
        # Strategy 4: Semantic similarity (for remaining slots)
        if len(results) < limit:
            all_works = base_query.limit(limit * 3).all()
            candidates = [(w.id, w.title) for w in all_works if w not in [r[0] for r in results]]
            
            if candidates:
                semantic_results = self.semantic_matcher.find_similar(
                    query, candidates, 
                    top_k=limit - len(results),
                    min_similarity=settings.MIN_SIMILARITY_THRESHOLD
                )
                
                for work_id, title, sim_score in semantic_results:
                    work = db.query(WorkMetadata).filter(WorkMetadata.id == work_id).first()
                    if work:
                        results.append((work, sim_score))
        
        return results
    
    def _calculate_relevance_score(
        self, 
        query: str, 
        work: WorkMetadata, 
        query_analysis: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate relevance score combining multiple signals with phrase awareness"""
        
        title = work.title or ""
        normalized_query = normalize_title(query).lower()
        normalized_title = normalize_title(title).lower()
        
        query_words = normalized_query.split()
        title_words = normalized_title.split()
        
        # Get query analysis if not provided
        if query_analysis is None:
            query_analysis = self._analyze_query(query)
        
        # === EXACT MATCH COMPONENT ===
        exact_score = 0.0
        if normalized_query == normalized_title:
            exact_score = 1.0
        elif normalized_query in normalized_title:
            # Full query appears as substring
            exact_score = 0.85
        elif normalized_title in normalized_query:
            exact_score = 0.6
        
        # === PHRASE/WORD OVERLAP COMPONENT ===
        phrase_score = 0.0
        if len(query_words) > 1:
            # Count how many query words appear in title
            matching_words = sum(1 for w in query_words if w in normalized_title)
            word_overlap_ratio = matching_words / len(query_words)
            
            # Check for consecutive word matches (phrase match)
            consecutive_matches = 0
            for i in range(len(query_words) - 1):
                bigram = f"{query_words[i]} {query_words[i+1]}"
                if bigram in normalized_title:
                    consecutive_matches += 1
            
            # Phrase score based on word overlap and consecutiveness
            phrase_score = word_overlap_ratio * 0.7
            if consecutive_matches > 0:
                phrase_score += 0.3 * (consecutive_matches / (len(query_words) - 1))
            
            # PENALTY: If multi-word query but low word overlap, severely penalize
            min_ratio = query_analysis.get('min_word_match_ratio', 0.3)
            if word_overlap_ratio < min_ratio:
                phrase_score *= 0.2  # Harsh penalty for low overlap
        else:
            # Single word query - check if word is significant in title
            if normalized_query in title_words:
                phrase_score = 0.8  # Direct word match
            elif normalized_query in normalized_title:
                phrase_score = 0.5  # Substring match
        
        # === FUZZY MATCH COMPONENT ===
        fuzzy_score = self.fuzzy_matcher.combined_score(query, title)
        
        # === SEMANTIC SIMILARITY ===
        semantic_score = self.semantic_matcher.compute_similarity(query, title)
        
        # === DATA CONFIDENCE BOOST ===
        confidence_boost = (work.data_confidence or 0.5) * 0.05
        
        # === COMBINE SCORES ===
        # For multi-word queries, phrase matching is crucial
        if len(query_words) > 1:
            combined = (
                self.exact_weight * exact_score +
                self.phrase_weight * phrase_score +
                self.semantic_weight * semantic_score +
                self.fuzzy_weight * fuzzy_score * 0.5 +  # Reduce fuzzy weight for phrases
                confidence_boost
            )
        else:
            combined = (
                self.exact_weight * exact_score +
                self.phrase_weight * phrase_score +
                self.semantic_weight * semantic_score +
                self.fuzzy_weight * fuzzy_score +
                confidence_boost
            )
        
        return min(combined, 1.0)  # Cap at 1.0
    
    def _rank_and_deduplicate(
        self,
        results: List[Tuple[WorkMetadata, float]],
        max_results: int,
        min_score: float = 0.15  # Minimum score threshold to include
    ) -> List[Tuple[WorkMetadata, float]]:
        """Rank results, remove duplicates, and filter low-relevance items"""
        
        # Filter by minimum score
        filtered_results = [(work, score) for work, score in results if score >= min_score]
        
        # Deduplicate by normalized title
        seen_titles = set()
        unique_results = []
        
        for work, score in filtered_results:
            normalized = normalize_title(work.title)
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_results.append((work, score))
        
        # Sort by score (descending)
        unique_results.sort(key=lambda x: x[1], reverse=True)
        
        return unique_results[:max_results]
    
    def _generate_explanation(
        self,
        original_query: str,
        corrected_query: str,
        was_corrected: bool,
        results: List[Tuple[WorkMetadata, float]],
        content_type: Optional[str]
    ) -> str:
        """Generate human-readable AI explanation of search process"""
        
        explanation_parts = []
        query_analysis = self._analyze_query(original_query)
        
        # Explain correction
        if was_corrected:
            explanation_parts.append(
                f"I understood you were looking for \"{corrected_query}\" "
                f"(corrected from \"{original_query}\")."
            )
        else:
            explanation_parts.append(f"Searching for \"{original_query}\".")
        
        # Explain content type filter
        if content_type:
            explanation_parts.append(f"Filtered by content type: {content_type}.")
        
        # Suggest content type for technical queries
        if not content_type and query_analysis.get('is_technical'):
            suggested = query_analysis.get('suggested_type')
            if suggested:
                explanation_parts.append(
                    f"💡 Tip: This looks like a technical query. "
                    f"Try selecting '{suggested}' as the content type for more relevant results."
                )
        
        # Explain results
        if not results:
            explanation_parts.append(
                "I couldn't find any matching works in my database or web sources. "
                "Try a different search term or check the spelling."
            )
            if query_analysis.get('is_technical'):
                explanation_parts.append(
                    "For technology-related searches, try selecting 'Patent' or 'Software' as the content type."
                )
        elif len(results) == 1:
            work, score = results[0]
            confidence = "high" if score > 0.8 else "moderate" if score > 0.6 else "low"
            explanation_parts.append(
                f"Found 1 result with {confidence} confidence. "
                f"Best match: \"{work.title}\" ({work.content_type or 'unknown type'})."
            )
        else:
            best_work, best_score = results[0]
            explanation_parts.append(
                f"Found {len(results)} results. "
                f"Best match: \"{best_work.title}\" with {best_score:.0%} relevance."
            )
            
            # Warn if results seem unrelated (low scores)
            if best_score < 0.5 and query_analysis.get('is_phrase'):
                explanation_parts.append(
                    "⚠️ Results may not be exactly what you're looking for. "
                    "Try a more specific search or select a content type."
                )
            
            # Explain variety in results
            types = set(w.content_type for w, _ in results if w.content_type)
            if len(types) > 1:
                explanation_parts.append(
                    f"Results include: {', '.join(types)}."
                )
        
        return " ".join(explanation_parts)
    
    def _generate_suggestions(
        self,
        query: str,
        results: List[Tuple[WorkMetadata, float]],
        db: Session
    ) -> List[str]:
        """Generate related search suggestions"""
        suggestions = []
        
        # Spelling alternatives
        spell_suggestions = self.spell_corrector.get_suggestions(query, max_suggestions=2)
        suggestions.extend(spell_suggestions)
        
        # Related creators
        if results:
            creators = set()
            for work, _ in results[:3]:
                if work.creator:
                    creators.add(work.creator)
            
            for creator in list(creators)[:2]:
                suggestions.append(f"Works by {creator}")
        
        # Content type suggestions
        if results:
            work, _ = results[0]
            if work.content_type:
                suggestions.append(f"More {work.content_type}s")
        
        return list(set(suggestions))[:5]
    
    def _log_search(
        self,
        original_query: str,
        corrected_query: str,
        result_count: int,
        session_id: str,
        search_time_ms: int,
        db: Session
    ):
        """Log search for learning and analytics"""
        try:
            log_entry = SearchLog(
                query_text=original_query,
                query_normalized=normalize_title(original_query),
                corrected_query=corrected_query if corrected_query != original_query else None,
                result_count=result_count,
                was_successful=result_count > 0,
                search_time_ms=search_time_ms,
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging search: {e}")
    
    def learn_from_selection(
        self,
        query: str,
        selected_work_id: int,
        db: Session
    ):
        """Learn from user's result selection"""
        
        work = db.query(WorkMetadata).filter(WorkMetadata.id == selected_work_id).first()
        if work:
            # Teach spell corrector
            self.spell_corrector.learn_from_search(query, work.title)
            
            # Update search log
            try:
                recent_log = db.query(SearchLog).filter(
                    SearchLog.query_text == query
                ).order_by(SearchLog.timestamp.desc()).first()
                
                if recent_log:
                    recent_log.user_selected_id = selected_work_id
                    db.commit()
            except Exception as e:
                logger.error(f"Error updating search log: {e}")
    
    def provide_feedback(
        self,
        search_id: int,
        rating: int,
        was_correct: bool,
        db: Session
    ):
        """Record user feedback for model improvement"""
        try:
            log_entry = db.query(SearchLog).filter(SearchLog.id == search_id).first()
            if log_entry:
                log_entry.feedback_score = rating
                log_entry.was_successful = was_correct
                db.commit()
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            'semantic_matcher': self.semantic_matcher.get_cache_stats(),
            'weights': {
                'semantic': self.semantic_weight,
                'fuzzy': self.fuzzy_weight,
                'exact': self.exact_weight,
            }
        }


# Singleton instance
_search_engine: Optional[AISearchEngine] = None


def get_search_engine() -> AISearchEngine:
    """Get or create search engine instance"""
    global _search_engine
    if _search_engine is None:
        _search_engine = AISearchEngine()
    return _search_engine
