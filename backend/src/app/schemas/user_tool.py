"""
UserTool schemas for API request/response.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserToolBase(BaseModel):
    """Base schema for UserTool."""

    tool_name: str = Field(..., description="System tool name from registry")
    name: str = Field(..., description="User-friendly display name")
    description: str | None = Field(None, description="Optional description")
    config: dict[str, Any] = Field(default_factory=dict, description="Tool configuration")
    is_active: bool = Field(True, description="Whether this tool config is active")


class UserToolCreate(UserToolBase):
    """Schema for creating a new UserTool."""

    pass


class UserToolCreateInternal(UserToolBase):
    """Internal schema with user_id."""

    user_id: str


class UserToolUpdate(BaseModel):
    """Schema for updating UserTool."""

    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class UserToolRead(UserToolBase):
    """Schema for reading UserTool."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    class Config:
        from_attributes = True


class UserToolListResponse(BaseModel):
    """Response for listing UserTools."""

    success: bool = True
    data: list[UserToolRead]
    total: int
    page: int
    page_size: int
    total_pages: int
