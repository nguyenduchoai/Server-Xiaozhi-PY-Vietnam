"""Template API router.

Exposes endpoints to list/create/update/delete templates, manage template assignments
to agents, and list agents using a template.

Templates are now independent resources that can be shared across multiple agents.
"""

from datetime import datetime, timezone as dt_timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.base import PaginatedResponse, SuccessResponse

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import (
    ForbiddenException,
    NotFoundException,
)
from ...core.logger import get_logger
from ...crud.crud_template import crud_template
from ...crud.crud_agent_template_assignment import crud_assignment
from ...crud.crud_agent import crud_agent
from ...crud.crud_provider import crud_provider
from ...crud import crud_template_knowledge_base
from ...services.quota_service import QuotaService
from ...schemas.template import (
    TemplateCreate,
    TemplateCreateInternal,
    TemplateRead,
    TemplateUpdate,
    TemplateUpdateInternal,
    TemplateWithProvidersRead,
    ProviderInfo,
)
from ...schemas.agent import AgentRead
from ...schemas.agent_template_assignment import AssignmentRead
from ...ai.module_factory import parse_provider_reference
from ...config import load_config

logger = get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


# ========== Helper Functions ==========


# Provider categories mapping for validation
PROVIDER_CATEGORIES = {
    "ASR": "ASR",
    "LLM": "LLM",
    "VLLM": "VLLM",
    "TTS": "TTS",
    "Memory": "Memory",
    "Intent": "Intent",
}


async def validate_provider_references(
    db: AsyncSession,
    user_id: str,
    provider_fields: dict[str, str | None],
) -> list[str]:
    """
    Validate provider references (config:{name} or db:{uuid} format).

    Args:
        db: AsyncSession
        user_id: UUID of user
        provider_fields: Dict of {field_name: provider_reference} to validate

    Returns:
        list[str]: List of validation errors (empty if all valid)
    """
    errors = []
    config = None  # Lazy load

    for field_name, reference in provider_fields.items():
        if reference is None:
            continue

        parsed = parse_provider_reference(reference)
        if parsed is None:
            errors.append(
                f"Invalid provider reference format for {field_name}: {reference}"
            )
            continue

        source, value = parsed
        expected_category = PROVIDER_CATEGORIES.get(field_name)

        if source == "config":
            # Validate config provider exists
            if config is None:
                try:
                    config = load_config()
                except Exception as e:
                    errors.append(f"Failed to load config: {str(e)}")
                    continue

            if expected_category not in config:
                errors.append(f"Category '{expected_category}' not found in config")
            elif value not in config[expected_category]:
                errors.append(
                    f"Provider '{value}' not found in config.yml for {field_name}"
                )

        elif source == "db":
            # Validate db provider exists and belongs to user OR is public
            from sqlalchemy import select, or_
            from ...models.provider import Provider as ProviderModel
            
            stmt = select(ProviderModel).where(
                ProviderModel.id == value,
                ProviderModel.is_deleted == False,
                ProviderModel.is_active == True,
                or_(
                    ProviderModel.user_id == user_id,
                    ProviderModel.is_public == True
                )
            )
            result = await db.execute(stmt)
            provider = result.scalar_one_or_none()

            if not provider:
                errors.append(
                    f"Provider '{value}' for {field_name} not found or not accessible"
                )
                continue

            # Validate provider category matches field
            if expected_category and provider.category != expected_category:
                errors.append(
                    f"Provider '{value}' has category '{provider.category}' "
                    f"but {field_name} requires '{expected_category}'"
                )

    return errors


async def _enrich_template_with_providers(
    db: AsyncSession,
    template: TemplateRead | dict,
) -> dict:
    """
    Enrich a single template with full provider info.

    Args:
        db: AsyncSession
        template: TemplateRead model or dict

    Returns:
        dict: Template with provider info instead of just references
    """
    provider_fields = ["ASR", "LLM", "VLLM", "TTS", "Memory", "Intent"]
    config = None

    template_dict = (
        template.model_dump() if hasattr(template, "model_dump") else dict(template)
    )

    for field in provider_fields:
        reference = template_dict.get(field)
        if not reference:
            template_dict[field] = None
            continue

        parsed = parse_provider_reference(reference)
        if not parsed:
            template_dict[field] = None
            continue

        source, value = parsed

        if source == "db":
            provider = await crud_provider.get(db=db, id=value, is_deleted=False)
            if provider:
                template_dict[field] = ProviderInfo(
                    reference=f"db:{provider.get('id')}",
                    id=provider.get("id"),
                    name=provider.get("name"),
                    type=provider.get("type"),
                    source="user",
                )
            else:
                template_dict[field] = None
        elif source == "config":
            if config is None:
                try:
                    config = load_config()
                except Exception:
                    config = {}

            category = PROVIDER_CATEGORIES.get(field, field)
            if category in config and value in config[category]:
                cfg = config[category][value]
                provider_type = (
                    cfg.get("type", value) if isinstance(cfg, dict) else value
                )
                template_dict[field] = ProviderInfo(
                    reference=f"config:{value}",
                    name=value,
                    type=provider_type,
                    source="default",
                )
            else:
                template_dict[field] = None

    return template_dict


async def _enrich_templates_with_providers(
    db: AsyncSession,
    templates: list,
) -> list[dict]:
    """
    Enrich multiple templates with full provider info.

    Args:
        db: AsyncSession
        templates: List of TemplateRead models or dicts

    Returns:
        list[dict]: Templates with provider info
    """
    if not templates:
        return []

    enriched = []
    for template in templates:
        enriched_template = await _enrich_template_with_providers(db, template)
        enriched.append(enriched_template)

    return enriched


# ========== Template CRUD Endpoints ==========


@router.get("", response_model=PaginatedResponse[TemplateWithProvidersRead])
async def list_templates(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    include_public: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """
    Return a paginated list of templates owned by the current user.

    Optionally include public templates from other users.

    Query Parameters:
    - page: int (1-based, default=1)
    - page_size: int (1-100, default=10)
    - include_public: bool (default=False) - Include public templates

    Returns:
        PaginatedResponse[TemplateWithProvidersRead]: Structured pagination payload
    """
    try:
        logger.debug(
            f"Listing templates for user {current_user['id']}, "
            f"include_public={include_public}"
        )

        templates_data = await crud_template.get_templates_for_user(
            db=db,
            user_id=current_user["id"],
            offset=(page - 1) * page_size,
            limit=page_size,
            include_public=include_public,
        )

        total = templates_data.get("total_count", 0)
        total_pages = (total + page_size - 1) // page_size

        # Enrich templates with provider info
        enriched_templates = await _enrich_templates_with_providers(
            db, templates_data["data"]
        )

        return PaginatedResponse(
            success=True,
            message="Success",
            data=enriched_templates,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=TemplateWithProvidersRead, status_code=201)
async def create_template(
    template: TemplateCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Create a new template for the authenticated user.

    Templates are independent and can be assigned to multiple agents.

    Body:
        TemplateCreate: Template content with provider references

    Returns:
        TemplateWithProvidersRead: Newly created template with provider info
    """
    try:
        logger.info(
            f"Creating template '{template.name}' for user {current_user['id']}"
        )

        # Check template quota using QuotaService
        quota_service = QuotaService(db)
        can_create, message = await quota_service.can_create_template(current_user["id"])
        if not can_create:
            raise HTTPException(status_code=403, detail=message)

        # Validate provider references
        provider_fields = {
            "ASR": template.ASR,
            "LLM": template.LLM,
            "VLLM": template.VLLM,
            "TTS": template.TTS,
            "Memory": template.Memory,
            "Intent": template.Intent,
        }
        validation_errors = await validate_provider_references(
            db=db,
            user_id=current_user["id"],
            provider_fields=provider_fields,
        )
        if validation_errors:
            raise HTTPException(status_code=400, detail="; ".join(validation_errors))

        # Create template
        template_create_internal = TemplateCreateInternal(
            **template.model_dump(),
            user_id=current_user["id"],
        )

        created_template = await crud_template.create(
            db=db,
            object=template_create_internal,
            schema_to_select=TemplateRead,
            return_as_model=True,
        )

        # Handle knowledge_base_ids if provided
        if template.knowledge_base_ids:
            await crud_template_knowledge_base.set_knowledge_bases_for_template(
                db=db,
                template_id=created_template.id,
                knowledge_base_ids=template.knowledge_base_ids,
            )

        logger.info(f"Template {created_template.id} created successfully")

        # Enrich with provider info and KB IDs
        enriched = await _enrich_template_with_providers(db, created_template)
        enriched["knowledge_base_ids"] = template.knowledge_base_ids or []
        return enriched

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}", response_model=TemplateWithProvidersRead)
async def get_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Get template details by ID.

    User can access templates they own or public templates.

    Returns:
        TemplateWithProvidersRead: Template with provider info

    Raises:
        NotFoundException: If template not found
        ForbiddenException: If user cannot access template
    """
    try:
        logger.debug(f"Fetching template {template_id}")

        template = await crud_template.get(
            db=db,
            id=template_id,
            is_deleted=False,
            schema_to_select=TemplateRead,
            return_as_model=True,
        )

        if not template:
            raise NotFoundException(f"Template {template_id} not found")

        # Check access
        can_access = await crud_template.can_access_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_access:
            raise ForbiddenException("You do not have access to this template")

        # Enrich with provider info
        enriched = await _enrich_template_with_providers(db, template)
        
        # Add knowledge_base_ids
        kb_ids = await crud_template_knowledge_base.get_knowledge_base_ids_for_template(
            db=db,
            template_id=template_id,
        )
        enriched["knowledge_base_ids"] = kb_ids
        
        # Add course_ids
        from sqlalchemy import select
        from ...models.template_course import TemplateCourse
        course_stmt = select(TemplateCourse.course_id).where(
            TemplateCourse.template_id == template_id
        ).order_by(TemplateCourse.course_order)
        course_result = await db.execute(course_stmt)
        enriched["course_ids"] = [row[0] for row in course_result.fetchall()]

        return enriched

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{template_id}", response_model=TemplateWithProvidersRead)
async def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Update a template.

    Only the owner can update a template.

    Body:
        TemplateUpdate: Partial template payload

    Returns:
        TemplateWithProvidersRead: Updated template with provider info

    Raises:
        NotFoundException: If template not found
        ForbiddenException: If user is not the owner
    """
    try:
        logger.debug(f"Updating template {template_id}")

        # Check ownership
        can_modify = await crud_template.can_modify_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_modify:
            # Check if template exists
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You can only modify templates you own")

        # Get all update data (exclude_unset=True, but we need to handle kb_ids specially)
        update_dict = template_update.model_dump(exclude_unset=True)
        
        # Also check if knowledge_base_ids was explicitly set (even if set to None or empty list)
        # Pydantic 2.x uses model_fields_set to track which fields were explicitly provided
        if "knowledge_base_ids" in template_update.model_fields_set:
            update_dict["knowledge_base_ids"] = template_update.knowledge_base_ids
            
        provider_fields = {
            field: update_dict.get(field)
            for field in ["ASR", "LLM", "VLLM", "TTS", "Memory", "Intent"]
            if field in update_dict
        }
        if provider_fields:
            validation_errors = await validate_provider_references(
                db=db,
                user_id=current_user["id"],
                provider_fields=provider_fields,
            )
            if validation_errors:
                raise HTTPException(
                    status_code=400, detail="; ".join(validation_errors)
                )

        # Handle knowledge_base_ids if provided
        logger.debug(f"Update dict keys: {list(update_dict.keys())}")
        logger.debug(f"knowledge_base_ids in update_dict: {'knowledge_base_ids' in update_dict}")
        if "knowledge_base_ids" in update_dict:
            kb_ids = update_dict.pop("knowledge_base_ids") or []
            logger.info(f"Setting knowledge_base_ids for template {template_id}: {kb_ids}")
            await crud_template_knowledge_base.set_knowledge_bases_for_template(
                db=db,
                template_id=template_id,
                knowledge_base_ids=kb_ids,
            )

        # Update template (remove kb_ids from update_data as it's handled separately)
        update_data = TemplateUpdateInternal(
            **{k: v for k, v in update_dict.items() if k != "knowledge_base_ids"},
            updated_at=datetime.now(dt_timezone.utc),
        )

        updated_template = await crud_template.update(
            db=db,
            object=update_data,
            id=template_id,
            schema_to_select=TemplateRead,
            return_as_model=True,
        )

        logger.info(f"Template {template_id} updated successfully")

        # Enrich with provider info and KB IDs
        enriched = await _enrich_template_with_providers(db, updated_template)
        kb_ids = await crud_template_knowledge_base.get_knowledge_base_ids_for_template(
            db=db,
            template_id=template_id,
        )
        enriched["knowledge_base_ids"] = kb_ids
        return enriched

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    """
    Soft delete a template.

    Only the owner can delete a template.
    Deleting a template will also remove all assignments and clear
    active_template_id from agents using it.

    Raises:
        NotFoundException: If template not found
        ForbiddenException: If user is not the owner
    """
    try:
        logger.info(f"Deleting template {template_id}")

        # Check ownership
        can_modify = await crud_template.can_modify_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_modify:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You can only delete templates you own")

        # Get agents using this template to clear their active_template_id
        from sqlalchemy import update
        from ...models.agent import Agent

        stmt = (
            update(Agent)
            .where(Agent.active_template_id == template_id)
            .values(active_template_id=None, updated_at=datetime.now(dt_timezone.utc))
        )
        await db.execute(stmt)

        # Soft delete template (cascade will handle assignments)
        await crud_template.delete(db=db, id=template_id)

        logger.info(f"Template {template_id} deleted successfully")

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== Template Assignment Endpoints ==========


@router.get("/{template_id}/agents", response_model=PaginatedResponse[AgentRead])
async def list_agents_using_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, Any]:
    """
    List agents that have this template assigned.

    Only shows agents owned by the current user.

    Returns:
        PaginatedResponse[AgentRead]: Paginated list of agents

    Raises:
        NotFoundException: If template not found
        ForbiddenException: If user cannot access template
    """
    try:
        logger.debug(f"Listing agents using template {template_id}")

        # Check access
        can_access = await crud_template.can_access_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_access:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You do not have access to this template")

        agents_data = await crud_template.get_agents_using_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
            offset=(page - 1) * page_size,
            limit=page_size,
        )

        total = agents_data.get("total_count", 0)
        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            success=True,
            message="Success",
            data=agents_data["data"],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error listing agents using template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{template_id}/agents/{agent_id}",
    response_model=SuccessResponse[AssignmentRead],
    status_code=201,
)
async def add_agent_to_template(
    template_id: str,
    agent_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    set_active: Annotated[bool, Query()] = False,
) -> dict:
    """
    Add an agent to this template (assign template to agent).

    User must own the agent. User must own the template OR template must be public.

    Query Parameters:
    - set_active: bool (default=False) - Set as active template for agent

    Returns:
        SuccessResponse[AssignmentRead]: Created assignment

    Raises:
        NotFoundException: If template or agent not found
        ForbiddenException: If user cannot access template or doesn't own agent
    """
    try:
        logger.info(f"Assigning template {template_id} to agent {agent_id}")

        # Check template access
        can_access = await crud_template.can_access_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_access:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You do not have access to this template")

        # Check agent ownership
        agent = await crud_agent.get(
            db=db,
            id=agent_id,
            user_id=current_user["id"],
            is_deleted=False,
        )

        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found")

        # Create assignment
        assignment = await crud_assignment.assign_template_to_agent(
            db=db,
            agent_id=agent_id,
            template_id=template_id,
            set_active=set_active,
        )

        # If set_active, update agent's active_template_id
        if set_active:
            from ...schemas.agent import AgentUpdateInternal

            update_data = AgentUpdateInternal(
                active_template_id=template_id,
                updated_at=datetime.now(dt_timezone.utc),
            )
            await crud_agent.update(
                db=db,
                object=update_data,
                id=agent_id,
            )
            logger.info(f"Set template {template_id} as active for agent {agent_id}")

        logger.info(f"Template {template_id} assigned to agent {agent_id}")

        return SuccessResponse(
            success=True,
            message="Template assigned successfully",
            data=assignment,
        )

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error assigning template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{template_id}/agents/{agent_id}", status_code=204)
async def remove_agent_from_template(
    template_id: str,
    agent_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    """
    Remove an agent from this template (unassign template from agent).

    User must own the agent.
    If this was the active template, clears agent's active_template_id.

    Raises:
        NotFoundException: If assignment not found
        ForbiddenException: If user doesn't own agent
    """
    try:
        logger.info(f"Unassigning template {template_id} from agent {agent_id}")

        # Check agent ownership
        agent = await crud_agent.get(
            db=db,
            id=agent_id,
            user_id=current_user["id"],
            is_deleted=False,
            schema_to_select=AgentRead,
            return_as_model=True,
        )

        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found")

        # Remove assignment
        removed = await crud_assignment.unassign_template_from_agent(
            db=db,
            agent_id=agent_id,
            template_id=template_id,
        )

        if not removed:
            raise NotFoundException(
                f"Assignment not found for template {template_id} and agent {agent_id}"
            )

        # If this was active template, clear it
        if agent.active_template_id == template_id:
            from ...schemas.agent import AgentUpdateInternal

            update_data = AgentUpdateInternal(
                active_template_id=None,
                updated_at=datetime.now(dt_timezone.utc),
            )
            await crud_agent.update(
                db=db,
                object=update_data,
                id=agent_id,
            )
            logger.info(f"Cleared active template for agent {agent_id}")

        logger.info(f"Template {template_id} unassigned from agent {agent_id}")

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== Template Course Endpoints ==========


@router.post("/{template_id}/courses/{course_id}", status_code=201)
async def add_course_to_template(
    template_id: str,
    course_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Add a course to this template.

    User must own the template. Course must be accessible (user owns it or it's public).

    Returns:
        SuccessResponse: Success message
    """
    try:
        logger.info(f"Adding course {course_id} to template {template_id}")

        # Check template ownership
        can_modify = await crud_template.can_modify_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_modify:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You can only modify templates you own")

        # Check if course exists and is accessible
        from sqlalchemy import select, or_
        from ...models.education.course import EduCourse

        stmt = select(EduCourse).where(
            EduCourse.id == course_id,
            EduCourse.is_published == True,  # Course must be published
            or_(
                EduCourse.user_id == current_user["id"],
                EduCourse.is_public == True,
            ),
        )
        result = await db.execute(stmt)
        course = result.scalar_one_or_none()

        if not course:
            raise NotFoundException(f"Course {course_id} not found or not accessible")

        # Create assignment
        from ...models.template_course import TemplateCourse

        # Check if already assigned
        existing_stmt = select(TemplateCourse).where(
            TemplateCourse.template_id == template_id,
            TemplateCourse.course_id == course_id,
        )
        existing = await db.execute(existing_stmt)
        if existing.scalar_one_or_none():
            return SuccessResponse(
                success=True,
                message="Course already assigned to template",
                data={"template_id": template_id, "course_id": course_id},
            ).model_dump()

        # Get next order
        from sqlalchemy import func

        max_order_stmt = select(func.max(TemplateCourse.course_order)).where(
            TemplateCourse.template_id == template_id
        )
        max_order_result = await db.execute(max_order_stmt)
        max_order = max_order_result.scalar() or 0

        template_course = TemplateCourse(
            template_id=template_id,
            course_id=course_id,
            course_order=max_order + 1,
        )
        db.add(template_course)
        await db.commit()

        logger.info(f"Course {course_id} added to template {template_id}")

        return SuccessResponse(
            success=True,
            message="Course added to template successfully",
            data={"template_id": template_id, "course_id": course_id},
        ).model_dump()

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error adding course to template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{template_id}/courses/{course_id}", status_code=204)
async def remove_course_from_template(
    template_id: str,
    course_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    """
    Remove a course from this template.

    User must own the template.

    Raises:
        NotFoundException: If assignment not found
        ForbiddenException: If user doesn't own template
    """
    try:
        logger.info(f"Removing course {course_id} from template {template_id}")

        # Check template ownership
        can_modify = await crud_template.can_modify_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_modify:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You can only modify templates you own")

        # Delete assignment
        from sqlalchemy import delete
        from ...models.template_course import TemplateCourse

        stmt = delete(TemplateCourse).where(
            TemplateCourse.template_id == template_id,
            TemplateCourse.course_id == course_id,
        )
        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount == 0:
            raise NotFoundException(
                f"Course {course_id} not assigned to template {template_id}"
            )

        logger.info(f"Course {course_id} removed from template {template_id}")

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error removing course from template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}/courses")
async def list_courses_for_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    List courses assigned to this template.

    Returns:
        SuccessResponse: List of courses
    """
    try:
        logger.debug(f"Listing courses for template {template_id}")

        # Check access
        can_access = await crud_template.can_access_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )

        if not can_access:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You do not have access to this template")

        # Get courses
        from sqlalchemy import select
        from ...models.template_course import TemplateCourse
        from ...models.education.course import EduCourse

        stmt = (
            select(EduCourse)
            .join(TemplateCourse, TemplateCourse.course_id == EduCourse.id)
            .where(
                TemplateCourse.template_id == template_id,
                EduCourse.is_published == True,
            )
            .order_by(TemplateCourse.course_order)
        )
        result = await db.execute(stmt)
        courses = result.scalars().all()

        return SuccessResponse(
            success=True,
            message="Success",
            data=[
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "difficulty": c.difficulty,
                    "estimated_hours": c.estimated_hours,
                    "is_published": c.is_published,
                }
                for c in courses
            ],
        ).model_dump()

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error listing courses for template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== Agent-Centric: Clone Template to Agent ==========


@router.post("/{template_id}/clone-to-agent/{agent_id}", response_model=SuccessResponse)
async def clone_template_to_agent(
    template_id: str,
    agent_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Clone a template's config into an agent's inline fields.

    AGENT-CENTRIC: Copies prompt, LLM, TTS, ASR, Memory, Intent, tools,
    KB IDs, notebook IDs, etc. from the template directly into the agent.
    The agent becomes self-contained — no longer requires the template at runtime.

    Also sets source_template_id on the agent for tracking.

    User must own the agent. User must own the template or template must be public.

    Returns:
        SuccessResponse: Confirmation with cloned field list
    """
    try:
        logger.info(
            f"Cloning template {template_id} into agent {agent_id} (Agent-Centric)"
        )

        # Check template access
        can_access = await crud_template.can_access_template(
            db=db,
            template_id=template_id,
            user_id=current_user["id"],
        )
        if not can_access:
            template = await crud_template.get(db=db, id=template_id, is_deleted=False)
            if not template:
                raise NotFoundException(f"Template {template_id} not found")
            raise ForbiddenException("You do not have access to this template")

        # Check agent ownership
        agent = await crud_agent.get(
            db=db,
            id=agent_id,
            user_id=current_user["id"],
            is_deleted=False,
        )
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found")

        # Get full template data
        template = await crud_template.get(
            db=db,
            id=template_id,
            is_deleted=False,
            schema_to_select=TemplateRead,
            return_as_model=True,
        )
        if not template:
            raise NotFoundException(f"Template {template_id} not found")

        # Fields to clone from template to agent
        clone_fields = [
            "prompt", "ASR", "LLM", "VLLM", "TTS", "tts_voice",
            "Memory", "Intent", "tools", "summary_memory",
            "enable_memory", "enable_knowledge_base",
        ]

        # Build update dict
        update_data = {}
        cloned_fields = []
        for field in clone_fields:
            value = getattr(template, field, None)
            if value is not None:
                update_data[field] = value
                cloned_fields.append(field)

        # Track source template
        update_data["source_template_id"] = template_id
        update_data["updated_at"] = datetime.now(dt_timezone.utc)

        # Clone KB IDs
        kb_ids = await crud_template_knowledge_base.get_knowledge_base_ids_for_template(
            db=db,
            template_id=template_id,
        )
        if kb_ids:
            update_data["knowledge_base_ids"] = kb_ids
            cloned_fields.append("knowledge_base_ids")

        # Apply update to agent
        from ...schemas.agent import AgentUpdateInternal
        agent_update = AgentUpdateInternal(**update_data)
        await crud_agent.update(
            db=db,
            object=agent_update,
            id=agent_id,
        )

        logger.info(
            f"✅ Cloned template {template_id} into agent {agent_id}. "
            f"Fields: {cloned_fields}"
        )

        return SuccessResponse(
            success=True,
            message=f"Template config cloned into agent. Fields: {', '.join(cloned_fields)}",
            data={
                "agent_id": agent_id,
                "source_template_id": template_id,
                "cloned_fields": cloned_fields,
            },
        ).model_dump()

    except NotFoundException:
        raise
    except ForbiddenException:
        raise
    except Exception as e:
        logger.error(f"Error cloning template to agent: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

