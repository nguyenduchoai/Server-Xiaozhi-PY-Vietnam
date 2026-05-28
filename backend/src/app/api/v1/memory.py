"""
Memory API Endpoints

Manages conversation memories for personalized AI interactions.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.logger import get_logger
from ...schemas.conversation_memory import (
    ConversationMemoryCreate,
    ConversationMemoryRead,
    ConversationMemoryUpdate,
    ConversationMemoryList,
    MemoryContext,
    EmotionLogCreate,
    EmotionLogRead,
    EmotionSummary,
)
from ...services.memory_service import MemoryService

router = APIRouter(tags=["memory"], prefix="/memory")

logger = get_logger(__name__)


# ==================== Device Memory Endpoints ====================

@router.get("/devices/{device_id}", response_model=ConversationMemoryList)
async def get_device_memories(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    Get all memories for a device.
    
    Returns memories stored for personalization, including user facts,
    preferences, habits, and short-term context.
    """
    service = MemoryService(db)
    memories = await service.get_all_memories(
        device_id=device_id,
        user_id=UUID(current_user["id"]),
        memory_type=memory_type,
        category=category
    )
    
    return ConversationMemoryList(
        data=[ConversationMemoryRead.model_validate(m) for m in memories],
        total=len(memories)
    )


@router.get("/devices/{device_id}/{key}", response_model=ConversationMemoryRead)
async def get_device_memory(
    device_id: str,
    key: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get a specific memory by key."""
    service = MemoryService(db)
    memory = await service.get_memory(
        device_id=device_id,
        key=key,
        user_id=UUID(current_user["id"])
    )
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return ConversationMemoryRead.model_validate(memory)


@router.post("/devices/{device_id}", response_model=ConversationMemoryRead, status_code=201)
async def create_device_memory(
    device_id: str,
    data: ConversationMemoryCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Create or update a memory for a device.
    
    If a memory with the same key already exists, it will be updated.
    """
    service = MemoryService(db)
    memory = await service.create_memory(
        device_id=device_id,
        data=data,
        user_id=UUID(current_user["id"])
    )
    
    return ConversationMemoryRead.model_validate(memory)


@router.put("/devices/{device_id}/{key}", response_model=ConversationMemoryRead)
async def update_device_memory(
    device_id: str,
    key: str,
    data: ConversationMemoryUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update an existing memory."""
    service = MemoryService(db)
    memory = await service.update_memory(
        device_id=device_id,
        key=key,
        data=data,
        user_id=UUID(current_user["id"])
    )
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return ConversationMemoryRead.model_validate(memory)


@router.delete("/devices/{device_id}/{key}", status_code=204)
async def delete_device_memory(
    device_id: str,
    key: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a memory."""
    service = MemoryService(db)
    deleted = await service.delete_memory(
        device_id=device_id,
        key=key,
        user_id=UUID(current_user["id"])
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")


@router.delete("/devices/{device_id}", status_code=204)
async def clear_device_memories(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    memory_type: Optional[str] = Query(None, description="Only clear specific type"),
):
    """Clear all memories for a device."""
    # TODO: Implement bulk delete
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ==================== Memory Context Endpoints ====================

@router.get("/devices/{device_id}/context", response_model=MemoryContext)
async def get_memory_context(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Get aggregated memory context for a device.
    
    Returns a structured context object that can be used for
    personalizing AI responses.
    """
    service = MemoryService(db)
    context = await service.get_memory_context(
        device_id=device_id,
        user_id=UUID(current_user["id"])
    )
    
    return context


@router.get("/devices/{device_id}/context/prompt")
async def get_memory_prompt(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    base_prompt: str = Query("", description="Base prompt to inject memory into"),
):
    """
    Get memory-enhanced prompt text.
    
    Combines the base prompt with memory context for personalized AI interactions.
    """
    service = MemoryService(db)
    enhanced_prompt = await service.inject_memory_into_prompt(
        base_prompt=base_prompt,
        device_id=device_id,
        user_id=UUID(current_user["id"])
    )
    
    return {"prompt": enhanced_prompt}


# ==================== Emotion Endpoints ====================

@router.post("/devices/{device_id}/emotions", response_model=EmotionLogRead, status_code=201)
async def log_emotion(
    device_id: str,
    data: EmotionLogCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Log a detected emotion for a device."""
    service = MemoryService(db)
    emotion = await service.log_emotion(
        device_id=device_id,
        data=data,
        user_id=UUID(current_user["id"])
    )
    
    return EmotionLogRead.model_validate(emotion)


@router.get("/devices/{device_id}/emotions", response_model=list[EmotionLogRead])
async def get_recent_emotions(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent emotion logs for a device."""
    service = MemoryService(db)
    emotions = await service.get_recent_emotions(
        device_id=device_id,
        hours=hours,
        limit=limit
    )
    
    return [EmotionLogRead.model_validate(e) for e in emotions]


@router.get("/devices/{device_id}/emotions/summary", response_model=EmotionSummary)
async def get_emotion_summary(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
):
    """Get emotion summary/statistics for a device."""
    service = MemoryService(db)
    summary = await service.get_emotion_summary(
        device_id=device_id,
        hours=hours
    )
    
    return EmotionSummary(**summary)


# ==================== Learning Endpoints ====================

@router.post("/devices/{device_id}/learn")
async def learn_from_message(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    message: str = Query(..., description="User message to learn from"),
):
    """
    Extract and store information from a user message.
    
    Uses pattern matching to identify facts, preferences, and other
    learnable information from user input.
    """
    service = MemoryService(db)
    learned = await service.learn_from_message(
        device_id=device_id,
        message=message,
        user_id=UUID(current_user["id"])
    )
    
    return {
        "success": True,
        "learned_count": len(learned),
        "learned": [
            {"key": m.key, "value": m.value, "summary": m.summary}
            for m in learned
        ]
    }
