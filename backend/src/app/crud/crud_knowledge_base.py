"""
CRUD operations for Knowledge Base entity.
"""

from typing import Optional, List, Tuple
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KnowledgeBase, AgentKnowledgeBase, KnowledgeEmbedding
from ..schemas.knowledge_base_schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate


class CRUDKnowledgeBase:
    """CRUD operations for KnowledgeBase."""

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:
        """Create a new knowledge base."""
        kb = KnowledgeBase(
            user_id=user_id,
            name=data.name,
            description=data.description,
            embedding_model=data.embedding_model,
        )
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        return kb

    async def get(
        self,
        db: AsyncSession,
        kb_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[KnowledgeBase]:
        """Get a knowledge base by ID, optionally filtered by user."""
        query = select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.is_deleted == False,
        )
        if user_id:
            query = query.where(KnowledgeBase.user_id == user_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Tuple[List[KnowledgeBase], int]:
        """List knowledge bases for a user with pagination."""
        # Base query
        query = select(KnowledgeBase).where(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.is_deleted == False,
        )
        
        # Search filter
        if search:
            query = query.where(KnowledgeBase.name.ilike(f"%{search}%"))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.order_by(KnowledgeBase.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        items = list(result.scalars().all())
        
        return items, total

    async def update(
        self,
        db: AsyncSession,
        kb: KnowledgeBase,
        data: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        """Update a knowledge base."""
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(kb, key, value)
        
        await db.commit()
        await db.refresh(kb)
        return kb

    async def delete(
        self,
        db: AsyncSession,
        kb: KnowledgeBase,
    ) -> None:
        """Soft delete a knowledge base."""
        kb.is_deleted = True
        await db.commit()

    async def get_entry_count(
        self,
        db: AsyncSession,
        kb_id: str,
    ) -> int:
        """Get count of entries in a knowledge base."""
        query = select(func.count()).where(
            KnowledgeEmbedding.knowledge_base_id == kb_id
        )
        result = await db.execute(query)
        return result.scalar() or 0

    async def get_agent_count(
        self,
        db: AsyncSession,
        kb_id: str,
    ) -> int:
        """Get count of agents linked to a knowledge base."""
        query = select(func.count()).where(
            AgentKnowledgeBase.knowledge_base_id == kb_id
        )
        result = await db.execute(query)
        return result.scalar() or 0

    async def get_linked_agent_ids(
        self,
        db: AsyncSession,
        kb_id: str,
    ) -> List[str]:
        """Get IDs of agents linked to a knowledge base."""
        query = select(AgentKnowledgeBase.agent_id).where(
            AgentKnowledgeBase.knowledge_base_id == kb_id
        )
        result = await db.execute(query)
        return [row[0] for row in result.all()]


# ============================================================================
# Agent-KB Linking Operations
# ============================================================================

class CRUDAgentKnowledgeBase:
    """CRUD operations for Agent-KnowledgeBase links."""

    async def get_kb_ids_for_agent(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> List[str]:
        """Get all knowledge base IDs linked to an agent."""
        query = select(AgentKnowledgeBase.knowledge_base_id).where(
            AgentKnowledgeBase.agent_id == agent_id
        )
        result = await db.execute(query)
        return [row[0] for row in result.all()]

    async def get_kbs_for_agent(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> List[KnowledgeBase]:
        """Get all knowledge bases linked to an agent."""
        query = (
            select(KnowledgeBase)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .where(
                AgentKnowledgeBase.agent_id == agent_id,
                KnowledgeBase.is_deleted == False,
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_agent_kbs(
        self,
        db: AsyncSession,
        agent_id: str,
        kb_ids: List[str],
    ) -> None:
        """Replace all knowledge bases for an agent."""
        # Delete existing links
        await db.execute(
            delete(AgentKnowledgeBase).where(
                AgentKnowledgeBase.agent_id == agent_id
            )
        )
        
        # Create new links
        for kb_id in kb_ids:
            link = AgentKnowledgeBase(
                agent_id=agent_id,
                knowledge_base_id=kb_id,
            )
            db.add(link)
        
        await db.commit()

    async def link_agent_to_kb(
        self,
        db: AsyncSession,
        agent_id: str,
        kb_id: str,
    ) -> AgentKnowledgeBase:
        """Link an agent to a knowledge base."""
        link = AgentKnowledgeBase(
            agent_id=agent_id,
            knowledge_base_id=kb_id,
        )
        db.add(link)
        await db.commit()
        return link

    async def unlink_agent_from_kb(
        self,
        db: AsyncSession,
        agent_id: str,
        kb_id: str,
    ) -> None:
        """Unlink an agent from a knowledge base."""
        await db.execute(
            delete(AgentKnowledgeBase).where(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.knowledge_base_id == kb_id,
            )
        )
        await db.commit()


# Singleton instances
crud_knowledge_base = CRUDKnowledgeBase()
crud_agent_kb = CRUDAgentKnowledgeBase()
