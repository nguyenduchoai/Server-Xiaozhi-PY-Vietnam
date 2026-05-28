"""Unified Knowledge API - Smart Router for all knowledge operations.

Single endpoint for all knowledge operations:
- Auto-routes to RAGFlow or ChromaDB based on input type
- Fallback when service unavailable
- Unified response format

Usage:
    POST /agents/{id}/knowledge/upload - Upload any file
    POST /agents/{id}/knowledge/text - Add text
    POST /agents/{id}/knowledge/import/sheets - Import Google Sheets
    POST /agents/{id}/knowledge/search - Search across all backends
    GET  /agents/{id}/knowledge/documents - List all documents
    DELETE /agents/{id}/knowledge/documents/{doc_id} - Delete document
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
from ...services.unified_knowledge_service import (
    get_unified_knowledge_service,
    KnowledgeBackend,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/agents/{agent_id}/knowledge", tags=["knowledge-unified"])


# ==================== Schemas ====================


class TextKnowledgeRequest(BaseModel):
    """Request for adding text knowledge."""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=10, max_length=100000)
    backend: str = Field(default="auto", description="Backend: auto, ragflow, chromadb")
    image_url: str | None = Field(default=None, max_length=2000, description="Optional image URL for display")


class GoogleSheetsRequest(BaseModel):
    """Request for importing Google Sheets."""
    url: str = Field(..., description="Google Sheets URL")


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str = Field(..., min_length=1, max_length=1000)
    k: int = Field(default=5, ge=1, le=20)
    search_all: bool = Field(default=True, description="Search all backends")


class UpdateChunkRequest(BaseModel):
    """Request for updating a chunk."""
    content: str = Field(..., min_length=1, max_length=100000)
    title: str | None = Field(default=None, max_length=500)


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


def parse_backend(backend_str: str) -> KnowledgeBackend:
    """Parse backend string to enum."""
    if backend_str == "ragflow":
        return KnowledgeBackend.RAGFLOW
    elif backend_str == "chromadb":
        return KnowledgeBackend.CHROMADB
    return KnowledgeBackend.AUTO


# ==================== Endpoints ====================


@router.get("/health", response_model=SuccessResponse[dict])
async def check_health(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Check health of all knowledge backends.
    
    Returns availability of RAGFlow and ChromaDB.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    health = await service.check_backends_health(force=True)
    
    return SuccessResponse(
        data={
            "status": "healthy" if any(health.values()) else "degraded",
            "backends": health,
            "message": "At least one backend available" if any(health.values()) else "No backends available",
        }
    )


@router.post("/text", response_model=SuccessResponse[dict])
async def add_text_knowledge(
    agent_id: str,
    request: TextKnowledgeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Add text knowledge (auto-routed to optimal backend).
    
    For manually entered knowledge snippets.
    Default backend: ChromaDB (lightweight).
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    backend = parse_backend(request.backend)
    
    try:
        result = await service.add_text(
            agent_id=agent_id,
            title=request.title,
            content=request.content,
            preferred_backend=backend,
            image_url=request.image_url,  # NEW: Pass image URL
        )
        
        return SuccessResponse(
            data=result,
            message=f"Đã thêm kiến thức vào {result['backend']}"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Add text error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-image", response_model=SuccessResponse[dict])
async def upload_knowledge_image(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    file: UploadFile = File(...),
) -> SuccessResponse[dict]:
    """Upload an image for knowledge entry.
    
    Automatically resizes to max 800x800 and compresses to max 500KB.
    Returns public URL for the image.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Chỉ chấp nhận file ảnh: JPEG, PNG, WebP, GIF"
        )
    
    content = await file.read()
    
    # Max 10MB original upload
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File quá lớn (max 10MB)")
    
    try:
        from PIL import Image
        import io
        import uuid
        import os
        
        # Open image
        img = Image.open(io.BytesIO(content))
        
        # Convert to RGB if necessary (for JPEG saving)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Resize if larger than 800x800
        max_size = 800
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Prepare output
        output = io.BytesIO()
        
        # Compress to fit 500KB
        max_bytes = 500 * 1024  # 500KB
        quality = 95
        
        while quality > 20:
            output.seek(0)
            output.truncate()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            if output.tell() <= max_bytes:
                break
            quality -= 5
        
        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        filename = f"{agent_id}_{file_id}.jpg"
        
        # Save to uploads directory
        upload_dir = os.environ.get("UPLOADS_DIR", "/app/data/uploads") + "/knowledge/images"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(output.getvalue())
        
        # Generate public URL
        public_url = f"/uploads/knowledge/images/{filename}"
        
        final_size = output.tell()
        logger.info(f"Uploaded knowledge image: {filename}, size: {final_size/1024:.1f}KB, dimensions: {img.width}x{img.height}")
        
        return SuccessResponse(
            data={
                "url": public_url,
                "filename": filename,
                "size": final_size,
                "width": img.width,
                "height": img.height,
            },
            message="Đã upload hình ảnh thành công"
        )
        
    except Exception as e:
        logger.error(f"Image upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý ảnh: {str(e)}")


@router.post("/upload", response_model=SuccessResponse[dict])
async def upload_file(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    file: UploadFile = File(...),
    backend: str = "auto",
) -> SuccessResponse[dict]:
    """Upload a file (auto-routed based on file type).
    
    Routing rules:
    - PDF, DOCX, HTML → RAGFlow (if available) or ChromaDB
    - Excel, CSV, TXT → ChromaDB
    - Markdown → ChromaDB (fallback to RAGFlow)
    
    Max file size: 50MB
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    content = await file.read()
    
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File quá lớn (max 50MB)")
    
    service = get_unified_knowledge_service()
    preferred = parse_backend(backend)
    
    try:
        result = await service.upload_file(
            agent_id=agent_id,
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            preferred_backend=preferred,
        )
        
        return SuccessResponse(
            data=result,
            message=f"Đã upload {file.filename} vào {result['backend']}"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/sheets", response_model=SuccessResponse[dict])
async def import_google_sheets(
    agent_id: str,
    request: GoogleSheetsRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Import from Google Sheets.
    
    The sheet must be shared publicly or with "Anyone with link".
    Expected columns: title (optional), content/nội dung
    
    Backend: ChromaDB (only)
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        result = await service.import_google_sheets(
            agent_id=agent_id,
            sheet_url=request.url,
        )
        
        return SuccessResponse(
            data=result,
            message=f"Đã import {result.get('added', 0)} dòng từ Google Sheets"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Sheets import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SuccessResponse[dict])
async def search_knowledge(
    agent_id: str,
    request: SearchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Search across all knowledge backends.
    
    Combines results from RAGFlow and ChromaDB, sorted by relevance.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        result = await service.search(
            agent_id=agent_id,
            query=request.query,
            top_k=request.k,
            search_all=request.search_all,
        )
        
        return SuccessResponse(data=result)
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=SuccessResponse[dict])
async def list_documents(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    limit: int = 100,
) -> SuccessResponse[dict]:
    """List all documents from all backends."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        result = await service.list_documents(
            agent_id=agent_id,
            limit=limit,
        )
        
        return SuccessResponse(data=result)
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/chunks", response_model=SuccessResponse[dict])
async def get_document_chunks(
    agent_id: str,
    doc_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    page_size: int = 50,
) -> SuccessResponse[dict]:
    """Get chunks from a RAGFlow document.
    
    Returns the parsed text chunks from a document uploaded to RAGFlow.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        # Get dataset for this agent
        dataset_id = await service.ragflow_service.get_or_create_agent_dataset(agent_id)
        
        # Get chunks from RAGFlow
        result = await service.ragflow_service.get_document_chunks(
            dataset_id=dataset_id,
            document_id=doc_id,
            page=page,
            page_size=page_size,
        )
        
        # Parse response
        data = result.get("data", {})
        chunks = data.get("chunks", []) if isinstance(data, dict) else []
        
        return SuccessResponse(data={
            "chunks": [
                {
                    "id": chunk.get("id"),
                    "content": chunk.get("content"),
                    "document_id": chunk.get("document_id"),
                }
                for chunk in chunks
            ],
            "total": data.get("total", len(chunks)) if isinstance(data, dict) else len(chunks),
            "page": page,
            "page_size": page_size,
        })
    except Exception as e:
        logger.error(f"Get chunks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}", response_model=SuccessResponse[dict])
async def delete_document(
    agent_id: str,
    doc_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    backend: str | None = None,
) -> SuccessResponse[dict]:
    """Delete a document from knowledge base.
    
    If backend not specified, tries both.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    backend_enum = parse_backend(backend) if backend else None
    
    try:
        deleted = await service.delete_document(
            agent_id=agent_id,
            doc_id=doc_id,
            backend=backend_enum if backend_enum != KnowledgeBackend.AUTO else None,
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return SuccessResponse(
            data={"id": doc_id, "deleted": True},
            message="Đã xóa tài liệu"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=SuccessResponse[dict])
async def get_stats(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Get statistics from all knowledge backends."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        stats = await service.get_stats(agent_id=agent_id)
        return SuccessResponse(data=stats)
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chunk Operations ====================


@router.get("/chunks", response_model=SuccessResponse[dict])
async def list_all_chunks(
    agent_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    limit: int = 100,
) -> SuccessResponse[dict]:
    """List all chunks/entries from ChromaDB with full content.
    
    Returns all knowledge entries that can be edited.
    """
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        result = await service.chromadb_service.list_documents(
            agent_id=agent_id,
            limit=limit,
        )
        
        return SuccessResponse(data={
            "chunks": [
                {
                    "id": doc.get("id"),
                    "title": doc.get("title") or "Untitled",
                    "content": doc.get("content"),
                    "source": doc.get("source"),
                    "type": doc.get("type"),
                    "image_url": doc.get("image_url"),  # NEW: Include image URL
                }
                for doc in result.get("documents", [])
            ],
            "total": result.get("total", 0),
        })
    except Exception as e:
        logger.error(f"List chunks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chunks/{chunk_id}", response_model=SuccessResponse[dict])
async def update_chunk(
    agent_id: str,
    chunk_id: str,
    request: UpdateChunkRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Update a ChromaDB chunk content."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        await service.chromadb_service.update_document(
            agent_id=agent_id,
            doc_id=chunk_id,
            content=request.content,
            title=request.title,
        )
        
        return SuccessResponse(
            data={"id": chunk_id, "updated": True},
            message="Đã cập nhật nội dung"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Update chunk error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chunks/{chunk_id}", response_model=SuccessResponse[dict])
async def delete_chunk(
    agent_id: str,
    chunk_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """Delete a ChromaDB chunk."""
    await verify_agent_ownership(db, agent_id, current_user["id"])
    
    service = get_unified_knowledge_service()
    
    try:
        await service.chromadb_service.delete_document(
            agent_id=agent_id,
            doc_id=chunk_id,
        )
        
        return SuccessResponse(
            data={"id": chunk_id, "deleted": True},
            message="Đã xóa chunk"
        )
    except Exception as e:
        logger.error(f"Delete chunk error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
