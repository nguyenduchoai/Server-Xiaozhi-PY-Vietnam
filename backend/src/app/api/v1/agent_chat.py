"""
Agent Chat API — Browser-based text chat for testing agents

Provides a REST endpoint to chat with any agent directly from the browser.
Loads the agent's LLM provider and system prompt.
Maintains conversation history within a session.
"""

import re
import uuid
from typing import Annotated, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.models.agent import Agent
from app.core.logger import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["Agent Chat"])

# In-memory session storage (simple approach for testing)
# Max sessions to prevent unbounded memory growth
_MAX_SESSIONS = 200
_chat_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    images: List[str] = []  # extracted image URLs from reply


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def agent_chat(
    agent_id: str,
    data: ChatRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Chat with an agent via text. Returns LLM response.
    Uses the agent's configured LLM provider, prompt, and product catalog.
    """
    # 1. Load agent
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.is_deleted == False)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    # Check ownership (unless superadmin)
    is_super = current_user.get("is_superuser") or current_user.get("role") in ["admin", "super_admin"]
    if not is_super and str(agent.user_id) != str(current_user["id"]):
        raise HTTPException(403, "Not your agent")
    
    # 2. Build system prompt
    system_prompt = agent.prompt or "Bạn là trợ lý AI thân thiện."
    
    # Add current time context
    now = datetime.now()
    system_prompt = system_prompt.replace("{{current_time}}", now.strftime("%H:%M"))
    

    
    # 4. Get or create session
    session_id = data.session_id or str(uuid.uuid4())
    if session_id not in _chat_sessions:
        # Evict oldest sessions if at capacity
        if len(_chat_sessions) >= _MAX_SESSIONS:
            oldest_key = next(iter(_chat_sessions))
            del _chat_sessions[oldest_key]
        _chat_sessions[session_id] = []
    
    history = _chat_sessions[session_id]
    
    # 5. Build dialogue
    dialogue = [{"role": "system", "content": system_prompt}]
    
    # Add history (max last 20 messages)
    for msg in history[-20:]:
        dialogue.append(msg)
    
    # Add current user message
    dialogue.append({"role": "user", "content": data.message})
    
    # 6. Get LLM provider
    llm_provider = await _get_llm_provider(db, agent)
    if not llm_provider:
        raise HTTPException(500, "No LLM provider configured for this agent")
    
    # 7. Generate response
    try:
        reply = ""
        for token in llm_provider.response(session_id, dialogue):
            reply += token
        
        if not reply.strip():
            reply = "Xin lỗi, tôi không thể trả lời lúc này."
        
    except Exception as e:
        logger.error(f"LLM response error: {e}")
        raise HTTPException(500, "LLM service unavailable, please try again")
    
    # 8. Save to history (In-Memory for dialogue context)
    history.append({"role": "user", "content": data.message})
    history.append({"role": "assistant", "content": reply})
    
    # Keep max 40 messages in memory
    if len(history) > 40:
        _chat_sessions[session_id] = history[-40:]
    
    # 9. Extract image URLs from reply for rich display
    images = _extract_images(reply)

    # 10. Save to Database so it appears in History tab
    try:
        from app.services.agent_service import agent_service
        # Save User Message
        await agent_service.save_chat_message(
            db=db,
            agent_id=agent_id,
            session_id=session_id,
            chat_type=1, # 1 for user
            content=data.message
        )
        # Save Assistant Message
        await agent_service.save_chat_message(
            db=db,
            agent_id=agent_id,
            session_id=session_id,
            chat_type=2, # 2 for assistant
            content=reply
        )
    except Exception as e:
        logger.error(f"Failed to save Chat Test messages to DB: {e}")
    
    return ChatResponse(
        reply=reply,
        session_id=session_id,
        images=images,
    )


@router.delete("/{agent_id}/chat/{session_id}")
async def clear_chat_session(
    agent_id: str,
    session_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Clear chat session history."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    return {"message": "Session cleared"}


async def _get_llm_provider(db: AsyncSession, agent: Agent):
    """Instantiate the agent's LLM provider."""
    try:
        from app.models.provider import Provider
        
        # Agent stores LLM as "db:UUID" format
        llm_ref = agent.LLM  # e.g., "db:019b8ebb-db46-79be-9cdd-134ee39b2c42"
        provider = None
        
        if llm_ref and llm_ref.startswith("db:"):
            provider_id = llm_ref.split(":", 1)[1]
            result = await db.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
        
        if not provider:
            # Fallback: find any LLM provider for user
            result = await db.execute(
                select(Provider).where(
                    Provider.user_id == agent.user_id,
                    Provider.category == "LLM",
                    Provider.is_active == True,
                ).limit(1)
            )
            provider = result.scalar_one_or_none()
        
        if not provider:
            return None
        
        # Build config dict from provider
        config = dict(provider.config or {})
        config["type"] = provider.type
        
        from app.ai.module_factory import initialize_llm_from_config
        return initialize_llm_from_config(config)
        
    except Exception as e:
        logger.error(f"Failed to create LLM provider: {e}")
        import traceback
        traceback.print_exc()
        return None







def _extract_images(text: str) -> list[str]:
    """Extract image URLs from markdown text."""
    # Match ![alt](url) and plain image URLs
    patterns = [
        r'!\[.*?\]\((https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*)\)',
        r'!\[.*?\]\((/uploads/\S+\.(?:jpg|jpeg|png|gif|webp)\S*)\)',
    ]
    images = []
    for pattern in patterns:
        images.extend(re.findall(pattern, text, re.IGNORECASE))
    return images

