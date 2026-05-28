"""
Memory Service

Manages conversation memories for personalized AI interactions.
Handles memory storage, retrieval, and LLM prompt injection.
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.conversation_memory import ConversationMemory, EmotionLog, MemoryType, MemorySource
from ..schemas.conversation_memory import (
    ConversationMemoryCreate,
    ConversationMemoryUpdate,
    MemoryContext,
    EmotionLogCreate,
)
from ..core.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Service for managing conversation memories"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Memory CRUD ====================
    
    async def get_memory(
        self, 
        device_id: str, 
        key: str,
        user_id: Optional[UUID] = None
    ) -> Optional[ConversationMemory]:
        """Get a specific memory by key"""
        query = select(ConversationMemory).where(
            and_(
                ConversationMemory.device_id == device_id,
                ConversationMemory.key == key
            )
        )
        if user_id:
            query = query.where(ConversationMemory.user_id == str(user_id))
        
        result = await self.db.execute(query)
        memory = result.scalar_one_or_none()
        
        if memory:
            # Track access
            memory.increment_access()
            await self.db.commit()
        
        return memory
    
    async def get_all_memories(
        self,
        device_id: str,
        user_id: Optional[UUID] = None,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        include_expired: bool = False
    ) -> list[ConversationMemory]:
        """Get all memories for a device/user"""
        conditions = [ConversationMemory.device_id == device_id]
        
        if user_id:
            conditions.append(ConversationMemory.user_id == str(user_id))
        if memory_type:
            conditions.append(ConversationMemory.memory_type == memory_type)
        if category:
            conditions.append(ConversationMemory.category == category)
        if not include_expired:
            conditions.append(
                or_(
                    ConversationMemory.expires_at.is_(None),
                    ConversationMemory.expires_at > datetime.utcnow()
                )
            )
        
        query = select(ConversationMemory).where(and_(*conditions))
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create_memory(
        self,
        device_id: str,
        data: ConversationMemoryCreate,
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
        expires_in_hours: Optional[int] = None
    ) -> ConversationMemory:
        """Create or update a memory"""
        # Check if memory already exists
        existing = await self.get_memory(device_id, data.key, user_id)
        
        if existing:
            # Update existing memory
            existing.value = data.value
            existing.summary = data.summary
            existing.confidence = data.confidence
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            return existing
        
        # Create new memory
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        elif data.memory_type == MemoryType.SHORT_TERM.value:
            expires_at = datetime.utcnow() + timedelta(hours=24)  # Default 24h for short-term
        
        memory = ConversationMemory(
            device_id=device_id,
            user_id=str(user_id) if user_id else None,
            agent_id=str(agent_id) if agent_id else None,
            key=data.key,
            value=data.value,
            memory_type=data.memory_type,
            category=data.category,
            summary=data.summary,
            confidence=data.confidence,
            source=data.source,
            expires_at=expires_at
        )
        
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        
        logger.info(f"Created memory '{data.key}' for device {device_id}")
        return memory
    
    async def update_memory(
        self,
        device_id: str,
        key: str,
        data: ConversationMemoryUpdate,
        user_id: Optional[UUID] = None
    ) -> Optional[ConversationMemory]:
        """Update an existing memory"""
        memory = await self.get_memory(device_id, key, user_id)
        if not memory:
            return None
        
        if data.value is not None:
            memory.value = data.value
        if data.summary is not None:
            memory.summary = data.summary
        if data.confidence is not None:
            memory.confidence = data.confidence
        if data.category is not None:
            memory.category = data.category
        
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        return memory
    
    async def delete_memory(
        self,
        device_id: str,
        key: str,
        user_id: Optional[UUID] = None
    ) -> bool:
        """Delete a memory"""
        conditions = [
            ConversationMemory.device_id == device_id,
            ConversationMemory.key == key
        ]
        if user_id:
            conditions.append(ConversationMemory.user_id == str(user_id))
        
        result = await self.db.execute(
            delete(ConversationMemory).where(and_(*conditions))
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def cleanup_expired(self) -> int:
        """Remove expired memories"""
        result = await self.db.execute(
            delete(ConversationMemory).where(
                and_(
                    ConversationMemory.expires_at.isnot(None),
                    ConversationMemory.expires_at < datetime.utcnow()
                )
            )
        )
        await self.db.commit()
        return result.rowcount
    
    # ==================== Memory Context ====================
    
    async def get_memory_context(
        self,
        device_id: str,
        user_id: Optional[UUID] = None
    ) -> MemoryContext:
        """Build memory context for LLM prompt injection"""
        memories = await self.get_all_memories(device_id, user_id)
        
        context = MemoryContext()
        
        for mem in memories:
            if mem.key == "user_name":
                context.user_name = str(mem.value)
            elif mem.memory_type == MemoryType.PREFERENCE.value:
                context.preferences[mem.key] = mem.value
            elif mem.memory_type == MemoryType.FACT.value:
                context.facts[mem.key] = mem.value
            elif mem.memory_type == MemoryType.HABIT.value:
                context.habits[mem.key] = mem.value
            elif mem.memory_type == MemoryType.RELATIONSHIP.value:
                context.relationships.append(mem.value)
        
        return context
    
    async def inject_memory_into_prompt(
        self,
        base_prompt: str,
        device_id: str,
        user_id: Optional[UUID] = None
    ) -> str:
        """Inject memory context into LLM system prompt"""
        context = await self.get_memory_context(device_id, user_id)
        
        # Only inject if there's meaningful context
        if not context.user_name and not context.preferences and not context.facts:
            return base_prompt
        
        memory_text = context.to_prompt_text()
        return f"{base_prompt}\n\n{memory_text}"
    
    # ==================== Learning from Conversations ====================
    
    async def learn_from_message(
        self,
        device_id: str,
        message: str,
        user_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None
    ) -> list[ConversationMemory]:
        """
        Extract and store information from user message.
        Uses pattern matching and LLM to identify facts/preferences.
        """
        learned = []
        
        # Pattern: "Tên tôi là X" / "Tôi là X"
        import re
        name_patterns = [
            r"tên (?:tôi|em|mình) là (\w+)",
            r"(?:tôi|em|mình) là (\w+)",
            r"gọi (?:tôi|em|mình) là (\w+)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message.lower())
            if match:
                name = match.group(1).capitalize()
                memory = await self.create_memory(
                    device_id=device_id,
                    data=ConversationMemoryCreate(
                        key="user_name",
                        value=name,
                        memory_type=MemoryType.FACT.value,
                        source=MemorySource.EXPLICIT.value,
                        summary=f"Người dùng tên là {name}"
                    ),
                    user_id=user_id,
                    agent_id=agent_id
                )
                learned.append(memory)
                break
        
        # Pattern: "Tôi thích X" / "Tôi yêu X"
        preference_patterns = [
            (r"(?:tôi|em|mình) (?:thích|yêu|mê) (\w+(?:\s+\w+)*)", "likes"),
            (r"(?:tôi|em|mình) không thích (\w+(?:\s+\w+)*)", "dislikes"),
        ]
        
        for pattern, pref_type in preference_patterns:
            match = re.search(pattern, message.lower())
            if match:
                value = match.group(1)
                memory = await self.create_memory(
                    device_id=device_id,
                    data=ConversationMemoryCreate(
                        key=f"preference_{pref_type}",
                        value=value,
                        memory_type=MemoryType.PREFERENCE.value,
                        source=MemorySource.EXPLICIT.value,
                        summary=f"{'Thích' if pref_type == 'likes' else 'Không thích'}: {value}"
                    ),
                    user_id=user_id,
                    agent_id=agent_id
                )
                learned.append(memory)
        
        return learned
    
    # ==================== Emotion Logging ====================
    
    async def log_emotion(
        self,
        device_id: str,
        data: EmotionLogCreate,
        user_id: Optional[UUID] = None
    ) -> EmotionLog:
        """Log detected emotion"""
        emotion_log = EmotionLog(
            device_id=device_id,
            user_id=str(user_id) if user_id else None,
            message_id=data.message_id,
            emotion=data.emotion,
            confidence=data.confidence,
            emotion_scores=data.emotion_scores,
            source_text=data.source_text
        )
        
        self.db.add(emotion_log)
        await self.db.commit()
        await self.db.refresh(emotion_log)
        
        return emotion_log
    
    async def get_recent_emotions(
        self,
        device_id: str,
        hours: int = 24,
        limit: int = 100
    ) -> list[EmotionLog]:
        """Get recent emotion logs"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = (
            select(EmotionLog)
            .where(
                and_(
                    EmotionLog.device_id == device_id,
                    EmotionLog.detected_at >= since
                )
            )
            .order_by(EmotionLog.detected_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_emotion_summary(
        self,
        device_id: str,
        hours: int = 24
    ) -> dict[str, Any]:
        """Get summary of recent emotions"""
        emotions = await self.get_recent_emotions(device_id, hours)
        
        if not emotions:
            return {
                "dominant_emotion": "neutral",
                "emotion_distribution": {},
                "trend": "stable",
                "sample_count": 0,
                "period_hours": hours
            }
        
        # Count emotions
        emotion_counts: dict[str, int] = {}
        for e in emotions:
            emotion_counts[e.emotion] = emotion_counts.get(e.emotion, 0) + 1
        
        total = len(emotions)
        distribution = {k: v / total for k, v in emotion_counts.items()}
        dominant = max(emotion_counts, key=emotion_counts.get)
        
        return {
            "dominant_emotion": dominant,
            "emotion_distribution": distribution,
            "trend": "stable",  # Could implement trend analysis
            "sample_count": total,
            "period_hours": hours
        }
