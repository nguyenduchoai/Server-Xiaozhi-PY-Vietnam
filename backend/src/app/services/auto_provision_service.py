"""Auto-Provision Service.

Creates shadow user + device + agent for new devices.
Triggered when a device with unknown MAC connects via OTA.
"""

from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import get_logger
from ..crud.crud_system_setting import crud_system_setting

logger = get_logger(__name__)
TAG = "AutoProvision"


async def is_auto_provision_enabled(db: AsyncSession) -> bool:
    """Check if auto-provisioning is enabled."""
    val = await crud_system_setting.get(db, "auto_provision.enabled")
    if val is None:
        return False
    # Handle both boolean True and string "true"/"True"/"1"
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


async def auto_provision_device(
    db: AsyncSession,
    mac_address: str,
    device_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Auto-provision a new device: create shadow user + device + default agent.

    Returns device info dict or None if auto-provision is disabled.
    """
    # Normalize MAC once. Internal helpers (_create_shadow_user, _create_device)
    # mix raw and .upper() forms — without normalization here the device-existence
    # check on line 138 (raw case) can miss a row that was inserted on line 170
    # (.upper()), and the second insert hits the (user_id, mac_address) unique
    # constraint and rolls the whole transaction back.
    mac_address = (mac_address or "").upper()

    # Check if enabled
    if not await is_auto_provision_enabled(db):
        logger.info(f"[{TAG}] Auto-provision disabled. MAC {mac_address} needs manual activation.")
        return None
    
    try:
        # 1. Create shadow user
        shadow_user = await _create_shadow_user(db, mac_address)
        if not shadow_user:
            return None
        
        # 2. Create device record
        device = await _create_device(db, mac_address, str(shadow_user["id"]), device_data)
        if not device:
            return None
        
        # 3. Create default agent (clone from template or create basic)
        agent = await _create_default_agent(db, shadow_user["id"], mac_address)
        
        # 4. Bind device to agent
        if agent:
            await _bind_device_to_agent(db, device["id"], agent["id"])
        
        await db.commit()
        
        logger.info(
            f"[{TAG}] ✅ Auto-provisioned: MAC={mac_address}, "
            f"user={shadow_user['id'][:8]}..., device={device['id'][:8]}..., "
            f"agent={agent['id'][:8] if agent else 'None'}..."
        )
        
        return {
            "user_id": shadow_user["id"],
            "device_id": device["id"],
            "agent_id": agent["id"] if agent else None,
            "mac_address": mac_address,
            "auto_provisioned": True,
        }
        
    except Exception as e:
        logger.error(f"[{TAG}] Auto-provision failed for {mac_address}: {e}")
        await db.rollback()
        return None


async def _create_shadow_user(db: AsyncSession, mac_address: str) -> Optional[Dict[str, Any]]:
    """Create a shadow user account for the device."""
    from ..models.user import User, UserRole
    from ..core.security import get_password_hash
    import secrets
    
    mac_clean = mac_address.replace(":", "-").upper()
    email = f"{mac_clean}@device.xiaozhi.vn"
    mac_short = mac_address[-5:].replace(":", "")
    
    # Check if shadow user already exists for this MAC
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.shadow_mac == mac_address.upper())
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info(f"[{TAG}] Shadow user already exists for {mac_address}: {existing.id}")
        return {"id": existing.id, "email": existing.email}
    
    # Also check by email 
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info(f"[{TAG}] User with email {email} exists, reusing")
        return {"id": existing.id, "email": existing.email}
    
    # Create new shadow user
    user = User(
        name=f"Device {mac_short}",
        email=email,
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        is_shadow=True,
        shadow_mac=mac_address.upper(),
        timezone="Asia/Ho_Chi_Minh",
        role=UserRole.USER,
    )
    db.add(user)
    await db.flush()
    
    logger.info(f"[{TAG}] Created shadow user: {user.id} ({email})")
    return {"id": user.id, "email": user.email}


async def _create_device(
    db: AsyncSession, mac_address: str, user_id: str, device_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Create device record."""
    from ..crud.crud_device import crud_device
    
    # Check if device already exists
    existing = await crud_device.get_device_by_mac_address(db=db, mac_address=mac_address)
    if existing:
        logger.info(f"[{TAG}] Device already exists: {existing.id}")
        return {"id": str(existing.id), "mac_address": existing.mac_address}
    
    # Extract device info - handle both flat and nested OTA data formats
    device_info = device_data if isinstance(device_data, dict) else {}
    
    # board: OTA sends {"board": {"type": "esp32-s3"}} or {"board": "ESP32-S3"}
    board_raw = device_info.get("board", "ESP32-S3")
    if isinstance(board_raw, dict):
        board = board_raw.get("type") or board_raw.get("name") or "ESP32-S3"
    else:
        board = str(board_raw) if board_raw else "ESP32-S3"
    
    # firmware_version: from application.version or top-level
    app_info = device_info.get("application", {}) if isinstance(device_info.get("application"), dict) else {}
    fw_version = (
        app_info.get("version") 
        or device_info.get("firmware_version") 
        or device_info.get("version", "")
    )
    
    # chip_model_name: useful for device name
    chip_model = device_info.get("chip_model_name", "")
    device_name = (
        device_info.get("device_name") 
        or f"Xiaozhi {chip_model or board} {mac_address[-5:].replace(':', '')}"
    )
    
    device = await crud_device.create_device_from_activation(
        db=db,
        mac_address=mac_address.upper(),
        user_id=user_id,
        device_data={
            "device_name": device_name,
            "board": board,
            "firmware_version": fw_version,
            "status": "active",
        },
    )
    
    logger.info(f"[{TAG}] Created device: {device.id} (MAC: {mac_address})")
    return {"id": str(device.id), "mac_address": device.mac_address}


async def _create_default_agent(
    db: AsyncSession, user_id: str, mac_address: str,
) -> Optional[Dict[str, Any]]:
    """Create default agent using provider references from system settings.
    
    The admin selects LLM/TTS providers in System Settings → Auto-Provision.
    We just assign those same refs to the new agent.
    """
    from ..models.agent import Agent
    
    # Get auto-provision settings
    settings = await crud_system_setting.get_by_category(db, "auto_provision")
    
    llm_ref = settings.get("auto_provision.llm_provider_ref")  # e.g. "db:uuid" or "config:GeminiLLM"
    tts_ref = settings.get("auto_provision.tts_provider_ref")  # e.g. "db:uuid" or "config:EdgeTTS"
    tts_voice = settings.get("auto_provision.tts_voice", "vi-VN-HoaiMyNeural")
    system_prompt = settings.get("auto_provision.system_prompt",
        "Bạn là trợ lý AI thân thiện, nói tiếng Việt, ngắn gọn và hữu ích."
    )
    
    mac_short = mac_address[-5:].replace(":", "")
    
    agent = Agent(
        agent_name=f"Trợ lý {mac_short}",
        description="Trợ lý AI được tạo tự động khi thiết bị kết nối lần đầu",
        user_id=user_id,
        prompt=system_prompt,
        LLM=llm_ref,
        TTS=tts_ref,
        tts_voice=tts_voice,
    )
    db.add(agent)
    await db.flush()
    
    logger.info(f"[{TAG}] Created default agent: {agent.id} (LLM: {llm_ref}, TTS: {tts_ref})")
    return {"id": agent.id, "name": agent.agent_name}


async def _bind_device_to_agent(db: AsyncSession, device_id: str, agent_id: str) -> None:
    """Bind device to agent."""
    from ..crud.crud_device import crud_device
    from datetime import datetime, timezone
    
    await crud_device.update(
        db=db,
        object={"agent_id": agent_id, "updated_at": datetime.now(timezone.utc)},
        id=device_id,
    )
    logger.info(f"[{TAG}] Bound device {device_id[:8]}... to agent {agent_id[:8]}...")

