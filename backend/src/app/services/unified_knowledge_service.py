"""Unified Knowledge Service - Smart Router for RAGFlow & ChromaDB.

This service automatically routes knowledge requests to the optimal backend:
- RAGFlow: For complex documents (PDF, DOCX, HTML)
- ChromaDB: For text, Excel, Google Sheets

Features:
- Auto-detection of input type
- Fallback when service unavailable
- Unified response format
- Health-aware routing
"""

import asyncio
from enum import Enum

from ..core.config import settings
from ..core.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBackend(str, Enum):
    """Available knowledge storage backends."""
    CHROMADB = "chromadb"  # Primary backend
    AUTO = "auto"  # Let router decide (will use ChromaDB)


class InputType(str, Enum):
    """Types of input for knowledge ingestion."""
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    EXCEL = "excel"
    CSV = "csv"
    GOOGLE_SHEETS = "google_sheets"
    MARKDOWN = "markdown"
    TXT = "txt"
    URL = "url"  # Webpage URL
    YOUTUBE = "youtube"  # YouTube video


# Routing rules: ChromaDB handles all input types now
ROUTING_RULES: dict[InputType, list[KnowledgeBackend]] = {
    # All types use ChromaDB
    InputType.PDF: [KnowledgeBackend.CHROMADB],
    InputType.DOCX: [KnowledgeBackend.CHROMADB],
    InputType.HTML: [KnowledgeBackend.CHROMADB],
    InputType.TEXT: [KnowledgeBackend.CHROMADB],
    InputType.EXCEL: [KnowledgeBackend.CHROMADB],
    InputType.CSV: [KnowledgeBackend.CHROMADB],
    InputType.GOOGLE_SHEETS: [KnowledgeBackend.CHROMADB],
    InputType.MARKDOWN: [KnowledgeBackend.CHROMADB],
    InputType.TXT: [KnowledgeBackend.CHROMADB],
}


def detect_input_type(filename: str | None = None, content_type: str | None = None) -> InputType:
    """Detect input type from filename or content type.
    
    Args:
        filename: Original filename
        content_type: MIME content type
        
    Returns:
        Detected InputType
    """
    if filename:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        if ext == "pdf":
            return InputType.PDF
        elif ext in ("doc", "docx"):
            return InputType.DOCX
        elif ext in ("xls", "xlsx"):
            return InputType.EXCEL
        elif ext == "csv":
            return InputType.CSV
        elif ext == "html":
            return InputType.HTML
        elif ext == "md":
            return InputType.MARKDOWN
        elif ext == "txt":
            return InputType.TXT
    
    if content_type:
        if "pdf" in content_type:
            return InputType.PDF
        elif "word" in content_type or "docx" in content_type:
            return InputType.DOCX
        elif "excel" in content_type or "spreadsheet" in content_type:
            return InputType.EXCEL
        elif "csv" in content_type:
            return InputType.CSV
        elif "html" in content_type:
            return InputType.HTML
    
    # Default to text
    return InputType.TEXT


class UnifiedKnowledgeService:
    """Unified service for managing knowledge across multiple backends."""
    
    def __init__(self):
        self._ragflow_service = None
        self._chromadb_service = None
        self._ragflow_healthy: bool | None = None
        self._chromadb_healthy: bool | None = None
        self._last_health_check = 0
    
    @property
    def ragflow_service(self):
        """Lazy load RAGFlow service."""
        if self._ragflow_service is None:
            try:
                from .ragflow_service import RAGFlowService
                if settings.ragflow.enabled and settings.ragflow.base_url:
                    self._ragflow_service = RAGFlowService(
                        base_url=settings.ragflow.base_url,
                        api_key=settings.ragflow.api_key,
                    )
                else:
                    logger.debug("RAGFlow not configured (missing base_url or disabled)")
            except Exception as e:
                logger.warning(f"RAGFlow service not available: {e}")
        return self._ragflow_service
    
    @property
    def chromadb_service(self):
        """Lazy load ChromaDB service."""
        if self._chromadb_service is None:
            try:
                from .chromadb_service import get_chromadb_service
                self._chromadb_service = get_chromadb_service()
            except Exception as e:
                logger.warning(f"ChromaDB service not available: {e}")
        return self._chromadb_service
    
    async def check_backends_health(self, force: bool = False) -> dict[str, bool]:
        """Check health of all backends.
        
        Args:
            force: Force refresh health check
            
        Returns:
            Dict with backend health status
        """
        import time
        current_time = time.time()
        
        # Cache health for 30 seconds
        if not force and current_time - self._last_health_check < 30:
            return {
                "ragflow": self._ragflow_healthy or False,
                "chromadb": self._chromadb_healthy or False,
            }
        
        self._last_health_check = current_time
        
        # Check RAGFlow
        try:
            if self.ragflow_service and settings.ragflow.enabled:
                health = await self.ragflow_service.health_check()
                self._ragflow_healthy = health.get("status") == "healthy"
            else:
                self._ragflow_healthy = False
        except Exception:
            self._ragflow_healthy = False
        
        # Check ChromaDB
        try:
            if self.chromadb_service:
                health = await self.chromadb_service.health_check()
                self._chromadb_healthy = health.get("status") == "healthy"
            else:
                self._chromadb_healthy = False
        except Exception:
            self._chromadb_healthy = False
        
        logger.debug(f"Backend health: RAGFlow={self._ragflow_healthy}, ChromaDB={self._chromadb_healthy}")

        return {
            "ragflow": self._ragflow_healthy,
            "chromadb": self._chromadb_healthy,
        }
    
    def select_backend(
        self,
        input_type: InputType,
        preferred: KnowledgeBackend = KnowledgeBackend.AUTO,
    ) -> KnowledgeBackend | None:
        """Select the optimal backend for the given input type.
        
        Args:
            input_type: Type of input
            preferred: User-preferred backend (optional)
            
        Returns:
            Selected backend or None if none available
        """
        # If user specifies, try that first
        if preferred != KnowledgeBackend.AUTO:
            if preferred == KnowledgeBackend.RAGFLOW and self._ragflow_healthy:
                return KnowledgeBackend.RAGFLOW
            elif preferred == KnowledgeBackend.CHROMADB and self._chromadb_healthy:
                return KnowledgeBackend.CHROMADB
        
        # Get routing priorities for this input type
        priorities = ROUTING_RULES.get(input_type, [KnowledgeBackend.CHROMADB])
        
        # Try each in priority order
        for backend in priorities:
            if backend == KnowledgeBackend.RAGFLOW and self._ragflow_healthy:
                return KnowledgeBackend.RAGFLOW
            elif backend == KnowledgeBackend.CHROMADB and self._chromadb_healthy:
                return KnowledgeBackend.CHROMADB
        
        # Fallback: try any healthy backend
        if self._chromadb_healthy:
            return KnowledgeBackend.CHROMADB
        if self._ragflow_healthy:
            return KnowledgeBackend.RAGFLOW
        
        return None
    
    async def add_text(
        self,
        agent_id: str,
        title: str,
        content: str,
        preferred_backend: KnowledgeBackend = KnowledgeBackend.AUTO,
        image_url: str | None = None,  # NEW: Optional image URL
    ) -> dict:
        """Add text knowledge using the optimal backend.
        
        Args:
            agent_id: Agent identifier
            title: Document title
            content: Text content
            preferred_backend: Preferred backend (optional)
            image_url: Optional image URL for device display
            
        Returns:
            Result dict with backend used and document info
        """
        await self.check_backends_health()
        backend = self.select_backend(InputType.TEXT, preferred_backend)
        
        if not backend:
            raise RuntimeError("No knowledge backend available")
        
        if backend == KnowledgeBackend.CHROMADB:
            result = await self.chromadb_service.add_text(
                agent_id=agent_id,
                title=title,
                content=content,
                image_url=image_url,  # NEW: Pass image URL
            )
            return {
                "backend": "chromadb",
                "id": result.get("id"),
                "title": title,
                "image_url": image_url,  # NEW: Return image URL
                "status": "success",
            }
        else:
            # RAGFlow text upload
            result = await self.ragflow_service.upload_text(
                agent_id=agent_id,
                title=title,
                content=content,
            )
            return {
                "backend": "ragflow",
                "id": result.get("id"),
                "title": title,
                "status": "success",
            }
    
    async def upload_file(
        self,
        agent_id: str,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
        preferred_backend: KnowledgeBackend = KnowledgeBackend.AUTO,
    ) -> dict:
        """Upload a file using the optimal backend.
        
        Args:
            agent_id: Agent identifier
            file_content: File bytes
            filename: Original filename
            content_type: MIME type (optional)
            preferred_backend: Preferred backend (optional)
            
        Returns:
            Result dict with backend used and document info
        """
        await self.check_backends_health()
        
        input_type = detect_input_type(filename, content_type)
        backend = self.select_backend(input_type, preferred_backend)
        
        if not backend:
            raise RuntimeError("No knowledge backend available")
        
        logger.info(f"Routing {filename} ({input_type.value}) to {backend.value}")
        
        if backend == KnowledgeBackend.CHROMADB:
            # ChromaDB handles different file types with specific extractors
            if input_type == InputType.EXCEL:
                result = await self.chromadb_service.add_from_excel(
                    agent_id=agent_id,
                    file_content=file_content,
                    filename=filename,
                )
            elif input_type == InputType.PDF:
                result = await self.chromadb_service.add_from_pdf(
                    agent_id=agent_id,
                    file_content=file_content,
                    filename=filename,
                )
            elif input_type == InputType.DOCX:
                result = await self.chromadb_service.add_from_docx(
                    agent_id=agent_id,
                    file_content=file_content,
                    filename=filename,
                )
            else:
                # Plain text files (TXT, MD, etc.)
                try:
                    text = file_content.decode("utf-8")
                except UnicodeDecodeError:
                    text = file_content.decode("latin-1")
                
                result = await self.chromadb_service.add_text(
                    agent_id=agent_id,
                    title=filename,
                    content=text,
                )
            
            return {
                "backend": "chromadb",
                "input_type": input_type.value,
                "filename": filename,
                "added": result.get("added", 1),
                "pages": result.get("pages"),
                "sections": result.get("sections"),
                "status": "success",
            }
        else:
            # RAGFlow handles document parsing
            # First get or create dataset for this agent
            dataset_id = await self.ragflow_service.get_or_create_agent_dataset(agent_id)
            
            result = await self.ragflow_service.upload_document_bytes(
                dataset_id=dataset_id,
                content=file_content,
                filename=filename,
            )
            
            # Extract document ID from response
            doc_data = result.get("data", [])
            doc_id = None
            if isinstance(doc_data, list) and len(doc_data) > 0:
                doc_id = doc_data[0].get("id")
            elif isinstance(doc_data, dict):
                doc_id = doc_data.get("id")
            
            # Auto-trigger parsing after upload
            if doc_id:
                try:
                    await self.ragflow_service.parse_document(dataset_id, [doc_id])
                    logger.info(f"Triggered parsing for document: {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to trigger parsing: {e}")
            
            return {
                "backend": "ragflow",
                "input_type": input_type.value,
                "filename": filename,
                "document_id": doc_id,
                "dataset_id": dataset_id,
                "status": "success",
                "parsing": "started",
            }
    
    async def import_google_sheets(
        self,
        agent_id: str,
        sheet_url: str,
    ) -> dict:
        """Import from Google Sheets (always uses ChromaDB).
        
        Args:
            agent_id: Agent identifier
            sheet_url: Google Sheets URL
            
        Returns:
            Result dict
        """
        await self.check_backends_health()
        
        if not self._chromadb_healthy:
            raise RuntimeError("ChromaDB not available for Google Sheets import")
        
        result = await self.chromadb_service.add_from_google_sheets(
            agent_id=agent_id,
            sheet_url=sheet_url,
        )
        
        return {
            "backend": "chromadb",
            "input_type": "google_sheets",
            "source": sheet_url,
            "added": result.get("added", 0),
            "status": "success",
        }
    
    async def search(
        self,
        agent_id: str,
        query: str,
        top_k: int = 5,
        search_all: bool = True,
    ) -> dict:
        """Search across all backends.
        
        Args:
            agent_id: Agent identifier
            query: Search query
            top_k: Number of results per backend
            search_all: Search all backends or just primary
            
        Returns:
            Combined results from all backends
        """
        await self.check_backends_health()
        
        results = {
            "query": query,
            "chunks": [],
            "backends_searched": [],
        }
        
        tasks = []
        
        # Search ChromaDB
        if self._chromadb_healthy:
            async def search_chromadb():
                try:
                    chunks = await self.chromadb_service.search(
                        agent_id=agent_id,
                        query=query,
                        top_k=top_k,
                    )
                    return [{"backend": "chromadb", **c} for c in chunks]
                except Exception as e:
                    logger.warning(f"ChromaDB search error: {e}")
                    return []
            
            tasks.append(("chromadb", search_chromadb()))
        
        # Search RAGFlow
        if self._ragflow_healthy and search_all:
            async def search_ragflow():
                try:
                    result = await self.ragflow_service.search(
                        agent_id=agent_id,
                        query=query,
                        top_k=top_k,
                    )
                    chunks = result.get("chunks", [])
                    return [{"backend": "ragflow", **c} for c in chunks]
                except Exception as e:
                    logger.warning(f"RAGFlow search error: {e}")
                    return []
            
            tasks.append(("ragflow", search_ragflow()))
        
        # Run searches in parallel
        if tasks:
            task_results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            
            for (backend_name, _), task_result in zip(tasks, task_results):
                if isinstance(task_result, Exception):
                    logger.warning(f"{backend_name} search failed: {task_result}")
                else:
                    results["chunks"].extend(task_result)
                    results["backends_searched"].append(backend_name)
        
        # Sort by score (highest first)
        results["chunks"].sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Limit to top_k overall
        results["chunks"] = results["chunks"][:top_k]
        results["total"] = len(results["chunks"])
        
        return results
    
    async def list_documents(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> dict:
        """List documents from all backends.
        
        Args:
            agent_id: Agent identifier
            limit: Max documents per backend
            
        Returns:
            Combined document list
        """
        await self.check_backends_health()
        
        documents = []
        
        # ChromaDB documents
        if self._chromadb_healthy:
            try:
                result = await self.chromadb_service.list_documents(
                    agent_id=agent_id,
                    limit=limit,
                )
                for doc in result.get("documents", []):
                    documents.append({
                        "backend": "chromadb",
                        "id": doc.get("id"),
                        "name": doc.get("title") or doc.get("source") or "Untitled",
                        "title": doc.get("title"),
                        "content": doc.get("content"),
                        "source": doc.get("source"),
                        "type": doc.get("type"),
                        "image_url": doc.get("image_url"),  # NEW
                    })
            except Exception as e:
                logger.warning(f"ChromaDB list error: {e}")
        
        # RAGFlow documents
        if self._ragflow_healthy:
            try:
                # Get or create dataset for this agent
                dataset_id = await self.ragflow_service.get_or_create_agent_dataset(agent_id)
                result = await self.ragflow_service.list_documents(dataset_id=dataset_id)
                # RAGFlow returns: {"code": 0, "data": {"docs": [...], "total": N}}
                data = result.get("data", {})
                docs_list = data.get("docs", []) if isinstance(data, dict) else []
                for doc in docs_list:
                    documents.append({
                        "backend": "ragflow",
                        "id": doc.get("id"),
                        "title": doc.get("name"),
                        "name": doc.get("name"),
                        "status": doc.get("status"),
                        "chunk_count": doc.get("chunk_count", 0),
                        "created_at": doc.get("create_time"),
                    })
            except Exception as e:
                logger.warning(f"RAGFlow list error: {e}")
        
        return {
            "documents": documents,
            "total": len(documents),
        }
    
    async def delete_document(
        self,
        agent_id: str,
        doc_id: str,
        backend: KnowledgeBackend | None = None,
    ) -> bool:
        """Delete a document.
        
        Args:
            agent_id: Agent identifier
            doc_id: Document ID
            backend: Specific backend (optional, tries both if not specified)
            
        Returns:
            True if deleted
        """
        await self.check_backends_health()
        
        if backend == KnowledgeBackend.CHROMADB or backend is None:
            if self._chromadb_healthy:
                try:
                    await self.chromadb_service.delete_document(agent_id, doc_id)
                    return True
                except Exception:
                    if backend == KnowledgeBackend.CHROMADB:
                        raise
        
        if backend == KnowledgeBackend.RAGFLOW or backend is None:
            if self._ragflow_healthy:
                try:
                    # Get dataset_id for this agent
                    dataset_id = await self.ragflow_service.get_or_create_agent_dataset(agent_id)
                    await self.ragflow_service.delete_document(dataset_id, doc_id)
                    logger.info(f"Deleted RAGFlow document: {doc_id}")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to delete RAGFlow document: {e}")
                    if backend == KnowledgeBackend.RAGFLOW:
                        raise
        
        return False
    
    async def get_stats(self, agent_id: str) -> dict:
        """Get statistics from all backends.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Combined stats
        """
        await self.check_backends_health()
        
        stats = {
            "agent_id": agent_id,
            "backends": {},
            "total_documents": 0,
        }
        
        if self._chromadb_healthy:
            try:
                chromadb_stats = await self.chromadb_service.get_stats(agent_id)
                stats["backends"]["chromadb"] = chromadb_stats
                stats["total_documents"] += chromadb_stats.get("document_count", 0)
            except Exception:
                stats["backends"]["chromadb"] = {"status": "error"}
        
        if self._ragflow_healthy:
            try:
                # RAGFlow stats from document list
                dataset_id = await self.ragflow_service.get_or_create_agent_dataset(agent_id)
                docs = await self.ragflow_service.list_documents(dataset_id=dataset_id)
                data = docs.get("data", {})
                count = len(data.get("docs", [])) if isinstance(data, dict) else 0
                stats["backends"]["ragflow"] = {"document_count": count}
                stats["total_documents"] += count
            except Exception:
                stats["backends"]["ragflow"] = {"status": "error"}
        
        return stats


# Singleton instance
_unified_service: UnifiedKnowledgeService | None = None


def get_unified_knowledge_service() -> UnifiedKnowledgeService:
    """Get singleton unified knowledge service."""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedKnowledgeService()
    return _unified_service
