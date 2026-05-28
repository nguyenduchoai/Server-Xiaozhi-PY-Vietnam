"""
Emoji Pack API Endpoints

CRUD operations for emoji packs with custom emotion management.
"""

import os
import logging
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import io

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user, get_optional_user
from app.models.emoji_pack import EMOTION_NAMES
from app.schemas.emoji_pack import (
    EmojiPackCreate,
    EmojiPackUpdate,
    EmojiPackSummary,
    EmojiPackDetail,
    EmojiPackListResponse,
    EmojiPackAuthor,
    EmotionAssetInfo,
    EmotionUploadResponse,
    ShareRequest,
    ShareResponse,
)
from app.crud import emoji_pack as crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emoji-packs", tags=["emoji-packs"])

# Storage path for emoji assets
EMOJI_STORAGE_PATH = os.environ.get("EMOJI_STORAGE_PATH", "/app/data/emoji-packs")

# Limits
MAX_FILE_SIZE = 500 * 1024  # 500KB
MAX_GIF_FRAMES = 60
ALLOWED_EXTENSIONS = {"png", "gif"}


def get_storage_path(user_id: str, pack_id: str, emotion: str, ext: str) -> str:
    """Generate storage path for emoji asset"""
    base_path = os.path.join(EMOJI_STORAGE_PATH, user_id, pack_id)
    os.makedirs(base_path, exist_ok=True)
    return os.path.join(base_path, f"{emotion}.{ext}")


def get_asset_url(pack_id: str, emotion: str) -> str:
    """Generate URL for emoji asset"""
    return f"/api/v1/emoji-packs/{pack_id}/emotions/{emotion}/file"


def get_library_emoji_url(library: str, emotion: str) -> str:
    """Get URL for library emoji (from CDN or static)"""
    emoji_unicode_map = {
        "neutral": "1f636", "happy": "1f60a", "laughing": "1f606",
        "funny": "1f602", "sad": "1f614", "angry": "1f620",
        "crying": "1f62d", "loving": "1f60d", "embarrassed": "1f633",
        "surprised": "1f62f", "shocked": "1f631", "thinking": "1f914",
        "winking": "1f609", "cool": "1f60e", "relaxed": "1f60c",
        "delicious": "1f924", "kissy": "1f618", "confident": "1f60f",
        "sleepy": "1f634", "silly": "1f61c", "confused": "1f644",
    }
    unicode = emoji_unicode_map.get(emotion, "1f636")
    
    if library == "twemoji":
        return f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{unicode}.png"
    elif library == "noto":
        return f"https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/72/emoji_u{unicode}.png"
    elif library == "openmoji":
        return f"https://openmoji.org/data/color/72x72/{unicode.upper()}.png"
    return f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{unicode}.png"


# ============ Community Gallery (MUST be before /{pack_id}) ============

@router.get("/community", response_model=EmojiPackListResponse)
async def get_community_packs(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Optional[dict] = Depends(get_optional_user),
    search: Optional[str] = None,
    featured_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get public community packs"""
    user_id = current_user["id"] if current_user else ""
    
    packs, total = await crud.list_emoji_packs(
        db, user_id=user_id, filter_type="public",
        search=search, page=page, page_size=page_size,
    )
    
    if featured_only:
        packs = [p for p in packs if p.is_featured]
        total = len(packs)
    
    data = [EmojiPackSummary(
        id=pack.id, name=pack.name, description=pack.description,
        target_size=pack.target_size, base_pack=pack.base_pack,
        emotion_count=len(EMOTION_NAMES), is_public=True,
        is_featured=pack.is_featured, download_count=pack.download_count,
        preview_url=f"/api/v1/emoji-packs/{pack.id}/preview",
        created_at=pack.created_at,
        author=EmojiPackAuthor(id=pack.user_id, name="User"),
    ) for pack in packs]
    
    return EmojiPackListResponse(success=True, data=data, total=total, page=page, page_size=page_size)


# ============ Pack CRUD Endpoints ============

@router.get("", response_model=EmojiPackListResponse)
async def list_emoji_packs(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    filter: str = Query("all", pattern="^(mine|public|all)$"),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List emoji packs (user's own + public approved)"""
    packs, total = await crud.list_emoji_packs(
        db, user_id=current_user["id"], filter_type=filter,
        search=search, page=page, page_size=page_size,
    )
    
    data = []
    for pack in packs:
        author = EmojiPackAuthor(id=pack.user_id, name="User") if pack.is_public else None
        data.append(EmojiPackSummary(
            id=pack.id, name=pack.name, description=pack.description,
            target_size=pack.target_size, base_pack=pack.base_pack,
            emotion_count=len(EMOTION_NAMES), is_public=pack.is_public,
            is_featured=pack.is_featured, download_count=pack.download_count,
            preview_url=f"/api/v1/emoji-packs/{pack.id}/preview",
            created_at=pack.created_at, author=author,
        ))
    
    return EmojiPackListResponse(success=True, data=data, total=total, page=page, page_size=page_size)


@router.post("", response_model=EmojiPackDetail)
async def create_emoji_pack(
    data: EmojiPackCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Create a new emoji pack"""
    pack = await crud.create_emoji_pack(db, current_user["id"], data)
    
    emotions = {e: EmotionAssetInfo(
        url=get_library_emoji_url(pack.base_pack, e), file_type="png", is_custom=False
    ) for e in EMOTION_NAMES}
    
    return EmojiPackDetail(
        id=pack.id, name=pack.name, description=pack.description,
        target_size=pack.target_size, base_pack=pack.base_pack,
        is_public=pack.is_public, is_featured=pack.is_featured,
        approval_status=pack.approval_status, download_count=pack.download_count,
        emotions=emotions, created_at=pack.created_at, updated_at=pack.updated_at,
    )


@router.get("/{pack_id}", response_model=EmojiPackDetail)
async def get_emoji_pack(
    pack_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Get emoji pack details with all emotions"""
    pack = await crud.get_emoji_pack(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    custom_assets = {a.emotion_name: a for a in pack.assets}
    emotions = {}
    for e in EMOTION_NAMES:
        if e in custom_assets:
            a = custom_assets[e]
            emotions[e] = EmotionAssetInfo(
                url=get_asset_url(pack.id, e), file_type=a.file_type, is_custom=True,
                has_animation=a.has_animation, frame_count=a.frame_count, file_size=a.file_size,
            )
        else:
            emotions[e] = EmotionAssetInfo(
                url=get_library_emoji_url(pack.base_pack, e), file_type="png", is_custom=False
            )
    
    return EmojiPackDetail(
        id=pack.id, name=pack.name, description=pack.description,
        target_size=pack.target_size, base_pack=pack.base_pack,
        is_public=pack.is_public, is_featured=pack.is_featured,
        approval_status=pack.approval_status, download_count=pack.download_count,
        emotions=emotions, created_at=pack.created_at, updated_at=pack.updated_at,
    )


@router.patch("/{pack_id}", response_model=EmojiPackDetail)
async def update_emoji_pack(
    pack_id: str,
    data: EmojiPackUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Update emoji pack metadata"""
    pack = await crud.get_emoji_pack_by_owner(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    await crud.update_emoji_pack(db, pack, data)
    return await get_emoji_pack(pack_id, current_user, db)


@router.delete("/{pack_id}")
async def delete_emoji_pack(
    pack_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Delete emoji pack and all assets"""
    pack = await crud.get_emoji_pack_by_owner(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    pack_path = os.path.join(EMOJI_STORAGE_PATH, current_user["id"], pack_id)
    if os.path.exists(pack_path):
        import shutil
        shutil.rmtree(pack_path, ignore_errors=True)
    
    await crud.delete_emoji_pack(db, pack)
    return {"success": True, "message": "Emoji pack deleted"}


# ============ Emotion Upload Endpoints ============

@router.post("/{pack_id}/emotions/{emotion}", response_model=EmotionUploadResponse)
async def upload_emotion(
    pack_id: str,
    emotion: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    file: UploadFile = File(...),
):
    """Upload custom emoji for specific emotion"""
    if emotion not in EMOTION_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid emotion. Must be one of: {', '.join(EMOTION_NAMES)}")
    
    pack = await crud.get_emoji_pack_by_owner(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum: {MAX_FILE_SIZE // 1024}KB")
    
    has_animation = False
    frame_count = 1
    
    try:
        img = Image.open(io.BytesIO(content))
        
        if ext == "gif":
            try:
                frame_count = 0
                while True:
                    frame_count += 1
                    img.seek(frame_count)
            except EOFError:
                pass
            has_animation = frame_count > 1
            if frame_count > MAX_GIF_FRAMES:
                raise HTTPException(status_code=400, detail=f"GIF has too many frames ({frame_count}). Maximum: {MAX_GIF_FRAMES}")
        
        if img.width != pack.target_size or img.height != pack.target_size:
            img = img.resize((pack.target_size, pack.target_size), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            if ext == "gif" and has_animation:
                output.write(content)
            else:
                img.save(output, format="PNG" if ext == "png" else "GIF")
            content = output.getvalue()
            file_size = len(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
    
    file_path = get_storage_path(current_user["id"], pack_id, emotion, ext)
    with open(file_path, "wb") as f:
        f.write(content)
    
    await crud.create_or_update_pack_asset(
        db, pack_id=pack_id, emotion_name=emotion, file_path=file_path,
        file_type=ext, file_size=file_size, has_animation=has_animation,
        frame_count=frame_count, original_filename=file.filename,
    )
    
    return EmotionUploadResponse(
        emotion=emotion, url=get_asset_url(pack_id, emotion), file_type=ext,
        has_animation=has_animation, frame_count=frame_count, file_size=file_size,
    )


@router.delete("/{pack_id}/emotions/{emotion}")
async def delete_emotion(
    pack_id: str,
    emotion: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Reset emotion to default"""
    if emotion not in EMOTION_NAMES:
        raise HTTPException(status_code=400, detail="Invalid emotion name")
    
    pack = await crud.get_emoji_pack_by_owner(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    asset = await crud.get_pack_asset(db, pack_id, emotion)
    if not asset:
        raise HTTPException(status_code=404, detail="Custom emotion not found")
    
    if os.path.exists(asset.file_path):
        os.remove(asset.file_path)
    
    await crud.delete_pack_asset(db, asset)
    return {"success": True, "message": f"Emotion '{emotion}' reset to default"}


@router.get("/{pack_id}/emotions/{emotion}/file")
async def get_emotion_file(
    pack_id: str,
    emotion: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Download emotion file"""
    pack = await crud.get_emoji_pack(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    asset = await crud.get_pack_asset(db, pack_id, emotion)
    if not asset or not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="Emotion asset not found")
    
    media_type = "image/gif" if asset.file_type == "gif" else "image/png"
    return FileResponse(asset.file_path, media_type=media_type, filename=f"{emotion}.{asset.file_type}")


# ============ Sharing Endpoints ============

@router.post("/{pack_id}/share", response_model=ShareResponse)
async def share_emoji_pack(
    pack_id: str,
    data: ShareRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Share pack publicly"""
    pack = await crud.get_emoji_pack_by_owner(db, pack_id, current_user["id"])
    if not pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    if data.share_type == "public":
        pack = await crud.share_emoji_pack(db, pack, auto_approve=True)
        return ShareResponse(success=True, approval_status=pack.approval_status, message="Pack is now public")
    else:
        pack = await crud.unshare_emoji_pack(db, pack)
        return ShareResponse(success=True, approval_status=pack.approval_status, message="Pack is now private")


@router.post("/{pack_id}/clone", response_model=EmojiPackDetail)
async def clone_emoji_pack(
    pack_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Clone a public pack to user's collection"""
    source_pack = await crud.get_emoji_pack(db, pack_id, current_user["id"])
    if not source_pack:
        raise HTTPException(status_code=404, detail="Emoji pack not found")
    
    if source_pack.user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot clone your own pack")
    
    new_pack = await crud.clone_emoji_pack(db, source_pack, current_user["id"])
    return await get_emoji_pack(new_pack.id, current_user, db)
