"""
Spell Correction Module
Handles misspellings, typos, and fuzzy matching for title search
Uses multiple strategies for robust correction
"""

import re
from typing import Optional, List, Tuple, Dict, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class SpellCorrector:
    """
    Advanced spell corrector for title search
    - Handles common typos
    - Learns from search patterns
    - Supports phonetic matching
    """
    
    def __init__(self):
        # Common letter substitutions (typos)
        self.keyboard_neighbors = {
            'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs',
            'e': 'wrsdf', 'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yujnbg',
            'i': 'uojkl', 'j': 'uikmnh', 'k': 'iojlm', 'l': 'kopk',
            'm': 'njk', 'n': 'bhjm', 'o': 'iplk', 'p': 'ol',
            'q': 'wa', 'r': 'edft', 's': 'wedxza', 't': 'rfgy',
            'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
            'y': 'tghu', 'z': 'asx'
        }
        
        # Common misspellings for famous works
        self.known_corrections = {
            'harry poter': 'harry potter',
            'hary potter': 'harry potter',
            'harrry potter': 'harry potter',
            'lord of the ring': 'lord of the rings',
            'starwars': 'star wars',
            'star war': 'star wars',
            'beatles': 'the beatles',
            'shakespear': 'shakespeare',
            'shakspeare': 'shakespeare',
            'romeo juliet': 'romeo and juliet',
            'micheal jackson': 'michael jackson',
            'micheal': 'michael',
            'lenon': 'lennon',
            'beethovn': 'beethoven',
            'mozard': 'mozart',
            'tolstoi': 'tolstoy',
            'dostoevsky': 'dostoyevsky',
            'hemmingway': 'hemingway',
            'fitzgerld': 'fitzgerald',
        }
        
        # Learned corrections from user searches
        self._learned_corrections: Dict[str, str] = {}
        
        # Word frequency from searches (for probability-based correction)
        self._word_freq: Counter = Counter()
        
        # Known valid titles for direct matching
        self._known_titles: Set[str] = set()
    
    def correct(self, text: str) -> Tuple[str, bool]:
        """
        Correct spelling in text
        Returns (corrected_text, was_corrected)
        """
        if not text:
            return text, False
        
        original = text.lower().strip()
        corrected = original
        was_corrected = False
        
        # Step 1: Check known corrections
        if original in self.known_corrections:
            return self.known_corrections[original], True
        
        # Check learned corrections
        if original in self._learned_corrections:
            return self._learned_corrections[original], True
        
        # Step 2: Check if it's already a known valid title
        if original in self._known_titles:
            return text, False
        
        # Step 3: Word-level correction
        words = original.split()
        corrected_words = []
        
        for word in words:
            # Check known word corrections
            if word in self.known_corrections:
                corrected_words.append(self.known_corrections[word])
                was_corrected = True
            # Check learned corrections
            elif word in self._learned_corrections:
                corrected_words.append(self._learned_corrections[word])
                was_corrected = True
            else:
                # Try to correct using edit distance
                corrected_word = self._correct_word(word)
                if corrected_word != word:
                    was_corrected = True
                corrected_words.append(corrected_word)
        
        corrected = ' '.join(corrected_words)
        
        # Step 4: Check for missing spaces (e.g., "harrypotter" -> "harry potter")
        if not was_corrected and ' ' not in original:
            split_result = self._try_split_words(original)
            if split_result and split_result != original:
                corrected = split_result
                was_corrected = True
        
        return corrected, was_corrected
    
    def _correct_word(self, word: str) -> str:
        """Correct a single word"""
        if len(word) < 3:
            return word
        
        # Check against frequent words
        if word in self._word_freq:
            return word
        
        # Find candidates within edit distance 1-2
        candidates = self._get_candidates(word)
        
        if not candidates:
            return word
        
        # Return most frequent candidate
        return max(candidates, key=lambda x: self._word_freq.get(x, 0))
    
    def _get_candidates(self, word: str) -> Set[str]:
        """Get correction candidates for a word"""
        candidates = set()
        
        # Edit distance 1
        edits1 = self._edits1(word)
        candidates.update(w for w in edits1 if w in self._word_freq)
        
        if candidates:
            return candidates
        
        # Edit distance 2
        for e1 in edits1:
            edits2 = self._edits1(e1)
            candidates.update(w for w in edits2 if w in self._word_freq)
        
        return candidates
    
    def _edits1(self, word: str) -> Set[str]:
        """Generate all strings that are one edit away from word"""
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        
        # Deletions
        deletes = [L + R[1:] for L, R in splits if R]
        
        # Transpositions
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        
        # Replacements
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        
        # Insertions
        inserts = [L + c + R for L, R in splits for c in letters]
        
        return set(deletes + transposes + replaces + inserts)
    
    def _try_split_words(self, text: str) -> Optional[str]:
        """Try to split concatenated words"""
        # Common known splits
        known_splits = {
            'harrypotter': 'harry potter',
            'lordoftherings': 'lord of the rings',
            'starwars': 'star wars',
            'gameofthrones': 'game of thrones',
        }
        
        if text in known_splits:
            return known_splits[text]
        
        # Try dynamic splitting using word frequency
        result = self._split_words(text)
        if result and len(result.split()) > 1:
            return result
        
        return None
    
    def _split_words(self, text: str) -> str:
        """Split concatenated words using dynamic programming"""
        if not self._word_freq:
            return text
        
        # Simple greedy splitting
        words = []
        remaining = text
        
        while remaining:
            found = False
            # Try to find the longest matching word
            for end in range(len(remaining), 0, -1):
                candidate = remaining[:end]
                if candidate in self._word_freq and len(candidate) >= 2:
                    words.append(candidate)
                    remaining = remaining[end:]
                    found = True
                    break
            
            if not found:
                # No match, keep the character
                words.append(remaining[0])
                remaining = remaining[1:]
        
        return ' '.join(words)
    
    def learn_from_search(self, query: str, selected_title: str):
        """
        Learn from user searches
        Called when user selects a result, teaching the system correct spellings
        """
        query_normalized = query.lower().strip()
        title_normalized = selected_title.lower().strip()
        
        # If query differs from title, learn the correction
        if query_normalized != title_normalized:
            self._learned_corrections[query_normalized] = title_normalized
        
        # Add to known titles
        self._known_titles.add(title_normalized)
        
        # Update word frequencies
        for word in title_normalized.split():
            self._word_freq[word] += 1
    
    def add_known_titles(self, titles: List[str]):
        """Add known valid titles to the vocabulary"""
        for title in titles:
            title_lower = title.lower().strip()
            self._known_titles.add(title_lower)
            
            for word in title_lower.split():
                if len(word) >= 2:
                    self._word_freq[word] += 1
    
    def get_suggestions(self, query: str, max_suggestions: int = 5) -> List[str]:
        """Get spelling correction suggestions"""
        suggestions = []
        
        corrected, was_corrected = self.correct(query)
        if was_corrected:
            suggestions.append(corrected)
        
        # Generate variations
        words = query.lower().split()
        for i, word in enumerate(words):
            candidates = self._get_candidates(word)
            for candidate in list(candidates)[:2]:
                variation = words.copy()
                variation[i] = candidate
                suggestion = ' '.join(variation)
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        return suggestions[:max_suggestions]


class PhoneticMatcher:
    """
    Phonetic matching for handling pronunciation-based typos
    Uses Soundex and Metaphone-like algorithms
    """
    
    @staticmethod
    def soundex(word: str) -> str:
        """Generate Soundex code for a word"""
        if not word:
            return ""
        
        word = word.upper()
        soundex_code = word[0]
        
        mapping = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6',
        }
        
        for char in word[1:]:
            code = mapping.get(char, '')
            if code and code != soundex_code[-1]:
                soundex_code += code
        
        # Pad with zeros
        soundex_code = soundex_code[:4].ljust(4, '0')
        
        return soundex_code
    
    @staticmethod
    def match_phonetically(word1: str, word2: str) -> bool:
        """Check if two words match phonetically"""
        return PhoneticMatcher.soundex(word1) == PhoneticMatcher.soundex(word2)
