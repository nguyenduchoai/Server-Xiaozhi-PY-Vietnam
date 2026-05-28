"""
Knowledge Base API endpoints.

CRUD operations for independent knowledge bases.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...crud.crud_knowledge_base import crud_knowledge_base
from ...schemas.knowledge_base_schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseWithStats,
    KnowledgeBaseListResponse,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all knowledge bases for current user."""
    items, total = await crud_knowledge_base.list(
        db=db,
        user_id=current_user.get('id'),
        page=page,
        page_size=page_size,
        search=search,
    )
    
    # Enrich with stats
    result_items = []
    for kb in items:
        entry_count = await crud_knowledge_base.get_entry_count(db, kb.id)
        agent_count = await crud_knowledge_base.get_agent_count(db, kb.id)
        result_items.append(
            KnowledgeBaseWithStats(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                ragflow_dataset_id=kb.ragflow_dataset_id,
                embedding_model=kb.embedding_model,
                created_at=kb.created_at,
                updated_at=kb.updated_at,
                entry_count=entry_count,
                agent_count=agent_count,
            )
        )
    
    return KnowledgeBaseListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new knowledge base."""
    kb = await crud_knowledge_base.create(
        db=db,
        user_id=current_user.get('id'),
        data=data,
    )
    return KnowledgeBaseResponse.model_validate(kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseWithStats)
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a knowledge base by ID."""
    kb = await crud_knowledge_base.get(
        db=db,
        kb_id=kb_id,
        user_id=current_user.get('id'),
    )
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    
    entry_count = await crud_knowledge_base.get_entry_count(db, kb.id)
    agent_count = await crud_knowledge_base.get_agent_count(db, kb.id)
    
    return KnowledgeBaseWithStats(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        ragflow_dataset_id=kb.ragflow_dataset_id,
        embedding_model=kb.embedding_model,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        entry_count=entry_count,
        agent_count=agent_count,
    )


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update a knowledge base."""
    kb = await crud_knowledge_base.get(
        db=db,
        kb_id=kb_id,
        user_id=current_user.get('id'),
    )
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    
    kb = await crud_knowledge_base.update(db=db, kb=kb, data=data)
    return KnowledgeBaseResponse.model_validate(kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Soft delete a knowledge base."""
    kb = await crud_knowledge_base.get(
        db=db,
        kb_id=kb_id,
        user_id=current_user.get('id'),
    )
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    
    await crud_knowledge_base.delete(db=db, kb=kb)
    return None
