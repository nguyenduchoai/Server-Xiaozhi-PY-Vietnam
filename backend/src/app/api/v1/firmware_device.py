"""
Firmware API - Endpoints for ESP32 firmware to interact with backend.

Endpoints designed for low-bandwidth, low-memory devices:
- Minimal JSON payloads
- No authentication cookies (token-based)
- Simple request/response format
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Query, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...core.db.database import async_get_db
from ...core.logger import get_logger
from ...models.agent import Agent
from ...models.device import Device
from ...ai.utils import AuthToken
from ...crud.crud_device import crud_device, normalize_mac_address
from ...models.template import Template
from datetime import datetime, timezone

logger = get_logger(__name__)
router = APIRouter(prefix="/firmware", tags=["firmware-device"])


# ============================================================================
# AUTH HELPERS
# ============================================================================


def _device_mac_filter(mac_address: str):
    return func.lower(Device.mac_address) == normalize_mac_address(mac_address).lower()


async def verify_device_token(
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
) -> tuple[str, str]:
    """
    Verify device token and return (device_id, user_id).
    
    Args:
        device_id: Device MAC address from header
        authorization: Bearer token from header
        db: Database session
        
    Returns:
        tuple: (device_id, user_id)
        
    Raises:
        HTTPException: If authentication fails
    """
    device_id = normalize_mac_address(device_id)

    # Extract token
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    elif authorization.startswith("Bearer+"):
        token = authorization[7:]
    else:
        token = authorization
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )
    
    # Verify token. Auth key is read from cached config; load_config() now
    # expands ${ENV_VAR} placeholders so SERVER_AUTH_KEY env works correctly.
    try:
        from ...config.config_loader import load_config
        config = load_config()
        auth_key = config.get("server", {}).get("auth_key", "")

        # Reject placeholder leakage (BE-C4 safeguard): if env var was not set
        # and YAML still contains a literal "${...}", fail loud instead of
        # silently mismatching every device token.
        if not auth_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server auth key not configured"
            )
        if isinstance(auth_key, str) and auth_key.startswith("${"):
            logger.error(
                "auth_key in config.yml is an unresolved env placeholder %r — "
                "did you forget to set SERVER_AUTH_KEY?",
                auth_key,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server auth key env var not set",
            )

        auth_token = AuthToken(secret_key=auth_key)
        is_valid, extracted_device = auth_token.verify_token(token)

        extracted_device = normalize_mac_address(extracted_device)
        if not is_valid or extracted_device != device_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or mismatched token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )
    
    # Get device's user_id
    result = await db.execute(
        select(Device.user_id).where(_device_mac_filter(device_id))
    )
    user_id = result.scalar_one_or_none()
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not registered"
        )
    
    return device_id, str(user_id)


# ============================================================================
# AGENT ENDPOINTS
# ============================================================================

@router.get("/agents")
async def get_agents_for_device(
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get list of agents available for device to switch to.
    
    Firmware uses this to populate the Agent Selector UI.
    Returns agents belonging to the same user as the device.
    
    Headers:
        device-id: Device MAC address
        authorization: Bearer token
        
    Query:
        offset: Pagination offset (default 0)
        limit: Max results (default 20, max 50)
        
    Returns:
        {
            "agents": [
                {
                    "id": "uuid",
                    "name": "Trợ lý nhà",
                    "description": "AI điều khiển smart home",
                    "is_active": true
                },
                ...
            ],
            "total": 5,
            "device_agent_id": "uuid"  // Current device's default agent
        }
    """
    # Verify device and get user_id
    device_id, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    logger.info(f"[Firmware] Device {device_id} requesting agent list for user {user_id}")
    
    # Get device's current agent (the default one)
    device_result = await db.execute(
        select(Device.agent_id).where(_device_mac_filter(device_id))
    )
    device_agent_id = device_result.scalar_one_or_none()
    
    # Get all agents for this user
    
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(Agent).where(
            Agent.user_id == user_id,
            Agent.is_deleted == False,
        )
    )
    total = count_result.scalar() or 0
    
    # Get paginated agents
    result = await db.execute(
        select(
            Agent.id,
            Agent.agent_name,
            Agent.description,
            Agent.avatar_url,
        )
        .where(
            Agent.user_id == user_id,
            Agent.is_deleted == False,
        )
        .order_by(Agent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    
    # Format response for firmware (minimal payload)
    agents = []
    for row in rows:
        agent_id, name, description, avatar_url = row
        agents.append({
            "id": str(agent_id),
            "name": name or "Unnamed Agent",
            "description": description[:50] if description else "",  # Truncate for firmware
            "avatar_url": avatar_url,  # Image URL for device display
            "is_active": str(agent_id) == str(device_agent_id),
        })
    
    logger.info(f"[Firmware] Returning {len(agents)} agents for device {device_id}")
    
    return {
        "agents": agents,
        "total": total,
        "device_agent_id": str(device_agent_id) if device_agent_id else None,
    }


@router.get("/agents/{agent_id}")
async def get_agent_detail_for_device(
    agent_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get single agent details for firmware.
    
    Headers:
        device-id: Device MAC address
        authorization: Bearer token
        
    Path:
        agent_id: Agent UUID to fetch
        
    Returns:
        {
            "id": "uuid",
            "name": "Trợ lý nhà",
            "description": "Full description",
            "template_name": "Smart Home Template",
            "llm_type": "openai",
            "tts_type": "edge"
        }
    """
    # Verify device and get user_id
    _, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    # Get agent (must belong to same user)
    
    result = await db.execute(
        select(
            Agent.id,
            Agent.agent_name,
            Agent.description,
            Agent.avatar_url,
            Agent.active_template_id,
            Template.name.label("template_name"),
            Template.avatar_url.label("template_avatar_url"),
            Template.LLM,
            Template.TTS,
        )
        .outerjoin(Template, Agent.active_template_id == Template.id)
        .where(
            Agent.id == agent_id,
            Agent.user_id == user_id,
            Agent.is_deleted == False,
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )
    
    return {
        "id": str(row.id),
        "name": row.agent_name or "Unnamed Agent",
        "description": row.description or "",
        "avatar_url": row.avatar_url,  # Agent avatar
        "template_name": row.template_name or "Default",
        "template_avatar_url": row.template_avatar_url,  # Template avatar
        "llm_type": _extract_provider_type(row.LLM),
        "tts_type": _extract_provider_type(row.TTS),
    }


def _extract_provider_type(ref: str | None) -> str:
    """Extract provider type from reference string for display."""
    if not ref:
        return "default"
    
    # Reference format: "config:OpenAI" or "db:uuid"
    if ref.startswith("config:"):
        return ref[7:]
    elif ref.startswith("db:"):
        return "custom"
    return ref


@router.post("/agents/{agent_id}/activate")
async def activate_agent_for_device(
    agent_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Set agent as active for this device (optional - firmware can also just send Agent-Id header).
    
    This endpoint updates the device's default agent, so next time
    the device connects without Agent-Id header, it will use this agent.
    
    Headers:
        device-id: Device MAC address
        authorization: Bearer token
        
    Path:
        agent_id: Agent UUID to activate
        
    Returns:
        {"success": true, "message": "Agent activated"}
    """
    # Verify device and get user_id
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    # Verify agent belongs to same user
    result = await db.execute(
        select(Agent.id).where(
            Agent.id == agent_id,
            Agent.user_id == user_id,
            Agent.is_deleted == False,
        )
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or access denied"
        )
    
    # Update device's agent_id
    
    await crud_device.update(
        db=db,
        object={"agent_id": agent_id},
        mac_address=device_id_str,
    )
    
    await db.commit()
    
    logger.info(f"[Firmware] Device {device_id_str} activated agent {agent_id}")
    
    return {
        "success": True,
        "message": "Agent activated",
        "agent_id": agent_id,
    }


# ============================================================================
# DEVICE STATUS ENDPOINTS
# ============================================================================

@router.get("/status")
async def get_device_status(
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get device configuration status.
    
    Firmware uses this to check if device is properly configured.
    
    Returns:
        {
            "registered": true,
            "has_agent": true,
            "agent_name": "Trợ lý",
            "has_template": true,
            "server_version": "2.0.0"
        }
    """
    # Verify device
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    # Get device with agent info
    
    result = await db.execute(
        select(
            Device.id,
            Device.agent_id,
            Agent.agent_name,
            Agent.active_template_id,
            Template.name.label("template_name"),
        )
        .outerjoin(Agent, Device.agent_id == Agent.id)
        .outerjoin(Template, Agent.active_template_id == Template.id)
        .where(_device_mac_filter(device_id_str))
    )
    row = result.one_or_none()
    
    if not row:
        return {
            "registered": False,
            "has_agent": False,
            "agent_name": None,
            "has_template": False,
            "server_version": "2.0.0",
        }
    
    return {
        "registered": True,
        "has_agent": row.agent_id is not None,
        "agent_name": row.agent_name,
        "has_template": row.active_template_id is not None,
        "template_name": row.template_name,
        "server_version": "2.0.0",
    }


