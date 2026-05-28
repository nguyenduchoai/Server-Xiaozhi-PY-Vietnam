"""Device activation API for ESP32 and IoT devices.

Exposes endpoint for devices to request a 6-digit activation code.
The code is displayed on device screen; user enters code in app to bind device to agent.

Flow:
1. ESP32 calls POST /api/v1/devices/request-activation with mac_address + device_data
2. Backend generates 6-digit code, stores:
   - activation:{code} -> mac_address (for lookup)
   - device_activation:{mac_address} -> {code, device_data} (for binding)
3. ESP32 displays code on screen
4. User opens app, enters code via POST /api/v1/agents/{agent_id}/bind-device
5. Backend binds device to agent, clears cache
"""

import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_redis_client, async_get_db as get_async_db, get_current_user
from ...ai.utils.activation_cache import (
    store_activation_code,
    store_device_activation_data,
    get_device_activation_data,
    get_mac_from_code,
    delete_activation_code,
    ACTIVATION_TTL,
)
from ...core.logger import get_logger
from ...core.rate_limit import rate_limit_dependency
from ...crud.crud_device import crud_device
from ...schemas.device import DeviceRead
from ...services.intercom_service import get_intercom_service
from ...services.quota_service import QuotaService

logger = get_logger(__name__)

router = APIRouter(prefix="/devices", tags=["devices"])


# ========== Schemas ==========


class ActivationRequest(BaseModel):
    """Request body for device activation code request."""

    mac_address: Annotated[
        str,
        Field(
            min_length=11,
            max_length=17,
            examples=["AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"],
            description="Device MAC address",
        ),
    ]
    device_name: str | None = Field(default=None, max_length=255)
    board: str | None = Field(
        default=None, max_length=100, examples=["ESP32", "ESP32-S3"]
    )
    firmware_version: str | None = Field(default=None, max_length=50)


class ActivationResponse(BaseModel):
    """Response containing the 6-digit activation code."""

    code: Annotated[
        str,
        Field(
            min_length=6,
            max_length=8,
            examples=["123456"],
            description="6-digit activation code to display on device screen",
        ),
    ]
    expires_in: int = Field(
        default=ACTIVATION_TTL,
        description="Code expiration time in seconds",
    )
    message: str = Field(
        default="Display this code on device screen. User will enter it in app to bind device.",
    )


# ========== Helpers ==========


def generate_activation_code() -> str:
    """Generate an 8-character alphanumeric activation code (BE-H3 hardening).

    Uses cryptographically secure random.
    Charset excludes ambiguous chars (0, O, 1, I, l) to ease user entry.
    Entropy: 32^8 ≈ 1.1 trillion combinations (vs old 6-digit 900K).
    Combined with /devices/activate rate-limit + lockout, brute force
    becomes infeasible.

    Returns:
        str: 8-char uppercase alphanumeric code, e.g. "K7XQ4PMR"
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 31 chars, no 0/O/1/I/L
    return "".join(secrets.choice(alphabet) for _ in range(8))


# ========== Endpoints ==========


@router.get("", response_model=dict)
async def list_devices(
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = 1,
    page_size: int = 100,
):
    """List all devices owned by current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        PaginatedResponse with devices
    """
    
    try:
        result = await crud_device.get_multi(
            db=db,
            user_id=current_user["id"],
            offset=(page - 1) * page_size,
            limit=page_size,
            schema_to_select=DeviceRead,
        )
        
        devices = result.get("data", [])
        total = result.get("total_count", 0)
        
        return {
            "success": True,
            "data": devices,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }
        
    except Exception as e:
        logger.error(f"Error listing devices: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi lấy danh sách thiết bị")


@router.post("/request-activation", response_model=ActivationResponse, status_code=200)
async def request_activation_code(
    request: ActivationRequest,
    redis: Annotated[Redis, Depends(get_redis_client)],
    _rate_limit: None = Depends(rate_limit_dependency(calls=5, period=60, key_prefix="device_activation")),
) -> ActivationResponse:
    """Request a 6-digit activation code for device binding.

    Called by ESP32/IoT device on first boot or when user initiates pairing.
    The code should be displayed on device screen for user to enter in app.

    Flow:
    1. Check if device already has a pending activation code
    2. If yes, return existing code (avoid code spam)
    3. If no, generate new 6-digit code
    4. Store code -> mac_address mapping
    5. Store mac_address -> {code, device_data} bundle
    6. Return code to device

    Args:
        request: ActivationRequest with mac_address and optional device info
        redis: Redis client for cache operations

    Returns:
        ActivationResponse with 6-digit code and expiration info

    Raises:
        HTTPException 503: If Redis is unavailable
        HTTPException 500: On unexpected errors
    """
    mac_address = request.mac_address.upper()  # Normalize MAC to uppercase

    try:
        # Check if device already has pending activation
        existing_data = await get_device_activation_data(redis, mac_address)
        if existing_data and existing_data.get("code"):
            logger.info(
                f"Returning existing activation code for MAC {mac_address}"
            )
            return ActivationResponse(
                code=existing_data["code"],
                expires_in=ACTIVATION_TTL,
                message="Existing activation code returned. Display on device screen.",
            )

        # Generate new activation code
        code = generate_activation_code()
        logger.debug(f"Generated activation code {code} for MAC {mac_address}")

        # Prepare device data for later binding
        device_data = {
            "device_name": request.device_name,
            "board": request.board,
            "firmware_version": request.firmware_version,
            "status": "pending_activation",
        }

        # Store activation code -> mac_address (for lookup by code)
        await store_activation_code(redis, mac_address, code, ttl=ACTIVATION_TTL)

        # Store mac_address -> {code, device_data} (for binding)
        await store_device_activation_data(
            redis, mac_address, code, device_data, ttl=ACTIVATION_TTL
        )

        logger.info(
            f"Activation code {code} created for device {mac_address} "
            f"(board: {request.board}, firmware: {request.firmware_version})"
        )

        return ActivationResponse(
            code=code,
            expires_in=ACTIVATION_TTL,
            message="Display this code on device screen. User will enter it in app to bind device.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate activation code for {mac_address}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate activation code. Please try again.",
        )


@router.get("/activation-status/{mac_address}")
async def get_activation_status(
    mac_address: str,
    redis: Annotated[Redis, Depends(get_redis_client)],
    _rate_limit: None = Depends(rate_limit_dependency(calls=10, period=60, key_prefix="activation_status")),
) -> dict:
    """Check if device has pending activation code.

    Useful for ESP32 to check if activation is still pending or completed.

    Args:
        mac_address: Device MAC address
        redis: Redis client

    Returns:
        dict with status: "pending", "not_found"
    """
    mac_address = mac_address.upper()

    try:
        existing_data = await get_device_activation_data(redis, mac_address)

        if existing_data and existing_data.get("code"):
            return {
                "status": "pending",
                "code": existing_data["code"],
                "message": "Activation code is still valid. Waiting for user to bind.",
            }

        return {
            "status": "not_found",
            "message": "No pending activation. Device may already be bound or code expired.",
        }

    except Exception as e:
        logger.error(f"Failed to check activation status for {mac_address}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check activation status")


# ========== User Activation Endpoint ==========


class UserActivateRequest(BaseModel):
    """Request body for user to activate device with code or MAC address."""
    code: Annotated[
        str,
        Field(
            min_length=6,
            max_length=17,
            examples=["123456", "AA:BB:CC:DD:EE:FF"],
            description="6-digit activation code or 12/17-char MAC address",
        ),
    ]


class UserActivateResponse(BaseModel):
    """Response after successful device activation."""
    id: str
    mac_address: str
    name: str | None
    board: str | None
    message: str


@router.post("/activate", response_model=UserActivateResponse, status_code=200)
async def activate_device_by_code(
    request: UserActivateRequest,
    redis: Annotated[Redis, Depends(get_redis_client)],
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Activate a device using the 6-digit code displayed on device screen.
    
    This creates the device in the database without binding to any agent.
    User can later assign the device to an agent.
    
    Args:
        request: Contains the 6-digit activation code
        redis: Redis client
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserActivateResponse with device info
        
    Raises:
        HTTPException 400: Code not found or expired
        HTTPException 500: Internal error
    """
    
    code = request.code.strip()
    
    try:
        import re
        
        # Check if the input is a MAC address (format: AABBCCDDEEFF or AA:BB:CC:DD:EE:FF)
        normalized_code = code.replace(":", "").replace("-", "").upper()
        is_mac = len(normalized_code) == 12 and all(c in "0123456789ABCDEF" for c in normalized_code)
        
        if is_mac:
            # Reformat to standard MAC AA:BB:CC:DD:EE:FF
            mac_address = ":".join(normalized_code[i:i+2] for i in range(0, 12, 2))
            logger.info(f"User binding device directly by MAC address: {mac_address}")
            
            # Default device data for direct MAC binding
            device_data = {
                "device_name": f"Device {normalized_code[-6:]}",
                "board": "ESP32",
                "firmware_version": "Unknown",
                "status": "active",
            }
        else:
            # 1. Get mac_address from activation code
            mac_address = await get_mac_from_code(redis, code)
            if not mac_address:
                logger.warning(f"Activation code {code} not found or expired")
                raise HTTPException(
                    status_code=400,
                    detail="Mã kích hoạt không hợp lệ hoặc đã hết hạn",
                )
            
            logger.debug(f"Retrieved mac_address: {mac_address} for code: {code}")
            
            # 2. Get device data from cache
            device_data = await get_device_activation_data(redis, mac_address)
            if not device_data:
                logger.warning(f"Device data not found for mac_address: {mac_address}")
                raise HTTPException(
                    status_code=400,
                    detail="Dữ liệu thiết bị không tìm thấy",
                )
            
            logger.debug(f"Retrieved device data for mac: {mac_address}")
        
        # Check device quota using QuotaService
        quota_service = QuotaService(db)
        can_create, message = await quota_service.can_create_device(current_user["id"])
        if not can_create:
            raise HTTPException(status_code=403, detail=message)
        
        # 3. Create or get device (without agent binding)
        try:
            device = await crud_device.create_device_from_activation(
                db=db,
                mac_address=mac_address,
                user_id=current_user["id"],
                device_data=device_data,
            )
        except ValueError as e:
            logger.warning(f"Device activation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # 4. Clean up activation cache
        try:
            await delete_activation_code(redis, code)
            # Keep device_data for potential agent binding later
            logger.debug(f"Cleaned up activation code: {code}")
        except Exception as e:
            logger.warning(f"Failed to clean up cache: {str(e)}")
        
        logger.info(f"Device {device.id} activated for user {current_user['id']}")
        
        return UserActivateResponse(
            id=str(device.id),
            mac_address=device.mac_address,
            name=device.device_name,
            board=device.board,
            message="Thiết bị đã được kích hoạt thành công",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating device: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi kích hoạt thiết bị")


@router.get("/{device_id}/capabilities", response_model=dict)
async def get_device_capabilities(
    device_id: str,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Return the hardware capability profile reported by the device's FW.

    Capabilities are populated automatically on every WS/MQTT hello (see
    `app.ai.handle.helloHandle`) — the FW sends a `capabilities` block via
    `BoardCapability::ToJson()`. Admin UI uses this to gate features
    (camera/meeting/vision/etc.) per device.

    Returns:
        {
            "capabilities": {...} | null,
            "updated_at": "2026-05-08T01:23:45+00:00" | null
        }
    """
    from sqlalchemy import select
    from ...models.device import Device

    result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    # Authorization: owner OR admin
    is_admin = current_user.get("is_superuser") or current_user.get("role") == "admin"
    if str(device.user_id) != str(current_user.get("id")) and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "capabilities": device.capabilities,
        "updated_at": (
            device.capabilities_updated_at.isoformat()
            if device.capabilities_updated_at else None
        ),
    }


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a device by ID.
    
    Only the device owner can delete it.
    
    Args:
        device_id: Device UUID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException 404: Device not found
        HTTPException 403: Not device owner
    """
    
    try:
        # Get device to verify ownership
        device = await crud_device.get(
            db=db,
            id=device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
        
        if device.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xóa thiết bị này")
        
        # Delete device
        await crud_device.delete(db=db, id=device_id)
        
        logger.info(f"Device {device_id} deleted by user {current_user['id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi xóa thiết bị")


class DeviceUpdateRequest(BaseModel):
    """Request body for updating device."""
    device_name: str | None = Field(default=None, max_length=255, description="Tên thiết bị")
    board: str | None = Field(default=None, max_length=100, description="Loại board (ESP32, Raspberry Pi, etc.)")
    status: str | None = Field(default=None, max_length=50, description="Trạng thái thiết bị")
    intercom_enabled: bool | None = Field(default=None, description="Cho phép nhận cuộc gọi Intercom từ bạn bè")
    background_image_url: str | None = Field(default=None, description="Ảnh nền hiển thị trên thiết bị khi rảnh rỗi")
    features: dict | None = Field(default=None, description="Tùy chỉnh tính năng (Sales, Quảng Cáo, v.v.)")


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: str,
    request: DeviceUpdateRequest,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update device information.
    
    Only the device owner can update it.
    
    Args:
        device_id: Device UUID
        request: Fields to update (device_name, board, status)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated DeviceRead
        
    Raises:
        HTTPException 404: Device not found
        HTTPException 403: Not device owner
    """
    
    try:
        # Get device to verify ownership
        device = await crud_device.get(
            db=db,
            id=device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
        
        if device.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật thiết bị này")
        
        # Build update data
        update_data = {}
        if request.device_name is not None:
            update_data["device_name"] = request.device_name
        if request.board is not None:
            update_data["board"] = request.board
        if request.status is not None:
            update_data["status"] = request.status
        if request.intercom_enabled is not None:
            update_data["intercom_enabled"] = request.intercom_enabled
        if request.background_image_url is not None:
            update_data["background_image_url"] = request.background_image_url
        if request.features is not None:
            # Merge with existing features if they exist
            existing_features = device.features or {}
            update_data["features"] = {**existing_features, **request.features}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Không có dữ liệu cập nhật")
        
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update device
        await crud_device.update(
            db=db,
            object=update_data,
            id=device_id,
        )
        await db.commit()
        
        logger.info(f"Device {device_id} updated by user {current_user['id']}: {update_data}")
        
        # Clear IdleBannerManager cache if features changed
        if request.features is not None:
            try:
                from app.services.idle_banner_manager import get_idle_banner_manager
                mgr = get_idle_banner_manager()
                if mgr and device.mac_address in mgr._device_state:
                    del mgr._device_state[device.mac_address]
                    logger.info(f"Cleared IdleBannerManager state for {device.mac_address} due to features update")
            except Exception as e:
                logger.warning(f"Could not clear IdleBannerManager state: {e}")
                
        # Fetch fresh device data
        device = await crud_device.get(
            db=db,
            id=device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        return device
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device: {str(e)}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi cập nhật thiết bị")


# ========== Intercom Direct Test Endpoint ==========


class IntercomRequest(BaseModel):
    """Request body for direct intercom message."""
    target_device_id: str = Field(..., description="Target device ID to send message to")
    message: str = Field(..., max_length=500, description="Message to send")


@router.post("/{device_id}/intercom", status_code=200)
async def send_intercom_message(
    device_id: str,
    request_body: IntercomRequest,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request = None,
):
    """Send direct intercom message from one device to another.
    
    This bypasses the AI and sends the message directly via MQTT.
    Used for testing intercom functionality.
    
    Args:
        device_id: Source device ID (sending device)
        request_body: Contains target_device_id and message
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    
    try:
        # Verify source device ownership
        source_device = await crud_device.get(
            db=db,
            id=device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        if not source_device:
            raise HTTPException(status_code=404, detail="Thiết bị nguồn không tồn tại")
        
        if source_device.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Bạn không có quyền điều khiển thiết bị này")
        
        # Get target device
        target_device = await crud_device.get(
            db=db,
            id=request_body.target_device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        if not target_device:
            raise HTTPException(status_code=404, detail="Thiết bị đích không tồn tại")
        
        # Verify target device belongs to same user (for now, can expand for friends later)
        if target_device.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Bạn không có quyền gửi tin nhắn đến thiết bị này")
        
        # Get MQTT service from app state
        mqtt_service = getattr(request.app.state, "mqtt_service", None) if request else None
        
        # Get intercom service and inject MQTT
        intercom_service = get_intercom_service()
        if mqtt_service:
            intercom_service.set_mqtt_service(mqtt_service)
        
        success = await intercom_service.send_direct_message(
            from_device_id=device_id,
            from_device_name=source_device.device_name or source_device.mac_address,
            to_device_mac=target_device.mac_address,
            message=request_body.message,
        )
        
        if success:
            logger.info(f"Intercom message sent from {device_id} to {request_body.target_device_id}")
            return {
                "success": True,
                "message": f"Đã gửi tin nhắn Intercom đến {target_device.device_name or target_device.mac_address}",
                "device_id": device_id,
                "target_device_id": request_body.target_device_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Không thể gửi tin nhắn Intercom")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending intercom message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi gửi Intercom: {str(e)}")


# ========== Voice Intercom Endpoint ==========


@router.post("/{device_id}/voice-intercom", status_code=200)
async def send_voice_intercom(
    device_id: str,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request,
    audio: "UploadFile" = None,
    target_device_id: str = None,
):
    """Send voice intercom message - converts audio to text and sends to target device.
    
    Flow:
    1. Receive audio file from browser (webm/opus format)
    2. Convert to text using ASR 
    3. Send text to target device via MQTT intercom
    4. Target device plays TTS
    
    Args:
        device_id: Source device ID (sending device)
        audio: Audio file (webm/opus from browser MediaRecorder)
        target_device_id: Target device ID to send message to
        
    Returns:
        Success with transcription text
    """
    
    try:
        # Parse form data
        form = await request.form()
        audio_file = form.get("audio")
        target_device_id = form.get("target_device_id")
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="Audio file is required")
        if not target_device_id:
            raise HTTPException(status_code=400, detail="Target device ID is required")
        
        # Verify source device ownership
        source_device = await crud_device.get(
            db=db,
            id=device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        if not source_device:
            raise HTTPException(status_code=404, detail="Thiết bị nguồn không tồn tại")
        
        if source_device.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Bạn không có quyền điều khiển thiết bị này")
        
        # Get target device
        target_device = await crud_device.get(
            db=db,
            id=target_device_id,
            schema_to_select=DeviceRead,
            return_as_model=True,
        )
        
        if not target_device:
            raise HTTPException(status_code=404, detail="Thiết bị đích không tồn tại")
        
        # Verify target device belongs to same user (for now)
        if target_device.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Bạn không có quyền gửi tin nhắn đến thiết bị này")
        
        # Read audio data
        audio_content = await audio_file.read()
        logger.info(f"Voice intercom: Received {len(audio_content)} bytes of audio")
        
        # TODO: Process audio through ASR to get text
        # For now, use a placeholder - in production, integrate with ASR service
        transcription = "[Voice message - ASR integration pending]"
        
        # Try to use ASR if available
        try:
            import tempfile
            import os
            import subprocess
            
            # Save temp file for ASR
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_content)
                tmp_path = tmp.name
            
            try:
                # Convert webm to wav using ffmpeg
                wav_path = tmp_path.replace(".webm", ".wav")
                result = subprocess.run([
                    "ffmpeg", "-y", "-i", tmp_path,
                    "-ar", "16000", "-ac", "1", "-f", "wav", wav_path
                ], capture_output=True, timeout=30)
                
                if result.returncode != 0:
                    logger.warning(f"ffmpeg conversion failed: {result.stderr.decode()}")
                    raise Exception("ffmpeg conversion failed")
                
                # Use standard ASR provider from config (VietNamASRLocal / Sherpa ONNX)
                from ...ai.module_factory import initialize_asr
                from ...config.config_loader import load_config
                
                sys_config = load_config()
                asr_provider = initialize_asr(sys_config)
                
                if asr_provider:
                    import wave
                    with open(wav_path, "rb") as f:
                        wav_reader = wave.open(f, "rb")
                        pcm_data = wav_reader.readframes(wav_reader.getnframes())
                        wav_reader.close()
                    
                    # Convert to frames (960 samples per frame at 16kHz = 60ms)
                    frame_size = 960 * 2  # 16-bit PCM
                    frames = [pcm_data[i:i+frame_size] for i in range(0, len(pcm_data), frame_size)]
                    
                    text, _ = await asr_provider.speech_to_text(frames, "intercom", audio_format="pcm")
                    if text:
                        transcription = text
                        logger.info(f"Voice intercom ASR result: {transcription}")
                else:
                    logger.warning("No ASR provider configured for intercom")
                
                # Cleanup
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
        except Exception as asr_error:
            logger.warning(f"ASR processing failed, using placeholder: {asr_error}")
        
        # Get MQTT service from app state
        mqtt_service = getattr(request.app.state, "mqtt_service", None)
        
        # Get intercom service and inject MQTT
        intercom_service = get_intercom_service()
        if mqtt_service:
            intercom_service.set_mqtt_service(mqtt_service)
        
        # Send intercom message
        success = await intercom_service.send_direct_message(
            from_device_id=device_id,
            from_device_name=source_device.device_name or source_device.mac_address,
            to_device_mac=target_device.mac_address,
            message=transcription,
        )
        
        if success:
            logger.info(f"Voice intercom sent from {device_id} to {target_device_id}: {transcription[:50]}...")
            return {
                "success": True,
                "transcription": transcription,
                "message": f"Đã gửi voice intercom: {transcription}",
                "device_id": device_id,
                "target_device_id": target_device_id,
            }
        else:
            raise HTTPException(status_code=500, detail="Không thể gửi voice intercom")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending voice intercom: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi gửi Voice Intercom: {str(e)}")


# ========== Agent-Device Many-to-Many Endpoints ==========


class AssignAgentRequest(BaseModel):
    """Request to assign an agent to a device."""
    agent_id: str = Field(..., max_length=36, description="Agent UUID to assign")
    set_active: bool = Field(default=False, description="Set this agent as active immediately")


@router.get("/{device_id}/agents")
async def list_device_agents(
    device_id: str,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """List all agents assigned to a device.
    
    Returns agents with their assignment info (is_active, display_order).
    Used for the agent switching UI on both web and device.
    """
    from ...crud.crud_agent_device_assignment import get_agents_for_device

    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập thiết bị này")

    agents = await get_agents_for_device(db, device_id)
    return {"success": True, "agents": agents, "total": len(agents)}


@router.post("/{device_id}/agents")
async def assign_agent_to_device(
    device_id: str,
    request_body: AssignAgentRequest,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Assign an agent to a device (M2M relationship).
    
    Creates the agent-device assignment. If set_active=True,
    this agent becomes the active one and the previous active is deactivated.
    """
    from ...crud.crud_agent import crud_agents
    from ...crud.crud_agent_device_assignment import assign_device_to_agent, get_agents_for_device

    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Không có quyền quản lý thiết bị này")

    # Verify agent ownership
    agent = await crud_agents.get(db=db, id=request_body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent không tồn tại")

    try:
        await assign_device_to_agent(
            db, request_body.agent_id, device_id, set_active=request_body.set_active
        )
        await db.commit()
        
        agents = await get_agents_for_device(db, device_id)
        logger.info(f"Assigned agent {request_body.agent_id} to device {device_id}")
        return {"success": True, "message": "Đã gán agent cho thiết bị", "agents": agents}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error assigning agent to device: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi gán agent: {str(e)}")


@router.delete("/{device_id}/agents/{agent_id}")
async def unassign_agent_from_device(
    device_id: str,
    agent_id: str,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Remove an agent from a device.
    
    If the removed agent was active, the next available agent
    becomes active automatically.
    """
    from ...crud.crud_agent_device_assignment import unassign_device_from_agent

    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Không có quyền quản lý thiết bị này")

    removed = await unassign_device_from_agent(db, agent_id, device_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Agent chưa được gán cho thiết bị này")

    await db.commit()
    logger.info(f"Unassigned agent {agent_id} from device {device_id}")
    return {"success": True, "message": "Đã gỡ agent khỏi thiết bị"}


@router.put("/{device_id}/switch-agent/{agent_id}")
async def switch_device_agent(
    device_id: str,
    agent_id: str,
    db: Annotated["AsyncSession", Depends(get_async_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Switch the active agent on a device.
    
    The agent must already be assigned to the device.
    Deactivates the current active agent and activates the specified one.
    Also syncs the legacy device.agent_id FK for backward compatibility.
    """
    from ...crud.crud_agent_device_assignment import switch_active_agent, get_agents_for_device

    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Không có quyền quản lý thiết bị này")

    assignment = await switch_active_agent(db, device_id, agent_id)
    if not assignment:
        raise HTTPException(
            status_code=404, 
            detail="Agent chưa được gán cho thiết bị này. Hãy gán agent trước."
        )

    await db.commit()
    agents = await get_agents_for_device(db, device_id)
    logger.info(f"Switched device {device_id} to agent {agent_id}")
    return {
        "success": True,
        "message": f"Đã chuyển sang agent mới",
        "active_agent_id": agent_id,
        "agents": agents,
    }
