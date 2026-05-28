"""
CRUD operations for Sales Program and Meeting Room.
"""

from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales_program import SalesProgram
from app.models.meeting_room import MeetingRoom
from app.core.logger import setup_logging

logger = setup_logging()


# ============================================================
# SalesProgram CRUD
# ============================================================

async def create_sales_program(
    db: AsyncSession,
    user_id: str,
    name: str,
    description: str = None,
    mode: str = "sales",
    system_prompt: str = None,
    knowledge_base_id: str = None,
    welcome_message: str = None,
    business_name: str = None,
    business_address: str = None,
    business_phone: str = None,
    display_config: dict = None,
) -> SalesProgram:
    """Create a new sales program."""
    program = SalesProgram(
        user_id=user_id,
        name=name,
    )
    # Set optional fields manually (init=False pattern)
    program.description = description
    program.mode = mode
    program.system_prompt = system_prompt
    program.knowledge_base_id = knowledge_base_id
    program.welcome_message = welcome_message
    program.business_name = business_name
    program.business_address = business_address
    program.business_phone = business_phone
    program.display_config = display_config
    
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


async def get_sales_program(
    db: AsyncSession,
    program_id: str,
    user_id: str = None,
) -> Optional[SalesProgram]:
    """Get a single sales program by ID, optionally filtered by owner."""
    query = select(SalesProgram).where(SalesProgram.id == program_id)
    if user_id:
        query = query.where(SalesProgram.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_sales_programs(
    db: AsyncSession,
    user_id: str,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SalesProgram], int]:
    """Get list of sales programs for a user."""
    base = select(SalesProgram).where(SalesProgram.user_id == user_id)
    if active_only:
        base = base.where(SalesProgram.is_active == True)
    
    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    
    # Items
    query = base.order_by(SalesProgram.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return items, total


async def update_sales_program(
    db: AsyncSession,
    program: SalesProgram,
    data: dict,
) -> SalesProgram:
    """Update sales program fields."""
    updatable = [
        "name", "description", "mode", "system_prompt",
        "knowledge_base_id", "welcome_message",
        "business_name", "business_address", "business_phone",
        "display_config", "is_active",
    ]
    for key in updatable:
        if key in data:
            setattr(program, key, data[key])
    
    await db.commit()
    await db.refresh(program)
    return program


async def delete_sales_program(db: AsyncSession, program: SalesProgram) -> None:
    """Delete a sales program permanently."""
    await db.delete(program)
    await db.commit()


# ============================================================
# MeetingRoom CRUD
# ============================================================

async def create_meeting_room(
    db: AsyncSession,
    user_id: str,
    name: str,
    department: str = None,
    description: str = None,
    default_language: str = "vi",
    auto_extract_tasks: bool = True,
    auto_summarize: bool = True,
    notification_config: dict = None,
    members: dict = None,
) -> MeetingRoom:
    """Create a new meeting room."""
    room = MeetingRoom(
        user_id=user_id,
        name=name,
    )
    room.department = department
    room.description = description
    room.default_language = default_language
    room.auto_extract_tasks = auto_extract_tasks
    room.auto_summarize = auto_summarize
    room.notification_config = notification_config
    room.members = members
    
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


async def get_meeting_room(
    db: AsyncSession,
    room_id: str,
    user_id: str = None,
) -> Optional[MeetingRoom]:
    """Get a single meeting room by ID, optionally filtered by owner."""
    query = select(MeetingRoom).where(MeetingRoom.id == room_id)
    if user_id:
        query = query.where(MeetingRoom.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_meeting_rooms(
    db: AsyncSession,
    user_id: str,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[MeetingRoom], int]:
    """Get list of meeting rooms for a user."""
    base = select(MeetingRoom).where(MeetingRoom.user_id == user_id)
    if active_only:
        base = base.where(MeetingRoom.is_active == True)
    
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    
    query = base.order_by(MeetingRoom.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    return items, total


async def update_meeting_room(
    db: AsyncSession,
    room: MeetingRoom,
    data: dict,
) -> MeetingRoom:
    """Update meeting room fields."""
    updatable = [
        "name", "department", "description",
        "default_language", "auto_extract_tasks", "auto_summarize",
        "notification_config", "members", "is_active",
    ]
    for key in updatable:
        if key in data:
            setattr(room, key, data[key])
    
    await db.commit()
    await db.refresh(room)
    return room


async def delete_meeting_room(db: AsyncSession, room: MeetingRoom) -> None:
    """Delete a meeting room permanently."""
    await db.delete(room)
    await db.commit()
