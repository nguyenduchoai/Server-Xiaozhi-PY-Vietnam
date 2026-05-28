"""
Knowledge Base Entries API endpoints.

CRUD operations for entries within a knowledge base.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logger import get_logger

logger = get_logger(__name__)

from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...models import KnowledgeEmbedding
from ...crud.crud_knowledge_base import crud_knowledge_base
from ...schemas.knowledge_base_schemas import (
    KnowledgeEntryCreate,
    KnowledgeEntryResponse,
    KnowledgeEntryListResponse,
)

router = APIRouter(prefix="/knowledge-bases/{kb_id}/entries", tags=["knowledge-entries"])


async def get_kb_or_404(
    kb_id: str,
    db: AsyncSession,
    user_id: str,
):
    """Helper to get KB or raise 404."""
    kb = await crud_knowledge_base.get(db=db, kb_id=kb_id, user_id=user_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return kb


@router.get("", response_model=KnowledgeEntryListResponse)
async def list_entries(
    kb_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # Accept the alternative offset/limit pagination scheme too — some FE
    # callers send these instead of page/page_size.
    offset: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=100),
    doc_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List entries in a knowledge base."""
    await get_kb_or_404(kb_id, db, current_user.get('id'))

    # Resolve pagination: if FE sent offset/limit, derive page/page_size.
    if limit is not None:
        page_size = max(1, min(100, int(limit)))
    if offset is not None and limit:
        page = (int(offset) // max(int(limit), 1)) + 1

    # Base query
    query = select(KnowledgeEmbedding).where(
        KnowledgeEmbedding.knowledge_base_id == kb_id
    )

    # Filter by doc_type
    if doc_type:
        query = query.where(KnowledgeEmbedding.doc_type == doc_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(KnowledgeEmbedding.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    entries = list(result.scalars().all())

    return KnowledgeEntryListResponse(
        items=[KnowledgeEntryResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    kb_id: str,
    data: KnowledgeEntryCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a text entry to knowledge base."""
    await get_kb_or_404(kb_id, db, current_user.get('id'))
    
    # Create entry
    entry = KnowledgeEmbedding(
        knowledge_base_id=kb_id,
        content=data.content,
        doc_type=data.doc_type,
        source=data.source,
        metadata_json=json.dumps(data.metadata) if data.metadata else None,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    # TODO: Generate embedding asynchronously
    # For now, embedding is None until background job processes it
    
    return KnowledgeEntryResponse.model_validate(entry)


@router.post("/upload", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    kb_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to knowledge base (PDF, DOCX, TXT, CSV)."""
    await get_kb_or_404(kb_id, db, current_user.get('id'))
    
    # Validate file type
    allowed_types = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "text",
        "text/csv": "csv",
        "application/vnd.ms-excel": "excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
    }
    
    content_type = file.content_type or ""
    if content_type not in allowed_types:
        # Try by extension
        filename = file.filename or ""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        ext_map = {"pdf": "pdf", "docx": "docx", "txt": "text", "csv": "csv", "xlsx": "excel", "xls": "excel"}
        doc_type = ext_map.get(ext)
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, DOCX, TXT, CSV, Excel",
            )
    else:
        doc_type = allowed_types[content_type]
    
    # Read file content
    content = await file.read()
    
    # For text files, decode directly
    if doc_type == "text":
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1")
    elif doc_type == "pdf":
        # Extract PDF text using PyMuPDF (fitz)
        try:
            import fitz  # PyMuPDF
            import io
            
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            text_parts = []
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text_parts.append(page.get_text())
            pdf_doc.close()
            
            text_content = "\n\n".join(text_parts).strip()
            if not text_content:
                text_content = f"[File: {file.filename}] PDF contains no extractable text (possibly scanned images)"
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            text_content = f"[File: {file.filename}] PDF extraction failed: {str(e)}"
    elif doc_type == "docx":
        # Extract DOCX text using python-docx
        try:
            from docx import Document
            import io
            
            doc = Document(io.BytesIO(content))
            text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
            text_content = "\n\n".join(text_parts).strip()
            if not text_content:
                text_content = f"[File: {file.filename}] DOCX contains no extractable text"
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            text_content = f"[File: {file.filename}] DOCX extraction failed: {str(e)}"
    elif doc_type in ("csv", "excel"):
        # For CSV/Excel, store as placeholder for now
        text_content = f"[File: {file.filename}] Spreadsheet content - {len(content)} bytes"
    else:
        text_content = f"[File: {file.filename}] Content pending extraction..."
    
    # Create entry
    entry = KnowledgeEmbedding(
        knowledge_base_id=kb_id,
        content=text_content,
        doc_type=doc_type,
        source=file.filename or "upload",
        metadata_json=json.dumps({"original_filename": file.filename, "size": len(content), "extracted": True}),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    return KnowledgeEntryResponse.model_validate(entry)


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_entry(
    kb_id: str,
    entry_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific entry."""
    await get_kb_or_404(kb_id, db, current_user.get('id'))
    
    query = select(KnowledgeEmbedding).where(
        KnowledgeEmbedding.id == entry_id,
        KnowledgeEmbedding.knowledge_base_id == kb_id,
    )
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
    
    return KnowledgeEntryResponse.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    kb_id: str,
    entry_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete an entry."""
    await get_kb_or_404(kb_id, db, current_user.get('id'))
    
    query = select(KnowledgeEmbedding).where(
        KnowledgeEmbedding.id == entry_id,
        KnowledgeEmbedding.knowledge_base_id == kb_id,
    )
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
    
    await db.delete(entry)
    await db.commit()
    return None
