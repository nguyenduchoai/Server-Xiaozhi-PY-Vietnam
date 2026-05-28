"""
Firmware Management API Routes.

Endpoints for uploading, managing, and deploying firmware updates
to ESP32 devices at scale.
"""

import hashlib
import os
import aiofiles
from pathlib import Path
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.crud.crud_firmware import crud_firmware, crud_firmware_deployment
from app.models.firmware import BoardType, DeploymentStatus
from app.schemas.firmware import (
    FirmwareCreate,
    FirmwareUpdate,
    FirmwareRead,
    FirmwareList,
    DeploymentCreate,
    DeploymentUpdate,
    DeploymentRead,
    DeploymentList,
    DeviceUpdateCheck,
    DeviceUpdateResponse,
)
from app.core.logger import get_logger

router = APIRouter(prefix="/firmware", tags=["firmware"])
logger = get_logger(__name__)

# Firmware storage path (configurable via env)
FIRMWARE_STORAGE_PATH = Path(os.environ.get("FIRMWARE_STORAGE_PATH", "/app/data/firmware"))
ALLOWED_EXTENSIONS = {".bin", ".elf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


async def _calculate_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of file."""
    sha256 = hashlib.sha256()
    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


# ============ Firmware Endpoints ============


@router.post(
    "/upload",
    response_model=FirmwareRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload new firmware",
)
async def upload_firmware(
    file: Annotated[UploadFile, File(description="Firmware binary file (.bin)")],
    version: Annotated[str, Form(description="Firmware version (e.g., 1.0.0)")],
    board_type: Annotated[BoardType, Form(description="Target board type")] = BoardType.ALL,
    release_notes: Annotated[Optional[str], Form(description="Release notes")] = None,
    is_active: Annotated[bool, Form(description="Whether firmware is active")] = True,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload new firmware file.
    
    - **file**: Binary firmware file (.bin or .elf)
    - **version**: Semantic version string
    - **board_type**: Target board type (esp32, esp32s3, esp32c3, all)
    - **release_notes**: Optional release notes
    - **is_active**: Whether firmware should be active for updates
    """
    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB",
        )
    
    # Check version doesn't exist for this board type
    existing = await crud_firmware.get_by_version(db, version, board_type)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Firmware version {version} for {board_type.value} already exists",
        )
    
    # Create storage directory
    FIRMWARE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid4())[:8]
    file_name = f"{board_type.value}_{version}_{file_id}{file_ext}"
    file_path = FIRMWARE_STORAGE_PATH / file_name
    
    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)
    
    # Calculate checksum
    checksum = hashlib.sha256(file_content).hexdigest()
    
    # Create database entry
    firmware_in = FirmwareCreate(
        version=version,
        board_type=board_type,
        release_notes=release_notes,
        is_active=is_active,
    )
    
    firmware = await crud_firmware.create(
        db,
        obj_in=firmware_in,
        file_path=str(file_path),
        file_name=file_name,
        checksum=checksum,
        size=len(file_content),
        created_by=current_user["id"],
    )
    
    logger.info(
        f"Firmware uploaded: {version} for {board_type.value} by {current_user['id']}"
    )
    
    return firmware


@router.get(
    "",
    response_model=FirmwareList,
    summary="List all firmware versions",
)
async def list_firmware(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    board_type: Optional[BoardType] = Query(None, description="Filter by board type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all firmware versions with pagination and filtering."""
    skip = (page - 1) * page_size
    result = await crud_firmware.get_multi(
        db,
        skip=skip,
        limit=page_size,
        board_type=board_type,
        is_active=is_active,
    )
    
    return FirmwareList(
        items=result["data"],
        total=result["total_count"],
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{firmware_id}",
    response_model=FirmwareRead,
    summary="Get firmware details",
)
async def get_firmware(
    firmware_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get firmware details by ID."""
    firmware = await crud_firmware.get(db, firmware_id)
    if not firmware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firmware not found",
        )
    return firmware


@router.patch(
    "/{firmware_id}",
    response_model=FirmwareRead,
    summary="Update firmware metadata",
)
async def update_firmware(
    firmware_id: str,
    update_data: FirmwareUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update firmware metadata (release notes, active status, etc.)."""
    firmware = await crud_firmware.get(db, firmware_id)
    if not firmware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firmware not found",
        )
    
    updated = await crud_firmware.update(db, db_obj=firmware, obj_in=update_data)
    logger.info(f"Firmware {firmware_id} updated by {current_user['id']}")
    return updated


@router.delete(
    "/{firmware_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate firmware",
)
async def delete_firmware(
    firmware_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Deactivate firmware (soft delete)."""
    success = await crud_firmware.delete(db, id=firmware_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firmware not found",
        )
    logger.info(f"Firmware {firmware_id} deactivated by {current_user['id']}")


@router.get(
    "/{firmware_id}/download",
    summary="Download firmware file",
)
async def download_firmware(
    firmware_id: str,
    db: AsyncSession = Depends(async_get_db),
):
    """Download firmware binary file."""
    firmware = await crud_firmware.get(db, firmware_id)
    if not firmware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firmware not found",
        )
    
    if not firmware.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Firmware is no longer available",
        )
    
    file_path = Path(firmware.file_path)
    if not file_path.exists():
        logger.error(f"Firmware file not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firmware file not found on server",
        )
    
    # Increment download count
    await crud_firmware.increment_download_count(db, firmware_id)
    
    return FileResponse(
        path=file_path,
        filename=firmware.file_name,
        media_type="application/octet-stream",
        headers={
            "X-Checksum": firmware.checksum,
            "X-Version": firmware.version,
        },
    )


# ============ Deployment Endpoints ============


@router.post(
    "/deployments",
    response_model=DeploymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new deployment",
)
async def create_deployment(
    deployment_in: DeploymentCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new firmware deployment.
    
    - **firmware_id**: ID of firmware to deploy
    - **target_type**: all, board, user, or device
    - **target_value**: Board type, user ID, or comma-separated MACs
    - **rollout_percentage**: Percentage of devices to target (gradual rollout)
    - **scheduled_at**: Optional scheduled time (null = immediate)
    """
    # Verify firmware exists and is active
    firmware = await crud_firmware.get(db, deployment_in.firmware_id)
    if not firmware:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firmware not found",
        )
    
    if not firmware.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deploy inactive firmware",
        )
    
    deployment = await crud_firmware_deployment.create(
        db,
        obj_in=deployment_in,
        created_by=current_user["id"],
    )
    
    # Add firmware version to response
    deployment_dict = {
        **deployment.__dict__,
        "firmware_version": firmware.version,
    }
    
    logger.info(
        f"Deployment created: {deployment.id} for firmware {firmware.version} "
        f"by {current_user['id']}"
    )
    
    return DeploymentRead.model_validate(deployment_dict)


@router.get(
    "/deployments",
    response_model=DeploymentList,
    summary="List deployments",
)
async def list_deployments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[DeploymentStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    firmware_id: Optional[str] = Query(None, description="Filter by firmware"),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all deployments with pagination and filtering."""
    skip = (page - 1) * page_size
    result = await crud_firmware_deployment.get_multi(
        db,
        skip=skip,
        limit=page_size,
        status=status_filter,
        firmware_id=firmware_id,
    )
    
    # Add firmware version to each deployment
    items = []
    for deployment in result["data"]:
        deployment_dict = {
            **deployment.__dict__,
            "firmware_version": deployment.firmware.version if deployment.firmware else None,
        }
        items.append(DeploymentRead.model_validate(deployment_dict))
    
    return DeploymentList(
        items=items,
        total=result["total_count"],
        page=page,
        page_size=page_size,
    )


@router.get(
    "/deployments/{deployment_id}",
    response_model=DeploymentRead,
    summary="Get deployment details",
)
async def get_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get deployment details by ID."""
    deployment = await crud_firmware_deployment.get(db, deployment_id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    
    deployment_dict = {
        **deployment.__dict__,
        "firmware_version": deployment.firmware.version if deployment.firmware else None,
    }
    
    return DeploymentRead.model_validate(deployment_dict)


@router.patch(
    "/deployments/{deployment_id}",
    response_model=DeploymentRead,
    summary="Update deployment",
)
async def update_deployment(
    deployment_id: str,
    update_data: DeploymentUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update deployment status or rollout percentage.
    
    Use this to:
    - Pause a deployment (status=paused)
    - Cancel a deployment (status=cancelled)
    - Resume a deployment (status=rolling_out)
    - Adjust rollout percentage
    """
    deployment = await crud_firmware_deployment.get(db, deployment_id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    
    # Validate status transitions
    if update_data.status:
        current_status = deployment.status
        new_status = update_data.status
        
        # Cannot change completed/failed deployments
        if current_status in (DeploymentStatus.COMPLETED, DeploymentStatus.FAILED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change status of {current_status.value} deployment",
            )
        
        # Cannot go back to pending
        if new_status == DeploymentStatus.PENDING and current_status != DeploymentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revert deployment to pending status",
            )
    
    updated = await crud_firmware_deployment.update(
        db, db_obj=deployment, obj_in=update_data
    )
    
    updated_dict = {
        **updated.__dict__,
        "firmware_version": deployment.firmware.version if deployment.firmware else None,
    }
    
    logger.info(
        f"Deployment {deployment_id} updated by {current_user['id']}: {update_data}"
    )
    
    return DeploymentRead.model_validate(updated_dict)


# ============ Device Update Check ============


@router.post(
    "/check-update",
    response_model=DeviceUpdateResponse,
    summary="Check for firmware update (device endpoint)",
)
async def check_firmware_update(
    check_data: DeviceUpdateCheck,
    db: AsyncSession = Depends(async_get_db),
):
    """
    Check if firmware update is available for device.
    
    This endpoint is called by devices to check for updates.
    It checks both the latest firmware and any active deployments
    targeting the device.
    """
    # Map board type string to enum
    try:
        board_type = BoardType(check_data.board_type)
    except ValueError:
        board_type = BoardType.ESP32  # Default
    
    # Get latest firmware for this board type
    latest = await crud_firmware.get_latest(db, board_type)
    
    if not latest:
        return DeviceUpdateResponse(
            has_update=False,
            current_version=check_data.current_version,
        )
    
    # Simple version comparison (assumes semver-like format)
    has_update = latest.version != check_data.current_version
    
    if not has_update:
        return DeviceUpdateResponse(
            has_update=False,
            current_version=check_data.current_version,
        )
    
    # Generate download URL
    download_url = f"/api/v1/firmware/{latest.id}/download"
    
    return DeviceUpdateResponse(
        has_update=True,
        current_version=check_data.current_version,
        latest_version=latest.version,
        download_url=download_url,
        checksum=latest.checksum,
        size=latest.size,
        release_notes=latest.release_notes,
    )
