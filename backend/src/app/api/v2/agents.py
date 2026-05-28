"""
API v2 Agents Router

Enhanced agent endpoints with improved response format and features.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.core.schemas.api_response import (
    SuccessResponse,
    PaginatedResponse,
    create_paginated_response,
    create_success_response,
)
from app.services.agent_service import AgentService


router = APIRouter(prefix="/agents", tags=["Agents v2"])
security = HTTPBearer()


async def get_agent_service(
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> AgentService:
    """Get agent service dependency."""
    return AgentService(db)


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List agents",
    description="Get paginated list of agents with enhanced filters",
)
async def list_agents_v2(
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search in name/description"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
):
    """List agents with v2 enhancements."""
    agents = await agent_service.get_agents(
        skip=skip,
        limit=limit,
        user_id=user_id,
        is_active=is_active,
        search=search,
    )
    
    total = await agent_service.count_agents(
        user_id=user_id,
        is_active=is_active,
    )
    
    return create_paginated_response(
        data=[agent.model_dump() for agent in agents],
        page=skip // limit + 1,
        per_page=limit,
        total=total,
    )


@router.get(
    "/{agent_id}",
    response_model=SuccessResponse,
    summary="Get agent",
    description="Get detailed agent information",
)
async def get_agent_v2(
    agent_id: UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
):
    """Get agent by ID with v2 enhancements."""
    agent = await agent_service.get_agent(agent_id)
    
    if not agent:
        return create_success_response(
            data=None,
            action="not_found",
        )
    
    return create_success_response(
        data=agent.model_dump(),
        action="retrieved",
        resource="agent",
    )


@router.get(
    "/{agent_id}/banners",
    response_model=SuccessResponse,
    summary="Get Agent Banners",
    description="Pull banner configuration for devices/kiosks with version tracking. Used for local caching.",
)
async def get_agent_banners(
    agent_id: UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
):
    """Get banner configuration with version control for sync."""
    agent = await agent_service.get_agent(agent_id)
    
    if not agent:
        return create_success_response(
            data=None,
            action="not_found",
        )
        
    banners = agent.banner_images or []
    
    # Simple version hashing for cache control
    import hashlib
    import json
    version_hash = hashlib.md5(json.dumps(banners, sort_keys=True).encode()).hexdigest()
    
    return create_success_response(
        data={
            "version": version_hash,
            "banners": banners,
            "sync_interval": 3600, # seconds to wait before checking again
        },
        action="retrieved",
        resource="banners",
    )


@router.post(
    "",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent",
    description="Create a new agent with enhanced configuration",
)
async def create_agent_v2(
    agent_data: dict,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
):
    """Create a new agent with v2 enhancements."""
    agent = await agent_service.create_agent(agent_data)
    
    return create_success_response(
        data=agent.model_dump() if agent else None,
        action="created",
        resource="agent",
    )


@router.patch(
    "/{agent_id}",
    response_model=SuccessResponse,
    summary="Update agent",
    description="Update an existing agent",
)
async def update_agent_v2(
    agent_id: UUID,
    agent_data: dict,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
):
    """Update agent with v2 enhancements."""
    agent = await agent_service.update_agent(agent_id, agent_data)
    
    return create_success_response(
        data=agent.model_dump() if agent else None,
        action="updated",
        resource="agent",
    )


@router.delete(
    "/{agent_id}",
    response_model=SuccessResponse,
    summary="Delete agent",
    description="Delete an agent (soft delete)",
)
async def delete_agent_v2(
    agent_id: UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
):
    """Delete agent with v2 enhancements."""
    success = await agent_service.delete_agent(agent_id)
    
    return create_success_response(
        data={"deleted": success},
        action="deleted",
        resource="agent",
    )
