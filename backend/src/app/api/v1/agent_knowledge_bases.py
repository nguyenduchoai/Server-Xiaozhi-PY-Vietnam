"""
Agent Knowledge Base linking API endpoints.

Manage which knowledge bases are linked to an agent.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...crud.crud_agent import crud_agent
from ...crud.crud_knowledge_base import crud_knowledge_base, crud_agent_kb
from ...schemas.knowledge_base_schemas import (
    AgentKnowledgeBasesUpdate,
    AgentKnowledgeBasesResponse,
    AgentKnowledgeBaseLink,
)

router = APIRouter(prefix="/agents/{agent_id}/knowledge-bases", tags=["agent-knowledge-bases"])


async def get_agent_or_404(
    agent_id: str,
    db: AsyncSession,
    user_id: str,
) -> dict:
    """Helper to get agent or raise 404."""
    agent = await crud_agent.get(db=db, id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    # Handle both dict and model response
    is_deleted = agent.get("is_deleted", False) if isinstance(agent, dict) else getattr(agent, "is_deleted", False)
    if is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    # Check ownership
    agent_user_id = agent.get("user_id") if isinstance(agent, dict) else getattr(agent, "user_id", None)
    if str(agent_user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this agent",
        )
    return agent


@router.get("", response_model=AgentKnowledgeBasesResponse)
async def get_agent_knowledge_bases(
    agent_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all knowledge bases linked to an agent."""
    await get_agent_or_404(agent_id, db, current_user.get('id'))
    
    kbs = await crud_agent_kb.get_kbs_for_agent(db=db, agent_id=agent_id)
    
    return AgentKnowledgeBasesResponse(
        knowledge_bases=[
            AgentKnowledgeBaseLink(id=kb.id, name=kb.name)
            for kb in kbs
        ]
    )


@router.put("", response_model=AgentKnowledgeBasesResponse)
async def update_agent_knowledge_bases(
    agent_id: str,
    data: AgentKnowledgeBasesUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Replace all knowledge bases for an agent."""
    await get_agent_or_404(agent_id, db, current_user.get('id'))
    
    # Validate that all KB IDs exist and belong to user
    for kb_id in data.knowledge_base_ids:
        kb = await crud_knowledge_base.get(db=db, kb_id=kb_id, user_id=current_user.get('id'))
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Knowledge base {kb_id} not found or not owned by you",
            )
    
    # Update links
    await crud_agent_kb.update_agent_kbs(
        db=db,
        agent_id=agent_id,
        kb_ids=data.knowledge_base_ids,
    )
    
    # Return updated list
    kbs = await crud_agent_kb.get_kbs_for_agent(db=db, agent_id=agent_id)
    
    return AgentKnowledgeBasesResponse(
        knowledge_bases=[
            AgentKnowledgeBaseLink(id=kb.id, name=kb.name)
            for kb in kbs
        ]
    )
