"""
OpenMemory Provider - Brain-Inspired Memory Storage

Integrates OpenMemory API for multi-sector memory management:
- Episodic: Event memories (temporal data)
- Semantic: Facts & preferences (factual data)
- Procedural: Habits, triggers (action patterns)
- Emotional: Sentiment states (tone analysis)
- Reflective: Meta memory & logs (audit trail)

Flow: Summarize dialogue → Extract JSON → Add to OpenMemory → Query on demand
"""

import json
import traceback
from typing import List, Dict, Optional, Any
from app.core.logger import setup_logging
from ..base import MemoryProviderBase

TAG = __name__
logger = setup_logging()

# Prompt để tóm tắt hội thoại thành JSON có sector
SUMMARIZATION_PROMPT = """Bạn là hệ thống trích xuất thông tin (Memory Extractor).

## MỤC TIÊU
Trích xuất MỌI thông tin cá nhân của người dùng từ hội thoại và CHUYỂN ĐỔI thành định dạng nén siêu gọn (AAAK - AI Shorthand Dialect) để tiết kiệm token tối đa khi nạp vào memory context.

## QUY TẮC NÉN AAAK (AI SHORTHAND)
1. Lược bỏ hoàn toàn từ ngữ vô giá trị (như: "của tôi", "tên là", "rất thích").
2. Sử dụng ký hiệu:
   - `|` để phân cách các ý chính
   - `:` để gán giá trị
   - `+` thay cho "và"
   - `>` thay cho "thích hơn/chọn cái này thay cái kia"
   - `→` thay cho hành động/kết quả xảy ra
3. Dùng các tiền tố (Prefix) viết hoa: USER, FAM (Gia đình), WORK (Công việc), HOBBY (Sở thích), LOC (Địa điểm), EVENT (Sự kiện), HEALTH.

## VÍ DỤ NÉN
INPUT: "Con gái tôi tên là An, năm nay 5 tuổi, nó rất thích ăn dâu tây và ghét ăn rau."
OUTPUT: {"summary": "FAM:dau(An,5y) | LIKE:dau_tay | DISLIKE:rau", "tags": ["An", "con gái", "dâu tây", "rau"], "sector": "semantic"}

INPUT: "Hôm nay tôi đổi chỗ làm từ quận 1 qua quận 3, công việc code dạo này rất stress."
OUTPUT: {"summary": "WORK:code | LOC:Q1→Q3 | STATUS:stress", "tags": ["code", "quận 3", "stress"], "sector": "episodic"}

INPUT: "Tắt đèn đi."
OUTPUT: {"summary": "", "tags": [], "sector": "semantic"}

## SECTOR
- semantic: Bất biến, sự thật (Sở thích, Tên tuổi, Sức khoẻ)
- episodic: Sự kiện có tính thời điểm (Chuyển việc, Vừa đi chơi về)
- emotional: Cảm xúc, tâm trạng

## OUTPUT (TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON)
```json
{
  "summary": "chuỗi định dạng nén AAAK",
  "tags": ["tag1", "tag2"],
  "sector": "semantic"
}
```
"""


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Trích xuất JSON từ response LLM.
    Hỗ trợ format ```json...``` hoặc raw JSON.
    """
    try:
        # Thử tìm JSON trong ```json...```
        start = response.find("```json")
        if start != -1:
            end = response.find("```", start + 7)
            if end != -1:
                json_str = response[start + 7 : end].strip()
                return json.loads(json_str)

        # Thử parse trực tiếp
        return json.loads(response)
    except (json.JSONDecodeError, ValueError) as e:
        logger.bind(tag=TAG).error(f"Không thể parse JSON từ LLM response: {e}")
        return None


class MemoryProvider(MemoryProviderBase):
    """OpenMemory provider - Tích hợp OpenMemory API cho multi-sector memory."""

    def __init__(self, config: Dict[str, Any], summary_memory=None):
        """
        Khởi tạo OpenMemory provider.

        Args:
            config: Configuration dict chứa:
                - mode: "local" hoặc "remote" (default: "remote")
                - Local mode:
                  - local_path: SQLite database path
                  - tier: "fast" | "balanced" | "quality"
                  - embeddings_provider: "synthetic" | "openai" | "gemini"
                  - embeddings_api_key: API key cho embeddings
                  - embeddings_model: Optional model name
                - Remote mode:
                  - base_url: OpenMemory API base URL
                  - api_key: Optional API key for authentication
                - Common:
                  - k: Số lượng memory results (default: 3)
                  - max_tokens: Max tokens cho LLM tóm tắt (default: 2000)
            summary_memory: Unused, for compatibility
        """
        super().__init__(config)
        
        # Initialize LLM attribute to avoid AttributeError
        # LLM will be set later via set_llm() or init_memory()
        self.llm = None

        self.mode = config.get("mode", "remote")
        self.k = config.get("k", 3)
        self.max_tokens = config.get("max_tokens", 2000)

        # Lazy load OpenMemory client
        self._client = None
        self._client_initialized = False
        self._initialization_error = None

        logger.bind(tag=TAG).info(
            f"OpenMemory provider initialized - mode: {self.mode}, k: {self.k}, max_tokens: {self.max_tokens}"
        )

    def _get_client(self):
        """Lazy initialize OpenMemory client (openmemory-py v1.3+ API)."""
        if self._client_initialized:
            if self._initialization_error:
                raise Exception(self._initialization_error)
            return self._client

        try:
            # Dynamic import để tránh import error nếu không cài openmemory-py
            # Package name: openmemory-py (pip install), Import name: openmemory
            # openmemory-py v1.3+ API: Memory(user=user_id)
            from openmemory import Memory

            # Sử dụng role_id làm default user nếu có
            default_user = str(self.role_id) if self.role_id else "default"
            
            self._client = Memory(user=default_user)
            
            logger.bind(tag=TAG).debug(
                f"OpenMemory client initialized: default_user={default_user}"
            )

            self._client_initialized = True
            return self._client

        except ImportError as e:
            error_msg = f"OpenMemory SDK (openmemory-py) not installed. Install with: pip install openmemory-py. Error: {e}"
            logger.bind(tag=TAG).error(error_msg)
            self._initialization_error = error_msg
            self._client_initialized = True
            raise ImportError(error_msg)
        except Exception as e:
            error_msg = f"Failed to initialize OpenMemory client: {e}"
            logger.bind(tag=TAG).error(error_msg)
            self._initialization_error = error_msg
            self._client_initialized = True
            raise

    def _build_embeddings_config(self) -> Dict[str, Any]:
        """
        Build embeddings config cho local mode.

        Returns:
            Dict with keys: provider, apiKey (optional), model (optional)
        """
        provider = self.config.get("embeddings_provider", "synthetic")

        if provider == "synthetic":
            return {"provider": "synthetic"}

        embeddings_config = {
            "provider": provider,
            "apiKey": self.config.get("embeddings_api_key", ""),
        }

        # Thêm model nếu có
        model = self.config.get("embeddings_model")
        if model:
            embeddings_config["model"] = model

        logger.bind(tag=TAG).debug(
            f"Built embeddings config: provider={provider}, has_key={bool(embeddings_config.get('apiKey'))}, model={model}"
        )

        return embeddings_config

    async def save_memory(self, msgs: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Tóm tắt hội thoại và lưu vào OpenMemory.

        Flow:
        1. Convert Message list thành string
        2. Gọi LLM để tóm tắt theo JSON format
        3. Validate & extract JSON
        4. Add vào OpenMemory với user_id=role_id

        Args:
            msgs: List of Message objects from dialogue

        Returns:
            Dict with memory info or None if failed
        """
        try:
            # Kiểm tra LLM availability
            if self.llm is None:
                logger.bind(tag=TAG).error("LLM is not set for OpenMemory provider")
                return None

            # Kiểm tra min messages (giảm xuống 1 để bắt thông tin từ câu đầu tiên)
            if len(msgs) < 1:
                logger.bind(tag=TAG).debug(
                    "No messages to analyze"
                )
                return None

            # Convert Message list to string
            dialogue_str = self._format_dialogue(msgs)
            if not dialogue_str or dialogue_str.strip() == "":
                logger.bind(tag=TAG).debug("No valid dialogue content to summarize")
                return None

            # Call LLM to summarize
            logger.bind(tag=TAG).debug("Calling LLM for conversation summary")
            llm_response = self.llm.response_no_stream(
                system_prompt=SUMMARIZATION_PROMPT,
                user_prompt=dialogue_str,
                max_tokens=self.max_tokens,
                temperature=0.2,
            )

            # Extract and validate JSON
            summary_data = extract_json_from_response(llm_response)
            if not summary_data:
                logger.bind(tag=TAG).error("Failed to extract JSON from LLM response")
                return None

            # Skip if summary is empty
            if not summary_data.get("summary", "").strip():
                logger.bind(tag=TAG).debug("LLM returned empty summary, skipping save")
                return None

            # Add to OpenMemory
            result = await self._add_to_openmemory(summary_data)

            logger.bind(tag=TAG).info(
                f"Save memory successful - Role: {self.role_id}, Memory ID: {result.get('id') if result else 'N/A'}"
            )

            return result

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Error saving memory: {str(e)}\n{traceback.format_exc()}"
            )
            return None

    async def query_memory(self, query: str) -> str:
        """
        Query memories từ OpenMemory.

        Args:
            query: Search query string

        Returns:
            Formatted string of memory results để dùng cho LLM context
        """
        try:
            if not query or not query.strip():
                return ""

            # Check if initialization failed - return empty gracefully
            if self._initialization_error:
                logger.bind(tag=TAG).debug(
                    f"OpenMemory not available, skipping query: {self._initialization_error}"
                )
                return ""

            # Use direct HTTP API instead of SDK (SDK uses wrong endpoint)
            # OpenMemory server uses /memory/query for semantic search
            import httpx
            import os
            
            base_url = os.environ.get("OPENMEMORY_BASE_URL", "http://openmemory:8080")
            user_id = str(self.role_id) if self.role_id else None
            
            logger.bind(tag=TAG).debug(f"Querying OpenMemory for: {query} (limit={self.k})")
            
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    f"{base_url}/memory/query",
                    json={
                        "query": query,
                        "user_id": user_id,
                        "limit": self.k,
                    }
                )
                
                if response.status_code != 200:
                    logger.bind(tag=TAG).warning(f"Memory query failed: {response.status_code}")
                    return ""
                
                result = response.json()
            
            # Format results to string
            matches = result.get("matches", [])
            formatted = self._format_query_results(matches)

            logger.bind(tag=TAG).debug(f"Query returned {len(formatted)} characters from {len(matches)} matches")
            return formatted

        except Exception as e:
            # Log error but don't crash - return empty string
            logger.bind(tag=TAG).warning(
                f"Memory query failed (non-critical): {str(e)}"
            )
            return ""

    def _format_dialogue(self, msgs: List[Any]) -> str:
        """
        Convert Message list to formatted dialogue string.

        Args:
            msgs: List of Message objects

        Returns:
            Formatted dialogue string
        """
        dialogue_parts = []

        for msg in msgs:
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", "")

            # Skip empty messages
            if not content or not str(content).strip():
                continue

            # Skip system messages
            if role == "system":
                continue

            # Format role
            role_label = {
                "user": "User",
                "assistant": "Assistant",
                "tool": "System",
            }.get(role, role.capitalize())

            dialogue_parts.append(f"{role_label}: {str(content).strip()}")

        return "\n".join(dialogue_parts)

    def _format_query_results(self, result) -> str:
        """
        Format OpenMemory query results to string.

        Args:
            result: Query result from OpenMemory API (List[Dict] in v1.3+)

        Returns:
            Formatted string for LLM context
        """
        if not result:
            return ""

        # openmemory-py v1.3+ returns List[Dict] directly
        matches = result if isinstance(result, list) else result.get("matches", [])
        if not matches:
            return ""

        formatted_parts = ["[Previous Memories]"]

        for i, match in enumerate(matches, 1):
            # v1.3+ structure: {"id", "content", "score", "metadata", ...}
            content = match.get("content", "") or match.get("text", "")
            score = match.get("score", 0) or match.get("similarity", 0)

            if not content:
                continue

            formatted_parts.append(
                f"{i}. (relevance: {score:.2f}) {content}"
            )

        return "\n".join(formatted_parts) if len(formatted_parts) > 1 else ""

    async def _add_to_openmemory(
        self, summary_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Add summarized memory to OpenMemory.

        Args:
            summary_data: Dict with keys: summary, tags, sector

        Returns:
            Response from OpenMemory API
        """
        try:
            client = self._get_client()

            summary = summary_data.get("summary", "").strip()
            tags = summary_data.get("tags", [])
            sector = summary_data.get("sector", "semantic")

            # Validate sector
            valid_sectors = [
                "episodic",
                "semantic",
                "procedural",
                "emotional",
                "reflective",
            ]
            if sector not in valid_sectors:
                logger.bind(tag=TAG).warning(
                    f"Invalid sector '{sector}', defaulting to 'semantic'"
                )
                sector = "semantic"

            # Add __source:memory tag to distinguish from knowledge_base
            if "__source:memory" not in tags:
                tags = list(tags) + ["__source:memory"]

            # Prepare content with metadata (openmemory-py v1.3+ simple API)
            content_with_meta = f"[{sector.upper()}] {summary}"
            if tags:
                # Filter out internal tags from display
                display_tags = [t for t in tags if not t.startswith("__")]
                if display_tags:
                    content_with_meta += f" #{'#'.join(display_tags)}"

            # Add to OpenMemory (v1.3+ API: async add(content, user_id))
            logger.bind(tag=TAG).debug(
                f"Adding memory to OpenMemory - sector: {sector}, tags: {tags}"
            )

            user_id = str(self.role_id) if self.role_id else None
            
            # openmemory-py v1.3+ add is async
            result = await client.add(
                content=content_with_meta,
                user_id=user_id,
            )

            logger.bind(tag=TAG).debug(f"Memory added successfully: {result}")
            return result

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Error adding memory to OpenMemory: {str(e)}\n{traceback.format_exc()}"
            )
            return None
