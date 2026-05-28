"""OTA (Over-The-Air) Update Routes"""

import json
import time
import base64
import hashlib
import hmac
import random
import os
import aiofiles
from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Header, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.schemas import OTADeviceData
from app.config import Settings
from app.services import ThreadPoolService
from app.api.dependencies import (
    get_settings,
    get_thread_pool,
    get_cache_manager_dependency,
    get_current_user,
)
from app.ai.utils import get_local_ip, AuthToken
from app.crud.crud_device import crud_device
from app.crud.crud_firmware import crud_firmware
from app.models.firmware import BoardType
from app.core.db.database import async_get_db
from app.core.utils import CacheKey, BaseCacheManager
from ...core.logger import get_logger
from ...core.rate_limit import rate_limit_activation, rate_limit_ota
from app.core.utils.timezone import resolve_timezone
from app.config.config_loader import load_config
from app.services.auto_provision_service import auto_provision_device
from ...utils.license_utils import calculate_license_info, calculate_effective_features
from ...services.quota_service import QuotaService
from ...services.board_registry import get_board_info
from ...crud import crud_theme
from ...crud.crud_agent import crud_agent
from app.services import get_mqtt_service

router = APIRouter(prefix="/ota", tags=["ota"])

logger = get_logger(__name__)

# Cache expiration for device validation. Reduced from 300 → 30s (BE-C2 hardening).
# Cache key now requires HMAC of (mac, device_token) — see _validate_device_exists.
DEVICE_VALIDATION_CACHE_TTL = 30

# Constants
ACTIVATION_CODE_LENGTH = 8

# Assets storage path
ASSETS_STORAGE_PATH = Path("/app/data/assets")


async def _validate_device_exists(
    db: AsyncSession,
    mac_address: str,
    redis_client: Redis | None = None,
    device_token: str | None = None,
) -> bool:
    """
    Validate device exists in database with Redis caching.

    BE-C2 hardening:
      - Cache key bound to (mac, sha256(token)) so attacker spoofing MAC alone
        cannot reuse another device's cache slot.
      - TTL reduced from 300s → 30s.
      - MAC normalized to upper-case (case-collision protection).
      - If no device_token is presented, cache is bypassed entirely (every
        request hits DB) — prevents pure-MAC bypass.

    Args:
        db: AsyncSession for database operations
        mac_address: MAC address of device (AA:BB:CC:DD:EE:FF format)
        redis_client: Redis client for caching (optional)
        device_token: Bearer/HMAC token presented by device (optional)

    Returns:
        bool: True if device exists and is not deleted, False otherwise

    Raises:
        HTTPException: If device not found (401 Unauthorized)
    """
    mac_norm = (mac_address or "").upper()
    cache_key: str | None = None
    if device_token:
        token_digest = hashlib.sha256(device_token.encode("utf-8")).hexdigest()[:16]
        cache_key = f"device_validated:{mac_norm}:{token_digest}"

    # Try to get from Redis cache only when token-bound
    if redis_client and cache_key:
        try:
            cached_result = await redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Device validation cache hit for {mac_norm}")
                return cached_result.decode() == "true"
        except Exception as e:
            logger.warning(f"Cache read error for {mac_norm}: {e}")
            # Continue to database query if cache fails

    # Query database if not in cache
    try:
        device = await crud_device.get_device_by_mac_address(
            db=db,
            mac_address=mac_norm,
            include_deleted=False,
        )

        device_exists = device is not None

        # Cache the result only when token-bound
        if redis_client and cache_key:
            try:
                cache_value = "true" if device_exists else "false"
                await redis_client.set(
                    cache_key,
                    cache_value,
                    ex=DEVICE_VALIDATION_CACHE_TTL,
                )
                logger.debug(
                    f"Cached device validation for {mac_norm}: {cache_value}"
                )
            except Exception as e:
                logger.warning(f"Cache write error for {mac_norm}: {e}")

        if not device_exists:
            logger.warning(f"Device not found for MAC address: {mac_norm}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Device {mac_norm} not authorized",
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device validation error for {mac_norm}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Device validation failed: {str(e)}",
        )


@router.options("", include_in_schema=False)
async def ota_options():
    """Handle CORS preflight requests"""
    return {}


def _add_cors_headers(response):
    """Thêm header CORS"""
    response.headers["Access-Control-Allow-Headers"] = (
        "client-id, content-type, device-id"
    )
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"


def generate_password_signature(content: str, secret_key: str) -> str:
    """Tạo chữ ký mật khẩu MQTT

    Args:
        content: Nội dung dùng để ký (clientId + '|' + username)
        secret_key: Khóa bí mật

    Returns:
        str: Chữ ký HMAC-SHA256 được mã hóa Base64
    """
    try:
        hmac_obj = hmac.new(
            secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        )
        signature = hmac_obj.digest()
        return base64.b64encode(signature).decode("utf-8")
    except Exception as e:
        logger.error(f"MQTT password signature creation failed: {e}")
        return ""


def get_websocket_url(settings: Settings, local_ip: str, request: Request = None) -> str:
    """Lấy địa chỉ websocket

    OTA response sẽ trả URL này cho firmware để kết nối WebSocket.
    Standard protocol (original Python server): ws://host:port/
    Standard protocol (Java manager-api): ws://host:port/xiaozhi/v1/
    
    We use root path `/` as default — compatible with all firmware versions
    since we've registered root-level WebSocket handlers.
    
    Config `server.websocket` always takes priority if explicitly set.

    Args:
        settings: Settings object với server config
        local_ip: Địa chỉ IP cục bộ
        request: FastAPI Request object để lấy domain động

    Returns:
        str: Địa chỉ websocket
    """
    config = settings.to_dict()
    server_config = config.get("server", {})
    websocket_config = server_config.get("websocket", "")

    if websocket_config and "của bạn" not in websocket_config:
        return websocket_config
    
    # Try to use request headers to construct the WebSocket URL dynamically
    if request:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if host:
            # Check if host is not a private/internal IP or localhost
            is_internal = False
            host_clean = host.split(":")[0]
            if (host_clean == "localhost" or 
                host_clean == "backend" or 
                host_clean.startswith("127.") or 
                host_clean.startswith("172.") or 
                host_clean.startswith("192.168.") or 
                host_clean.startswith("10.")):
                is_internal = True
            
            if not is_internal:
                proto = request.headers.get("x-forwarded-proto") or request.url.scheme
                ws_proto = "wss" if proto == "https" else "ws"
                return f"{ws_proto}://{host}/ws/"

    # Fallback 1: check SERVER_URL in environment
    server_url = os.environ.get("SERVER_URL", "")
    if server_url and "localhost" not in server_url and "127.0.0.1" not in server_url:
        if server_url.startswith("https://"):
            domain = server_url.replace("https://", "").rstrip("/")
            return f"wss://{domain}/ws/"
        elif server_url.startswith("http://"):
            domain = server_url.replace("http://", "").rstrip("/")
            return f"ws://{domain}/ws/"

    # Fallback 2: If we still have request, even if internal IP, it's better than local_ip fallback
    if request:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if host:
            proto = request.headers.get("x-forwarded-proto") or request.url.scheme
            ws_proto = "wss" if proto == "https" else "ws"
            return f"{ws_proto}://{host}/ws/"

    port = settings.server.port
    return f"ws://{local_ip}:{port}/"



@router.get("", response_model=dict, include_in_schema=True, dependencies=[Depends(rate_limit_ota)])
@router.get("/", response_model=dict, include_in_schema=False, dependencies=[Depends(rate_limit_ota)])
async def ota_get(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """
    OTA GET - Returns WebSocket URL and status (handle_get)
    """
    try:
        local_ip = get_local_ip()
        websocket_url = get_websocket_url(settings, local_ip, request)

        message = f"OTA hoạt động bình thường, địa chỉ websocket gửi cho thiết bị là: {websocket_url}"
        return {"message": message, "websocket_url": websocket_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OTA giao diện gặp lỗi: {str(e)}",
        )


@router.post("", response_model=dict, dependencies=[Depends(rate_limit_ota)])
@router.post("/", response_model=dict, include_in_schema=False, dependencies=[Depends(rate_limit_ota)])
async def ota_post(
    request: Request,
    device_data: OTADeviceData,
    device_id: str = Header(..., alias="device-id"),
    client_id: str = Header(None, alias="client-id"),  # Optional — old firmware may not send this
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    OTA POST - Sends firmware config (MQTT or WebSocket) (handle_post)

    NEW LOGIC:
    - If device exists in DB → Send normal response (no activation)
    - If device NOT in DB → Generate activation code, store device data in Redis (24h TTL)

    Validates device exists in database when auth is enabled.
    """

    # device_id: Địa chỉ MAC thiết bị
    try:
        # Normalize MAC to uppercase. Devices may send mixed-case in the
        # device-id header; without normalization the existence check below
        # misses (DB stores uppercase via devices.py / auto-provision
        # creators) and we trigger a redundant auto-provision attempt that
        # then fails on the unique-constraint (user_id, mac_address) and
        # leaves the user stuck on the activation-code fallback even
        # though they were already provisioned.
        device_id = (device_id or "").upper()

        # Fallback client_id to device_id (matches original Java server behavior)
        if not client_id:
            client_id = device_id

        # NOTE: Xiaozhi is an independent system - no cross-domain proxying
        # Each domain (xiaozhi-ai-iot.vn / xiaozhi-ai-iot.vn) operates separately

        data = device_data.model_dump()

        # Load config từ YAML file
        # load_config imported at top-level

        config = load_config()
        server_config = config.get("server", {})
        local_ip = get_local_ip()

        tz_name = server_config.get("tz", "UTC")
        tz_info = resolve_timezone(tz_name)
        offset = datetime.now(tz_info).utcoffset()
        offset_minutes = int(offset.total_seconds() // 60) if offset else 0

        return_json = {
            "server_time": {
                "timestamp": int(round(time.time() * 1000)),
                "timezone_offset": offset_minutes,
            },
            # firmware key will only be included if update is available
        }

        # ============ NEW LOGIC: Check if device exists ============
        device_exists = await crud_device.get_device_by_mac_address(
            db=db, mac_address=device_id
        )

        if not device_exists:
            # ============ Auto-Provision: Try first ============
            # auto_provision_device imported at top-level
            
            provision_result = await auto_provision_device(db, device_id, data)
            if provision_result:
                # Device auto-provisioned! Re-fetch and continue with normal flow
                device_exists = await crud_device.get_device_by_mac_address(
                    db=db, mac_address=device_id
                )
                logger.info(
                    f"✅ Auto-provisioned device {device_id}. Sending normal config."
                )
            
        if not device_exists:
            # Auto-provision disabled or failed → Fallback to activation code
            logger.info(f"Device {device_id} not in DB. Generating activation code.")

            # Check if activation code already exists for this device
            existing_activation = await cache.get(CacheKey.DEVICE_ACTIVATION, device_id)
            
            if existing_activation and isinstance(existing_activation, dict) and "code" in existing_activation:
                # Reuse existing activation code
                activation_code = existing_activation["code"]
                logger.debug(f"Reusing existing activation code: {activation_code} for MAC {device_id}")
                # Ensure reverse lookup key exists (may have expired)
                try:
                    await cache.set(CacheKey.ACTIVATION_CODE, device_id, activation_code)
                except Exception as e:
                    logger.warning(f"Failed to refresh reverse lookup for activation code: {e}")
            else:
                # Generate new activation code
                activation_code = "".join(
                    random.choices("0123456789", k=ACTIVATION_CODE_LENGTH)
                )
                logger.debug(
                    f"Generated new activation code: {activation_code} for MAC {device_id}"
                )

                # Store activation code + OTA device data in Redis (24h TTL) - single operation
                try:
                    activation_payload = {
                        "code": activation_code,
                        "device_data": data,
                    }
                    # Store under mac_address key
                    await cache.set(
                        CacheKey.DEVICE_ACTIVATION, activation_payload, device_id
                    )
                    # Also store code->mac mapping for reverse lookup
                    await cache.set(CacheKey.ACTIVATION_CODE, device_id, activation_code)
                except Exception as e:
                    logger.error(f"Failed to store device activation data: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to store device activation data",
                    )

            # Add activation info to response
            activation_challenge = base64.b64encode(
                hashlib.sha256(activation_code.encode()).digest()
            ).decode("utf-8")[:32]

            return_json["activation"] = {
                "message": f"Mã kích hoạt: {activation_code}",
                "code": activation_code,
                "challenge": activation_challenge,
                "timeout_ms": 300000,  # 5 minutes to enter activation code
            }

            # Include MQTT config so device can poll /activate endpoint
            mqtt_common_config = config.get("mqtt", {})
            if mqtt_common_config:
                mqtt_endpoint = mqtt_common_config.get("device_url") or mqtt_common_config.get("url", "")
                for prefix in ("mqtt://", "mqtts://"):
                    if mqtt_endpoint.startswith(prefix):
                        mqtt_endpoint = mqtt_endpoint[len(prefix):]
                        break
                device_username = mqtt_common_config.get("device_username") or mqtt_common_config.get("username", "")
                device_password = mqtt_common_config.get("device_password") or mqtt_common_config.get("password", "")
                return_json["mqtt"] = {
                    "endpoint": mqtt_endpoint,
                    "client_id": device_id,
                    "username": device_username,
                    "password": device_password,
                    "subscribe_topic": f"device/{device_id}/#",
                    "publish_topic": "device-server",
                }

            logger.info(
                f"OTA activation response for {device_id} with code {activation_code}. "
                f"Returning activation-only (no websocket/audio). Device must poll /activate."
            )

            # CRITICAL: Return early! Do NOT send websocket/audio_params for unactivated devices.
            # The firmware will poll POST /ota/activate until it gets 200 (device registered).
            # Then firmware re-calls this OTA POST endpoint and gets the full config.
            return return_json

        # ============ Device exists → Normal response ============
        logger.info(f"Device {device_id} found in DB. Sending normal config.")

        # ============ MQTT Config (Unified — Single Block) ============
        # Priority: mqtt_common (EMQX direct) > mqtt_gateway (Node.js bridge)
        mqtt_common_config = config.get("mqtt", {})
        mqtt_gateway_endpoint = server_config.get("mqtt_gateway")
        
        if mqtt_common_config:
            # Direct EMQX connection (preferred — lower latency, no gateway hop)
            mqtt_endpoint = mqtt_common_config.get("device_url") or mqtt_common_config.get("url", "")
            # CRITICAL: Strip mqtt:// or mqtts:// prefix
            # Firmware code does: pos = endpoint.find(':'); broker = endpoint.substr(0, pos)
            # With "mqtt://host:port" → broker="mqtt", port=stoi("//host:port") → CRASH!
            for prefix in ("mqtt://", "mqtts://"):
                if mqtt_endpoint.startswith(prefix):
                    mqtt_endpoint = mqtt_endpoint[len(prefix):]
                    break
            
            device_username = mqtt_common_config.get("device_username") or mqtt_common_config.get("username", "")
            device_password = mqtt_common_config.get("device_password") or mqtt_common_config.get("password", "")
            return_json["mqtt"] = {
                "endpoint": mqtt_endpoint,
                "client_id": device_id,  # MAC address — firmware uses this for MQTT connect, enables EMQX client lookup
                "username": device_username,
                "password": device_password,
                "subscribe_topic": f"device/{device_id}/server",  # Not used by standard FW (it never subscribes), EMQX auto_subscribe handles this
                "publish_topic": "device-server",  # Topic for device → server messages
            }
            logger.debug(f"MQTT config (direct EMQX) for {device_id}: {mqtt_endpoint}")
            
        elif mqtt_gateway_endpoint:
            # Fallback: Node.js MQTT Gateway bridge (upstream pattern — higher latency)
            device_model = "default"
            try:
                if "device" in data and isinstance(data["device"], dict):
                    device_model = data["device"].get("model", "default")
                elif "model" in data:
                    device_model = data["model"]
                group_id = f"GID_{device_model}".replace(":", "_").replace(" ", "_")
            except Exception as e:
                logger.error(f"Failed to get device model: {e}")
                group_id = "GID_default"

            mac_address_safe = device_id.replace(":", "_")
            # Use client_id header for session disambiguation (if available)
            client_id_safe = client_id.replace(":", "_").replace("-", "_") if client_id else mac_address_safe
            mqtt_client_id = f"{group_id}@@@{mac_address_safe}@@@{client_id_safe}"

            user_data = {"ip": "unknown"}
            try:
                user_data_json = json.dumps(user_data)
                username = base64.b64encode(user_data_json.encode("utf-8")).decode(
                    "utf-8"
                )
            except Exception as e:
                logger.error(f"Failed to create username: {e}")
                username = ""

            password = ""
            signature_key = server_config.get("mqtt_signature_key", "")
            if signature_key:
                password = generate_password_signature(
                    mqtt_client_id + "|" + username, signature_key
                )
                if not password:
                    password = ""
            else:
                logger.warning("Missing MQTT signature key, password is empty")

            return_json["mqtt"] = {
                "endpoint": mqtt_gateway_endpoint,
                "client_id": mqtt_client_id,
                "username": username,
                "password": password,
                "publish_topic": "device-server",
                "subscribe_topic": f"devices/p2p/{mac_address_safe}",  # Reference server pattern for MQTT Gateway
            }
            logger.debug(f"MQTT config (gateway) for {device_id}: {mqtt_gateway_endpoint}")

        # ============ WebSocket Config (ALWAYS included — standard protocol) ============
        # Original Java server always sends websocket config alongside MQTT
        # Device firmware decides which transport to use
        token = ""
        auth_config = server_config.get("auth", {})
        auth_enable = auth_config.get("enabled", False)
        if auth_enable:
            # Device exists, check if it's in allowed devices
            allowed_devices = set(auth_config.get("allowed_devices", []))
            if allowed_devices and device_id not in allowed_devices:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Device {device_id} not authorized",
                )
            # Generate token using AuthToken with auth_key from server_config
            auth_key = server_config.get("auth_key", "")
            if auth_key:
                auth_token = AuthToken(secret_key=auth_key)
                token = auth_token.generate_token(device_id=device_id)
                logger.debug(
                    f"Generated AuthToken device token for device {device_id}"
                )
            else:
                logger.warning(
                    f"Missing auth_key in server_config for device {device_id}"
                )
                token = ""

        return_json["websocket"] = {
            "url": get_websocket_url(settings, local_ip, request),
            "token": token,
        }
        logger.debug(
            f"WebSocket config for device {device_id}: {return_json['websocket']['url']}"
        )

        # Generate device access_token for API calls (e.g., intercom-contacts)
        # This token uses AuthToken which is verified by firmware-device APIs
        auth_key = server_config.get("auth_key", "")
        if auth_key:
            auth_token = AuthToken(secret_key=auth_key)
            device_token = auth_token.generate_token(device_id=device_id)
            return_json["access_token"] = device_token
            logger.debug(f"Generated access_token for device {device_id}")
        else:
            logger.warning(f"No auth_key configured, device {device_id} will not have access_token")

        # Add audio params for device buffer configuration
        audio_config = config.get("audio", {})
        return_json["audio_params"] = {
            "format": audio_config.get("format", "opus"),
            "sample_rate": audio_config.get("sample_rate", 16000),
            "channels": audio_config.get("channels", 1),
            "frame_duration": audio_config.get("frame_duration", 60),
            # Buffer settings for smooth playback
            "buffer_size_ms": audio_config.get("buffer_size_ms", 500),  # 500ms buffer
            "min_buffer_ms": audio_config.get("min_buffer_ms", 200),    # Start playing after 200ms
            "max_buffer_ms": audio_config.get("max_buffer_ms", 2000),   # Max 2s buffer
        }
        logger.debug(f"Gửi cấu hình Audio Params cho thiết bị {device_id}")

            # Check for firmware update from database
        try:
            app_info = data.get("application") or {}
            current_version = app_info.get("version", "1.0.0")
            
            # Extract board type - support both firmware formats:
            # Vietnam FW:  { "device": { "board": "esp32s3" } }
            # Original FW: { "chip_model_name": "esp32s3", "board": { "type": "...", ... } }
            device_info = data.get("device") or {}
            board_type_str = device_info.get("board", "")
            if not board_type_str:
                # Fallback: original firmware sends chip_model_name at root level
                board_type_str = data.get("chip_model_name", "")
            if not board_type_str:
                # Fallback: original firmware sends "board" as object with board details
                board_obj = data.get("board")
                if isinstance(board_obj, dict):
                    board_type_str = board_obj.get("type", board_obj.get("name", ""))
                elif isinstance(board_obj, str):
                    board_type_str = board_obj
            if not board_type_str:
                board_type_str = "esp32s3"  # Safe default
            
            # Map board type string to enum
            try:
                board_type = BoardType(board_type_str.lower())
            except ValueError:
                board_type = BoardType.ALL
            
            # Firmware check disabled to prevent incorrect firmware mismatch and damage.
            latest_firmware = None
            
            if latest_firmware and latest_firmware.version != current_version:
                # New firmware available — include integrity material for
                # FW-C2 verification (sha256, signature). 'checksum' is kept
                # for backward compatibility with old firmware that reads it.
                fw_payload = {
                    "version": latest_firmware.version,
                    "url": f"/api/v1/firmware/{latest_firmware.id}/download",
                    "checksum": latest_firmware.checksum,
                    "size": latest_firmware.size,
                }
                # New: explicit sha256 hex (lower-case, 64 chars).
                sha = getattr(latest_firmware, "sha256", None) or latest_firmware.checksum
                if sha and isinstance(sha, str) and len(sha) == 64:
                    fw_payload["sha256"] = sha.lower()
                # Optional Ed25519 signature (base64 over sha256 bytes).
                sig = getattr(latest_firmware, "signature_b64", None)
                if sig:
                    fw_payload["signature"] = sig
                return_json["firmware"] = fw_payload
                logger.info(
                    f"Firmware update available for {device_id}: "
                    f"{current_version} -> {latest_firmware.version} "
                    f"(sha256={'yes' if 'sha256' in fw_payload else 'no'}, "
                    f"signed={'yes' if 'signature' in fw_payload else 'no'})"
                )
            # If no update available, don't include firmware key (device will skip OTA check)
        except Exception as e:
            logger.warning(f"Could not check firmware update for {device_id}: {e}")
            # Keep existing firmware info on error

        # ============ License Info ============
        try:
            if device_exists:
                # calculate_license_info, calculate_effective_features imported at top-level
                
                license_info = calculate_license_info(
                    license_type=getattr(device_exists, 'license_type', 'unlimited') or 'unlimited',
                    license_value=getattr(device_exists, 'license_value', None),
                    license_expiration_date=getattr(device_exists, 'license_expiration_date', None),
                    license_activated_at=getattr(device_exists, 'license_activated_at', None),
                )
                
                return_json["license"] = {
                    "is_valid": license_info.is_valid,
                    "type": license_info.license_type,
                    "remaining_days": license_info.remaining_days,
                    "message": license_info.message,
                }
                if license_info.expires_at:
                    return_json["license"]["expires_at"] = license_info.expires_at.isoformat()
                
                # ============ Feature Toggles ============
                firmware_features = None
                if latest_firmware:
                    firmware_features = getattr(latest_firmware, 'features', None)
                device_features = getattr(device_exists, 'features', None)
                
                # Get plan-level features from subscription
                plan_features = None
                try:
                    if device_exists and device_exists.user_id:
                        # QuotaService imported at top-level
                        quota_svc = QuotaService(db)
                        plan_features = await quota_svc.get_device_features_for_user(
                            str(device_exists.user_id)
                        )
                except Exception as pf_err:
                    logger.warning(f"Could not get plan features for {device_id}: {pf_err}")
                
                effective_features = calculate_effective_features(
                    firmware_features=firmware_features,
                    device_features=device_features,
                    plan_features=plan_features,
                )
                return_json["features"] = effective_features
                
                logger.debug(f"License: {license_info.license_type}, Features: {len(effective_features)} for {device_id}")
                
            # Update device info if board or firmware version changed
            if device_exists:
                update_data = {}
                if getattr(device_exists, "board", None) != board_type_str and board_type_str:
                    update_data["board"] = board_type_str
                if getattr(device_exists, "firmware_version", None) != current_version and current_version:
                    update_data["firmware_version"] = current_version
                    
                if update_data:
                    try:
                        from app.schemas.device import DeviceUpdateInternal
                        update_model = DeviceUpdateInternal(
                            **update_data,
                            updated_at=datetime.now(timezone.utc)
                        )
                        await crud_device.update(db=db, object=update_model, id=device_exists.id)
                        await db.commit()
                        logger.info(f"Cập nhật thông tin phần cứng cho {device_id}: {update_data}")
                    except Exception as e:
                        logger.warning(f"Không thể cập nhật thông tin phần cứng cho {device_id}: {e}")
                
        except Exception as e:
            logger.warning(f"Could not calculate license/features for {device_id}: {e}")

        # Add custom assets info if available (wallpaper, sounds, etc.)
        # NOTE: Temporarily disabled - may cause firmware crash on some boards
        # try:
        #     assets_metadata = await cache.get(CacheKey.DEVICE_ASSETS, device_id)
        #     if assets_metadata:
        #         return_json["assets"] = {
        #             "version": assets_metadata.get("version"),
        #             "hash": assets_metadata.get("hash"),
        #             "size": assets_metadata.get("size"),
        #             "url": f"/api/v1/ota/assets/{device_id}",
        #         }
        #         logger.debug(f"Gửi cấu hình Assets cho thiết bị {device_id}: version={assets_metadata.get('version')}")
        # except Exception as e:
        #     logger.warning(f"Could not get assets metadata for device {device_id}: {e}")
        
        # Add board info from registry (for screen validation, flash addresses)
        try:
            # Reuse board_type_str from firmware check above (handles both FW formats)
            board_name = board_type_str if board_type_str else ""
            if board_name:
                # get_board_info imported at top-level
                board_info = get_board_info(board_name)
                if board_info:
                    return_json["board_info"] = {
                        "name": board_info.name,
                        "chip": board_info.chip.value,
                        "screen_width": board_info.width,
                        "screen_height": board_info.height,
                        "screen_type": board_info.screen_type.value,
                        "color_format": board_info.color_format.value,
                        "data_partition_address": hex(board_info.data_partition_address),
                        "flash_size_mb": board_info.flash_size_mb,
                    }
                    logger.debug(f"Board info for {device_id}: {board_info.name} ({board_info.resolution})")
        except Exception as e:
            logger.warning(f"Could not get board info for device {device_id}: {e}")

        try:
            theme_id = getattr(device_exists, 'theme_id', None) if device_exists else None
            if theme_id:
                # crud_theme imported at top-level
                theme = await crud_theme.CRUDTheme().get(db, theme_id)
                if theme and theme.theme_data:
                    # Merge theme_data with any missing defaults
                    theme_config = theme.theme_data.copy() if isinstance(theme.theme_data, dict) else {}
                    
                    # Ensure clock config exists with all required fields
                    if "clock" not in theme_config:
                        theme_config["clock"] = {}
                    
                    clock_defaults = {
                        "hour_hand": "#FFFFFF",
                        "minute_hand": "#FFFFFF", 
                        "second_hand": "#FF0000",
                        "center_dot": "#FFFFFF",
                        "number_color": "#FFFFFF",
                        "tick_color": "#CCCCCC",
                        "background": "#000000",
                        "background_image_url": "",
                        "use_background_image": False,
                        "show_numbers": True,
                        "show_tick_marks": True
                    }
                    
                    for key, value in clock_defaults.items():
                        if key not in theme_config["clock"]:
                            theme_config["clock"][key] = value
                    
                    return_json["theme"] = theme_config
                    logger.debug(f"Theme config for {device_id}: {theme.name}")
            else:
                # Send default theme config with full clock configuration
                return_json["theme"] = {
                    "id": "default",
                    "name": "Default Theme",
                    "version": "1.0",
                    "colors": {
                        "primary": "#FF69B4",
                        "secondary": "#FF1493",
                        "background": "#1A1A2E",
                        "text": "#FFFFFF",
                        "accent": "#00CED1"
                    },
                    "clock": {
                        "hour_hand": "#FFFFFF",
                        "minute_hand": "#FFFFFF",
                        "second_hand": "#FF0000",
                        "center_dot": "#FFFFFF",
                        "number_color": "#FFFFFF",
                        "tick_color": "#CCCCCC",
                        "background": "#000000",
                        "background_image_url": "",
                        "use_background_image": False,
                        "show_numbers": True,
                        "show_tick_marks": True
                    },
                    "menu": {
                        "button_colors": ["#87CEEB", "#FF6B6B", "#FFCC00", "#98FB98", "#DDA0DD", "#87CEEB"],
                        "text_color": "#FFFFFF",
                        "background": "#1A1A2E"
                    },
                    "idle": {
                        "show_weather": True,
                        "show_lunar": True,
                        "background_url": ""
                    }
                }
        except Exception as e:
            logger.warning(f"Could not get theme for device {device_id}: {e}")

        # Add agents list for multi-agent support
        try:
            if device_exists and device_exists.agent_id:
                # crud_agent imported at top-level
                # Get the agent assigned to this device
                agent = await crud_agent.get(db=db, id=device_exists.agent_id)
                if agent:
                    # agent may be a dict or model object
                    agent_id = agent.get("id", "") if isinstance(agent, dict) else getattr(agent, "id", "")
                    agent_name = agent.get("agent_name", "") if isinstance(agent, dict) else getattr(agent, "agent_name", "")
                    agent_prompt = agent.get("system_prompt", "") if isinstance(agent, dict) else getattr(agent, "system_prompt", "")
                    return_json["agents"] = [
                        {
                            "id": str(agent_id),
                            "name": agent_name or "",
                            "description": (agent_prompt or "")[:100],
                            "icon_url": "",  # TODO: Add agent icon support
                            "is_active": True
                        }
                    ]
                    logger.debug(f"Agents for {device_id}: 1 agent ({agent_name})")
        except Exception as e:
            logger.warning(f"Could not get agents for device {device_id}: {e}")

        return return_json

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Request error: {str(e)}",
        )


@router.post("/download")
async def ota_download(
    device_id: str = Header(..., alias="device-id"),
    version: str = Header(...),
    thread_pool: ThreadPoolService = Depends(get_thread_pool),
):
    """Download firmware file"""

    def _prepare_download_sync():
        return {"file_path": None, "size": 0, "checksum": None}

    try:
        file_info = await thread_pool.run_blocking(_prepare_download_sync)

        if not file_info["file_path"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Firmware version {version} not found",
            )

        return {"message": "Download not yet implemented"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/activate", response_model=dict, include_in_schema=True, dependencies=[Depends(rate_limit_activation)])
async def ota_activate(
    device_id: str = Header(..., alias="device-id"),
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    OTA Activate - Confirm device activation

    Logic:
    - If device exists in DB → Status 200 (success)
    - If device NOT in DB but has activation code in Redis → Status 202 (pending)
    - Otherwise → Status 404 (not found)
    """
    try:
        if not device_id:
            raise ValueError("Device ID header missing")

        # Normalise MAC to uppercase — same reason as POST /ota: devices may
        # send mixed case in the device-id header but DB rows are stored
        # uppercase, so a raw-case query misses an existing device and the
        # endpoint then incorrectly returns "pending" or 404.
        device_id = device_id.upper()

        logger.info(f"Activation request for device {device_id}")

        # Check if device already exists in DB
        device_exists = await crud_device.get_device_by_mac_address(
            db=db, mac_address=device_id
        )

        if device_exists:
            # Device registered → Status 200
            logger.info(
                f"Device {device_id} already exists in DB. Activation confirmed."
            )
            return {"status": "success"}

        # Device not in DB → Check if activation data exists in Redis
        try:
            # Retrieve activation data by mac_address
            activation_data = await cache.get(CacheKey.DEVICE_ACTIVATION, device_id)

            if activation_data:
                # Activation data exists, waiting for binding
                logger.info(f"Device {device_id} has activation pending. Status 202.")
                return {
                    "status": "pending",
                    "message": "Chờ xác nhận từ user",
                }
            else:
                # No activation data found
                logger.warning(
                    f"Device {device_id} not found and no activation data in Redis"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found and no activation data available",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error retrieving activation data for device {device_id}: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Activation check failed",
            )

    except ValueError as e:
        logger.warning(f"Activation validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Activation error for device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Activation error: {str(e)}",
        )


# ============ ASSETS OTA ENDPOINTS ============


def _get_assets_path(device_id: str) -> Path:
    """Get assets storage path for a device"""
    return ASSETS_STORAGE_PATH / device_id


def _calculate_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


@router.post("/assets/upload", response_model=dict, include_in_schema=True)
async def upload_device_assets(
    device_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    Upload assets.bin for a specific device.
    
    - User must own the device
    - File will be stored and device notified via WebSocket
    """
    try:
        user_id = current_user["id"]
        
        # Verify device ownership
        device = await crud_device.get_device_by_mac_address(db=db, mac_address=device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        if str(device.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to upload assets for this device"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required"
            )
        
        # Create device assets directory
        assets_path = _get_assets_path(device_id)
        assets_path.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = assets_path / "assets.bin"
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        # Calculate hash and size
        file_hash = _calculate_file_hash(file_path)
        file_size = file_path.stat().st_size
        
        # Store assets metadata in Redis
        assets_metadata = {
            "version": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            "hash": file_hash,
            "size": file_size,
            "uploaded_at": datetime.utcnow().isoformat(),
            "uploaded_by": user_id,
        }
        
        await cache.set(
            CacheKey.DEVICE_ASSETS,
            assets_metadata,
            device_id,
            ttl=86400 * 30  # 30 days
        )
        
        logger.info(f"Assets uploaded for device {device_id}: {file_size} bytes, hash={file_hash}")
        
        # Notify device via MQTT (if available)
        try:
            # get_mqtt_service imported at top-level
            mqtt_service = get_mqtt_service()
            if mqtt_service and mqtt_service.is_available():
                notification = {
                    "type": "assets_update",
                    "version": assets_metadata["version"],
                    "hash": assets_metadata["hash"],
                    "size": assets_metadata["size"],
                    "download_url": f"/api/v1/ota/assets/{device_id}",
                }
                topic = f"device/{device_id}"
                await mqtt_service.publish(topic, notification)
                logger.info(f"Assets update notification sent to device {device_id} via MQTT")
        except Exception as e:
            logger.warning(f"Could not notify device {device_id}: {e}")
        
        return {
            "status": "success",
            "message": f"Assets uploaded successfully for device {device_id}",
            "metadata": assets_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading assets for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/assets/{device_id}", include_in_schema=True)
async def download_device_assets(
    device_id: str,
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    Download assets.bin for a device.
    
    Called by device to fetch custom assets.
    No auth required - device uses this during boot.
    """
    try:
        # Check if device exists
        device = await crud_device.get_device_by_mac_address(db=db, mac_address=device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        # Check if assets file exists
        assets_path = _get_assets_path(device_id) / "assets.bin"
        if not assets_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No assets available for device {device_id}"
            )
        
        # Get metadata
        metadata = await cache.get(CacheKey.DEVICE_ASSETS, device_id) or {}
        
        logger.info(f"Device {device_id} downloading assets")
        
        return FileResponse(
            path=assets_path,
            filename="assets.bin",
            media_type="application/octet-stream",
            headers={
                "X-Assets-Version": metadata.get("version", "unknown"),
                "X-Assets-Hash": metadata.get("hash", ""),
                "X-Assets-Size": str(metadata.get("size", 0)),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading assets for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )


@router.get("/assets/{device_id}/info", response_model=dict, include_in_schema=True)
async def get_device_assets_info(
    device_id: str,
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    Get assets metadata for a device.
    
    Device can check this to see if new assets are available.
    """
    try:
        # Check if device exists
        device = await crud_device.get_device_by_mac_address(db=db, mac_address=device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        # Get metadata from cache
        metadata = await cache.get(CacheKey.DEVICE_ASSETS, device_id)
        
        if not metadata:
            return {
                "has_assets": False,
                "message": "No custom assets configured for this device"
            }
        
        return {
            "has_assets": True,
            "version": metadata.get("version"),
            "hash": metadata.get("hash"),
            "size": metadata.get("size"),
            "uploaded_at": metadata.get("uploaded_at"),
            "download_url": f"/api/v1/ota/assets/{device_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assets info for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assets info: {str(e)}"
        )


@router.delete("/assets/{device_id}", response_model=dict, include_in_schema=True)
async def delete_device_assets(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    Delete custom assets for a device.
    
    User must own the device.
    """
    try:
        # `get_current_user` returns the User row dict (UserRead.model_dump()),
        # which has "id" but no "sub" field. Using .get("sub") here would always
        # return None and the ownership check below would 403 every legitimate
        # owner. Mirror the pattern used by upload/push (current_user["id"]).
        user_id = current_user["id"]

        # Verify device ownership
        device = await crud_device.get_device_by_mac_address(db=db, mac_address=device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )

        if str(device.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete assets for this device"
            )
        
        # Delete assets file
        assets_path = _get_assets_path(device_id) / "assets.bin"
        if assets_path.exists():
            os.remove(assets_path)
        
        # Delete metadata from cache
        await cache.delete(CacheKey.DEVICE_ASSETS, device_id)
        
        logger.info(f"Assets deleted for device {device_id}")
        
        return {
            "status": "success",
            "message": f"Assets deleted for device {device_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting assets for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delete failed: {str(e)}"
        )


@router.post("/assets/{device_id}/push", response_model=dict, include_in_schema=True)
async def push_assets_to_device(
    device_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
    cache: Annotated[BaseCacheManager, Depends(get_cache_manager_dependency)] = None,
):
    """
    Push assets update notification to device.
    
    Device will receive WebSocket message to download new assets.
    User must own the device.
    """
    try:
        user_id = current_user["id"]
        
        # Verify device ownership
        device = await crud_device.get_device_by_mac_address(db=db, mac_address=device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        
        if str(device.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to push assets to this device"
            )
        
        # Get assets metadata
        metadata = await cache.get(CacheKey.DEVICE_ASSETS, device_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No assets available to push"
            )
        
        notification = {
            "type": "assets_update",
            "version": metadata["version"],
            "hash": metadata["hash"],
            "size": metadata["size"],
            "download_url": f"/api/v1/ota/assets/{device_id}",
        }
        
        # Try WebSocket first (device is likely connected via WS)
        ws_sent = False
        if hasattr(request.app.state, "active_connections"):
            for handler in request.app.state.active_connections:
                # Match by device_id (UUID) or mac_address
                handler_device_id = getattr(handler, "device_id", None)
                handler_mac = None
                if hasattr(handler, "agent") and handler.agent:
                    handler_mac = handler.agent.get("device_mac_address")
                
                if str(handler_device_id) == str(device.id) or handler_mac == device_id:
                    try:
                        # json already imported at top-level
                        await handler.websocket.send_text(json.dumps(notification))
                        ws_sent = True
                        logger.info(f"Assets update pushed to device {device_id} via WebSocket")
                        break
                    except Exception as ws_err:
                        logger.warning(f"Failed to send via WebSocket: {ws_err}")
        
        if ws_sent:
            return {
                "status": "success",
                "message": f"Assets update pushed to device {device_id} via WebSocket",
                "device_online": True
            }
        
        # Fallback to MQTT
        try:
            # get_mqtt_service imported at top-level
            mqtt_service = get_mqtt_service()
            
            if mqtt_service and mqtt_service.is_available():
                topic = f"device/{device_id}"
                sent = await mqtt_service.publish(topic, notification)
                
                if sent:
                    return {
                        "status": "success",
                        "message": f"Assets update pushed to device {device_id} via MQTT",
                        "device_online": True
                    }
        except Exception as e:
            logger.warning(f"MQTT push failed for device {device_id}: {e}")
        
        return {
            "status": "pending",
            "message": f"Device {device_id} is offline. Will download on next boot.",
            "device_online": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing assets to device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Push failed: {str(e)}"
        )