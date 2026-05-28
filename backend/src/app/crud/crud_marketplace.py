"""
CRUD operations for Marketplace items, installations, and reviews.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.marketplace import MarketplaceItem, MarketplaceInstallation, MarketplaceReview

logger = logging.getLogger(__name__)


# ========== Marketplace Item CRUD ==========

async def get_marketplace_items(
    db: AsyncSession,
    type: str | None = None,
    category: str | None = None,
    search: str | None = None,
    status: str = "approved",
    is_featured: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[MarketplaceItem], int]:
    """Get paginated marketplace items with filters."""
    query = select(MarketplaceItem).where(
        and_(
            MarketplaceItem.is_deleted == False,
            MarketplaceItem.status == status,
            MarketplaceItem.is_public == True,
        )
    )

    if type:
        query = query.where(MarketplaceItem.type == type)
    if category:
        query = query.where(MarketplaceItem.category == category)
    if is_featured is not None:
        query = query.where(MarketplaceItem.is_featured == is_featured)
    if search:
        search_filter = or_(
            MarketplaceItem.name.ilike(f"%{search}%"),
            MarketplaceItem.description.ilike(f"%{search}%"),
            MarketplaceItem.short_description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(
        MarketplaceItem.is_featured.desc(),
        MarketplaceItem.install_count.desc(),
        MarketplaceItem.created_at.desc(),
    ).offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_marketplace_item(
    db: AsyncSession,
    item_id: str,
) -> MarketplaceItem | None:
    """Get a single marketplace item by ID."""
    result = await db.execute(
        select(MarketplaceItem).where(
            and_(
                MarketplaceItem.id == item_id,
                MarketplaceItem.is_deleted == False,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_marketplace_item(
    db: AsyncSession,
    seller_id: str,
    **kwargs,
) -> MarketplaceItem:
    """Create a new marketplace item."""
    item = MarketplaceItem(
        seller_id=seller_id,
        **kwargs,
    )
    db.add(item)
    await db.flush()
    logger.info(f"Created marketplace item: {item.name} (type={item.type})")
    return item


async def update_marketplace_item(
    db: AsyncSession,
    item_id: str,
    **kwargs,
) -> MarketplaceItem | None:
    """Update a marketplace item."""
    item = await get_marketplace_item(db, item_id)
    if not item:
        return None

    for key, value in kwargs.items():
        if hasattr(item, key) and value is not None:
            setattr(item, key, value)

    item.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return item


async def get_seller_items(
    db: AsyncSession,
    seller_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[MarketplaceItem], int]:
    """Get items created by a seller."""
    query = select(MarketplaceItem).where(
        and_(
            MarketplaceItem.seller_id == seller_id,
            MarketplaceItem.is_deleted == False,
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(MarketplaceItem.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


# ========== Installation CRUD ==========

async def install_item(
    db: AsyncSession,
    user_id: str,
    item_id: str,
    cloned_resource_type: str | None = None,
    cloned_resource_id: str | None = None,
    payment_status: str = "free",
    payment_amount: float = 0,
) -> MarketplaceInstallation:
    """Install a marketplace item for a user."""
    # Check if already installed
    existing = await get_installation(db, user_id, item_id)
    if existing and existing.uninstalled_at is None:
        return existing

    if existing and existing.uninstalled_at is not None:
        # Re-install
        existing.uninstalled_at = None
        existing.cloned_resource_type = cloned_resource_type
        existing.cloned_resource_id = cloned_resource_id
        await db.flush()
        return existing

    installation = MarketplaceInstallation(
        user_id=user_id,
        item_id=item_id,
        cloned_resource_type=cloned_resource_type,
        cloned_resource_id=cloned_resource_id,
        payment_status=payment_status,
        payment_amount=payment_amount,
    )
    db.add(installation)
    await db.flush()

    # Increment install count
    await db.execute(
        update(MarketplaceItem)
        .where(MarketplaceItem.id == item_id)
        .values(install_count=MarketplaceItem.install_count + 1)
    )

    logger.info(f"User {user_id} installed marketplace item {item_id}")
    return installation


async def uninstall_item(
    db: AsyncSession,
    user_id: str,
    item_id: str,
) -> bool:
    """Uninstall a marketplace item (soft uninstall)."""
    installation = await get_installation(db, user_id, item_id)
    if not installation or installation.uninstalled_at is not None:
        return False

    installation.uninstalled_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"User {user_id} uninstalled marketplace item {item_id}")
    return True


async def get_installation(
    db: AsyncSession,
    user_id: str,
    item_id: str,
) -> MarketplaceInstallation | None:
    """Get a specific installation."""
    result = await db.execute(
        select(MarketplaceInstallation).where(
            and_(
                MarketplaceInstallation.user_id == user_id,
                MarketplaceInstallation.item_id == item_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_installations(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[MarketplaceInstallation], int]:
    """Get user's installed items."""
    query = select(MarketplaceInstallation).where(
        and_(
            MarketplaceInstallation.user_id == user_id,
            MarketplaceInstallation.uninstalled_at == None,
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(MarketplaceInstallation.installed_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    installations = list(result.scalars().all())

    return installations, total


async def is_item_installed(
    db: AsyncSession,
    user_id: str,
    item_id: str,
) -> bool:
    """Check if a user has installed an item."""
    installation = await get_installation(db, user_id, item_id)
    return installation is not None and installation.uninstalled_at is None


# ========== Review CRUD ==========

async def create_review(
    db: AsyncSession,
    user_id: str,
    item_id: str,
    rating: int,
    comment: str | None = None,
) -> MarketplaceReview:
    """Create or update a review."""
    # Check existing
    existing = await get_user_review(db, user_id, item_id)
    if existing:
        existing.rating = rating
        existing.comment = comment
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await _update_item_rating(db, item_id)
        return existing

    review = MarketplaceReview(
        user_id=user_id,
        item_id=item_id,
        rating=rating,
        comment=comment,
    )
    db.add(review)
    await db.flush()

    await _update_item_rating(db, item_id)
    logger.info(f"User {user_id} reviewed item {item_id}: {rating}/5")
    return review


async def get_item_reviews(
    db: AsyncSession,
    item_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[MarketplaceReview], int]:
    """Get reviews for an item."""
    query = select(MarketplaceReview).where(
        MarketplaceReview.item_id == item_id
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(MarketplaceReview.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    reviews = list(result.scalars().all())

    return reviews, total


async def get_user_review(
    db: AsyncSession,
    user_id: str,
    item_id: str,
) -> MarketplaceReview | None:
    """Get user's review for an item."""
    result = await db.execute(
        select(MarketplaceReview).where(
            and_(
                MarketplaceReview.user_id == user_id,
                MarketplaceReview.item_id == item_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def _update_item_rating(
    db: AsyncSession,
    item_id: str,
) -> None:
    """Recalculate and update an item's average rating."""
    result = await db.execute(
        select(
            func.avg(MarketplaceReview.rating),
            func.count(MarketplaceReview.id),
        ).where(MarketplaceReview.item_id == item_id)
    )
    row = result.one()
    avg_rating = float(row[0]) if row[0] else 0
    count = row[1] or 0

    await db.execute(
        update(MarketplaceItem)
        .where(MarketplaceItem.id == item_id)
        .values(rating_avg=round(avg_rating, 2), rating_count=count)
    )
