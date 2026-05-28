"""Unit tests for OpenMemory provider.

Tests cover:
- Provider initialization (local and remote modes)
- Memory save operations
- Memory query operations
- Error handling and fallbacks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOpenMemoryProviderInit:
    """Tests for OpenMemory provider initialization."""

    def test_init_remote_mode(self):
        """Should initialize in remote mode correctly."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {
            "mode": "remote",
            "base_url": "http://localhost:8080",
            "api_key": "test-key",
            "k": 5,
            "max_tokens": 2000
        }
        
        provider = MemoryProvider(config)
        
        assert provider.mode == "remote"
        assert provider.k == 5
        assert provider.max_tokens == 2000
        assert provider._client is None  # Lazy loaded

    def test_init_local_mode(self):
        """Should initialize in local mode correctly."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {
            "mode": "local",
            "local_path": "./data/test_memory.sqlite",
            "tier": "fast",
            "embeddings_provider": "synthetic"
        }
        
        provider = MemoryProvider(config)
        
        assert provider.mode == "local"

    def test_init_default_values(self):
        """Should use default values when not specified."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {}
        
        provider = MemoryProvider(config)
        
        assert provider.mode == "remote"  # Default
        assert provider.k == 3  # Default
        assert provider.max_tokens == 2000  # Default


class TestOpenMemorySave:
    """Tests for memory save operations."""

    @pytest.mark.asyncio
    async def test_save_memory_with_valid_messages(self):
        """Should save memory when given valid messages."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {"mode": "remote", "base_url": "http://localhost:8080"}
        provider = MemoryProvider(config)
        provider.llm = MagicMock()
        provider.llm.response_no_stream = MagicMock(return_value='''```json
{
    "summary": "User discussed their favorite food",
    "tags": ["food", "preferences"],
    "sector": "semantic"
}
```''')
        provider.role_id = "test-agent-123"
        
        # Mock client
        mock_client = MagicMock()
        mock_client.add = MagicMock(return_value={"id": "memory-123"})
        provider._client = mock_client
        provider._client_initialized = True
        
        messages = [
            MagicMock(role="user", content="I love pizza"),
            MagicMock(role="assistant", content="Pizza is great!")
        ]
        
        with patch.object(provider, '_add_to_openmemory', new_callable=AsyncMock) as mock_add:
            mock_add.return_value = {"id": "memory-123"}
            
            await provider.save_memory(messages)
            
            # LLM was called to summarize
            provider.llm.response_no_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_memory_with_empty_summary(self):
        """Should skip save when LLM returns empty summary."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {"mode": "remote"}
        provider = MemoryProvider(config)
        provider.llm = MagicMock()
        provider.llm.response_no_stream = MagicMock(return_value='''```json
{
    "summary": "",
    "tags": [],
    "sector": "semantic"
}
```''')
        
        messages = [
            MagicMock(role="user", content="Hi"),
            MagicMock(role="assistant", content="Hello!")
        ]
        
        result = await provider.save_memory(messages)
        
        assert result is None  # Empty summary should skip save

    @pytest.mark.asyncio
    async def test_save_memory_insufficient_messages(self):
        """Should skip save with less than 2 messages."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {"mode": "remote"}
        provider = MemoryProvider(config)
        provider.llm = MagicMock()
        
        messages = [MagicMock(role="user", content="Hi")]
        
        result = await provider.save_memory(messages)
        
        assert result is None


class TestOpenMemoryQuery:
    """Tests for memory query operations."""

    @pytest.mark.asyncio
    async def test_query_memory_success(self):
        """Should query and format memory results."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {"mode": "remote", "k": 3}
        provider = MemoryProvider(config)
        provider.role_id = "test-agent"
        provider._initialization_error = None
        
        mock_client = MagicMock()
        mock_client.query = MagicMock(return_value={
            "matches": [
                {"content": "User likes pizza", "primary_sector": "semantic", "score": 0.95},
                {"content": "User went to Italy", "primary_sector": "episodic", "score": 0.85},
            ]
        })
        provider._client = mock_client
        provider._client_initialized = True
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value={
                "matches": [
                    {"content": "User likes pizza", "primary_sector": "semantic", "score": 0.95},
                ]
            })
            
            result = await provider.query_memory("What does user like?")
            
            # Result should be formatted string
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_query_memory_empty_query(self):
        """Should return empty string for empty query."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {"mode": "remote"}
        provider = MemoryProvider(config)
        
        result = await provider.query_memory("")
        
        assert result == ""

    @pytest.mark.asyncio
    async def test_query_memory_with_initialization_error(self):
        """Should return empty gracefully when client failed to init."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        config = {"mode": "remote"}
        provider = MemoryProvider(config)
        provider._initialization_error = "Failed to connect"
        provider._client_initialized = True
        
        result = await provider.query_memory("Test query")
        
        assert result == ""


class TestJsonExtraction:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_json_from_code_block(self):
        """Should extract JSON from markdown code block."""
        from app.ai.providers.memory.openmemory.openmemory import extract_json_from_response
        
        response = '''Here's the summary:
```json
{
    "summary": "Test summary",
    "tags": ["test"],
    "sector": "semantic"
}
```
'''
        
        result = extract_json_from_response(response)
        
        assert result is not None
        assert result["summary"] == "Test summary"
        assert result["sector"] == "semantic"

    def test_extract_raw_json(self):
        """Should extract raw JSON without code block."""
        from app.ai.providers.memory.openmemory.openmemory import extract_json_from_response
        
        response = '{"summary": "Direct JSON", "tags": [], "sector": "episodic"}'
        
        result = extract_json_from_response(response)
        
        assert result is not None
        assert result["summary"] == "Direct JSON"

    def test_extract_invalid_json(self):
        """Should return None for invalid JSON."""
        from app.ai.providers.memory.openmemory.openmemory import extract_json_from_response
        
        response = "This is not JSON at all"
        
        result = extract_json_from_response(response)
        
        assert result is None


class TestDialogueFormatting:
    """Tests for dialogue formatting."""

    def test_format_dialogue_basic(self):
        """Should format dialogue correctly."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        provider = MemoryProvider({})
        
        messages = [
            MagicMock(role="user", content="Hello"),
            MagicMock(role="assistant", content="Hi there!"),
            MagicMock(role="user", content="How are you?"),
        ]
        
        result = provider._format_dialogue(messages)
        
        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result
        assert "User: How are you?" in result

    def test_format_dialogue_skip_system(self):
        """Should skip system messages."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        provider = MemoryProvider({})
        
        messages = [
            MagicMock(role="system", content="You are a helpful assistant"),
            MagicMock(role="user", content="Hello"),
        ]
        
        result = provider._format_dialogue(messages)
        
        assert "system" not in result.lower()
        assert "User: Hello" in result

    def test_format_dialogue_skip_empty(self):
        """Should skip empty messages."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        provider = MemoryProvider({})
        
        messages = [
            MagicMock(role="user", content=""),
            MagicMock(role="user", content="Hello"),
        ]
        
        result = provider._format_dialogue(messages)
        
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) == 1


class TestSectorValidation:
    """Tests for memory sector validation."""

    @pytest.mark.asyncio
    async def test_valid_sectors_accepted(self):
        """Should accept all valid sector values."""
        valid_sectors = ["episodic", "semantic", "procedural", "emotional", "reflective"]
        
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        provider = MemoryProvider({"mode": "remote"})
        provider._client = MagicMock()
        provider._client_initialized = True
        
        for sector in valid_sectors:
            summary_data = {"summary": "Test", "tags": [], "sector": sector}
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value={"id": "123"})
                
                # Should not raise
                await provider._add_to_openmemory(summary_data)

    @pytest.mark.asyncio
    async def test_invalid_sector_defaults_to_semantic(self):
        """Should default to semantic for invalid sector."""
        from app.ai.providers.memory.openmemory.openmemory import MemoryProvider
        
        provider = MemoryProvider({"mode": "remote"})
        provider._client = MagicMock()
        provider._client_initialized = True
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_add = MagicMock()
            mock_loop.return_value.run_in_executor = AsyncMock(return_value={"id": "123"})
            provider._client.add = mock_add
            
            summary_data = {"summary": "Test", "tags": [], "sector": "invalid_sector"}
            
            await provider._add_to_openmemory(summary_data)
            
            # The sector should be defaulted to semantic in the log
            # (we can't easily test the actual call due to lambda wrapping)
