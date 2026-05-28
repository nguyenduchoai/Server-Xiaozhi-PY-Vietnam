"""
PgVector Knowledge Service - PostgreSQL native vector database for Knowledge Base.

Replaces ChromaDB (SQLite-based) with pgvector for better scalability.

Features:
- Native PostgreSQL vector storage
- HNSW index for fast similarity search
- Same API as ChromaDBService for easy migration
- Async operations

Usage:
    from app.services.pgvector_knowledge import get_pgvector_service
    
    service = get_pgvector_service()
    await service.add_documents(agent_id, documents)
    results = await service.search(agent_id, query, top_k=5)
"""

import asyncio
import json
import os
from typing import Any

from sqlalchemy import text

from ..core.db.database import local_session, async_engine
from ..core.logger import get_logger
from ..models.knowledge_embedding import KnowledgeEmbedding

logger = get_logger(__name__)

# Lazy import for embeddings
_embedding_model = None


def _get_embedding_model():
    """Get or create embedding model (lazy init)."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from openai import OpenAI
            jina_api_key = os.environ.get("JINA_API_KEY")
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            
            if jina_api_key:
                _embedding_model = ("jina", OpenAI(api_key=jina_api_key, base_url="https://api.jina.ai/v1"))
                logger.info("Using Jina V3 embeddings for pgvector (Hybrid RAG Ready)")
            elif openai_api_key:
                _embedding_model = ("openai", OpenAI(api_key=openai_api_key))
                logger.info("Using OpenAI embeddings for pgvector")
            else:
                # Fallback to sentence-transformers
                from sentence_transformers import SentenceTransformer
                _embedding_model = ("local", SentenceTransformer("all-MiniLM-L6-v2"))
                logger.info("Using local SentenceTransformer embeddings")
        except ImportError as e:
            logger.warning(f"No embedding model available: {e}")
            _embedding_model = ("none", None)
    return _embedding_model


async def get_embedding(text: str) -> list[float] | None:
    """Generate embedding for text and pad to exactly 1536 dimensions as required by Postgres Schema."""
    model_type, model = _get_embedding_model()
    
    embedding = None
    if model_type == "jina":
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.embeddings.create(
                    input=text,
                    model="jina-embeddings-v3"
                )
            )
            embedding = response.data[0].embedding
        except Exception as e:
            logger.error(f"Jina embedding error: {e}")
            return None
    elif model_type == "openai":
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
            )
            embedding = response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return None
    elif model_type == "local":
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.encode(text).tolist()
            )
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            return None
            
    # CRITICAL: Pad vector exactly to 1536 dimensions to match Vector(1536) in Postgres 
    # Zero-padding preserves identical cosine similarity! 
    # Jina is 1024, Local is 384, OpenAI is 1536.
    if embedding is not None:
        if len(embedding) < 1536:
            embedding.extend([0.0] * (1536 - len(embedding)))
        elif len(embedding) > 1536:
            embedding = embedding[:1536] 
            
    return embedding


class PgVectorKnowledgeService:
    """PostgreSQL pgvector-based knowledge service.
    
    Provides semantic search over agent knowledge bases using
    PostgreSQL's native vector extension.
    """
    
    def __init__(self):
        """Initialize service."""
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure pgvector extension and indexes are created."""
        if self._initialized:
            return
        
        async with async_engine.begin() as conn:
            # Create pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Create HNSW index for fast similarity search (if not exists)
            # HNSW is faster than IVFFlat for recall
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_knowledge_embedding_hnsw 
                ON knowledge_embeddings 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            
            # Create GIN index for Hybrid Full-Text Search (BM25 equivalent)
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_knowledge_embedding_fts 
                ON knowledge_embeddings 
                USING gin (to_tsvector('simple', content))
            """))
            
            logger.info("pgvector + FTS extension and indexes initialized")
        
        self._initialized = True
    
    async def add_documents(
        self,
        agent_id: str,
        documents: list[dict[str, Any]],
        doc_type: str = "text",
        source: str = "manual",
    ) -> dict:
        """Add documents to agent's knowledge base.
        
        Args:
            agent_id: Agent ID
            documents: List of dicts with 'content' and optionally 'metadata'
            doc_type: Document type
            source: Source of documents
            
        Returns:
            Dict with count of added documents and IDs
        """
        await self._ensure_initialized()
        
        added_ids = []
        
        async with local_session() as session:
            for doc in documents:
                content = doc.get("content", "")
                if not content:
                    continue
                
                # Generate embedding
                embedding = await get_embedding(content)
                
                # Create record
                knowledge = KnowledgeEmbedding(
                    agent_id=agent_id,
                    content=content,
                    embedding=embedding,
                    metadata_json=json.dumps(doc.get("metadata", {})),
                    doc_type=doc_type,
                    source=source,
                )
                
                session.add(knowledge)
                added_ids.append(knowledge.id)
            
            await session.commit()
        
        logger.info(f"Added {len(added_ids)} documents for agent {agent_id}")
        
        return {
            "success": True,
            "count": len(added_ids),
            "ids": added_ids,
        }
    
    async def search(
        self,
        agent_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
        kb_ids: list[str] | None = None,
    ) -> list[dict]:
        """Semantic search in agent's knowledge base.
        
        Args:
            agent_id: Agent ID (used when kb_ids is None)
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)
            kb_ids: Optional list of KnowledgeBase IDs to search across
                    When provided, searches across these KBs instead of by agent_id
        
        Returns:
            List of matching documents with similarity scores
        """
        await self._ensure_initialized()
        
        # Generate query embedding
        query_embedding = await get_embedding(query)
        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []
        
        # Convert to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        async with local_session() as session:
            # Build WHERE clause based on search mode
            if kb_ids:
                # Multi-KB search: search across specific knowledge bases
                placeholders = ", ".join(f":kb_{i}" for i in range(len(kb_ids)))
                where_clause = f"knowledge_base_id IN ({placeholders})"
                params = {f"kb_{i}": kb_id for i, kb_id in enumerate(kb_ids)}
            else:
                # Legacy mode: search by agent_id
                where_clause = "agent_id = :agent_id"
                params = {"agent_id": agent_id}
            
            params["query_embedding"] = embedding_str
            params["limit"] = top_k
            params["query"] = query  # For Hybrid BM25 Keyword Search
            
            # Execute Hybrid Search (BM25 + Semantic Search) using Reciprocal Rank Fusion (RRF)
            result = await session.execute(
                text(f"""
                    WITH vector_search AS (
                        SELECT id, 1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity,
                               ROW_NUMBER() OVER(ORDER BY embedding <=> CAST(:query_embedding AS vector)) as rank
                        FROM knowledge_embeddings
                        WHERE {{where_clause}} AND embedding IS NOT NULL
                        LIMIT :limit * 2
                    ),
                    keyword_search AS (
                        SELECT id,
                               ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :query)) as kw_score,
                               ROW_NUMBER() OVER(ORDER BY ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :query)) DESC) as rank
                        FROM knowledge_embeddings
                        WHERE {{where_clause}} AND to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
                        LIMIT :limit * 2
                    )
                    SELECT 
                        k.id, k.content, k.metadata_json, k.doc_type, k.source, k.knowledge_base_id, k.created_at,
                        COALESCE(v.similarity, 0) as similarity,
                        COALESCE(kws.kw_score, 0) as kw_score,
                        COALESCE(v.rank, 100) as vector_rank,
                        COALESCE(kws.rank, 100) as kw_rank,
                        -- RRF Formulation: score = 1/(k + rank_1) + 1/(k + rank_2)
                        (COALESCE(1.0 / (60 + v.rank), 0.0) + COALESCE(1.0 / (60 + kws.rank), 0.0)) as rrf_score
                    FROM knowledge_embeddings k
                    LEFT JOIN vector_search v ON k.id = v.id
                    LEFT JOIN keyword_search kws ON k.id = kws.id
                    WHERE (v.id IS NOT NULL OR kws.id IS NOT NULL)
                    ORDER BY rrf_score DESC
                    LIMIT :limit
                """.replace("{where_clause}", where_clause)),
                params,
            )
            
            rows = result.fetchall()
        
        # Filter and format results
        results = []
        for row in rows:
            # We relax absolute similarity threshold due to RRF incorporating keyword ranks
            # But we still extract the vector similarity to display
            similarity = float(row.similarity) if row.similarity else 0
            results.append({
                "id": str(row.id),
                "content": row.content,
                "metadata": json.loads(row.metadata_json) if row.metadata_json else {},
                "doc_type": row.doc_type,
                "source": row.source,
                "knowledge_base_id": str(row.knowledge_base_id) if row.knowledge_base_id else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "similarity": round(similarity, 4),
                "rrf_score": float(row.rrf_score),
            })
        
        search_mode = f"hybrid_kb_ids={len(kb_ids)}" if kb_ids else f"hybrid_agent={agent_id}"
        logger.debug(f"Hybrid Search '{query}' returned {len(results)} results ({search_mode})")
        return results
    
    async def get_all_documents(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Get all documents for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Max documents to return
            offset: Pagination offset
            
        Returns:
            Dict with documents list and total count
        """
        await self._ensure_initialized()
        
        async with local_session() as session:
            # Get total count
            count_result = await session.execute(
                text("SELECT COUNT(*) FROM knowledge_embeddings WHERE agent_id = :agent_id"),
                {"agent_id": agent_id}
            )
            total = count_result.scalar() or 0
            
            # Get documents
            result = await session.execute(
                text("""
                    SELECT id, content, metadata_json, doc_type, source, created_at
                    FROM knowledge_embeddings
                    WHERE agent_id = :agent_id
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"agent_id": agent_id, "limit": limit, "offset": offset}
            )
            
            documents = []
            for row in result.fetchall():
                documents.append({
                    "id": str(row.id),
                    "content": row.content,
                    "metadata": json.loads(row.metadata_json) if row.metadata_json else {},
                    "doc_type": row.doc_type,
                    "source": row.source,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
        
        return {
            "total": total,
            "documents": documents,
            "limit": limit,
            "offset": offset,
        }
    
    async def delete_document(self, agent_id: str, doc_id: str) -> bool:
        """Delete a document by ID.
        
        Args:
            agent_id: Agent ID (for ownership verification)
            doc_id: Document ID
            
        Returns:
            True if deleted, False if not found
        """
        async with local_session() as session:
            result = await session.execute(
                text("""
                    DELETE FROM knowledge_embeddings 
                    WHERE id = :doc_id AND agent_id = :agent_id
                    RETURNING id
                """),
                {"doc_id": doc_id, "agent_id": agent_id}
            )
            await session.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted document {doc_id} from agent {agent_id}")
            return deleted
    
    async def delete_all(self, agent_id: str) -> int:
        """Delete all documents for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Number of deleted documents
        """
        async with local_session() as session:
            result = await session.execute(
                text("DELETE FROM knowledge_embeddings WHERE agent_id = :agent_id"),
                {"agent_id": agent_id}
            )
            await session.commit()
            
            count = result.rowcount
            logger.info(f"Deleted {count} documents for agent {agent_id}")
            return count
    
    async def get_stats(self, agent_id: str = None) -> dict:
        """Get statistics for knowledge base.
        
        Args:
            agent_id: Optional agent ID filter
            
        Returns:
            Stats dict with counts
        """
        async with local_session() as session:
            if agent_id:
                result = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded,
                            COUNT(DISTINCT doc_type) as doc_types
                        FROM knowledge_embeddings
                        WHERE agent_id = :agent_id
                    """),
                    {"agent_id": agent_id}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded,
                            COUNT(DISTINCT agent_id) as agents,
                            COUNT(DISTINCT doc_type) as doc_types
                        FROM knowledge_embeddings
                    """)
                )
            
            row = result.fetchone()
            
            return {
                "total_documents": row.total if row else 0,
                "embedded_documents": row.embedded if row else 0,
                "agents": getattr(row, "agents", None) if row else None,
                "doc_types": row.doc_types if row else 0,
            }


# Singleton instance
_pgvector_service: PgVectorKnowledgeService | None = None


def get_pgvector_service() -> PgVectorKnowledgeService:
    """Get singleton PgVector Knowledge service."""
    global _pgvector_service
    if _pgvector_service is None:
        _pgvector_service = PgVectorKnowledgeService()
    return _pgvector_service
