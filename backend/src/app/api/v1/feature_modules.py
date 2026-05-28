"""
Feature Modules API — Sales Programs, Meeting Rooms, Agent Feature Toggles.

Endpoints:
- /api/v1/features/sales-programs — CRUD for Sales Programs
- /api/v1/features/meeting-rooms — CRUD for Meeting Rooms
- /api/v1/features/agents/{agent_id} — Get/Update feature config for an Agent
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, conlist
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.models.agent import Agent
from app.models.user_subscription import UserSubscription, SubscriptionStatus
from app.models.subscription_plan import SubscriptionPlan
from app.services.agent_feature_assignments import validate_agent_feature_assignments
from app.crud.crud_feature_modules import (
    create_sales_program, get_sales_program, get_sales_programs,
    update_sales_program, delete_sales_program,
    create_meeting_room, get_meeting_room, get_meeting_rooms,
    update_meeting_room, delete_meeting_room,
)
from app.core.logger import setup_logging

logger = setup_logging()
TAG = __name__

router = APIRouter(prefix="/features", tags=["Feature Modules"])


# ============================================================
# Config Sub-Models (typed instead of raw dict)
# ============================================================

class DisplayConfig(BaseModel):
    """Sales program display/UI configuration."""
    theme: Optional[str] = Field(None, max_length=50)
    layout: Optional[str] = Field(None, max_length=50)
    show_prices: bool = True
    show_images: bool = True
    currency: str = Field("VND", max_length=10)
    custom_css: Optional[str] = Field(None, max_length=5000)

    model_config = {"extra": "allow"}  # Allow additional fields for flexibility


class NotificationConfig(BaseModel):
    """Meeting room notification configuration."""
    email_enabled: bool = False
    telegram_enabled: bool = False
    zalo_enabled: bool = False
    email_recipients: Optional[List[str]] = Field(None, max_length=20)
    telegram_chat_id: Optional[str] = Field(None, max_length=100)
    zalo_oa_id: Optional[str] = Field(None, max_length=100)
    notify_on_summary: bool = True
    notify_on_tasks: bool = True

    model_config = {"extra": "allow"}  # Allow additional fields for flexibility


# ============================================================
# Schemas
# ============================================================

class SalesProgramCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    mode: str = Field("sales", max_length=50)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    knowledge_base_id: Optional[str] = Field(None, max_length=100)
    welcome_message: Optional[str] = Field(None, max_length=1000)
    business_name: Optional[str] = Field(None, max_length=200)
    business_address: Optional[str] = Field(None, max_length=500)
    business_phone: Optional[str] = Field(None, max_length=50)
    display_config: Optional[DisplayConfig] = None

class SalesProgramUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    mode: Optional[str] = Field(None, max_length=50)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    knowledge_base_id: Optional[str] = Field(None, max_length=100)
    welcome_message: Optional[str] = Field(None, max_length=1000)
    business_name: Optional[str] = Field(None, max_length=200)
    business_address: Optional[str] = Field(None, max_length=500)
    business_phone: Optional[str] = Field(None, max_length=50)
    display_config: Optional[DisplayConfig] = None
    is_active: Optional[bool] = None

class SalesProgramResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    mode: str = "sales"
    system_prompt: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    welcome_message: Optional[str] = None
    business_name: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    display_config: Optional[DisplayConfig] = None
    is_active: bool = True
    
    model_config = {"from_attributes": True}

class MeetingRoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    department: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    default_language: str = Field("vi", max_length=10)
    auto_extract_tasks: bool = True
    auto_summarize: bool = True
    notification_config: Optional[NotificationConfig] = None
    members: Optional[list] = None

class MeetingRoomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    default_language: Optional[str] = Field(None, max_length=10)
    auto_extract_tasks: Optional[bool] = None
    auto_summarize: Optional[bool] = None
    notification_config: Optional[NotificationConfig] = None
    members: Optional[list] = None
    is_active: Optional[bool] = None

class MeetingRoomResponse(BaseModel):
    id: str
    user_id: str
    name: str
    department: Optional[str] = None
    description: Optional[str] = None
    default_language: str = "vi"
    auto_extract_tasks: bool = True
    auto_summarize: bool = True
    notification_config: Optional[NotificationConfig] = None
    members: Optional[list] = None
    is_active: bool = True
    
    model_config = {"from_attributes": True}

class AgentFeaturesUpdate(BaseModel):
    enable_education: Optional[bool] = None
    enable_sales: Optional[bool] = None
    enable_meeting: Optional[bool] = None
    enable_knowledge_base: Optional[bool] = None
    enable_memory: Optional[bool] = None
    course_ids: Optional[conlist(str, max_length=50)] = None
    sales_program_ids: Optional[conlist(str, max_length=50)] = None
    meeting_room_ids: Optional[conlist(str, max_length=50)] = None
    knowledge_base_ids: Optional[conlist(str, max_length=50)] = None

class AgentFeaturesResponse(BaseModel):
    agent_id: str
    enable_education: bool = False
    enable_sales: bool = False
    enable_meeting: bool = False
    enable_knowledge_base: bool = True
    enable_memory: bool = True
    course_ids: List[str] = []
    sales_program_ids: List[str] = []
    meeting_room_ids: List[str] = []
    knowledge_base_ids: List[str] = []
    # Plan-level gating: which features user's subscription allows
    plan_allowed: dict = {}
    plan_name: str = "FREE"


def _is_superuser(user: dict) -> bool:
    """Check if user is admin/superadmin."""
    if user.get("is_superuser"):
        return True
    return user.get("role") in ["admin", "super_admin"]


# Feature key → plan feature key mapping
_FEATURE_TO_PLAN_KEY = {
    "enable_education": "education",
    "enable_sales": "sales",
    "enable_meeting": "meeting",
    "enable_knowledge_base": "knowledge_base",
    "enable_memory": "memory",
}


def _is_feature_allowed(plan_features: dict, plan_key: str) -> bool:
    """Support both keys: sales + enable_sales (legacy plans)."""
    if not plan_features:
        return True
    if plan_key in plan_features:
        return bool(plan_features.get(plan_key))
    prefixed = f"enable_{plan_key}"
    if prefixed in plan_features:
        return bool(plan_features.get(prefixed))
    return True


async def _get_user_plan_features(db: AsyncSession, user_id: str) -> tuple[dict, str]:
    """
    Get user's subscription plan features.
    Returns (plan_allowed_features, plan_name).
    If no subscription, returns FREE plan features.
    """

    try:
        # Get active subscription
        sub_query = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(UserSubscription.created_at.desc())
            .limit(1)
        )
        sub_result = await db.execute(sub_query)
        subscription = sub_result.scalar_one_or_none()

        if subscription:
            plan = await db.get(SubscriptionPlan, subscription.plan_id)
            if plan and plan.allowed_device_features:
                return plan.allowed_device_features, plan.name

        # Fallback: get FREE plan
        free_query = select(SubscriptionPlan).where(SubscriptionPlan.name == "FREE")
        free_result = await db.execute(free_query)
        free_plan = free_result.scalar_one_or_none()
        if free_plan and free_plan.allowed_device_features:
            return free_plan.allowed_device_features, "FREE"

    except Exception as e:
        logger.bind(tag=TAG).warning(f"Failed to get plan features for {user_id}: {e}")

    # Ultimate fallback: all allowed
    return {}, "FREE"


def _build_features_response(agent, plan_features: dict, plan_name: str) -> AgentFeaturesResponse:
    """Build standardized AgentFeaturesResponse from agent model."""
    return AgentFeaturesResponse(
        agent_id=agent.id,
        enable_education=getattr(agent, "enable_education", False),
        enable_sales=getattr(agent, "enable_sales", False),
        enable_meeting=getattr(agent, "enable_meeting", False),
        enable_knowledge_base=getattr(agent, "enable_knowledge_base", True),
        enable_memory=getattr(agent, "enable_memory", True),
        course_ids=getattr(agent, "course_ids", []) or [],
        sales_program_ids=getattr(agent, "sales_program_ids", []) or [],
        meeting_room_ids=getattr(agent, "meeting_room_ids", []) or [],
        knowledge_base_ids=getattr(agent, "knowledge_base_ids", []) or [],
        plan_allowed=plan_features,
        plan_name=plan_name,
    )


# ============================================================
# Sales Programs API
# ============================================================

@router.get("/sales-programs", response_model=list[SalesProgramResponse])
async def list_sales_programs(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all sales programs for current user."""
    programs, _ = await get_sales_programs(db, current_user["id"])
    return [SalesProgramResponse.model_validate(p) for p in programs]


@router.post("/sales-programs", response_model=SalesProgramResponse, status_code=201)
async def create_new_sales_program(
    data: SalesProgramCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new sales program."""
    # Subscription gating: check if user's plan allows sales
    if not _is_superuser(current_user):
        plan_features, plan_name = await _get_user_plan_features(db, current_user["id"])
        if plan_features and not _is_feature_allowed(plan_features, "sales"):
            raise HTTPException(
                403,
                f"Tính năng 'sales' không có trong gói {plan_name}. "
                f"Vui lòng nâng cấp gói để sử dụng."
            )
    program = await create_sales_program(
        db, user_id=current_user["id"], **data.model_dump(exclude_none=True),
    )
    return SalesProgramResponse.model_validate(program)


@router.get("/sales-programs/{program_id}", response_model=SalesProgramResponse)
async def get_sales_program_detail(
    program_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get sales program detail."""
    user_id = None if _is_superuser(current_user) else current_user["id"]
    program = await get_sales_program(db, program_id, user_id=user_id)
    if not program:
        raise HTTPException(404, "Sales program not found")
    return SalesProgramResponse.model_validate(program)


@router.put("/sales-programs/{program_id}", response_model=SalesProgramResponse)
async def update_sales_program_detail(
    program_id: str,
    data: SalesProgramUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a sales program."""
    user_id = None if _is_superuser(current_user) else current_user["id"]
    program = await get_sales_program(db, program_id, user_id=user_id)
    if not program:
        raise HTTPException(404, "Sales program not found")
    updated = await update_sales_program(db, program, data.model_dump(exclude_none=True))
    return SalesProgramResponse.model_validate(updated)


@router.delete("/sales-programs/{program_id}", status_code=204)
async def delete_sales_program_detail(
    program_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a sales program."""
    user_id = None if _is_superuser(current_user) else current_user["id"]
    program = await get_sales_program(db, program_id, user_id=user_id)
    if not program:
        raise HTTPException(404, "Sales program not found")
    await delete_sales_program(db, program)


# ============================================================
# Meeting Rooms API
# ============================================================

@router.get("/meeting-rooms", response_model=list[MeetingRoomResponse])
async def list_meeting_rooms(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all meeting rooms for current user."""
    rooms, _ = await get_meeting_rooms(db, current_user["id"])
    return [MeetingRoomResponse.model_validate(r) for r in rooms]


@router.post("/meeting-rooms", response_model=MeetingRoomResponse, status_code=201)
async def create_new_meeting_room(
    data: MeetingRoomCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new meeting room."""
    # Subscription gating: check if user's plan allows meeting
    if not _is_superuser(current_user):
        plan_features, plan_name = await _get_user_plan_features(db, current_user["id"])
        if plan_features and not _is_feature_allowed(plan_features, "meeting"):
            raise HTTPException(
                403,
                f"Tính năng 'meeting' không có trong gói {plan_name}. "
                f"Vui lòng nâng cấp gói để sử dụng."
            )
    room = await create_meeting_room(
        db, user_id=current_user["id"], **data.model_dump(exclude_none=True),
    )
    return MeetingRoomResponse.model_validate(room)


@router.get("/meeting-rooms/{room_id}", response_model=MeetingRoomResponse)
async def get_meeting_room_detail(
    room_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get meeting room detail."""
    user_id = None if _is_superuser(current_user) else current_user["id"]
    room = await get_meeting_room(db, room_id, user_id=user_id)
    if not room:
        raise HTTPException(404, "Meeting room not found")
    return MeetingRoomResponse.model_validate(room)


@router.put("/meeting-rooms/{room_id}", response_model=MeetingRoomResponse)
async def update_meeting_room_detail(
    room_id: str,
    data: MeetingRoomUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a meeting room."""
    user_id = None if _is_superuser(current_user) else current_user["id"]
    room = await get_meeting_room(db, room_id, user_id=user_id)
    if not room:
        raise HTTPException(404, "Meeting room not found")
    updated = await update_meeting_room(db, room, data.model_dump(exclude_none=True))
    return MeetingRoomResponse.model_validate(updated)


@router.delete("/meeting-rooms/{room_id}", status_code=204)
async def delete_meeting_room_detail(
    room_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a meeting room."""
    user_id = None if _is_superuser(current_user) else current_user["id"]
    room = await get_meeting_room(db, room_id, user_id=user_id)
    if not room:
        raise HTTPException(404, "Meeting room not found")
    await delete_meeting_room(db, room)


# ============================================================
# Agent Feature Toggles API
# ============================================================

@router.get("/agents/{agent_id}", response_model=AgentFeaturesResponse)
async def get_agent_features(
    agent_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get feature module configuration for an agent."""
    
    query = select(Agent).where(Agent.id == agent_id, Agent.is_deleted == False)
    if not _is_superuser(current_user):
        query = query.where(Agent.user_id == current_user["id"])
    
    result = await db.execute(query)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    # Get plan features for gating info
    user_id = current_user["id"] if not _is_superuser(current_user) else agent.user_id
    plan_features, plan_name = await _get_user_plan_features(db, user_id)
    
    return _build_features_response(agent, plan_features, plan_name)


@router.patch("/agents/{agent_id}", response_model=AgentFeaturesResponse)
async def update_agent_features(
    agent_id: str,
    data: AgentFeaturesUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update feature module toggles and assignments for an agent."""
    
    query = select(Agent).where(Agent.id == agent_id, Agent.is_deleted == False)
    if not _is_superuser(current_user):
        query = query.where(Agent.user_id == current_user["id"])
    
    result = await db.execute(query)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    # --- Subscription gating check ---
    update_data = data.model_dump(exclude_none=True)
    assignment_user_id = agent.user_id if _is_superuser(current_user) else current_user["id"]
    update_data = await validate_agent_feature_assignments(
        db,
        user_id=str(assignment_user_id),
        update_data=update_data,
    )
    if update_data.get("course_ids"):
        update_data["enable_education"] = True
    if update_data.get("sales_program_ids"):
        update_data["enable_sales"] = True
    if update_data.get("meeting_room_ids"):
        update_data["enable_meeting"] = True
    
    if not _is_superuser(current_user):
        user_id = current_user["id"]
        plan_features, plan_name = await _get_user_plan_features(db, user_id)
        
        if plan_features:
            for feature_key, plan_key in _FEATURE_TO_PLAN_KEY.items():
                # If user is trying to enable a feature that plan doesn't allow
                if feature_key in update_data and update_data[feature_key] is True:
                    if not _is_feature_allowed(plan_features, plan_key):
                        raise HTTPException(
                            403,
                            f"Tính năng '{plan_key}' không có trong gói {plan_name}. "
                            f"Vui lòng nâng cấp gói để sử dụng."
                        )
    
    # Update only provided fields
    for key, value in update_data.items():
        if hasattr(agent, key):
            setattr(agent, key, value)
    
    await db.commit()
    await db.refresh(agent)
    
    logger.bind(tag=TAG).info(
        f"Updated features for agent {agent_id}: {list(update_data.keys())}"
    )
    
    # Get plan features for response
    resp_user_id = current_user["id"] if not _is_superuser(current_user) else agent.user_id
    plan_features, plan_name = await _get_user_plan_features(db, resp_user_id)
    
    return _build_features_response(agent, plan_features, plan_name)
