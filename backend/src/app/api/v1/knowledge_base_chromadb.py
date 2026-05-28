"""Knowledge Base API V3 - ChromaDB Integration.

Provides endpoints for:
- Text knowledge creation
- Excel import
- Google Sheets import
- Search
- Document management

Works alongside RAGFlow (V2) for hybrid approach.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import ForbiddenException, NotFoundException
from ...core.logger import get_logger
from ...crud.crud_agent import crud_agent
from ...schemas.agent import AgentRead
from ...schemas.base import SuccessResponse
from ...services.chromadb_service import get_chromadb_service

logger = get_logger(__name__)

router = APIRouter(prefix="/agents/{agent_id}/chromadb", tags=["knowledge-base-chromadb"])


# ==================== Schemas ====================


class TextKnowledgeRequest(BaseModel):
    """Request for adding text knowledge."""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=10, max_length=100000)


class GoogleSheetsRequest(BaseModel):
    """Request for importing Google Sheets."""
    url: str = Field(..., description="Google Sheets URL")


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str = Field(..., min_length=1, max_length=1000)
    k: int = Field(default=5, ge=1, le=20)


class DocumentResponse(BaseModel):
    """Document info response."""
    id: str
    title: str
    content: str
    source: str
    type: str


class SearchResult(BaseModel):
    """Search result item."""
    content: str
    title: str
    source: str
    score: float


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
    """Check ChromaDB health status."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    health = await service.health_check()
    
    return SuccessResponse(data=health)


@router.post("/text", response_model=SuccessResponse[dict])
async def add_text_knowledge(
    agent_id: str,
    request: TextKnowledgeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Add text knowledge to agent's ChromaDB collection.
    
    Use this for manually entered knowledge snippets.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    result = await service.add_text(
        agent_id=agent_id,
        title=request.title,
        content=request.content,
    )
    
    return SuccessResponse(
        data=result,
        message="Đã thêm kiến thức thành công"
    )


@router.post("/import/excel", response_model=SuccessResponse[dict])
async def import_excel(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    file: UploadFile = File(...),
) -> SuccessResponse[dict]:
    """Import knowledge from Excel file (.xlsx, .xls).
    
    Expected columns:
    - title (optional): Document title
    - content/nội dung: Main content
    
    If no title column, row numbers are used.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx, .xls) are supported"
        )
    
    content = await file.read()
    
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    
    service = get_chromadb_service()
    
    try:
        result = await service.add_from_excel(
            agent_id=agent_id,
            file_content=content,
            filename=file.filename,
        )
        
        return SuccessResponse(
            data=result,
            message=f"Đã import {result.get('added', 0)} dòng từ Excel"
        )
    except Exception as e:
        logger.error(f"Excel import error: {e}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@router.post("/import/google-sheets", response_model=SuccessResponse[dict])
async def import_google_sheets(
    agent_id: str,
    request: GoogleSheetsRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Import knowledge from Google Sheets.
    
    The sheet must be shared publicly or with "Anyone with link".
    
    Expected columns:
    - title (optional): Document title
    - content/nội dung: Main content
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    
    try:
        result = await service.add_from_google_sheets(
            agent_id=agent_id,
            sheet_url=request.url,
        )
        
        return SuccessResponse(
            data=result,
            message=f"Đã import {result.get('added', 0)} dòng từ Google Sheets"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Google Sheets import error: {e}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@router.post("/search", response_model=SuccessResponse[dict])
async def search_knowledge(
    agent_id: str,
    request: SearchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Search in agent's ChromaDB knowledge base."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    results = await service.search(
        agent_id=agent_id,
        query=request.query,
        top_k=request.k,
    )
    
    return SuccessResponse(
        data={
            "query": request.query,
            "chunks": results,
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
    """List all documents in agent's ChromaDB collection."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    result = await service.list_documents(
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
    """Delete a document from agent's ChromaDB collection."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    await service.delete_document(agent_id=agent_id, doc_id=doc_id)
    
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
    """Delete all knowledge in agent's ChromaDB collection."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    await service.delete_collection(agent_id=agent_id)
    
    return SuccessResponse(
        data={"agent_id": agent_id, "deleted": True},
        message="Đã xóa toàn bộ kiến thức"
    )


@router.get("/stats", response_model=SuccessResponse[dict])
async def get_stats(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Get statistics for agent's ChromaDB collection."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_chromadb_service()
    stats = await service.get_stats(agent_id=agent_id)
    
    return SuccessResponse(data=stats)
