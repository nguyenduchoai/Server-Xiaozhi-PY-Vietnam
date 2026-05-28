"""
Skill Marketplace API Endpoints

Browse, install, and manage skills from the marketplace.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.logger import get_logger
from datetime import datetime
from ...models.skill import (
    Skill, 
    SkillInstallation, 
    SkillReview,
    SkillType,
    SkillCategory,
)

router = APIRouter(tags=["marketplace"], prefix="/marketplace")

logger = get_logger(__name__)


def _is_superuser(user: dict) -> bool:
    """Check if user is admin/superadmin."""
    if user.get("is_superuser"):
        return True
    return user.get("role") in ["admin", "super_admin"]


# ==================== Schemas ====================

class SkillConfig(BaseModel):
    """Typed configuration for skills"""
    command: Optional[str] = Field(None, max_length=500, description="Command to execute")
    env: Optional[dict[str, str]] = Field(None, description="Environment variables")
    args: Optional[list[str]] = Field(None, description="Command arguments")
    url: Optional[str] = Field(None, max_length=2048, description="Service URL")
    schema_version: str = Field("1.0", max_length=20)

    model_config = {"extra": "allow"}


class SkillBase(BaseModel):
    """Base skill schema"""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str = Field(..., max_length=5000)
    short_description: Optional[str] = Field(None, max_length=200)
    skill_type: str = SkillType.MCP_SERVER.value
    category: str = SkillCategory.UTILITIES.value
    tags: Optional[list[str]] = None
    config: SkillConfig


class SkillCreate(SkillBase):
    """Schema for creating a skill"""
    version: str = "1.0.0"
    readme: Optional[str] = None
    icon_url: Optional[str] = None
    banner_url: Optional[str] = None
    screenshots: Optional[list[str]] = None
    is_premium: bool = False
    price: Optional[int] = None  # Price in VND (0 = free)
    is_public: bool = False
    is_featured: bool = False


class SkillUpdate(BaseModel):
    """Schema for updating a skill"""
    name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    config: Optional[SkillConfig] = None
    version: Optional[str] = None
    readme: Optional[str] = None
    icon_url: Optional[str] = None
    banner_url: Optional[str] = None
    screenshots: Optional[list[str]] = None
    is_public: Optional[bool] = None
    is_premium: Optional[bool] = None
    price: Optional[int] = None
    is_featured: Optional[bool] = None


class SkillRead(SkillBase):
    """Schema for reading a skill"""
    id: str
    author_id: str
    author_name: str
    author_verified: bool
    version: str
    icon_url: Optional[str] = None
    banner_url: Optional[str] = None
    screenshots: Optional[list[str]] = None
    install_count: int
    rating: float
    rating_count: int
    is_public: bool
    is_verified: bool
    is_featured: bool
    is_premium: bool = False
    price: Optional[int] = None
    
    model_config = {"from_attributes": True}


class SkillDetail(SkillRead):
    """Detailed skill schema"""
    readme: Optional[str] = None
    screenshots: Optional[list[str]] = None
    changelog: Optional[str] = None
    documentation_url: Optional[str] = None


class SkillListResponse(BaseModel):
    """Paginated skill list response"""
    success: bool = True
    data: list[SkillRead]
    total: int
    page: int
    page_size: int


class SkillReviewCreate(BaseModel):
    """Schema for creating a review"""
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = Field(None, max_length=5000)


class SkillReviewRead(BaseModel):
    """Schema for reading a review"""
    id: str
    user_id: str
    rating: int
    title: Optional[str]
    comment: Optional[str]
    version_reviewed: str
    helpful_count: int
    created_at: str

    model_config = {"from_attributes": True}


# ==================== Browse Endpoints ====================

@router.get("/skills", response_model=SkillListResponse)
async def browse_skills(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    category: Optional[str] = Query(None, description="Filter by category"),
    skill_type: Optional[str] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search term"),
    sort: str = Query("popular", description="Sort by: popular, newest, rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Browse available skills in the marketplace.
    
    Filter by category, type, or search term.
    """
    conditions = [Skill.is_public == True, Skill.is_approved == True]
    
    if category:
        conditions.append(Skill.category == category)
    if skill_type:
        conditions.append(Skill.skill_type == skill_type)
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Skill.name.ilike(search_pattern),
                Skill.description.ilike(search_pattern),
                Skill.short_description.ilike(search_pattern),
            )
        )
    
    # Count total
    count_query = select(func.count(Skill.id)).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar() or 0
    
    # Build query with sorting
    query = select(Skill).where(and_(*conditions))
    
    if sort == "popular":
        query = query.order_by(desc(Skill.install_count))
    elif sort == "newest":
        query = query.order_by(desc(Skill.created_at))
    elif sort == "rating":
        query = query.order_by(desc(Skill.rating))
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    skills = result.scalars().all()
    
    return SkillListResponse(
        data=[SkillRead.model_validate(s) for s in skills],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/skills/featured", response_model=list[SkillRead])
async def get_featured_skills(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(10, ge=1, le=50),
):
    """Get featured skills."""
    query = (
        select(Skill)
        .where(and_(
            Skill.is_public == True,
            Skill.is_featured == True,
            Skill.is_approved == True,
        ))
        .order_by(desc(Skill.install_count))
        .limit(limit)
    )
    
    result = await db.execute(query)
    skills = result.scalars().all()
    
    return [SkillRead.model_validate(s) for s in skills]


@router.get("/skills/categories")
async def get_categories():
    """Get available skill categories."""
    return {
        "categories": [
            {"value": c.value, "label": c.value.replace("_", " ").title()}
            for c in SkillCategory
        ]
    }


@router.get("/skills/{skill_id}", response_model=SkillDetail)
async def get_skill_detail(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get detailed information about a skill."""
    result = await db.execute(select(Skill).where(Skill.id == str(skill_id)))
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check access (public or owner)
    if not skill.is_public and str(skill.author_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Increment view count
    skill.view_count += 1
    await db.commit()
    
    return SkillDetail.model_validate(skill)


# ==================== My Skills ====================

@router.get("/my-skills", response_model=list[SkillRead])
async def get_my_skills(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get skills created by the current user."""
    query = (
        select(Skill)
        .where(Skill.author_id == str(current_user["id"]))
        .order_by(desc(Skill.created_at))
    )
    
    result = await db.execute(query)
    skills = result.scalars().all()
    
    return [SkillRead.model_validate(s) for s in skills]


@router.post("/skills", response_model=SkillRead, status_code=201)
async def create_skill(
    data: SkillCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Submit a new skill to the marketplace."""
    user_id = str(current_user["id"])
    
    # Check slug uniqueness
    existing = await db.execute(
        select(Skill).where(Skill.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Slug '{data.slug}' already exists"
        )
    
    skill_data = data.model_dump()
    skill = Skill(
        **skill_data,
        author_id=user_id,
        author_name=current_user.get("name", current_user.get("username", "Unknown")),
    )
    
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    
    logger.info(f"User {user_id} created skill: {skill.name}")
    
    return SkillRead.model_validate(skill)


@router.put("/skills/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: UUID,
    data: SkillUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a skill (author only)."""
    result = await db.execute(select(Skill).where(Skill.id == str(skill_id)))
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    if str(skill.author_id) != str(current_user["id"]) and not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(skill, key, value)
    
    await db.commit()
    await db.refresh(skill)
    
    return SkillRead.model_validate(skill)


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a skill (author only)."""
    result = await db.execute(select(Skill).where(Skill.id == str(skill_id)))
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    if str(skill.author_id) != str(current_user["id"]) and not _is_superuser(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.delete(skill)
    await db.commit()


# ==================== Installation ====================

@router.get("/installations")
async def get_installations(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get installed skills (returns installation records with skill info)."""
    user_id = str(current_user["id"])
    query = (
        select(SkillInstallation)
        .where(
            and_(
                SkillInstallation.user_id == user_id,
                SkillInstallation.is_active == True,
            )
        )
    )
    result = await db.execute(query)
    installations = result.scalars().all()
    
    items = []
    for inst in installations:
        # Get skill info
        skill_result = await db.execute(select(Skill).where(Skill.id == str(inst.skill_id)))
        skill = skill_result.scalar_one_or_none()
        items.append({
            "id": str(inst.id),
            "skill_id": str(inst.skill_id),
            "skill_name": skill.name if skill else "Unknown",
            "skill_icon": skill.icon_url if skill else None,
            "version_installed": inst.installed_version or "1.0.0",
            "installed_at": inst.created_at.isoformat() if inst.created_at else None,
            "is_active": inst.is_active,
        })
    
    return {"success": True, "data": items}


@router.get("/installed", response_model=list[SkillRead])
async def get_installed_skills(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get skills installed by the current user."""
    user_id = str(current_user["id"])
    
    query = (
        select(Skill)
        .join(SkillInstallation, SkillInstallation.skill_id == Skill.id)
        .where(
            and_(
                SkillInstallation.user_id == user_id,
                SkillInstallation.is_active == True,
            )
        )
    )
    
    result = await db.execute(query)
    skills = result.scalars().all()
    
    return [SkillRead.model_validate(s) for s in skills]


@router.post("/skills/{skill_id}/install", status_code=201)
async def install_skill(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Install a skill."""
    user_id = str(current_user["id"])
    
    # Get skill
    result = await db.execute(select(Skill).where(Skill.id == str(skill_id)))
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    if not skill.is_public:
        raise HTTPException(status_code=403, detail="Skill is not public")
    
    # Check if already installed
    existing = await db.execute(
        select(SkillInstallation).where(
            and_(
                SkillInstallation.skill_id == str(skill_id),
                SkillInstallation.user_id == user_id,
            )
        )
    )
    
    installation = existing.scalar_one_or_none()
    
    if installation:
        if installation.is_active:
            raise HTTPException(status_code=400, detail="Skill already installed")
        # Reactivate
        installation.is_active = True
        installation.uninstalled_at = None
    else:
        # Create new installation
        installation = SkillInstallation(
            skill_id=str(skill_id),
            user_id=user_id,
            installed_version=skill.version,
        )
        db.add(installation)
        
        # Update install count
        skill.install_count += 1
        skill.active_installs += 1
    
    await db.commit()
    
    logger.info(f"User {user_id} installed skill: {skill.name}")
    
    return {
        "success": True,
        "message": f"Skill '{skill.name}' installed successfully",
        "config": skill.config
    }


@router.delete("/skills/{skill_id}/install", status_code=204)
async def uninstall_skill(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Uninstall a skill."""
    user_id = str(current_user["id"])
    
    result = await db.execute(
        select(SkillInstallation).where(
            and_(
                SkillInstallation.skill_id == str(skill_id),
                SkillInstallation.user_id == user_id,
            )
        )
    )
    
    installation = result.scalar_one_or_none()
    
    if not installation or not installation.is_active:
        raise HTTPException(status_code=404, detail="Skill not installed")
    
    installation.is_active = False
    installation.uninstalled_at = datetime.utcnow()
    
    # Update skill counts
    skill = await db.execute(select(Skill).where(Skill.id == str(skill_id)))
    skill = skill.scalar_one_or_none()
    if skill:
        skill.active_installs = max(0, skill.active_installs - 1)
    
    await db.commit()


@router.delete("/skills/{skill_id}/uninstall", status_code=204)
async def uninstall_skill_alias(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Alias for uninstall (frontend uses /uninstall path)."""
    return await uninstall_skill(skill_id, db, current_user)


# ==================== Reviews ====================

@router.get("/skills/{skill_id}/reviews", response_model=list[SkillReviewRead])
async def get_skill_reviews(
    skill_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """Get reviews for a skill."""
    query = (
        select(SkillReview)
        .where(
            and_(
                SkillReview.skill_id == str(skill_id),
                SkillReview.is_approved == True,
                SkillReview.is_hidden == False,
            )
        )
        .order_by(desc(SkillReview.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    return [SkillReviewRead.model_validate(r) for r in reviews]


@router.post("/skills/{skill_id}/reviews", response_model=SkillReviewRead, status_code=201)
async def create_review(
    skill_id: UUID,
    data: SkillReviewCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Add a review for a skill."""
    user_id = str(current_user["id"])
    
    # Check if skill exists
    result = await db.execute(select(Skill).where(Skill.id == str(skill_id)))
    skill = result.scalar_one_or_none()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if user has installed the skill
    installation = await db.execute(
        select(SkillInstallation).where(
            and_(
                SkillInstallation.skill_id == str(skill_id),
                SkillInstallation.user_id == user_id,
            )
        )
    )
    installation = installation.scalar_one_or_none()
    
    # Check if already reviewed
    existing_review = await db.execute(
        select(SkillReview).where(
            and_(
                SkillReview.skill_id == str(skill_id),
                SkillReview.user_id == user_id,
            )
        )
    )
    
    if existing_review.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already reviewed this skill")
    
    review = SkillReview(
        skill_id=str(skill_id),
        user_id=user_id,
        rating=data.rating,
        title=data.title,
        comment=data.comment,
        version_reviewed=skill.version,
        is_verified_purchase=installation is not None,
    )
    
    db.add(review)
    
    # Update skill rating
    skill.update_rating(data.rating)
    
    await db.commit()
    await db.refresh(review)
    
    return SkillReviewRead.model_validate(review)


# ==================== Marketplace Items (Templates, Themes, Courses) ====================


@router.get("/items")
async def browse_marketplace_items(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    type: Optional[str] = Query(None, description="Filter by type: template, theme, course, feature, emoji_pack"),
    category: Optional[str] = Query(None, description="Filter by category: education, business, entertainment, utility"),
    search: Optional[str] = Query(None, description="Search term"),
    featured: Optional[bool] = Query(None, description="Filter featured items"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Browse marketplace items (templates, themes, courses, features).
    
    Returns approved, public items with pagination.
    """
    from ...crud import crud_marketplace as mp_crud

    items, total = await mp_crud.get_marketplace_items(
        db=db,
        type=type,
        category=category,
        search=search,
        is_featured=featured,
        page=page,
        page_size=page_size,
    )

    # Enrich with installation status
    data = []
    for item in items:
        item_dict = {
            "id": item.id,
            "seller_id": item.seller_id,
            "type": item.type,
            "category": item.category,
            "name": item.name,
            "description": item.description,
            "short_description": item.short_description,
            "price": float(item.price) if item.price else 0,
            "currency": item.currency,
            "icon_url": item.icon_url,
            "cover_image_url": item.cover_image_url,
            "screenshots": item.screenshots,
            "install_count": item.install_count,
            "rating_avg": float(item.rating_avg) if item.rating_avg else 0,
            "rating_count": item.rating_count,
            "is_featured": item.is_featured,
            "version": item.version,
            "tags": item.tags,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        # Check if installed by current user
        is_installed = await mp_crud.is_item_installed(db, current_user["id"], item.id)
        item_dict["is_installed"] = is_installed
        data.append(item_dict)

    return {
        "success": True,
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/items/{item_id}")
async def get_marketplace_item_detail(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get detailed info about a marketplace item."""
    from ...crud import crud_marketplace as mp_crud
    from ...crud.crud_users import crud_users

    item = await mp_crud.get_marketplace_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get seller info
    seller = await crud_users.get(db=db, id=item.seller_id)
    seller_name = seller.name if seller else "Unknown"

    is_installed = await mp_crud.is_item_installed(db, current_user["id"], item_id)

    return {
        "success": True,
        "data": {
            "id": item.id,
            "seller_id": item.seller_id,
            "seller_name": seller_name,
            "type": item.type,
            "category": item.category,
            "name": item.name,
            "description": item.description,
            "short_description": item.short_description,
            "price": float(item.price) if item.price else 0,
            "currency": item.currency,
            "source_type": item.source_type,
            "icon_url": item.icon_url,
            "cover_image_url": item.cover_image_url,
            "screenshots": item.screenshots,
            "install_count": item.install_count,
            "rating_avg": float(item.rating_avg) if item.rating_avg else 0,
            "rating_count": item.rating_count,
            "status": item.status,
            "is_featured": item.is_featured,
            "version": item.version,
            "tags": item.tags,
            "is_installed": is_installed,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        },
    }


@router.post("/items/{item_id}/install")
async def install_marketplace_item(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Install a marketplace item.
    
    For templates: Clones the template to user's account.
    For other types: Creates an installation record.
    
    Free items are installed directly.
    Paid items require payment verification (TODO).
    """
    from ...crud import crud_marketplace as mp_crud
    from ...crud.crud_template import crud_template

    item = await mp_crud.get_marketplace_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.status != "approved":
        raise HTTPException(status_code=400, detail="Item is not available for installation")

    # Check if already installed
    already = await mp_crud.is_item_installed(db, current_user["id"], item_id)
    if already:
        raise HTTPException(status_code=400, detail="Item already installed")

    # Check payment for paid items
    if item.price and float(item.price) > 0:
        raise HTTPException(status_code=402, detail="Payment required. Paid items coming soon.")

    cloned_resource_type = None
    cloned_resource_id = None

    # Clone based on source type
    if item.source_type == "template" and item.source_id:
        # Clone template to user's account
        from ...schemas.template import TemplateRead, TemplateCreateInternal

        source_template = await crud_template.get(
            db=db,
            id=item.source_id,
            is_deleted=False,
            schema_to_select=TemplateRead,
            return_as_model=True,
        )

        if not source_template:
            raise HTTPException(status_code=500, detail="Source template not found")

        # Create clone
        clone_data = TemplateCreateInternal(
            user_id=current_user["id"],
            name=f"{source_template.name}",
            prompt=source_template.prompt,
            ASR=source_template.ASR,
            LLM=source_template.LLM,
            VLLM=source_template.VLLM,
            TTS=source_template.TTS,
            tts_voice=source_template.tts_voice,
            Memory=source_template.Memory,
            Intent=source_template.Intent,
            tools=source_template.tools,
            summary_memory=source_template.summary_memory,
            is_public=False,
            enable_memory=source_template.enable_memory,
            enable_knowledge_base=source_template.enable_knowledge_base,
            memory_scope=source_template.memory_scope,
        )

        cloned_template = await crud_template.create(
            db=db,
            object=clone_data,
        )

        cloned_resource_type = "template"
        cloned_resource_id = cloned_template["id"] if isinstance(cloned_template, dict) else cloned_template.id

        logger.info(
            f"Cloned template '{source_template.name}' for user {current_user['id']} "
            f"(source={item.source_id}, clone={cloned_resource_id})"
        )

    # Create installation record
    installation = await mp_crud.install_item(
        db=db,
        user_id=current_user["id"],
        item_id=item_id,
        cloned_resource_type=cloned_resource_type,
        cloned_resource_id=cloned_resource_id,
    )

    await db.commit()

    return {
        "success": True,
        "message": f"'{item.name}' đã được cài đặt thành công",
        "data": {
            "installation_id": installation.id,
            "item_id": item_id,
            "item_name": item.name,
            "cloned_resource_type": cloned_resource_type,
            "cloned_resource_id": cloned_resource_id,
        },
    }


@router.delete("/items/{item_id}/uninstall")
async def uninstall_marketplace_item(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Uninstall a marketplace item."""
    from ...crud import crud_marketplace as mp_crud

    removed = await mp_crud.uninstall_item(db, current_user["id"], item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Item not installed")

    await db.commit()

    return {
        "success": True,
        "message": "Item đã được gỡ cài đặt",
    }


@router.get("/my-installations")
async def get_my_installations(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get current user's installed marketplace items."""
    from ...crud import crud_marketplace as mp_crud

    installations, total = await mp_crud.get_user_installations(
        db=db,
        user_id=current_user["id"],
        page=page,
        page_size=page_size,
    )

    data = []
    for inst in installations:
        # Get item info
        item = await mp_crud.get_marketplace_item(db, inst.item_id)
        data.append({
            "installation_id": inst.id,
            "item_id": inst.item_id,
            "item_name": item.name if item else "Unknown",
            "item_type": item.type if item else None,
            "cloned_resource_type": inst.cloned_resource_type,
            "cloned_resource_id": inst.cloned_resource_id,
            "installed_at": inst.installed_at.isoformat() if inst.installed_at else None,
        })

    return {
        "success": True,
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/items")
async def create_marketplace_item(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    name: str = Query(..., min_length=1, max_length=255),
    type: str = Query(..., description="template, theme, course, feature, emoji_pack"),
    source_type: str = Query(..., description="template, emoji_pack, etc."),
    source_id: str = Query(..., description="UUID of source resource"),
    description: str = Query(default=""),
    short_description: str = Query(default=""),
    category: Optional[str] = Query(default=None),
    price: float = Query(default=0, ge=0),
):
    """
    Create a marketplace item (publish for others to install).
    
    The source resource must belong to the current user.
    Item starts in 'draft' status.
    """
    from ...crud import crud_marketplace as mp_crud

    # Verify ownership of source resource
    if source_type == "template":
        from ...crud.crud_template import crud_template
        from ...schemas.template import TemplateRead

        template = await crud_template.get(
            db=db, id=source_id, is_deleted=False,
            schema_to_select=TemplateRead, return_as_model=True,
        )
        if not template or template.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Source template not found or not owned by you")

    item = await mp_crud.create_marketplace_item(
        db=db,
        seller_id=current_user["id"],
        name=name,
        type=type,
        source_type=source_type,
        source_id=source_id,
        description=description,
        short_description=short_description,
        category=category,
        price=price,
    )

    await db.commit()

    return {
        "success": True,
        "message": f"Item '{name}' created as draft",
        "data": {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            "status": item.status,
        },
    }


@router.put("/items/{item_id}/submit")
async def submit_item_for_review(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Submit a draft item for review/approval."""
    from ...crud import crud_marketplace as mp_crud

    item = await mp_crud.get_marketplace_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.seller_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your item")
    if item.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail=f"Item is already {item.status}")

    await mp_crud.update_marketplace_item(db, item_id, status="pending")
    await db.commit()

    return {
        "success": True,
        "message": "Item submitted for review",
        "data": {"id": item_id, "status": "pending"},
    }


@router.put("/items/{item_id}/approve")
async def approve_marketplace_item(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Approve a marketplace item (superadmin only)."""
    if not current_user.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Superadmin required")

    from ...crud import crud_marketplace as mp_crud

    item = await mp_crud.get_marketplace_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await mp_crud.update_marketplace_item(db, item_id, status="approved")
    await db.commit()

    return {
        "success": True,
        "message": f"Item '{item.name}' approved",
    }


@router.post("/items/{item_id}/reviews")
async def review_marketplace_item(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    rating: int = Query(..., ge=1, le=5),
    comment: Optional[str] = Query(default=None),
):
    """Add a review for a marketplace item."""
    from ...crud import crud_marketplace as mp_crud

    item = await mp_crud.get_marketplace_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    review = await mp_crud.create_review(
        db=db,
        user_id=current_user["id"],
        item_id=item_id,
        rating=rating,
        comment=comment,
    )

    await db.commit()

    return {
        "success": True,
        "data": {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment,
        },
    }


@router.get("/items/{item_id}/reviews")
async def get_marketplace_item_reviews(
    item_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """Get reviews for a marketplace item."""
    from ...crud import crud_marketplace as mp_crud

    reviews, total = await mp_crud.get_item_reviews(
        db=db, item_id=item_id, page=page, page_size=page_size
    )

    from ...crud.crud_users import crud_users

    data = []
    for r in reviews:
        user = await crud_users.get(db=db, id=r.user_id)
        data.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_name": user.name if user else "Anonymous",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "success": True,
        "data": data,
        "total": total,
    }
