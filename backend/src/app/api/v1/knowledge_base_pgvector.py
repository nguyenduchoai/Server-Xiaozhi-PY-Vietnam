"""Knowledge Base API - PgVector (PostgreSQL native vectors).

Provides endpoints for:
- Text knowledge creation
- Semantic search
- Document management

Uses PostgreSQL pgvector extension for scalable vector storage.
Replaces ChromaDB for production use.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import ForbiddenException, NotFoundException
from ...core.logger import get_logger
from ...crud.crud_agent import crud_agent
from ...schemas.agent import AgentRead
from ...schemas.base import SuccessResponse
from ...services.pgvector_knowledge import get_pgvector_service

logger = get_logger(__name__)

router = APIRouter(prefix="/agents/{agent_id}/pgvector", tags=["knowledge-base-pgvector"])


# ==================== Schemas ====================


class TextKnowledgeRequest(BaseModel):
    """Request for adding text knowledge."""
    content: str = Field(..., min_length=10, max_length=100000)
    doc_type: str = Field(default="text", max_length=50)
    source: str = Field(default="manual", max_length=255)
    metadata: dict = Field(default_factory=dict)


class BulkKnowledgeRequest(BaseModel):
    """Request for adding multiple knowledge items."""
    documents: list[dict] = Field(..., min_length=1, max_length=100)
    doc_type: str = Field(default="text", max_length=50)
    source: str = Field(default="bulk", max_length=255)


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    threshold: float = Field(default=0.5, ge=0, le=1)


# ==================== Helper ====================


async def verify_agent_ownership(
    db: AsyncSession,
    agent_id: str,
    user_id: str,
) -> AgentRead:
    """Verify that the user owns the specified agent."""
    agent = await crud_agent.get(
        db=db,
        id=agent_id,
        schema_to_select=AgentRead,
        return_as_model=True,
    )

    if not agent:
        raise NotFoundException(f"Agent {agent_id} not found")

    if agent.user_id != user_id:
        raise ForbiddenException("You don't have access to this agent")

    return agent


# ==================== Endpoints ====================


@router.get("/health", response_model=SuccessResponse[dict])
async def check_health(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Check PgVector health status."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    await service._ensure_initialized()
    
    return SuccessResponse(data={
        "status": "healthy",
        "backend": "pgvector",
        "version": "PostgreSQL with pgvector extension",
    })


@router.post("/text", response_model=SuccessResponse[dict])
async def add_text_knowledge(
    agent_id: str,
    request: TextKnowledgeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Add text knowledge to agent's knowledge base.
    
    Use this for manually entered knowledge snippets.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    result = await service.add_documents(
        agent_id=agent_id,
        documents=[{
            "content": request.content,
            "metadata": request.metadata,
        }],
        doc_type=request.doc_type,
        source=request.source,
    )
    
    return SuccessResponse(
        data=result,
        message="Đã thêm kiến thức thành công"
    )


@router.post("/bulk", response_model=SuccessResponse[dict])
async def add_bulk_knowledge(
    agent_id: str,
    request: BulkKnowledgeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Add multiple knowledge items at once.
    
    Each document in the list should have:
    - content: The text content (required)
    - metadata: Optional metadata dict
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    result = await service.add_documents(
        agent_id=agent_id,
        documents=request.documents,
        doc_type=request.doc_type,
        source=request.source,
    )
    
    return SuccessResponse(
        data=result,
        message=f"Đã thêm {result.get('count', 0)} kiến thức"
    )


@router.post("/search", response_model=SuccessResponse[dict])
async def search_knowledge(
    agent_id: str,
    request: SearchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Search in agent's knowledge base using semantic similarity."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    results = await service.search(
        agent_id=agent_id,
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
    )
    
    return SuccessResponse(
        data={
            "query": request.query,
            "results": results,
            "total": len(results),
        }
    )


@router.get("/documents", response_model=SuccessResponse[dict])
async def list_documents(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    limit: int = 100,
    offset: int = 0,
) -> SuccessResponse[dict]:
    """List all documents in agent's knowledge base."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    result = await service.get_all_documents(
        agent_id=agent_id,
        limit=limit,
        offset=offset,
    )
    
    return SuccessResponse(data=result)


@router.delete("/documents/{doc_id}", response_model=SuccessResponse[dict])
async def delete_document(
    agent_id: str,
    doc_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Delete a document from agent's knowledge base."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    deleted = await service.delete_document(agent_id=agent_id, doc_id=doc_id)
    
    if not deleted:
        raise NotFoundException(f"Document {doc_id} not found")
    
    return SuccessResponse(
        data={"id": doc_id, "deleted": True},
        message="Đã xóa tài liệu"
    )


@router.delete("/", response_model=SuccessResponse[dict])
async def delete_all_knowledge(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Delete all knowledge in agent's knowledge base."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    count = await service.delete_all(agent_id=agent_id)
    
    return SuccessResponse(
        data={"agent_id": agent_id, "deleted_count": count},
        message=f"Đã xóa {count} tài liệu"
    )


@router.get("/stats", response_model=SuccessResponse[dict])
async def get_stats(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Get statistics for agent's knowledge base."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_pgvector_service()
    stats = await service.get_stats(agent_id=agent_id)
    
    return SuccessResponse(data=stats)
