"""
Emoji Pack CRUD Operations

Database operations for emoji packs and assets.
"""

import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload

from ..models.emoji_pack import EmojiPack, EmojiPackAsset, FlashJob, ApprovalStatus
from ..schemas.emoji_pack import EmojiPackCreate, EmojiPackUpdate


async def create_emoji_pack(
    db: AsyncSession,
    user_id: str,
    data: EmojiPackCreate
) -> EmojiPack:
    """Create a new emoji pack"""
    pack = EmojiPack(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=data.name,
    )
    pack.description = data.description
    pack.target_size = data.target_size
    pack.base_pack = data.base_pack
    
    db.add(pack)
    await db.commit()
    await db.refresh(pack)
    return pack


async def get_emoji_pack(
    db: AsyncSession,
    pack_id: str,
    user_id: Optional[str] = None
) -> Optional[EmojiPack]:
    """Get emoji pack by ID with assets"""
    query = select(EmojiPack).options(
        selectinload(EmojiPack.assets)
    ).where(EmojiPack.id == pack_id)
    
    # If user_id provided, check ownership or public
    if user_id:
        query = query.where(
            or_(
                EmojiPack.user_id == user_id,
                and_(
                    EmojiPack.is_public == True,
                    EmojiPack.approval_status == ApprovalStatus.APPROVED.value
                )
            )
        )
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_emoji_pack_by_owner(
    db: AsyncSession,
    pack_id: str,
    user_id: str
) -> Optional[EmojiPack]:
    """Get emoji pack only if user owns it"""
    query = select(EmojiPack).options(
        selectinload(EmojiPack.assets)
    ).where(
        EmojiPack.id == pack_id,
        EmojiPack.user_id == user_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_emoji_packs(
    db: AsyncSession,
    user_id: str,
    filter_type: str = "all",  # "mine", "public", "all"
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> tuple[List[EmojiPack], int]:
    """List emoji packs with pagination"""
    
    # Base query
    query = select(EmojiPack)
    count_query = select(func.count(EmojiPack.id))
    
    # Apply filter
    if filter_type == "mine":
        query = query.where(EmojiPack.user_id == user_id)
        count_query = count_query.where(EmojiPack.user_id == user_id)
    elif filter_type == "public":
        query = query.where(
            EmojiPack.is_public == True,
            EmojiPack.approval_status == ApprovalStatus.APPROVED.value
        )
        count_query = count_query.where(
            EmojiPack.is_public == True,
            EmojiPack.approval_status == ApprovalStatus.APPROVED.value
        )
    else:  # "all"
        query = query.where(
            or_(
                EmojiPack.user_id == user_id,
                and_(
                    EmojiPack.is_public == True,
                    EmojiPack.approval_status == ApprovalStatus.APPROVED.value
                )
            )
        )
        count_query = count_query.where(
            or_(
                EmojiPack.user_id == user_id,
                and_(
                    EmojiPack.is_public == True,
                    EmojiPack.approval_status == ApprovalStatus.APPROVED.value
                )
            )
        )
    
    # Apply search
    if search:
        search_filter = EmojiPack.name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(EmojiPack.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    packs = list(result.scalars().all())
    
    return packs, total


async def update_emoji_pack(
    db: AsyncSession,
    pack: EmojiPack,
    data: EmojiPackUpdate
) -> EmojiPack:
    """Update emoji pack metadata"""
    if data.name is not None:
        pack.name = data.name
    if data.description is not None:
        pack.description = data.description
    
    await db.commit()
    await db.refresh(pack)
    return pack


async def delete_emoji_pack(
    db: AsyncSession,
    pack: EmojiPack
) -> None:
    """Delete emoji pack and all assets"""
    await db.delete(pack)
    await db.commit()


async def share_emoji_pack(
    db: AsyncSession,
    pack: EmojiPack,
    auto_approve: bool = False
) -> EmojiPack:
    """Submit pack for public sharing"""
    pack.is_public = True
    pack.approval_status = ApprovalStatus.APPROVED.value if auto_approve else ApprovalStatus.PENDING.value
    
    await db.commit()
    await db.refresh(pack)
    return pack


async def unshare_emoji_pack(
    db: AsyncSession,
    pack: EmojiPack
) -> EmojiPack:
    """Make pack private again"""
    pack.is_public = False
    pack.approval_status = ApprovalStatus.PRIVATE.value
    
    await db.commit()
    await db.refresh(pack)
    return pack


async def clone_emoji_pack(
    db: AsyncSession,
    source_pack: EmojiPack,
    user_id: str,
    new_name: Optional[str] = None
) -> EmojiPack:
    """Clone a public pack to user's collection"""
    new_pack = EmojiPack(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=new_name or f"{source_pack.name} (Copy)",
    )
    new_pack.description = source_pack.description
    new_pack.target_size = source_pack.target_size
    new_pack.base_pack = source_pack.base_pack
    
    db.add(new_pack)
    await db.commit()
    
    # Clone assets
    for asset in source_pack.assets:
        new_asset = EmojiPackAsset(
            id=str(uuid.uuid4()),
            pack_id=new_pack.id,
            emotion_name=asset.emotion_name,
            file_path=asset.file_path,
        )
        new_asset.file_type = asset.file_type
        new_asset.file_size = asset.file_size
        new_asset.has_animation = asset.has_animation
        new_asset.frame_count = asset.frame_count
        new_asset.is_custom = asset.is_custom
        db.add(new_asset)
    
    await db.commit()
    await db.refresh(new_pack)
    
    # Increment download count on source
    source_pack.download_count += 1
    await db.commit()
    
    return new_pack


# ============ Emoji Pack Asset CRUD ============

async def get_pack_asset(
    db: AsyncSession,
    pack_id: str,
    emotion_name: str
) -> Optional[EmojiPackAsset]:
    """Get specific emotion asset from pack"""
    query = select(EmojiPackAsset).where(
        EmojiPackAsset.pack_id == pack_id,
        EmojiPackAsset.emotion_name == emotion_name
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_or_update_pack_asset(
    db: AsyncSession,
    pack_id: str,
    emotion_name: str,
    file_path: str,
    file_type: str = "png",
    file_size: int = 0,
    has_animation: bool = False,
    frame_count: int = 1,
    original_filename: Optional[str] = None
) -> EmojiPackAsset:
    """Create or update an emotion asset"""
    
    # Check if exists
    existing = await get_pack_asset(db, pack_id, emotion_name)
    
    if existing:
        existing.file_path = file_path
        existing.file_type = file_type
        existing.file_size = file_size
        existing.has_animation = has_animation
        existing.frame_count = frame_count
        existing.is_custom = True
        existing.original_filename = original_filename
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        asset = EmojiPackAsset(
            id=str(uuid.uuid4()),
            pack_id=pack_id,
            emotion_name=emotion_name,
            file_path=file_path,
        )
        asset.file_type = file_type
        asset.file_size = file_size
        asset.has_animation = has_animation
        asset.frame_count = frame_count
        asset.is_custom = True
        asset.original_filename = original_filename
        
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        return asset


async def delete_pack_asset(
    db: AsyncSession,
    asset: EmojiPackAsset
) -> None:
    """Delete an emotion asset (reset to default)"""
    await db.delete(asset)
    await db.commit()


# ============ Flash Job CRUD ============

async def create_flash_job(
    db: AsyncSession,
    user_id: str,
    device_id: str,
    pack_id: Optional[str] = None,
    asset_type: str = "emoji_pack"
) -> FlashJob:
    """Create a new flash job"""
    job = FlashJob(
        id=str(uuid.uuid4()),
        user_id=user_id,
        device_id=device_id,
    )
    job.pack_id = pack_id
    job.asset_type = asset_type
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_flash_job(
    db: AsyncSession,
    job_id: str,
    user_id: Optional[str] = None
) -> Optional[FlashJob]:
    """Get flash job by ID"""
    query = select(FlashJob).where(FlashJob.id == job_id)
    if user_id:
        query = query.where(FlashJob.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_flash_job_status(
    db: AsyncSession,
    job: FlashJob,
    status: str,
    progress: int = 0,
    message: Optional[str] = None
) -> FlashJob:
    """Update flash job status"""
    from datetime import datetime, timezone
    
    job.status = status
    job.progress = progress
    job.message = message
    
    if status == "in_progress" and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    elif status in ["completed", "failed"]:
        job.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(job)
    return job
