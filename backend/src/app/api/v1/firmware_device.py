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
from ...crud.crud_meeting import (
    get_meeting,
    update_meeting,
    soft_delete_meeting,
    complete_meeting,
    create_meeting,
    get_tasks_by_meeting,
    get_transcript_by_meeting,
)
from ...models.meeting import MeetingStatus
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


# ============================================================================
# INTERCOM ENDPOINTS
# ============================================================================

@router.get("/intercom-contacts")
async def get_intercom_contacts_for_device(
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get all intercom contacts for device.
    
    Returns combined list of:
    1. User's own devices (excluding current device)
    2. Friends' devices (where intercom_enabled=True)
    
    Headers:
        device-id: Device MAC address
        authorization: Bearer token
        
    Returns:
        {
            "contacts": [
                {
                    "id": "uuid",
                    "name": "2.8 LCD",
                    "mac": "98:a3:16:e8:df:48",
                    "type": "own",
                    "owner": "Tôi",
                    "status": "online"
                },
                ...
            ],
            "total": 5
        }
    """
    # Verify device and get user_id
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    logger.info(f"[Firmware] Device {device_id_str} requesting intercom contacts")
    
    contacts = []
    
    # 1. Get user's own devices (excluding current device)
    own_devices_result = await db.execute(
        select(
            Device.id,
            Device.device_name,
            Device.mac_address,
            Device.status,
        ).where(
            Device.user_id == user_id,
            Device.mac_address != device_id_str,  # Exclude current device
        )
    )
    own_devices = own_devices_result.all()
    
    for device in own_devices:
        contacts.append({
            "id": str(device.id),
            "name": device.device_name or device.mac_address,
            "mac": device.mac_address,
            "type": "own",
            "owner": "Tôi",
            "status": device.status or "unknown",
        })
    
    # 2. Get friends' devices
    try:
        from ...models.friend import Friend
        from ...models.user import User
        
        # Get accepted friends with intercom enabled
        friends_result = await db.execute(
            select(Friend).where(
                Friend.user_id == user_id,
                Friend.status == "accepted",
                Friend.intercom_enabled == True,
            )
        )
        friends = friends_result.scalars().all()
        
        for friend in friends:
            # Get friend's user info
            friend_user = await db.get(User, friend.friend_id)
            if not friend_user:
                continue
            
            friend_name = friend.nickname or friend_user.name or "Bạn bè"
            
            # Get friend's devices
            friend_devices_result = await db.execute(
                select(
                    Device.id,
                    Device.device_name,
                    Device.mac_address,
                    Device.status,
                ).where(Device.user_id == friend.friend_id)
            )
            friend_devices = friend_devices_result.all()
            
            for device in friend_devices:
                contacts.append({
                    "id": str(device.id),
                    "name": device.device_name or device.mac_address,
                    "mac": device.mac_address,
                    "type": "friend",
                    "owner": friend_name,
                    "status": device.status or "unknown",
                })
                
    except Exception as e:
        logger.warning(f"Could not get friend devices: {e}")
    
    logger.info(f"[Firmware] Returning {len(contacts)} contacts for device {device_id_str}")
    
    return {
        "contacts": contacts,
        "total": len(contacts),
    }


# ============================================================================
# MEETING RECORDING ENDPOINTS (for ESP32 firmware)
# ============================================================================

@router.get("/meeting/list")
async def device_get_meeting_list(
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    limit: int = Query(5, description="Number of meetings to return"),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get a list of recent meetings for this device's user.
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    from ...crud.crud_meeting import get_meetings_by_user
    meetings, total = await get_meetings_by_user(db, user_id, page=1, page_size=limit)
    
    meeting_list = []
    for m in meetings:
        meeting_list.append({
            "id": str(m.id),
            "title": m.title,
            "status": m.status.value if hasattr(m.status, 'value') else str(m.status),
            "date": m.meeting_date.isoformat() if m.meeting_date else None,
        })
        
    return {
        "meetings": meeting_list,
        "total": total
    }


@router.post("/meeting/start")
async def device_start_meeting(
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    title: Optional[str] = Query(None, description="Meeting title"),
    db: AsyncSession = Depends(async_get_db),
):
    import time as _time
    _t0 = _time.monotonic()
    """
    Start a new meeting recording from firmware.
    
    Auto-creates meeting record — no need to create beforehand.
    FW should save the returned meeting_id for subsequent API calls.
    
    Headers:
        device-id: Device MAC address
        authorization: Bearer token (from OTA access_token)
        
    Query:
        title: Optional meeting title (default: auto-generated)
        
    Returns:
        {
            "meeting_id": "uuid",
            "title": "Cuộc họp 09/02/2026 21:30",
            "status": "recording",
            "created_at": "2026-02-09T21:30:00Z"
        }
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    _t_auth = _time.monotonic()

    # Auto-generate title if not provided
    now = datetime.now(timezone.utc)
    if not title:
        title = f"Cuộc họp {now.strftime('%d/%m/%Y %H:%M')}"

    # Create meeting record
    meeting = await create_meeting(
        db=db,
        user_id=user_id,
        title=title,
        meeting_date=now.date(),
        device_id=device_id_str,
    )
    _t_create = _time.monotonic()

    logger.info(
        "[Firmware] Device %s started meeting %s "
        "(auth=%.0fms, create=%.0fms, total=%.0fms)",
        device_id_str, meeting.id,
        (_t_auth - _t0) * 1000,
        (_t_create - _t_auth) * 1000,
        (_t_create - _t0) * 1000,
    )

    # Stream-only meeting: turn on the per-connection MeetingSessionRecorder
    # so that decoded PCM frames in vad/silero.py are forwarded into the WAV
    # buffer until /complete is called. If device has SD card it will also
    # upload a WAV; we still record server-side as a safety net.
    try:
        from app.ai.connection_registry import get as _get_conn
        from app.services.meeting_session_recorder import MeetingSessionRecorder
        conn = _get_conn(device_id_str)
        if conn is not None:
            if conn.meeting_session_recorder is None:
                conn.meeting_session_recorder = MeetingSessionRecorder(
                    owner_user_id=user_id, device_id=device_id_str,
                )
            await conn.meeting_session_recorder.start(
                meeting_id=str(meeting.id),
                sample_rate=getattr(conn, "client_sample_rate", 16000),
                channels=getattr(conn, "client_channels", 1),
            )
            conn.meeting_recording_active = True
            logger.info(
                "[Firmware] Server-side recorder armed for meeting %s "
                "on connection device=%s sr=%d",
                meeting.id, device_id_str,
                getattr(conn, "client_sample_rate", 16000),
            )
        else:
            logger.warning(
                "[Firmware] No active WS connection for %s — "
                "server-side recording disabled (will rely on FW upload)",
                device_id_str,
            )
    except Exception as e:
        logger.warning("[Firmware] Failed to arm session recorder: %s", e)

    return {
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "status": meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
        "created_at": meeting.created_at.isoformat() if meeting.created_at else now.isoformat(),
    }


@router.post("/meeting/{meeting_id}/upload")
async def device_upload_meeting_audio(
    meeting_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    audio_file: UploadFile = File(..., description="WAV audio file from SD card"),
    language: str = Query("vi", description="Language: vi or en"),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Upload full meeting audio from ESP32 SD card for processing.
    
    This is the MAIN endpoint firmware calls after recording stops.
    Server will: ASR → Voiceprint Match → Summarize → Extract Tasks.
    
    Processing runs in background. FW should poll /meeting/{id}/status.
    
    Headers:
        device-id: Device MAC address
        authorization: Bearer token
        
    Body (multipart/form-data):
        audio_file: WAV file (16kHz mono)
        language: "vi" or "en"
        
    Returns:
        {
            "status": "processing",
            "message": "Đang xử lý audio...",
            "meeting_id": "uuid"
        }
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    
    # Verify meeting exists and belongs to this device's user
    meeting = await get_meeting(db, meeting_id)
    if not meeting or str(meeting.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Read audio into memory
    audio_data = await audio_file.read()
    audio_size = len(audio_data)
    
    if audio_size < 1000:
        raise HTTPException(status_code=400, detail="Audio file too small")
    
    if audio_size > 500 * 1024 * 1024:  # 500MB max
        raise HTTPException(status_code=400, detail="Audio file too large (max 500MB)")
    
    logger.info(
        f"[Firmware] Device {device_id_str} uploaded {audio_size/1024/1024:.1f}MB audio for meeting {meeting_id}"
    )
    
    # Update meeting status to processing
    await update_meeting(db, meeting_id,
        status=MeetingStatus.PROCESSING,
        end_time=datetime.now(timezone.utc),
    )
    
    # Process in background
    import asyncio
    asyncio.create_task(
        _device_process_audio_background(
            meeting_id=meeting_id,
            user_id=user_id,
            audio_data=audio_data,
            language=language,
        )
    )
    
    return {
        "status": "processing",
        "message": "Đang xử lý audio. Vui lòng kiểm tra lại sau.",
        "meeting_id": meeting_id,
        "audio_size_mb": round(audio_size / 1024 / 1024, 1),
    }


@router.get("/meeting/{meeting_id}/status")
async def device_get_meeting_status(
    meeting_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Check meeting processing status. FW should poll this after upload.
    
    Returns:
        {
            "meeting_id": "uuid",
            "status": "completed",      // recording|processing|completed|error
            "title": "Cuộc họp...",
            "duration_seconds": 1800,
            "participants": ["Anh Minh", "Chị Lan"],
            "task_count": 3,
            "has_summary": true,
            "has_transcript": true
        }
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    
    meeting = await get_meeting(db, meeting_id)
    if not meeting or str(meeting.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check tasks and transcript status
    tasks = await get_tasks_by_meeting(db, meeting_id)
    transcript = await get_transcript_by_meeting(db, meeting_id)
    
    participants = meeting.participants or []
    if isinstance(participants, list):
        participant_names = [p.get("name", "Unknown") if isinstance(p, dict) else str(p) for p in participants]
    else:
        participant_names = []
    
    return {
        "meeting_id": str(meeting.id),
        "status": meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
        "title": meeting.title,
        "duration_seconds": meeting.duration_seconds or 0,
        "participants": participant_names,
        "task_count": len(tasks) if tasks else 0,
        "has_summary": bool(meeting.summary),
        "has_transcript": len(transcript) > 0 if transcript else False,
    }


@router.get("/meeting/{meeting_id}/summary")
async def device_get_meeting_summary(
    meeting_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get meeting summary (for TTS readback on device).
    
    Returns short summary text that FW can send to TTS.
    
    Returns:
        {
            "meeting_id": "uuid",
            "title": "Cuộc họp...",
            "summary": "Tóm tắt cuộc họp...",
            "key_decisions": ["Quyết định 1", "Quyết định 2"],
            "task_count": 3,
            "participants": ["Anh Minh", "Chị Lan"],
            "tts_text": "Cuộc họp có 2 người tham gia. Tóm tắt: ..."
        }
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    
    meeting = await get_meeting(db, meeting_id)
    if not meeting or str(meeting.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if not meeting.summary:
        return {
            "meeting_id": str(meeting.id),
            "status": "not_ready",
            "message": "Cuộc họp chưa được xử lý xong",
        }
    
    if not meeting.summary:
        return {
            "meeting_id": str(meeting.id),
            "status": "not_ready",
            "message": "Cuộc họp chưa được xử lý xong",
        }
    
    # Build TTS-friendly text
    participants = meeting.participants or []
    participant_names = [
        p.get("name", "Unknown") if isinstance(p, dict) else str(p)
        for p in participants
    ] if isinstance(participants, list) else []
    
    tasks = await get_tasks_by_meeting(db, meeting_id)
    task_count = len(tasks) if tasks else 0
    
    key_decisions = meeting.key_decisions or []
    decision_list = [d.get("decision", d) if isinstance(d, dict) else str(d) for d in key_decisions] if isinstance(key_decisions, list) else []
    
    # Generate compact TTS text for device
    tts_parts = [f"Cuộc họp \"{meeting.title}\""]
    if participant_names:
        tts_parts.append(f"có {len(participant_names)} người tham gia: {', '.join(participant_names[:5])}")
    tts_parts.append(f"Tóm tắt: {meeting.summary[:300]}")
    if decision_list:
        tts_parts.append(f"Có {len(decision_list)} quyết định quan trọng")
    if task_count > 0:
        tts_parts.append(f"và {task_count} công việc được giao")
    
    tts_text = ". ".join(tts_parts) + "."
    
    return {
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "summary": meeting.summary,
        "key_decisions": decision_list[:10],
        "task_count": task_count,
        "participants": participant_names,
        "tts_text": tts_text,
    }


@router.get("/meeting/{meeting_id}/tasks")
async def device_get_meeting_tasks(
    meeting_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get tasks from meeting for device readback.
    
    Returns:
        {
            "meeting_id": "uuid",
            "tasks": [
                {
                    "title": "Chuẩn bị báo cáo Q1",
                    "assignee": "Anh Minh",
                    "deadline": "2026-02-15",
                    "priority": "high",
                    "status": "pending"
                }
            ],
            "total": 3,
            "tts_text": "Có 3 công việc. Anh Minh: Chuẩn bị báo cáo. Chị Lan: Review code."
        }
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )
    
    
    meeting = await get_meeting(db, meeting_id)
    if not meeting or str(meeting.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    tasks = await get_tasks_by_meeting(db, meeting_id)
    
    task_list = []
    tts_parts = [f"Có {len(tasks)} công việc được giao"] if tasks else ["Không có công việc nào"]
    
    for t in (tasks or []):
        task_list.append({
            "title": t.title,
            "assignee": t.assignee_name or "Chưa giao",
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "priority": t.priority.value if hasattr(t.priority, 'value') else str(t.priority) if t.priority else "medium",
            "status": t.status.value if hasattr(t.status, 'value') else str(t.status) if t.status else "pending",
        })
        assignee = t.assignee_name or "Chưa giao"
        tts_parts.append(f"{assignee}: {t.title[:50]}")
    
    tts_text = ". ".join(tts_parts[:8]) + "."  # Limit TTS length
    
    return {
        "meeting_id": str(meeting.id),
        "tasks": task_list,
        "total": len(task_list),
        "tts_text": tts_text,
    }


@router.post("/meeting/{meeting_id}/complete")
async def device_complete_meeting(
    meeting_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Mark meeting as complete from firmware. Three modes:

    * **Stream-only** (no SD card): server-side ``MeetingSessionRecorder``
      buffered PCM throughout the meeting. We finalize it to a WAV on disk
      and kick the ASR/LLM background pipeline so the meeting transitions:
        recording → processing → completed.
    * **SD-card upload mode**: FW already POSTed the WAV via /upload which
      triggered processing. Calling /complete is idempotent — we just stamp
      end_time/duration.
    * **Failsafe**: even if no recording is found, we still set status
      PROCESSING then immediately COMPLETED (or FAILED) so the meeting never
      stays stuck on RECORDING.
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )

    meeting = await get_meeting(db, meeting_id)
    if not meeting or str(meeting.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Stamp end_time + transition to PROCESSING regardless of mode.
    meeting = await complete_meeting(db, meeting_id)

    # Finalize the server-side stream recorder (if any) and kick AI processing.
    triggered_processing = False
    try:
        from app.ai.connection_registry import get as _get_conn
        conn = _get_conn(device_id_str)
        if conn is not None and conn.meeting_session_recorder is not None:
            wav_path = await conn.meeting_session_recorder.finalize(meeting_id)
            conn.meeting_recording_active = False

            if wav_path:
                # Persist audio_file_url so admin UI can replay later.
                from ...crud.crud_meeting import update_meeting as _update_mtg
                await _update_mtg(db, meeting_id, audio_file_url=wav_path)

                # Read WAV bytes and hand off to background ASR pipeline.
                # File-based hand-off so we don't keep a long-lived buffer
                # on the connection.
                try:
                    with open(wav_path, "rb") as f:
                        audio_bytes = f.read()
                    asyncio.create_task(_device_process_audio_background(
                        meeting_id=meeting_id,
                        user_id=user_id,
                        audio_data=audio_bytes,
                        language="vi",
                    ))
                    triggered_processing = True
                    logger.info(
                        "[Firmware] Meeting %s → background processing kicked "
                        "(stream-only WAV %s, %d bytes)",
                        meeting_id, wav_path, len(audio_bytes),
                    )
                except Exception as e:
                    logger.error(
                        "[Firmware] Failed to read WAV for processing: %s", e
                    )
    except Exception as e:
        logger.warning("[Firmware] Recorder finalize hook failed: %s", e)

    # No background processing was triggered (no SD upload + no stream recorder
    # data). Don't let the meeting hang on PROCESSING forever — mark FAILED
    # with metadata so user can see why and delete it.
    if not triggered_processing:
        from ...crud.crud_meeting import update_meeting as _update_mtg
        from ...models.meeting import MeetingStatus
        # Only override if still PROCESSING (could have been COMPLETED by
        # an earlier upload path).
        latest = await get_meeting(db, meeting_id)
        if latest and latest.status == MeetingStatus.PROCESSING:
            await _update_mtg(
                db, meeting_id,
                status=MeetingStatus.FAILED,
                meeting_metadata={
                    "error": "no_audio_captured",
                    "note": "Stream recorder inactive and no /upload was called",
                },
            )
            logger.warning(
                "[Firmware] Meeting %s marked FAILED: no audio captured", meeting_id
            )

    return {
        "success": True,
        "meeting_id": meeting_id,
        "processing": triggered_processing,
    }


@router.delete("/meeting/{meeting_id}")
async def device_delete_meeting(
    meeting_id: str,
    device_id: str = Header(..., alias="device-id"),
    authorization: str = Header(...),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft delete meeting from firmware.

    Mirrors hardening of admin delete endpoint: cancels in-flight stream
    recorder + best-effort removes WAV. Idempotent — second call returns
    success even if already deleted (FW may retry on flaky network).
    """
    device_id_str, user_id = await verify_device_token(
        device_id=device_id,
        authorization=authorization,
        db=db,
    )

    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        # Idempotent: if already gone, treat as success so FW doesn't loop.
        return {"success": True, "meeting_id": meeting_id, "already_deleted": True}
    if str(meeting.user_id) != str(user_id):
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Cancel in-flight session recorder for this device.
    try:
        from app.ai.connection_registry import get as _get_conn
        conn = _get_conn(device_id_str)
        if conn is not None and conn.meeting_session_recorder is not None:
            if conn.meeting_session_recorder.current_meeting_id == meeting_id:
                await conn.meeting_session_recorder.cancel()
                conn.meeting_recording_active = False
    except Exception:
        pass

    # Best-effort remove WAV
    if meeting.audio_file_url:
        try:
            import os
            if os.path.isfile(meeting.audio_file_url):
                os.remove(meeting.audio_file_url)
        except Exception:
            pass

    success = await soft_delete_meeting(db, meeting_id)
    return {"success": success, "meeting_id": meeting_id}


# Background processing helper
async def _device_process_audio_background(
    meeting_id: str,
    user_id: str,
    audio_data: bytes,
    language: str = "vi",
):
    """Process meeting audio in background (same logic as web API)."""
    try:
        from ...core.db.database import async_get_db as get_db_gen
        from ...services.meeting_service import MeetingService
        from ...crud.crud_meeting import update_meeting
        from ...models.meeting import MeetingStatus
        
        # Get DB session
        async for db in get_db_gen():
            try:
                service = MeetingService()
                
                # Get providers from user's agent config
                from ...models.agent import Agent
                result = await db.execute(
                    select(Agent).where(Agent.user_id == user_id).limit(1)
                )
                agent = result.scalar_one_or_none()
                
                asr_provider = None
                llm_provider = None
                voiceprint_provider = None
                
                if agent:
                    config = agent.merged_config if hasattr(agent, 'merged_config') else {}
                    
                    try:
                        from ...ai.module_factory import initialize_asr
                        asr_provider = initialize_asr(config)
                    except Exception as e:
                        logger.warning(f"[Meeting BG] ASR init failed: {e}")
                    
                    try:
                        from ...ai.module_factory import initialize_llm
                        llm_provider = initialize_llm(config)
                    except Exception as e:
                        logger.warning(f"[Meeting BG] LLM init failed: {e}")
                    
                    try:
                        voiceprint_config = config.get("voiceprint")
                        if voiceprint_config and voiceprint_config.get("url"):
                            from ...ai.providers.voiceprints.voiceprint_provider import VoiceprintProvider
                            voiceprint_provider = VoiceprintProvider(voiceprint_config)
                    except Exception as e:
                        logger.warning(f"[Meeting BG] Voiceprint init failed: {e}")
                
                await service.process_meeting(
                    db=db,
                    meeting_id=meeting_id,
                    audio_data=audio_data,
                    language=language,
                    asr_provider=asr_provider,
                    llm_provider=llm_provider,
                    voiceprint_provider=voiceprint_provider,
                )
                
                logger.info(f"[Meeting BG] Successfully processed meeting {meeting_id}")
                
            except Exception as e:
                logger.error(f"[Meeting BG] Processing failed for {meeting_id}: {e}")
                try:
                    # MeetingStatus enum has FAILED, not ERROR — previous code
                    # raised AttributeError silently and left meeting stuck.
                    await update_meeting(db, meeting_id,
                        status=MeetingStatus.FAILED,
                        meeting_metadata={"error": str(e)},
                    )
                except Exception as inner:
                    logger.error(
                        "[Meeting BG] Failed to mark meeting as FAILED: %s",
                        inner,
                    )
            finally:
                break
                
    except Exception as e:
        logger.error(f"[Meeting BG] Fatal error for {meeting_id}: {e}")
