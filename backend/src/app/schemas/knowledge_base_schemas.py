"""
Knowledge Base Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Knowledge Base Schemas
# ============================================================================

class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a new knowledge base."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: str = Field(default="bkai-vietnamese-bi-encoder")


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating an existing knowledge base."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    embedding_model: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    """Response schema for a knowledge base."""
    id: str
    name: str
    description: Optional[str] = None
    ragflow_dataset_id: Optional[str] = None
    embedding_model: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseWithStats(KnowledgeBaseResponse):
    """Knowledge base with entry and agent counts."""
    entry_count: int = 0
    agent_count: int = 0


class KnowledgeBaseListResponse(BaseModel):
    """Paginated list of knowledge bases."""
    items: List[KnowledgeBaseWithStats]
    total: int
    page: int
    page_size: int


# ============================================================================
# Knowledge Entry Schemas
# ============================================================================

class KnowledgeEntryCreate(BaseModel):
    """Schema for creating a knowledge entry."""
    content: str = Field(..., min_length=1)
    doc_type: str = Field(default="text")
    source: str = Field(default="manual")
    metadata: Optional[dict] = None


class KnowledgeEntryResponse(BaseModel):
    """Response schema for a knowledge entry."""
    id: str
    content: str
    doc_type: str
    source: str
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeEntryListResponse(BaseModel):
    """Paginated list of knowledge entries."""
    items: List[KnowledgeEntryResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Agent-KB Linking Schemas
# ============================================================================

class AgentKnowledgeBasesUpdate(BaseModel):
    """Schema for updating agent's linked knowledge bases."""
    knowledge_base_ids: List[str]


class AgentKnowledgeBaseLink(BaseModel):
    """Simple KB info for agent's linked KBs."""
    id: str
    name: str

    model_config = {"from_attributes": True}


class AgentKnowledgeBasesResponse(BaseModel):
    """Response for agent's linked knowledge bases."""
    knowledge_bases: List[AgentKnowledgeBaseLink]


# ============================================================================
# Search Schemas
# ============================================================================

class KnowledgeSearchRequest(BaseModel):
    """Request for searching knowledge."""
    query: str = Field(..., min_length=1)
    agent_id: str
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    """Single search result."""
    content: str
    score: float
    source: str
    knowledge_base_id: Optional[str] = None
    knowledge_base_name: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    """Search results response."""
    results: List[KnowledgeSearchResult]
