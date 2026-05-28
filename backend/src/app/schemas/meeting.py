"""Meeting schemas - Pydantic validation for Meeting API."""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# Meeting
# =============================================================================

class MeetingCreate(BaseModel):
    """Create a new meeting (from device or web)."""
    title: str = Field(..., max_length=255, description="Tên cuộc họp")
    meeting_date: date = Field(..., description="Ngày họp")
    device_id: Optional[str] = Field(None, description="MAC thiết bị ghi âm")


class MeetingUpdate(BaseModel):
    """Update meeting (title, status, etc)."""
    title: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None


class MeetingResponse(BaseModel):
    """Meeting response for API."""
    id: str
    user_id: str
    title: str
    meeting_date: date
    device_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    summary: Optional[str] = None
    key_decisions: Optional[list] = None
    action_items: Optional[list] = None
    participants: Optional[list] = None
    total_chunks: int = 0
    rag_indexed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Paginated meeting list."""
    meetings: List[MeetingResponse]
    total: int


# =============================================================================
# Meeting Chunk
# =============================================================================

class MeetingChunkResponse(BaseModel):
    """Chunk upload response."""
    id: str
    meeting_id: str
    chunk_index: int
    duration_seconds: Optional[float] = None
    processed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Transcript
# =============================================================================

class TranscriptSegment(BaseModel):
    """Single transcript segment, including speaker diarization fields.

    `speaker_voiceprint_id` is set when the segment has been matched to a
    registered voiceprint speaker. Frontend should prefer `speaker_label`
    for display (human-readable) and use `speaker_voiceprint_id` for
    grouping/coloring.
    """
    id: str
    speaker_label: Optional[str] = None
    speaker_voiceprint_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: str
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class MeetingTranscriptResponse(BaseModel):
    """Full transcript for a meeting."""
    meeting_id: str
    segments: List[TranscriptSegment]
    total_segments: int


# =============================================================================
# Tasks
# =============================================================================

class MeetingTaskCreate(BaseModel):
    """Create a task manually."""
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_phone: Optional[str] = Field(None, max_length=20, description="SĐT để gửi Zalo")
    deadline: Optional[date] = None
    priority: str = "medium"


class MeetingTaskUpdate(BaseModel):
    """Update task status/details."""
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_phone: Optional[str] = None
    deadline: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class MeetingTaskResponse(BaseModel):
    """Task response."""
    id: str
    meeting_id: str
    title: str
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    assignee_phone: Optional[str] = None
    deadline: Optional[date] = None
    priority: str
    status: str
    notified: bool = False
    source_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeetingTaskListResponse(BaseModel):
    """Task list."""
    tasks: List[MeetingTaskResponse]
    total: int


# =============================================================================
# Meeting Summary (AI-generated)
# =============================================================================

class MeetingSummaryResponse(BaseModel):
    """AI-generated meeting summary."""
    meeting_id: str
    title: str
    summary: Optional[str] = None
    key_decisions: Optional[list] = None
    action_items: Optional[list] = None
    participants: Optional[list] = None
    duration_seconds: Optional[int] = None


# =============================================================================
# ASK (RAG Query)
# =============================================================================

class MeetingAskRequest(BaseModel):
    """Query about a meeting."""
    question: str = Field(..., description="Câu hỏi về cuộc họp")


class MeetingAskResponse(BaseModel):
    """AI answer about a meeting."""
    question: str
    answer: str
    sources: Optional[List[dict]] = None
