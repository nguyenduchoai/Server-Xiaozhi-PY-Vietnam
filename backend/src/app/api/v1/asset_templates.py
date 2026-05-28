"""
Asset Template API Endpoints

Manages ESP32 device asset templates.
- Admin can create/update templates
- Users can list and download templates for their devices
"""

from typing import Annotated, Any
from datetime import datetime, timezone
from uuid import uuid4
import base64
import os

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.crud import crud_asset_template, crud_device
from app.models.asset_template import AssetTemplate, BoardType, ScreenType
from app.schemas.asset_template import (
    AssetTemplateCreate,
    AssetTemplateUpdate,
    AssetTemplateRead,
    AssetTemplateDetail,
    AssetTemplateListResponse,
    BoardTypeEnum,
    ScreenTypeEnum,
)
from app.schemas.base import SuccessResponse
from app.core.logger import get_logger

router = APIRouter(prefix="/asset-templates", tags=["asset-templates"])
logger = get_logger(__name__)

# Asset storage directory
ASSET_STORAGE_DIR = os.environ.get("ASSET_STORAGE_DIR", "/app/data/assets")


def require_superuser(current_user: dict) -> dict:
    """Dependency to check if user is superuser or admin"""
    is_superuser = current_user.get("is_superuser")
    role = current_user.get("role")
    
    if is_superuser:
        return current_user
        
    if role in ["admin", "super_admin"]:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


@router.get("", response_model=AssetTemplateListResponse)
async def list_asset_templates(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    board_type: BoardTypeEnum | None = Query(default=None),
    screen_type: ScreenTypeEnum | None = Query(default=None),
    search: str | None = Query(default=None),
) -> AssetTemplateListResponse:
    """
    List all active asset templates.
    
    Can filter by board_type, screen_type, or search by name.
    """
    try:
        filters = {"is_active": True}
        
        if board_type:
            filters["board_type"] = board_type.value
        if screen_type:
            filters["screen_type"] = screen_type.value
        
        # Build query
        stmt = select(AssetTemplate).where(AssetTemplate.is_active == True)
        
        if board_type:
            stmt = stmt.where(AssetTemplate.board_type == board_type.value)
        if screen_type:
            stmt = stmt.where(AssetTemplate.screen_type == screen_type.value)
        if search:
            stmt = stmt.where(AssetTemplate.name.ilike(f"%{search}%"))
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.order_by(AssetTemplate.download_count.desc(), AssetTemplate.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(stmt)
        templates = result.scalars().all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return AssetTemplateListResponse(
            success=True,
            data=[AssetTemplateRead.model_validate(t) for t in templates],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
    except Exception as e:
        logger.error(f"Error listing asset templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/board-types")
async def get_board_types() -> dict[str, Any]:
    """Get all supported board types"""
    return {
        "board_types": [
            {"value": bt.value, "label": bt.value.upper()} 
            for bt in BoardType
        ],
        "screen_types": [
            {"value": st.value, "label": st.value.replace("_", " ").title()} 
            for st in ScreenType
        ],
    }


@router.get("/{template_id}", response_model=AssetTemplateDetail)
async def get_asset_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> AssetTemplateDetail:
    """Get asset template details"""
    try:
        template = await crud_asset_template.get(db=db, id=template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset template not found"
            )
        
        result = AssetTemplateDetail.model_validate(template)
        result.download_url = f"/api/v1/asset-templates/{template_id}/download"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting asset template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{template_id}/download")
async def download_asset_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Response:
    """
    Download the assets.bin file from a template.
    
    Increments download counter.
    """
    try:
        template = await crud_asset_template.get(db=db, id=template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset template not found"
            )
        
        if not template.asset_file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No asset file available for this template"
            )
        
        # Read file
        file_path = template.asset_file_path
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset file not found on server"
            )
        
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Increment download count
        template.download_count += 1
        await db.commit()
        
        filename = f"assets_{template.board_type.value}_{template.screen_width}x{template.screen_height}.bin"
        
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading asset template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("", response_model=SuccessResponse[AssetTemplateRead], status_code=status.HTTP_201_CREATED)
async def create_asset_template(
    template_data: AssetTemplateCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[AssetTemplateRead]:
    """
    Create a new asset template (Admin only).
    
    Upload the assets.bin file as base64 encoded string.
    """
    require_superuser(current_user)
    
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        template_id = str(uuid4())
        
        # Save asset file if provided
        asset_file_path = None
        asset_file_size = 0
        
        if template_data.asset_file_base64:
            # Decode base64
            try:
                # Handle data URL format
                file_data = template_data.asset_file_base64
                if "," in file_data:
                    file_data = file_data.split(",")[1]
                
                file_bytes = base64.b64decode(file_data)
                asset_file_size = len(file_bytes)
                
                # Ensure storage directory exists
                os.makedirs(ASSET_STORAGE_DIR, exist_ok=True)
                
                # Save file
                asset_file_path = os.path.join(ASSET_STORAGE_DIR, f"{template_id}.bin")
                with open(asset_file_path, "wb") as f:
                    f.write(file_bytes)
                    
            except Exception as e:
                logger.error(f"Error saving asset file: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid asset file: {str(e)}"
                )
        
        # If setting as default, unset other defaults for same board type
        if template_data.is_default:
            stmt = select(AssetTemplate).where(
                AssetTemplate.board_type == template_data.board_type.value,
                AssetTemplate.is_default == True
            )
            result = await db.execute(stmt)
            existing_defaults = result.scalars().all()
            for t in existing_defaults:
                t.is_default = False
        
        # Create template
        template = AssetTemplate(
            id=template_id,
            name=template_data.name,
            description=template_data.description,
            board_type=template_data.board_type.value,
            screen_type=template_data.screen_type.value,
            screen_width=template_data.screen_width,
            screen_height=template_data.screen_height,
            asset_file_path=asset_file_path,
            asset_file_size=asset_file_size,
            preview_image_base64=template_data.preview_image_base64,
            wake_word=template_data.wake_word,
            font_name=template_data.font_name,
            emoji_style=template_data.emoji_style,
            is_active=True,
            is_default=template_data.is_default,
            created_by_user_id=user_id,
            created_at=datetime.now(timezone.utc),
        )
        
        db.add(template)
        await db.commit()
        await db.refresh(template)
        
        logger.info(f"Asset template created: {template.id} ({template.name})")
        
        return SuccessResponse(
            success=True,
            message="Asset template created successfully",
            data=AssetTemplateRead.model_validate(template)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating asset template: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/upload-file/{template_id}")
async def upload_asset_file(
    template_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
) -> SuccessResponse[dict]:
    """
    Upload asset file for an existing template (Admin only).
    
    Accepts .bin files up to 10MB.
    """
    require_superuser(current_user)
    
    try:
        template = await crud_asset_template.get(db=db, id=template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset template not found"
            )
        
        # Validate file
        if not file.filename or not file.filename.endswith(".bin"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .bin files are allowed"
            )
        
        # Read file content
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 10MB limit"
            )
        
        # Ensure storage directory exists
        os.makedirs(ASSET_STORAGE_DIR, exist_ok=True)
        
        # Delete old file if exists
        if template.asset_file_path and os.path.exists(template.asset_file_path):
            os.remove(template.asset_file_path)
        
        # Save new file
        asset_file_path = os.path.join(ASSET_STORAGE_DIR, f"{template_id}.bin")
        with open(asset_file_path, "wb") as f:
            f.write(content)
        
        # Update template
        template.asset_file_path = asset_file_path
        template.asset_file_size = len(content)
        template.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Asset file uploaded for template {template_id}: {len(content)} bytes")
        
        return SuccessResponse(
            success=True,
            message="Asset file uploaded successfully",
            data={"file_size": len(content)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading asset file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/{template_id}", response_model=SuccessResponse[AssetTemplateRead])
async def update_asset_template(
    template_id: str,
    update_data: AssetTemplateUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[AssetTemplateRead]:
    """Update an asset template (Admin only)"""
    require_superuser(current_user)
    
    try:
        template = await crud_asset_template.get(db=db, id=template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset template not found"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Handle asset file update
        if "asset_file_base64" in update_dict and update_dict["asset_file_base64"]:
            file_data = update_dict.pop("asset_file_base64")
            if "," in file_data:
                file_data = file_data.split(",")[1]
            
            file_bytes = base64.b64decode(file_data)
            
            os.makedirs(ASSET_STORAGE_DIR, exist_ok=True)
            asset_file_path = os.path.join(ASSET_STORAGE_DIR, f"{template_id}.bin")
            with open(asset_file_path, "wb") as f:
                f.write(file_bytes)
            
            template.asset_file_path = asset_file_path
            template.asset_file_size = len(file_bytes)
        
        # Handle default flag
        if update_dict.get("is_default"):
            stmt = select(AssetTemplate).where(
                AssetTemplate.board_type == (update_dict.get("board_type") or template.board_type),
                AssetTemplate.is_default == True,
                AssetTemplate.id != template_id
            )
            result = await db.execute(stmt)
            for t in result.scalars().all():
                t.is_default = False
        
        for key, value in update_dict.items():
            if hasattr(template, key) and key not in ["asset_file_base64"]:
                setattr(template, key, value)
        
        template.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(template)
        
        return SuccessResponse(
            success=True,
            message="Asset template updated",
            data=AssetTemplateRead.model_validate(template)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating asset template: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{template_id}")
async def delete_asset_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    permanent: bool = Query(default=False),
) -> SuccessResponse[None]:
    """
    Delete an asset template (Admin only).
    
    By default, soft-deletes (sets is_active=False).
    Use permanent=true to permanently delete.
    """
    require_superuser(current_user)
    
    try:
        template = await crud_asset_template.get(db=db, id=template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset template not found"
            )
        
        if permanent:
            # Delete file
            if template.asset_file_path and os.path.exists(template.asset_file_path):
                os.remove(template.asset_file_path)
            
            await db.delete(template)
            await db.commit()
            message = "Asset template permanently deleted"
        else:
            template.is_active = False
            template.updated_at = datetime.now(timezone.utc)
            await db.commit()
            message = "Asset template deactivated"
        
        logger.info(f"Asset template deleted: {template_id} (permanent={permanent})")
        
        return SuccessResponse(
            success=True,
            message=message,
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting asset template: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/for-device/{device_id}")
async def get_templates_for_device(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> AssetTemplateListResponse:
    """
    Get compatible asset templates for a specific device.
    
    Matches templates based on device's board type.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        
        # Get device
        device = await crud_device.get(db=db, id=device_id)
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        # Check ownership
        if device.user_id != user_id and not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get device board type from board field or default to esp32s3
        board_type = "esp32s3"  # Default
        if device.board:
            chip_lower = device.board.lower()
            if "esp32c3" in chip_lower or "c3" in chip_lower:
                board_type = "esp32c3"
            elif "esp32c6" in chip_lower or "c6" in chip_lower:
                board_type = "esp32c6"
            elif "esp32s3" in chip_lower or "s3" in chip_lower:
                board_type = "esp32s3"
            elif "esp32" in chip_lower:
                board_type = "esp32"
        
        # Get compatible templates
        stmt = (
            select(AssetTemplate)
            .where(AssetTemplate.is_active == True)
            .where(AssetTemplate.board_type == board_type)
            .order_by(AssetTemplate.is_default.desc(), AssetTemplate.download_count.desc())
        )
        
        result = await db.execute(stmt)
        templates = result.scalars().all()
        
        return AssetTemplateListResponse(
            success=True,
            data=[AssetTemplateRead.model_validate(t) for t in templates],
            total=len(templates),
            page=1,
            page_size=100,
            total_pages=1,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting templates for device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
