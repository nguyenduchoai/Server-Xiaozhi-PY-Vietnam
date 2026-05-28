"""Meeting CRUD operations - Database operations for meetings, chunks, transcripts, tasks."""

from datetime import datetime, timezone, date
from typing import Optional, List
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.meeting import (
    Meeting, MeetingChunk, MeetingTranscript, MeetingTask, MeetingSettings,
    MeetingStatus, TaskStatus, TaskPriority,
)
from ..core.logger import setup_logging

TAG = __name__
logger = setup_logging()


# =============================================================================
# Meeting CRUD
# =============================================================================

async def create_meeting(
    db: AsyncSession,
    user_id: str,
    title: str,
    meeting_date: date,
    device_id: Optional[str] = None,
) -> Meeting:
    """Create a new meeting record."""
    meeting = Meeting(
        user_id=user_id,
        title=title,
        meeting_date=meeting_date,
        device_id=device_id,
        start_time=datetime.now(timezone.utc),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    logger.bind(tag=TAG).info(f"Created meeting: {meeting.id} - {title}")
    return meeting


async def get_meeting(db: AsyncSession, meeting_id: str) -> Optional[Meeting]:
    """Get meeting by ID."""
    result = await db.execute(
        select(Meeting).where(
            and_(Meeting.id == meeting_id, Meeting.is_deleted == False)
        )
    )
    return result.scalar_one_or_none()


async def get_meetings_by_user(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[List[Meeting], int]:
    """Get paginated meetings for a user."""
    conditions = [Meeting.user_id == user_id, Meeting.is_deleted == False]

    if status:
        conditions.append(Meeting.status == status)
    if date_from:
        conditions.append(Meeting.meeting_date >= date_from)
    if date_to:
        conditions.append(Meeting.meeting_date <= date_to)

    # Count
    count_q = select(func.count()).select_from(Meeting).where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    # Query
    query = (
        select(Meeting)
        .where(and_(*conditions))
        .order_by(desc(Meeting.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    meetings = list(result.scalars().all())

    return meetings, total


async def update_meeting(
    db: AsyncSession, meeting_id: str, **kwargs
) -> Optional[Meeting]:
    """Update meeting fields."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        return None

    kwargs["updated_at"] = datetime.now(timezone.utc)
    for key, value in kwargs.items():
        if hasattr(meeting, key) and value is not None:
            setattr(meeting, key, value)

    await db.commit()
    await db.refresh(meeting)
    return meeting


async def complete_meeting(db: AsyncSession, meeting_id: str) -> Optional[Meeting]:
    """Mark meeting recording as complete, start processing."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        return None

    meeting.end_time = datetime.now(timezone.utc)
    if meeting.start_time:
        meeting.duration_seconds = int(
            (meeting.end_time - meeting.start_time).total_seconds()
        )
    meeting.status = MeetingStatus.PROCESSING
    meeting.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(meeting)
    logger.bind(tag=TAG).info(
        f"Meeting {meeting_id} completed, duration={meeting.duration_seconds}s"
    )
    return meeting


async def soft_delete_meeting(db: AsyncSession, meeting_id: str) -> bool:
    """Soft delete a meeting."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        return False

    meeting.is_deleted = True
    meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return True


# =============================================================================
# Chunk CRUD
# =============================================================================

async def create_chunk(
    db: AsyncSession,
    meeting_id: str,
    chunk_index: int,
    audio_file_path: str,
    duration_seconds: Optional[float] = None,
) -> MeetingChunk:
    """Save an uploaded audio chunk."""
    chunk = MeetingChunk(
        meeting_id=meeting_id,
        chunk_index=chunk_index,
        audio_file_path=audio_file_path,
        duration_seconds=duration_seconds,
    )
    db.add(chunk)

    # Increment total_chunks on meeting
    meeting = await get_meeting(db, meeting_id)
    if meeting:
        meeting.total_chunks = (meeting.total_chunks or 0) + 1
        meeting.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(chunk)
    return chunk


async def get_chunks_by_meeting(
    db: AsyncSession, meeting_id: str
) -> List[MeetingChunk]:
    """Get all chunks for a meeting, ordered by index."""
    result = await db.execute(
        select(MeetingChunk)
        .where(MeetingChunk.meeting_id == meeting_id)
        .order_by(MeetingChunk.chunk_index)
    )
    return list(result.scalars().all())


# =============================================================================
# Transcript CRUD
# =============================================================================

async def create_transcript_segments(
    db: AsyncSession,
    meeting_id: str,
    segments: List[dict],
) -> int:
    """Bulk insert transcript segments.

    segments: [{speaker_label, start_time, end_time, text, confidence, speaker_voiceprint_id}]
    """
    count = 0
    for seg in segments:
        transcript = MeetingTranscript(
            meeting_id=meeting_id,
            text=seg["text"],
            speaker_label=seg.get("speaker_label"),
            speaker_voiceprint_id=seg.get("speaker_voiceprint_id"),
            start_time=seg.get("start_time"),
            end_time=seg.get("end_time"),
            confidence=seg.get("confidence"),
        )
        db.add(transcript)
        count += 1

    await db.commit()
    logger.bind(tag=TAG).info(f"Created {count} transcript segments for meeting {meeting_id}")
    return count


async def get_transcript_by_meeting(
    db: AsyncSession, meeting_id: str
) -> List[MeetingTranscript]:
    """Get full transcript for a meeting, ordered by time."""
    result = await db.execute(
        select(MeetingTranscript)
        .where(MeetingTranscript.meeting_id == meeting_id)
        .order_by(MeetingTranscript.start_time)
    )
    return list(result.scalars().all())


# =============================================================================
# Task CRUD
# =============================================================================

async def create_task(
    db: AsyncSession,
    meeting_id: str,
    title: str,
    description: Optional[str] = None,
    assignee_name: Optional[str] = None,
    assignee_email: Optional[str] = None,
    assignee_phone: Optional[str] = None,
    deadline: Optional[date] = None,
    priority: str = "medium",
    source_text: Optional[str] = None,
) -> MeetingTask:
    """Create a task from meeting."""
    task = MeetingTask(
        meeting_id=meeting_id,
        title=title,
        description=description,
        assignee_name=assignee_name,
        assignee_email=assignee_email,
        assignee_phone=assignee_phone,
        deadline=deadline,
        priority=TaskPriority(priority) if priority else TaskPriority.MEDIUM,
        source_text=source_text,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_tasks_by_meeting(
    db: AsyncSession, meeting_id: str
) -> List[MeetingTask]:
    """Get all tasks for a meeting."""
    result = await db.execute(
        select(MeetingTask)
        .where(MeetingTask.meeting_id == meeting_id)
        .order_by(MeetingTask.created_at)
    )
    return list(result.scalars().all())


async def get_tasks_by_user(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
) -> List[MeetingTask]:
    """Get tasks across all meetings for a user."""
    conditions = [Meeting.user_id == user_id, Meeting.is_deleted == False]
    if status:
        conditions.append(MeetingTask.status == status)

    result = await db.execute(
        select(MeetingTask)
        .join(Meeting, MeetingTask.meeting_id == Meeting.id)
        .where(and_(*conditions))
        .order_by(desc(MeetingTask.created_at))
    )
    return list(result.scalars().all())


async def update_task(
    db: AsyncSession, task_id: str, **kwargs
) -> Optional[MeetingTask]:
    """Update task fields."""
    result = await db.execute(
        select(MeetingTask).where(MeetingTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    kwargs["updated_at"] = datetime.now(timezone.utc)

    # Handle enum conversion
    if "status" in kwargs and kwargs["status"]:
        kwargs["status"] = TaskStatus(kwargs["status"])
    if "priority" in kwargs and kwargs["priority"]:
        kwargs["priority"] = TaskPriority(kwargs["priority"])

    for key, value in kwargs.items():
        if hasattr(task, key) and value is not None:
            setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return task


# =============================================================================
# Meeting Settings CRUD
# =============================================================================

async def get_meeting_settings(
    db: AsyncSession, user_id: str,
) -> Optional[MeetingSettings]:
    """Get meeting settings for a user."""
    result = await db.execute(
        select(MeetingSettings).where(MeetingSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_meeting_settings(
    db: AsyncSession, user_id: str, **kwargs,
) -> MeetingSettings:
    """Create or update meeting settings for a user."""
    settings = await get_meeting_settings(db, user_id)
    
    if settings:
        # Update existing
        kwargs["updated_at"] = datetime.now(timezone.utc)
        for key, value in kwargs.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)
    else:
        # Create new
        settings = MeetingSettings(user_id=user_id, **kwargs)
        db.add(settings)
    
    await db.commit()
    await db.refresh(settings)
    logger.bind(tag=TAG).info(f"Upserted meeting settings for user {user_id}")
    return settings
