"""
API endpoints for User Connections (Integrations).

Centralized channel configuration — users configure once, use everywhere.
Channels: telegram, zalo_oa, smtp, imap
"""

import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.crud import user_connection as conn_crud
from app.utils.config_encryption import encrypt_config, decrypt_config
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connections", tags=["Integrations"])

# ============ Schemas ============

VALID_TYPES = {"telegram", "zalo_oa", "smtp", "imap"}


class ConnectionConfig(BaseModel):
    """Typed connection configuration - channel-specific fields"""
    bot_token: Optional[str] = Field(None, max_length=500, description="Telegram bot token")
    chat_id: Optional[str] = Field(None, max_length=100, description="Telegram chat ID")
    oa_access_token: Optional[str] = Field(None, max_length=500, description="Zalo OA token")
    host: Optional[str] = Field(None, max_length=255, description="SMTP/IMAP host")
    port: Optional[int] = Field(None, ge=1, le=65535, description="SMTP/IMAP port")
    username: Optional[str] = Field(None, max_length=255, description="SMTP/IMAP username")
    password: Optional[str] = Field(None, max_length=500, description="SMTP/IMAP password")
    secure: Optional[bool] = Field(None, description="Use TLS/SSL")
    folder: Optional[str] = Field(None, max_length=100, description="IMAP folder")

    model_config = {"extra": "allow"}


class ConnectionCreate(BaseModel):
    type: str = Field(..., max_length=20, description="Channel type: telegram, zalo_oa, smtp, imap")
    name: str = Field(..., min_length=1, max_length=255, description="User-friendly label")
    config: ConnectionConfig = Field(default_factory=ConnectionConfig, description="Channel-specific configuration")
    enabled: bool = True


class ConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    config: Optional[ConnectionConfig] = None
    enabled: Optional[bool] = None


class ConnectionResponse(BaseModel):
    id: str
    user_id: str
    type: str
    name: str
    config: dict
    enabled: bool
    status: str
    status_info: Optional[dict] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============ Helper ============

def _sanitize_config(config: dict, conn_type: str, user_id: str = None) -> dict:
    """Decrypt then mask sensitive fields for response."""
    # First decrypt (in case stored encrypted)
    decrypted = decrypt_config(config, user_id)
    safe = dict(decrypted)
    sensitive_keys = ["bot_token", "oa_access_token", "password", "api_key"]
    for key in sensitive_keys:
        if key in safe and safe[key]:
            val = str(safe[key])
            safe[key] = val[:8] + "***" + val[-4:] if len(val) > 12 else "***"
    return safe


def _conn_to_response(conn) -> dict:
    """Convert UserConnection to response dict with sanitized config."""
    return {
        "id": conn.id,
        "user_id": conn.user_id,
        "type": conn.type,
        "name": conn.name,
        "config": _sanitize_config(conn.config or {}, conn.type, conn.user_id),
        "enabled": conn.enabled,
        "status": conn.status,
        "status_info": conn.status_info,
        "created_at": conn.created_at.isoformat() if conn.created_at else "",
        "updated_at": conn.updated_at.isoformat() if conn.updated_at else "",
    }


# ============ Endpoints ============

@router.get("")
async def list_connections(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    type: Optional[str] = None,
) -> dict[str, Any]:
    """List all connections for the current user."""
    connections = await conn_crud.get_connections(
        db, current_user["id"], connection_type=type
    )
    return {
        "connections": [_conn_to_response(c) for c in connections],
        "total": len(connections),
    }


@router.post("")
async def create_connection(
    body: ConnectionCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Create a new integration connection."""
    if body.type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}")

    # Encrypt sensitive fields before storage
    encrypted_config = encrypt_config(body.config, current_user["id"])
    
    conn = await conn_crud.create_connection(
        db,
        user_id=current_user["id"],
        type=body.type,
        name=body.name,
        config=encrypted_config,
        enabled=body.enabled,
    )
    return _conn_to_response(conn)


@router.get("/{connection_id}")
async def get_connection(
    connection_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get a specific connection."""
    conn = await conn_crud.get_connection(db, connection_id, current_user["id"])
    if not conn:
        raise HTTPException(404, "Connection not found")
    return _conn_to_response(conn)


@router.put("/{connection_id}")
async def update_connection(
    connection_id: str,
    body: ConnectionUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update a connection."""
    conn = await conn_crud.get_connection(db, connection_id, current_user["id"])
    if not conn:
        raise HTTPException(404, "Connection not found")

    update_data = body.model_dump(exclude_none=True)
    
    # Merge config (don't replace entirely — allow partial updates)
    if "config" in update_data and conn.config:
        # Decrypt existing config for merge
        existing = decrypt_config(dict(conn.config), current_user["id"])
        existing.update(update_data["config"])
        # Re-encrypt merged config
        update_data["config"] = encrypt_config(existing, current_user["id"])
    
    conn = await conn_crud.update_connection(db, conn, **update_data)
    return _conn_to_response(conn)


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Delete a connection."""
    conn = await conn_crud.get_connection(db, connection_id, current_user["id"])
    if not conn:
        raise HTTPException(404, "Connection not found")
    
    await conn_crud.delete_connection(db, conn)
    return {"success": True, "message": f"Connection '{conn.name}' deleted"}


# In-memory rate limiter for /test endpoint
_test_cooldowns: dict[str, float] = {}
_TEST_COOLDOWN_SECONDS = 10


@router.post("/{connection_id}/test")
async def test_connection(
    connection_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Test a connection to verify it works. Rate limited: 1 test per 30s per connection."""
    import time
    
    # Rate limit check
    cache_key = f"{current_user['id']}:{connection_id}"
    now = time.time()
    last_test = _test_cooldowns.get(cache_key, 0)
    if now - last_test < _TEST_COOLDOWN_SECONDS:
        remaining = int(_TEST_COOLDOWN_SECONDS - (now - last_test))
        raise HTTPException(429, f"Vui lòng chờ {remaining}s trước khi test lại")
    
    conn = await conn_crud.get_connection(db, connection_id, current_user["id"])
    if not conn:
        raise HTTPException(404, "Connection not found")

    _test_cooldowns[cache_key] = now
    result = await _test_channel(conn)
    
    # Update status
    new_status = "connected" if result["success"] else "error"
    await conn_crud.update_connection(
        db, conn,
        status=new_status,
        status_info={"last_test": result},
    )
    
    return result


@router.post("/{connection_id}/send-test")
async def send_test_message(
    connection_id: str,
    body: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Send a real test message through the connection."""
    import time
    
    cache_key = f"send:{current_user['id']}:{connection_id}"
    now = time.time()
    last = _test_cooldowns.get(cache_key, 0)
    if now - last < 10:
        remaining = int(10 - (now - last))
        raise HTTPException(429, f"Vui lòng chờ {remaining}s trước khi gửi lại")
    
    conn = await conn_crud.get_connection(db, connection_id, current_user["id"])
    if not conn:
        raise HTTPException(404, "Connection not found")
    
    recipient = body.get("recipient", "").strip()
    message = body.get("message", "🔔 Test từ Xiaozhi AI IOT").strip()
    if not recipient:
        raise HTTPException(400, "Nhập người nhận (recipient)")
    
    _test_cooldowns[cache_key] = now
    result = await _send_test_channel(conn, recipient, message)
    return result


async def _send_test_channel(conn, recipient: str, message: str) -> dict:
    """Send a test message through a specific channel."""
    try:
        config = decrypt_config(conn.config or {}, conn.user_id)
        if conn.type == "telegram":
            return await _send_test_telegram(config, recipient, message)
        elif conn.type == "zalo_oa":
            return await _send_test_zalo_oa(config, recipient, message)
        elif conn.type == "smtp":
            return await _send_test_smtp(config, recipient, message)
        return {"success": False, "error": f"Kênh {conn.type} chưa hỗ trợ gửi test"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _send_test_telegram(config: dict, chat_id: str, message: str) -> dict:
    import httpx
    token = config.get("bot_token", "")
    if not token:
        return {"success": False, "error": "Bot token chưa cấu hình"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        )
        data = r.json()
        if data.get("ok"):
            return {"success": True, "message": f"Đã gửi đến chat {chat_id}"}
        return {"success": False, "error": data.get("description", r.text[:200])}


async def _send_test_zalo_oa(config: dict, user_id: str, message: str) -> dict:
    import httpx
    token = config.get("oa_access_token", "")
    if not token:
        return {"success": False, "error": "OA Access Token chưa cấu hình"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://openapi.zalo.me/v3.0/oa/message/cs",
            headers={"access_token": token},
            json={"recipient": {"user_id": user_id}, "message": {"text": message}}
        )
        data = r.json()
        if data.get("error") == 0:
            return {"success": True, "message": f"Đã gửi đến Zalo OA user {user_id}"}
        return {"success": False, "error": data.get("message", r.text[:200])}


async def _send_test_smtp(config: dict, to_email: str, message: str) -> dict:
    import smtplib
    import ssl
    host = config.get("host", "")
    port = config.get("port", 587)
    username = config.get("username", "")
    password = config.get("password", "")
    secure = config.get("secure", True)
    
    msg = MIMEText(message, "plain", "utf-8")
    msg["From"] = username
    msg["To"] = to_email
    msg["Subject"] = "🔔 Test từ Xiaozhi AI IOT"
    
    try:
        if secure and port == 465:
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if secure:
                server.starttls()
        server.login(username, password)
        server.sendmail(username, [to_email], msg.as_string())
        server.quit()
        return {"success": True, "message": f"Đã gửi email đến {to_email}"}
    except Exception as e:
        return {"success": False, "error": str(e)}



# ============ Test Helpers ============

async def _test_channel(conn) -> dict:
    """Test a specific channel connection. Decrypts config before use."""
    try:
        config = decrypt_config(conn.config or {}, conn.user_id)
        if conn.type == "telegram":
            return await _test_telegram(config)
        elif conn.type == "zalo_oa":
            return await _test_zalo_oa(config)
        elif conn.type == "smtp":
            return await _test_smtp(config)
        elif conn.type == "imap":
            return await _test_imap(config)
        return {"success": False, "error": f"Unknown channel type: {conn.type}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_telegram(config: dict) -> dict:
    import httpx
    token = config.get("bot_token", "")
    if not token:
        return {"success": False, "error": "Bot token is required"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                bot = data["result"]
                return {"success": True, "bot_name": bot.get("first_name"), "bot_username": bot.get("username")}
        return {"success": False, "error": f"Telegram API error: {r.text[:200]}"}


async def _test_zalo_oa(config: dict) -> dict:
    import httpx
    token = config.get("oa_access_token", "")
    if not token:
        return {"success": False, "error": "OA Access Token is required"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("https://openapi.zalo.me/v2.0/oa/getoa",
                            headers={"access_token": token})
        if r.status_code == 200:
            data = r.json()
            if data.get("error") == 0:
                return {"success": True, "oa_name": data.get("data", {}).get("name")}
        return {"success": False, "error": f"Zalo OA API error: {r.text[:200]}"}


async def _test_smtp(config: dict) -> dict:
    import smtplib
    import ssl
    host = config.get("host", "")
    port = config.get("port", 587)
    username = config.get("username", "")
    password = config.get("password", "")
    secure = config.get("secure", True)
    
    if not all([host, username, password]):
        return {"success": False, "error": "host, username, password are required"}
    
    try:
        if secure and port == 465:
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if secure:
                server.starttls()
        server.login(username, password)
        server.quit()
        return {"success": True, "message": f"SMTP connected to {host}:{port}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_imap(config: dict) -> dict:
    import imaplib
    host = config.get("host", "")
    port = config.get("port", 993)
    username = config.get("username", "")
    password = config.get("password", "")
    secure = config.get("secure", True)
    
    if not all([host, username, password]):
        return {"success": False, "error": "host, username, password are required"}
    
    try:
        if secure:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        mail.login(username, password)
        folder = config.get("folder", "INBOX")
        status, data = mail.select(folder)
        count = int(data[0]) if status == "OK" else 0
        mail.logout()
        return {"success": True, "message": f"IMAP connected. {count} emails in {folder}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
