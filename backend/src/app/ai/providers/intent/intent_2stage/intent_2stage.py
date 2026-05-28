"""
2-Stage Intent Detection Provider

Optimized intent detection that separates:
- Stage 1: Fast category classification (~0.3-0.5s)
- Stage 2: Category-specific function call detection (~0.5-0.8s)

Total: ~0.8-1.3s vs original ~3-6s
"""

from __future__ import annotations

import json
import re
import time
import hashlib
from typing import List, Dict, TYPE_CHECKING, Optional

from ..base import IntentProviderBase
from .category_classifier import CategoryClassifier
from .category_tools_map import (
    get_category_tools,
    is_fast_path_category,
    get_fast_path_action
)
from .prompts import (
    build_function_call_prompt,
    get_fast_path_response
)
from app.ai.plugins_func.functions.play_music import initialize_music_handler
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler


class IntentProvider(IntentProviderBase):
    """
    2-Stage Intent Detection Provider.
    
    Significantly reduces latency by:
    1. Using a lightweight prompt for category classification
    2. Only loading category-specific tools for function detection
    3. Fast-path optimization for common intents (greeting, goodbye)
    """
    
    def __init__(self, config: dict):
        """
        Initialize the 2-stage intent provider.
        
        Args:
            config: Configuration dictionary with:
                - llm: Name of LLM provider to use
                - cache_ttl: Cache TTL in seconds (default: 600)
                - fast_path_categories: Categories to skip Stage 2
        """
        super().__init__(config)
        self.llm = None
        self.classifier: Optional[CategoryClassifier] = None
        self.cache_ttl = config.get("cache_ttl", 600)
        
        # Import cache manager
        from app.ai.utils.cache import async_cache_manager, CacheType
        self.cache_manager = async_cache_manager
        self.CacheType = CacheType
        
        # Track timing for optimization
        self.history_count = 4  # For dialogue context
        
        logger.bind(tag=TAG).info(
            "[2Stage] Intent provider initialized with cache_ttl=%s", 
            self.cache_ttl
        )
    
    def _ensure_classifier(self):
        """Ensure classifier is initialized with LLM."""
        if self.classifier is None and self.llm:
            self.classifier = CategoryClassifier(
                llm=self.llm,
                cache_manager=self.cache_manager,
                cache_type=self.CacheType
            )
    
    async def detect_intent(
        self, 
        conn: 'ConnectionHandler', 
        dialogue_history: List[Dict], 
        text: str
    ) -> str:
        """
        Detect intent using 2-stage approach.
        
        Args:
            conn: Connection handler with device info
            dialogue_history: Previous dialogue messages
            text: Current user input
            
        Returns:
            JSON string with function_call information
        """
        if not self.llm:
            raise ValueError("LLM provider not set")
        
        self._ensure_classifier()
        
        total_start = time.time()
        device_id = getattr(conn, "device_mac_address", None) or str(conn.device_id or "unknown")
        
        # =============================================
        # STAGE 1: Category Classification
        # =============================================
        stage1_start = time.time()
        category = await self.classifier.classify(text, device_id)
        stage1_time = time.time() - stage1_start
        
        logger.bind(tag=TAG).debug(
            f"[2Stage] Stage 1 complete: '{text[:20]}...' → {category} ({stage1_time:.3f}s)"
        )
        
        # =============================================
        # FAST-PATH: Skip Stage 2 for simple intents
        # =============================================
        if is_fast_path_category(category):
            action = get_fast_path_action(category)
            intent_result = get_fast_path_response(category)
            
            total_time = time.time() - total_start
            logger.bind(tag=TAG).info(
                f"[2Stage] Fast-path: {category} → {action} (total: {total_time:.3f}s)"
            )
            
            # Special handling for goodbye
            if category == "goodbye":
                self._log_intent_result("handle_exit_intent", {})
            elif category == "context_query":
                self._log_intent_result("result_for_context", {})
            else:
                self._log_intent_result("continue_chat", {})
            
            # Clean dialogue for chat continuation
            if category in ["greeting", "general_chat"]:
                self._clean_dialogue_history(conn)
            
            return intent_result
        
        # =============================================
        # STAGE 2: Function Call Detection
        # =============================================
        stage2_start = time.time()
        
        # Get category-specific tools
        category_tool_names = get_category_tools(category)
        
        # Filter available functions to only category tools
        functions = []
        if conn.func_handler:
            all_functions = conn.func_handler.get_functions() or []
            
            # Also include MCP tools
            if hasattr(conn, "mcp_client"):
                mcp_tools = conn.mcp_client.get_available_tools()
                if mcp_tools:
                    all_functions.extend(mcp_tools)
            
            # Filter to category tools only
            for func in all_functions:
                func_info = func.get("function", {})
                func_name = func_info.get("name", "")
                if func_name in category_tool_names or not category_tool_names:
                    functions.append(func)
        
        # Add music file names for music category
        music_context = ""
        if category == "music":
            music_config = initialize_music_handler(conn)
            music_file_names = music_config.get("music_file_names", [])
            if music_file_names:
                music_context = f"\n<musicNames>{music_file_names}</musicNames>"
        
        # Build Stage 2 prompt
        system_prompt, user_prompt = build_function_call_prompt(text, functions)
        system_prompt += music_context
        
        # Include dialogue context
        dialogue_context = self._build_dialogue_context(dialogue_history, text)
        full_user_prompt = f"{dialogue_context}\n{user_prompt}"
        
        # Call LLM for function detection
        try:
            intent_response = self.llm.response_no_stream(
                system_prompt=system_prompt,
                user_prompt=full_user_prompt
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"[2Stage] Stage 2 LLM error: {e}")
            return '{"function_call": {"name": "continue_chat"}}'
        
        stage2_time = time.time() - stage2_start
        
        # Parse and validate response
        intent = self._parse_intent_response(intent_response)
        
        total_time = time.time() - total_start
        
        # Log performance metrics
        logger.bind(tag=TAG).info(
            f"[2Stage] Complete: category={category}, "
            f"stage1={stage1_time:.3f}s, stage2={stage2_time:.3f}s, "
            f"total={total_time:.3f}s, tools_loaded={len(functions)}"
        )
        
        # Log the detected intent
        try:
            intent_data = json.loads(intent)
            if "function_call" in intent_data:
                func_call = intent_data["function_call"]
                self._log_intent_result(
                    func_call.get("name", "unknown"),
                    func_call.get("arguments", {})
                )
        except json.JSONDecodeError:
            pass
        
        # Cache the result
        cache_key = hashlib.md5(f"{device_id}:{text}".encode()).hexdigest()
        try:
            await self.cache_manager.set(
                self.CacheType.INTENT,
                cache_key,
                intent,
                ttl=self.cache_ttl
            )
        except Exception:
            pass
        
        return intent
    
    def _parse_intent_response(self, response: str) -> str:
        """Parse and validate the LLM response."""
        response = response.strip()
        
        # Try to extract JSON
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            response = match.group(0)
        
        # Validate JSON
        try:
            data = json.loads(response)
            if "function_call" in data:
                return response
        except json.JSONDecodeError:
            pass
        
        # Fallback
        return '{"function_call": {"name": "continue_chat"}}'
    
    def _build_dialogue_context(self, dialogue_history: List, text: str) -> str:
        """Build dialogue context for Stage 2."""
        msg_str = ""
        start_idx = max(0, len(dialogue_history) - self.history_count)
        
        for i in range(start_idx, len(dialogue_history)):
            msg = dialogue_history[i]
            # Handle both Message objects and dicts
            if hasattr(msg, "role"):
                role = msg.role
                content = msg.content if hasattr(msg, "content") else ""
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
            else:
                continue
            msg_str += f"{role}: {content}\n"
        
        return f"Dialogue context:\n{msg_str}"
    
    def _clean_dialogue_history(self, conn: 'ConnectionHandler'):
        """Clean tool-related messages from dialogue."""
        if hasattr(conn, "dialogue") and hasattr(conn.dialogue, "dialogue"):
            conn.dialogue.dialogue = [
                msg for msg in conn.dialogue.dialogue
                if getattr(msg, "role", None) not in ["tool", "function"]
            ]
    
    def _log_intent_result(self, func_name: str, args: dict):
        """Log the detected intent."""
        logger.bind(tag=TAG).info(
            f"[2Stage] Detected intent: {func_name}, args: {args}"
        )
    
    def replyResult(self, text: str, original_text: str) -> str:
        """Generate natural language reply for result_for_context."""
        return self.llm.response_no_stream(
            system_prompt=text,
            user_prompt=(
                "Hãy dựa trên nội dung trên, trả lời người dùng như một con người "
                "với giọng tự nhiên, ngắn gọn. Người dùng đang nói: " + original_text
            )
        )
