"""
Knowledge Base Entries API endpoints.

CRUD and import operations for knowledge base entries.
"""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...crud.crud_knowledge_base import crud_knowledge_base
from ...core.logger import get_logger
from ...services.chromadb_service import get_chromadb_service
from bs4 import BeautifulSoup
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge-bases/{kb_id}", tags=["knowledge-bases-entries"])


# ==================== Schemas ====================

class KnowledgeEntryResponse(BaseModel):
    id: str
    content: str
    doc_type: str
    source: str
    metadata_json: Optional[str] = None
    created_at: str
    updated_at: str


class KnowledgeEntryListResponse(BaseModel):
    items: list[KnowledgeEntryResponse]
    total: int
    page: int
    page_size: int


class KnowledgeEntryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)
    doc_type: str = Field(default="text")
    source: str = Field(default="manual")
    metadata: Optional[dict] = None


class UploadUrlRequest(BaseModel):
    url: str = Field(..., description="URL to fetch content from")


class GoogleSheetsImportRequest(BaseModel):
    url: str = Field(..., description="Google Sheets URL")
    sheet_name: str = Field(default="Sheet1", description="Sheet tab name")


# ==================== Helper ====================

async def verify_kb_ownership(db: AsyncSession, kb_id: str, user_id: str):
    """Verify that the user owns the knowledge base."""
    kb = await crud_knowledge_base.get(db=db, kb_id=kb_id, user_id=user_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return kb


# ==================== Entry Endpoints ====================

@router.get("/entries", response_model=KnowledgeEntryListResponse)
async def list_entries(
    kb_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all entries in a knowledge base."""
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    # Get entries from ChromaDB
    chromadb = get_chromadb_service()
    if not chromadb:
        return KnowledgeEntryListResponse(items=[], total=0, page=page, page_size=page_size)
    
    try:
        results = await chromadb.list_documents(kb_id, limit=page_size, offset=(page - 1) * page_size)
        
        items = []
        for doc in results.get("documents", []):
            items.append(KnowledgeEntryResponse(
                id=doc.get("id", ""),
                content=doc.get("content", "")[:500],  # Truncate for list
                doc_type=doc.get("metadata", {}).get("doc_type", "text"),
                source=doc.get("metadata", {}).get("source", "unknown"),
                metadata_json=None,
                created_at=doc.get("metadata", {}).get("created_at", ""),
                updated_at=doc.get("metadata", {}).get("updated_at", ""),
            ))
        
        return KnowledgeEntryListResponse(
            items=items,
            total=results.get("total", len(items)),
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error listing entries: {e}")
        return KnowledgeEntryListResponse(items=[], total=0, page=page, page_size=page_size)


@router.post("/entries", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    kb_id: str,
    data: KnowledgeEntryCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a text entry to the knowledge base."""
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    chromadb = get_chromadb_service()
    if not chromadb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )
    
    import uuid
    
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    try:
        await chromadb.add_document(
            collection_id=kb_id,
            doc_id=entry_id,
            content=data.content,
            metadata={
                "doc_type": data.doc_type,
                "source": data.source,
                "created_at": now,
                "updated_at": now,
                **(data.metadata or {}),
            },
        )
        
        return KnowledgeEntryResponse(
            id=entry_id,
            content=data.content[:500],
            doc_type=data.doc_type,
            source=data.source,
            metadata_json=None,
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        logger.error(f"Error creating entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entry: {str(e)}",
        )


@router.post("/entries/upload", response_model=KnowledgeEntryResponse)
async def upload_file(
    kb_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to the knowledge base."""
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    # Check file type
    allowed_types = [".txt", ".md", ".pdf", ".csv", ".docx"]
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed: {', '.join(allowed_types)}",
        )
    
    # Read content
    content = await file.read()
    
    # Parse content based on type
    text_content = ""
    if ext in [".txt", ".md"]:
        text_content = content.decode("utf-8", errors="ignore")
    elif ext == ".csv":
        text_content = content.decode("utf-8", errors="ignore")
    else:
        # For PDF/DOCX, store raw and note it's not parsed yet
        text_content = f"[File: {filename}] - Content not parsed yet"
    
    # Create entry
    chromadb = get_chromadb_service()
    if not chromadb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )
    
    import uuid
    
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    try:
        await chromadb.add_document(
            collection_id=kb_id,
            doc_id=entry_id,
            content=text_content,
            metadata={
                "doc_type": ext[1:],  # Remove dot
                "source": filename,
                "created_at": now,
                "updated_at": now,
            },
        )
        
        return KnowledgeEntryResponse(
            id=entry_id,
            content=text_content[:500],
            doc_type=ext[1:],
            source=filename,
            metadata_json=None,
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )


@router.post("/upload-url")
async def upload_from_url(
    kb_id: str,
    data: UploadUrlRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload content from a URL."""
    import httpx
    
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(data.url, follow_redirects=True)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            
            # Get text
            text = soup.get_text(separator="\n", strip=True)
            
            if not text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not extract text from URL",
                )
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch URL: {str(e)}",
        )
    
    # Create entry
    chromadb = get_chromadb_service()
    if not chromadb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )
    
    import uuid
    
    entry_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    try:
        await chromadb.add_document(
            collection_id=kb_id,
            doc_id=entry_id,
            content=text,
            metadata={
                "doc_type": "url",
                "source": data.url,
                "created_at": now,
                "updated_at": now,
            },
        )
        
        return {"success": True, "message": "Content imported from URL", "id": entry_id}
    except Exception as e:
        logger.error(f"Error uploading from URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import from URL: {str(e)}",
        )


@router.post("/import/sheets")
async def import_google_sheets(
    kb_id: str,
    data: GoogleSheetsImportRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Import data from Google Sheets."""
    import httpx
    import re
    
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    # Extract sheet ID from URL
    sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', data.url)
    if not sheet_id_match:
        # Maybe it's just the ID
        sheet_id = data.url.strip()
    else:
        sheet_id = sheet_id_match.group(1)
    
    # Build CSV export URL
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={data.sheet_name}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(csv_url)
            response.raise_for_status()
            csv_content = response.text
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch Google Sheets: {str(e)}. Make sure the sheet is shared publicly.",
        )
    
    # Parse CSV
    import csv
    import io
    
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sheet is empty or could not be parsed",
        )
    
    chromadb = get_chromadb_service()
    if not chromadb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )
    
    import uuid
    
    now = datetime.utcnow().isoformat()
    imported_count = 0
    
    # Find content column (case-insensitive)
    columns = list(rows[0].keys())
    
    def find_col(names: list[str]) -> str | None:
        for col in columns:
            if col.lower().strip() in [n.lower() for n in names]:
                return col
        return None
    
    content_col = find_col(["content", "nội dung", "text", "value", "mô tả", "description"])
    title_col = find_col(["title", "tên", "tiêu đề", "name", "tên sản phẩm"])
    image_col = find_col(["image_url", "url ảnh", "ảnh", "image", "hình", "img", "url_img"])
    
    if not content_col:
        # Use first column as content
        content_col = columns[0]
    
    logger.info(f"Importing sheets with columns: content={content_col}, title={title_col}, image={image_col}")

    try:
        for row in rows:
            content = row.get(content_col, "").strip()
            if not content:
                continue
            
            title = row.get(title_col, "").strip() if title_col else ""
            image_url = row.get(image_col, "").strip() if image_col else ""
            
            # Build full content with title
            full_content = f"# {title}\n\n{content}" if title else content
            
            entry_id = str(uuid.uuid4())
            await chromadb.add_document(
                collection_id=kb_id,
                doc_id=entry_id,
                content=full_content,
                metadata={
                    "doc_type": "sheets",
                    "source": f"Google Sheets: {data.sheet_name}",
                    "title": title,
                    "image_url": image_url,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            imported_count += 1
        
        return {"success": True, "message": f"Imported {imported_count} entries from Google Sheets"}
    except Exception as e:
        logger.error(f"Error importing from Google Sheets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import: {str(e)}",
        )


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_entries(
    kb_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Clear all entries from a knowledge base."""
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    chromadb = get_chromadb_service()
    if not chromadb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )
    
    try:
        await chromadb.delete_collection(kb_id)
        logger.info(f"Cleared all entries from KB {kb_id}")
        return None
    except Exception as e:
        logger.error(f"Error clearing entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear entries: {str(e)}",
        )


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    kb_id: str,
    entry_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a single entry."""
    await verify_kb_ownership(db, kb_id, current_user.get('id'))
    
    chromadb = get_chromadb_service()
    if not chromadb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )
    
    try:
        await chromadb.delete_document(kb_id, entry_id)
        return None
    except Exception as e:
        logger.error(f"Error deleting entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entry: {str(e)}",
        )
