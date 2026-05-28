"""
Conversation Memory Schemas

Pydantic schemas for conversation memory API.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationMemoryBase(BaseModel):
    """Base schema for conversation memory"""
    key: str = Field(..., min_length=1, max_length=100, description="Memory key/identifier")
    value: Any = Field(..., description="Memory value (any JSON-serializable data)")
    memory_type: str = Field(default="long_term", description="short_term, long_term, preference, fact, habit, relationship")
    category: Optional[str] = Field(None, max_length=50, description="Category for grouping")
    summary: Optional[str] = Field(None, description="Human-readable summary")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score 0-1")
    source: str = Field(default="explicit", description="explicit, inferred, system")


class ConversationMemoryCreate(ConversationMemoryBase):
    """Schema for creating a new memory"""
    pass


class ConversationMemoryUpdate(BaseModel):
    """Schema for updating a memory"""
    value: Optional[Any] = None
    summary: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    category: Optional[str] = None


class ConversationMemoryRead(ConversationMemoryBase):
    """Schema for reading a memory"""
    id: UUID
    device_id: str
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConversationMemoryList(BaseModel):
    """Response schema for listing memories"""
    success: bool = True
    data: list[ConversationMemoryRead]
    total: int
    

class MemoryContext(BaseModel):
    """Memory context to inject into LLM prompts"""
    user_name: Optional[str] = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    facts: dict[str, Any] = Field(default_factory=dict)
    habits: dict[str, Any] = Field(default_factory=dict)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    
    def to_prompt_text(self) -> str:
        """Convert memory context to text for LLM prompt injection"""
        lines = ["[Thông tin người dùng đã biết]"]
        
        if self.user_name:
            lines.append(f"- Tên: {self.user_name}")
        
        if self.preferences:
            lines.append("- Sở thích:")
            for k, v in self.preferences.items():
                lines.append(f"  + {k}: {v}")
        
        if self.facts:
            lines.append("- Thông tin:")
            for k, v in self.facts.items():
                lines.append(f"  + {k}: {v}")
        
        if self.habits:
            lines.append("- Thói quen:")
            for k, v in self.habits.items():
                lines.append(f"  + {k}: {v}")
        
        if self.relationships:
            lines.append("- Mối quan hệ:")
            for rel in self.relationships:
                lines.append(f"  + {rel.get('name', 'Unknown')}: {rel.get('relation', 'unknown')}")
        
        if self.recent_topics:
            lines.append(f"- Chủ đề gần đây: {', '.join(self.recent_topics)}")
        
        return "\n".join(lines)


# Emotion schemas
class EmotionLogCreate(BaseModel):
    """Schema for logging detected emotion"""
    emotion: str = Field(..., description="Detected emotion: neutral, happy, sad, angry, anxious, tired, excited")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    emotion_scores: Optional[dict[str, float]] = None
    source_text: Optional[str] = None
    message_id: Optional[UUID] = None


class EmotionLogRead(EmotionLogCreate):
    """Schema for reading emotion log"""
    id: UUID
    device_id: str
    user_id: Optional[UUID] = None
    detected_at: datetime

    model_config = {"from_attributes": True}


class EmotionSummary(BaseModel):
    """Summary of recent emotions"""
    dominant_emotion: str
    emotion_distribution: dict[str, float]
    trend: str  # improving, declining, stable
    sample_count: int
    period_hours: int
