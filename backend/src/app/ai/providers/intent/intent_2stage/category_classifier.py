"""
Stage 1: Category Classifier

Fast, lightweight classification of user intent into categories.
Uses a short prompt (~200 tokens) to minimize latency.
"""

from __future__ import annotations

import time
import hashlib
from typing import TYPE_CHECKING

from app.core.logger import setup_logging
from .category_tools_map import (
    CATEGORY_NAMES, 
    keyword_match_category
)
from .prompts import build_category_prompt

TAG = __name__
logger = setup_logging()

if TYPE_CHECKING:
    from app.ai.providers.llm.base import LLMProviderBase


class CategoryClassifier:
    """
    Stage 1 classifier for 2-stage intent detection.
    
    Classifies user input into one of the defined categories
    using a lightweight prompt to minimize latency.
    """
    
    def __init__(self, llm: 'LLMProviderBase', cache_manager=None, cache_type=None):
        """
        Initialize the category classifier.
        
        Args:
            llm: LLM provider for classification
            cache_manager: Optional async cache manager
            cache_type: Cache type enum for category caching
        """
        self.llm = llm
        self.cache_manager = cache_manager
        self.cache_type = cache_type
        self.cache_ttl = 600  # 10 minutes
        
    async def classify(self, text: str, device_id: str = "unknown") -> str:
        """
        Classify user input into a category.
        
        Uses a 3-tier approach:
        1. Check cache first
        2. Try keyword matching (instant)
        3. Fall back to LLM classification
        
        Args:
            text: User input text
            device_id: Device identifier for cache key
            
        Returns:
            Category name (string)
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = hashlib.md5(f"{device_id}:{text}".encode()).hexdigest()
        
        # Tier 1: Check cache
        if self.cache_manager and self.cache_type:
            try:
                cached = await self.cache_manager.get(
                    self.cache_type.INTENT, 
                    f"cat:{cache_key}"
                )
                if cached:
                    logger.bind(tag=TAG).debug(
                        f"[Stage1] Cache hit: '{text[:20]}...' → {cached}"
                    )
                    return cached
            except Exception as e:
                logger.bind(tag=TAG).debug(f"[Stage1] Cache error: {e}")
        
        # Tier 2: Keyword matching (instant, no API call)
        keyword_category = keyword_match_category(text)
        if keyword_category:
            logger.bind(tag=TAG).debug(
                f"[Stage1] Keyword match: '{text[:20]}...' → {keyword_category} "
                f"({(time.time() - start_time) * 1000:.1f}ms)"
            )
            # Cache the result
            await self._cache_result(cache_key, keyword_category)
            return keyword_category
        
        # Tier 3: LLM classification
        category = await self._llm_classify(text)
        
        # Validate category
        if category not in CATEGORY_NAMES:
            logger.bind(tag=TAG).warning(
                f"[Stage1] Invalid category '{category}', fallback to general_chat"
            )
            category = "general_chat"
        
        # Log performance
        elapsed = time.time() - start_time
        logger.bind(tag=TAG).info(
            f"[Stage1] LLM classify: '{text[:20]}...' → {category} ({elapsed:.3f}s)"
        )
        
        # Cache the result
        await self._cache_result(cache_key, category)
        
        return category
    
    async def _llm_classify(self, text: str) -> str:
        """
        Use LLM to classify the text.
        
        Args:
            text: User input
            
        Returns:
            Category name
        """
        system_prompt, user_prompt = build_category_prompt(text)
        
        try:
            # Use non-streaming for fastest response
            response = self.llm.response_no_stream(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # Parse response - should be a single word
            category = response.strip().lower()
            
            # Clean up common LLM artifacts
            category = category.replace('"', '').replace("'", '')
            category = category.split()[0] if category else "general_chat"
            
            return category
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"[Stage1] LLM error: {e}")
            return "general_chat"
    
    async def _cache_result(self, cache_key: str, category: str):
        """Cache the classification result."""
        if self.cache_manager and self.cache_type:
            try:
                await self.cache_manager.set(
                    self.cache_type.INTENT,
                    f"cat:{cache_key}",
                    category,
                    ttl=self.cache_ttl
                )
            except Exception as e:
                logger.bind(tag=TAG).debug(f"[Stage1] Cache set error: {e}")
