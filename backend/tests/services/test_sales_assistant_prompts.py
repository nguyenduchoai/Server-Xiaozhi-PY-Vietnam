import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.sales_assistant import SalesAssistantService, get_sales_assistant
from app.models.sales_program import SalesProgram

def test_sales_assistant_default_prompts():
    """Test returning correct fallback templates."""
    assistant = get_sales_assistant()
    
    sales_prompt = assistant.get_system_prompt("sales")
    assert "Tư vấn sản phẩm" in sales_prompt
    assert "UPSELL/CROSS-SELL" in sales_prompt

    livestream_prompt = assistant.get_system_prompt("livestream")
    assert "Host Livestream" in livestream_prompt
    assert "FOMO" in livestream_prompt

    restaurant_prompt = assistant.get_system_prompt("restaurant")
    assert "menu và món đặc biệt" in restaurant_prompt

@pytest.mark.asyncio
async def test_sales_prompt_injection_with_custom_template():
    """Test connection injects custom system prompt into agent."""
    from app.ai.connection import Connection
    
    # Mock connection setup
    mock_conn = MagicMock(spec=Connection)
    mock_conn.logger = MagicMock()
    mock_conn.agent = {"enable_sales": True, "sales_program_ids": ["test-id"]}
    
    # Pre-build fake SalesProgram directly
    test_program = SalesProgram(
        name="Test Store",
        system_prompt="CUSTOM_LIVESTREAM_RULES_123"
    )
    
    # Patch logic in connection to prevent DB hit
    with patch("app.ai.connection.local_session") as mock_db:
        session_instance = AsyncMock()
        mock_db.return_value.__aenter__.return_value = session_instance
        
        # Setup mock db query
        db_execute_result = MagicMock()
        db_execute_result.scalar_one_or_none.side_effect = [test_program]
        
        # Second call to get Products
        db_execute_result_2 = MagicMock()
        db_execute_result_2.scalars.return_value.all.return_value = []
        
        session_instance.execute.side_effect = [db_execute_result, db_execute_result_2]

        from app.ai.connection import Connection
        
        # Access the unprotected method via mock binding
        import types
        _inject_sales_context = Connection._inject_sales_context
        # Need to cast it so it takes the mock connection properly
        bound_method = types.MethodType(_inject_sales_context, mock_conn)
        
        final_prompt = await bound_method("Original Prompt")
        
        assert "CUSTOM_LIVESTREAM_RULES_123" in final_prompt
        assert "KỊCH BẢN BÁN HÀNG TÙY CHỈNH" in final_prompt
