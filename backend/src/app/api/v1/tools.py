"""Tools API router.

Exposes endpoints to:
- Get available tools with schemas for UI rendering
- CRUD operations for user tool configurations
"""

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.base import PaginatedResponse, SuccessResponse

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.logger import get_logger
from ...crud.crud_user_tool import crud_user_tool
from ...schemas.user_tool import (
    UserToolCreate,
    UserToolCreateInternal,
    UserToolUpdate,
    UserToolRead,
)
from ...ai.providers.tools.tool_schema_registry import (
    get_tool_schema,
    get_all_tool_schemas,
    get_all_categories,
    validate_tool_config,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


# ========== Helper Functions ==========


def mask_secrets(config: dict, tool_name: str) -> dict:
    """
    Mask sensitive fields in tool config for display.
    Fields like api_key, password, secret are masked.
    """
    if not config:
        return config
    
    sensitive_keys = {"api_key", "password", "secret", "token", "key", "credentials"}
    masked = {}
    
    for k, v in config.items():
        k_lower = k.lower()
        if any(sk in k_lower for sk in sensitive_keys) and isinstance(v, str) and v:
            # Mask all but first 4 and last 4 chars
            if len(v) > 8:
                masked[k] = v[:4] + "*" * (len(v) - 8) + v[-4:]
            else:
                masked[k] = "*" * len(v)
        else:
            masked[k] = v
    
    return masked


async def verify_tool_ownership(
    db: AsyncSession, tool_id: str, user_id: str
) -> UserToolRead:
    """Verify that tool belongs to user and return it."""
    tool = await crud_user_tool.get(
        db=db,
        id=tool_id,
        user_id=user_id,
        is_deleted=False,
        schema_to_select=UserToolRead,
        return_as_model=True,
    )
    
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool configuration '{tool_id}' not found",
        )
    
    return tool


# ========== API Endpoints ==========


@router.get("/available")
async def get_available_tools(
    current_user: Annotated[dict, Depends(get_current_user)],
    q: Annotated[
        str | None, Query(description="Search query for function name or description")
    ] = None,
) -> dict[str, Any]:
    """
    Get all available system functions with metadata.

    Returns list of functions from the system registry that can be used in agents.
    Supports optional filtering by name or description via `q` parameter.

    **Response Format:**
    - name: Unique function identifier
    - display_name: Human-readable function name
    - description: What the function does
    - category: Function category
    - source_type: Type of tool source (server_plugin, server_mcp, device_mcp)
    - parameters: JSON schema for function parameters
    - requires_config: Whether tool needs configuration
    """
    all_schemas = get_all_tool_schemas()
    tools = []

    for name, schema in all_schemas.items():
        # Skip if query filter doesn't match
        if q:
            q_lower = q.lower()
            if not (
                name.lower().find(q_lower) != -1
                or schema.display_name.lower().find(q_lower) != -1
                or schema.description.lower().find(q_lower) != -1
            ):
                continue

        tool_entry = {
            "name": schema.name,
            "display_name": schema.display_name,
            "description": schema.description,
            "category": schema.category.value,
            "source_type": "server_plugin",
            "parameters": schema.function_schema or {},
            "requires_config": schema.requires_config,
            "fields": [
                {
                    "name": f.name,
                    "display_name": f.display_name,
                    "field_type": f.field_type.value,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "options": f.options,
                }
                for f in schema.fields
            ] if schema.fields else [],
        }
        tools.append(tool_entry)

    # Sort by name for consistency
    tools.sort(key=lambda x: x["name"])

    return {
        "success": True,
        "data": tools,
        "total": len(tools),
    }


@router.get("/options")
async def get_tool_options(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get tool options for MULTISELECT dropdown in Intent Provider config.

    Returns both system tools and user's tool configs.
    """
    # Get system tools from registry
    all_schemas = get_all_tool_schemas()
    options = [
        {
            "value": schema.name,
            "label": schema.display_name,
            "description": schema.description,
            "category": schema.category.value,
            "source_type": "server_plugin",
        }
        for schema in all_schemas.values()
    ]

    # Sort by label
    options.sort(key=lambda x: x["label"])

    return {
        "success": True,
        "data": options,
        "total": len(options),
    }


@router.get("/categories")
async def get_tool_categories(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get all available tool categories."""
    categories = get_all_categories()
    return {
        "success": True,
        "data": [{"value": c.value, "label": c.value.title()} for c in categories],
    }


@router.get("/schemas/{tool_name}")
async def get_tool_schema_endpoint(
    tool_name: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get schema for a specific tool.

    Returns tool schema with fields for configuration UI.
    """
    schema = get_tool_schema(tool_name)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"Tool schema for '{tool_name}' not found",
        )

    return {
        "success": True,
        "data": {
            "name": schema.name,
            "display_name": schema.display_name,
            "description": schema.description,
            "category": schema.category.value,
            "requires_config": schema.requires_config,
            "fields": [
                {
                    "name": f.name,
                    "display_name": f.display_name,
                    "field_type": f.field_type.value,
                    "description": f.description,
                    "required": f.required,
                    "default": f.default,
                    "options": f.options,
                    "validation": f.validation,
                }
                for f in schema.fields
            ] if schema.fields else [],
            "function_schema": schema.function_schema,
        },
    }


# ========== User Tool CRUD Endpoints ==========


@router.get("/configs", response_model=PaginatedResponse[UserToolRead])
async def list_user_tools(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tool_name: Annotated[str | None, Query(description="Filter by tool name")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, Any]:
    """
    List user's tool configurations with pagination.

    Optionally filter by tool_name to get all configs for a specific tool.
    """
    user_id = current_user["id"]
    offset = (page - 1) * page_size

    # Build filters
    filters: dict[str, Any] = {
        "user_id": user_id,
        "is_deleted": False,
    }
    if tool_name:
        filters["tool_name"] = tool_name

    result = await crud_user_tool.get_multi(
        db=db,
        offset=offset,
        limit=page_size,
        schema_to_select=UserToolRead,
        return_as_model=True,
        **filters,
    )

    tools = result.get("data", [])
    total = result.get("total_count", 0)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Mask secrets
    data = []
    for tool in tools:
        tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else dict(tool)
        tool_dict["config"] = mask_secrets(tool_dict["config"], tool_dict["tool_name"])
        data.append(tool_dict)

    return {
        "success": True,
        "message": "Success",
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/configs", response_model=SuccessResponse[UserToolRead], status_code=201)
async def create_user_tool(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tool: UserToolCreate,
) -> dict[str, Any]:
    """
    Create a new tool configuration.

    Tool name must exist in the tool registry.
    Config is validated against the tool's schema.
    """
    user_id = current_user["id"]

    # Validate tool_name exists in registry
    schema = get_tool_schema(tool.tool_name)
    if not schema:
        raise HTTPException(
            status_code=400,
            detail=f"Tool '{tool.tool_name}' not found in registry",
        )

    # Validate config if tool requires it
    if schema.requires_config and tool.config:
        is_valid, normalized, errors = validate_tool_config(tool.tool_name, tool.config)
        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})
        tool.config = normalized

    # Create tool config
    tool_internal = UserToolCreateInternal(
        user_id=user_id,
        tool_name=tool.tool_name,
        name=tool.name,
        description=tool.description,
        config=tool.config or {},
        is_active=tool.is_active,
    )

    created = await crud_user_tool.create(db=db, object=tool_internal)

    # Convert to response
    created_dict = {
        "id": created.id,
        "user_id": created.user_id,
        "tool_name": created.tool_name,
        "name": created.name,
        "description": created.description,
        "config": mask_secrets(created.config, created.tool_name),
        "is_active": created.is_active,
        "created_at": created.created_at,
        "updated_at": created.updated_at,
        "is_deleted": created.is_deleted,
    }

    return {
        "success": True,
        "message": "Tool configuration created successfully",
        "data": created_dict,
    }


@router.get("/configs/{tool_id}", response_model=SuccessResponse[UserToolRead])
async def get_user_tool(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tool_id: str,
) -> dict[str, Any]:
    """
    Get a specific tool configuration by ID.

    Only returns tool if it belongs to the current user.
    """
    user_id = current_user["id"]
    tool = await verify_tool_ownership(db, tool_id, user_id)

    tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else dict(tool)
    tool_dict["config"] = mask_secrets(tool_dict["config"], tool_dict["tool_name"])

    return {
        "success": True,
        "message": "Success",
        "data": tool_dict,
    }


@router.put("/configs/{tool_id}", response_model=SuccessResponse[UserToolRead])
async def update_user_tool(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tool_id: str,
    update_data: UserToolUpdate,
) -> dict[str, Any]:
    """
    Update a tool configuration.

    If config is provided, it's validated against the tool's schema.
    """
    user_id = current_user["id"]
    existing = await verify_tool_ownership(db, tool_id, user_id)

    existing_dict = (
        existing.model_dump() if hasattr(existing, "model_dump") else dict(existing)
    )

    # Validate config if provided
    if update_data.config is not None:
        is_valid, normalized, errors = validate_tool_config(
            existing_dict["tool_name"], update_data.config
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})
        update_data.config = normalized

    # Build update dict
    update_dict: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if update_data.name is not None:
        update_dict["name"] = update_data.name
    if update_data.description is not None:
        update_dict["description"] = update_data.description
    if update_data.config is not None:
        update_dict["config"] = update_data.config
    if update_data.is_active is not None:
        update_dict["is_active"] = update_data.is_active

    await crud_user_tool.update(
        db=db,
        object=update_dict,
        id=tool_id,
        user_id=user_id,
    )

    # Get updated tool
    updated = await verify_tool_ownership(db, tool_id, user_id)
    result = updated.model_dump() if hasattr(updated, "model_dump") else dict(updated)
    result["config"] = mask_secrets(result["config"], result["tool_name"])

    return {
        "success": True,
        "message": "Tool configuration updated successfully",
        "data": result,
    }


@router.delete("/configs/{tool_id}", status_code=204)
async def delete_user_tool(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    tool_id: str,
) -> None:
    """
    Delete a tool configuration (soft delete).
    """
    user_id = current_user["id"]
    await verify_tool_ownership(db, tool_id, user_id)

    await crud_user_tool.delete(db=db, id=tool_id)
