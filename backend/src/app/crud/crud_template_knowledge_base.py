"""
CRUD operations for TemplateKnowledgeBase junction table.

Manages the many-to-many relationship between Templates and Knowledge Bases.
"""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.template_knowledge_base import TemplateKnowledgeBase
from ..models.knowledge_base import KnowledgeBase


async def get_knowledge_bases_for_template(
    db: AsyncSession, 
    template_id: str
) -> list[KnowledgeBase]:
    """Get all knowledge bases linked to a template."""
    query = (
        select(KnowledgeBase)
        .join(TemplateKnowledgeBase, TemplateKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
        .where(TemplateKnowledgeBase.template_id == template_id)
        .where(KnowledgeBase.is_deleted == False)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_knowledge_base_ids_for_template(
    db: AsyncSession, 
    template_id: str
) -> list[str]:
    """Get all knowledge base IDs linked to a template."""
    query = (
        select(TemplateKnowledgeBase.knowledge_base_id)
        .where(TemplateKnowledgeBase.template_id == template_id)
    )
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def add_knowledge_base_to_template(
    db: AsyncSession,
    template_id: str,
    knowledge_base_id: str
) -> TemplateKnowledgeBase:
    """Add a knowledge base to a template."""
    link = TemplateKnowledgeBase(
        template_id=template_id,
        knowledge_base_id=knowledge_base_id
    )
    db.add(link)
    await db.flush()
    return link


async def remove_knowledge_base_from_template(
    db: AsyncSession,
    template_id: str,
    knowledge_base_id: str
) -> bool:
    """Remove a knowledge base from a template."""
    query = delete(TemplateKnowledgeBase).where(
        TemplateKnowledgeBase.template_id == template_id,
        TemplateKnowledgeBase.knowledge_base_id == knowledge_base_id
    )
    result = await db.execute(query)
    return result.rowcount > 0


async def set_knowledge_bases_for_template(
    db: AsyncSession,
    template_id: str,
    knowledge_base_ids: list[str]
) -> list[str]:
    """
    Set the knowledge bases for a template (replaces existing).
    
    Returns the list of KB IDs that were set.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Deduplicate the list to prevent duplicate key errors
    unique_kb_ids = list(set(knowledge_base_ids)) if knowledge_base_ids else []
    
    logger.info(f"Setting KBs for template {template_id}: input={knowledge_base_ids}, unique={unique_kb_ids}")
    
    # Remove all existing links
    await db.execute(
        delete(TemplateKnowledgeBase).where(
            TemplateKnowledgeBase.template_id == template_id
        )
    )
    
    # Add new links (only unique ones)
    for kb_id in unique_kb_ids:
        link = TemplateKnowledgeBase(
            template_id=template_id,
            knowledge_base_id=kb_id
        )
        db.add(link)
        logger.debug(f"Added KB link: template={template_id}, kb={kb_id}")
    
    await db.flush()
    logger.info(f"Flushed {len(unique_kb_ids)} KB links for template {template_id}")
    return unique_kb_ids


async def get_templates_for_knowledge_base(
    db: AsyncSession,
    knowledge_base_id: str
) -> list[str]:
    """Get all template IDs that use a specific knowledge base."""
    query = (
        select(TemplateKnowledgeBase.template_id)
        .where(TemplateKnowledgeBase.knowledge_base_id == knowledge_base_id)
    )
    result = await db.execute(query)
    return [row[0] for row in result.all()]
