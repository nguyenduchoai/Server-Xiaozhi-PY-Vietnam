"""System Settings API — SuperAdmin only.

Manages global settings:
- Auto-provisioning config (select from existing providers)
- OAuth provider settings (Google, Zalo)
- General system settings
"""

from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import async_get_db, get_current_user
from ...crud.crud_system_setting import crud_system_setting
from ...core.logger import get_logger
from ...models.provider import Provider
from ...config import load_config
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(prefix="/system-settings", tags=["system-settings"])


# ========== Auth Helper ==========

def require_super_admin(current_user: dict) -> dict:
    """Verify user is SuperAdmin."""
    if current_user.get("role") != "super_admin" and not current_user.get("is_superuser"):
        raise HTTPException(403, "Chỉ SuperAdmin mới có quyền truy cập")
    return current_user


# ========== Schemas ==========

class AutoProvisionConfig(BaseModel):
    """Auto-provision settings — uses existing provider references."""
    enabled: bool = False
    llm_provider_ref: str | None = None       # e.g. "db:uuid" or "config:CopilotLLM"
    tts_provider_ref: str | None = None       # e.g. "db:uuid" or "config:EdgeTTS"
    tts_voice: str = "vi-VN-HoaiMyNeural"
    system_prompt: str = "Bạn là trợ lý AI thân thiện, nói tiếng Việt, ngắn gọn và hữu ích."


class OAuthConfig(BaseModel):
    """OAuth provider settings."""
    google_enabled: bool = False
    google_client_id: str | None = None
    google_client_secret: str | None = None
    zalo_enabled: bool = False
    zalo_app_id: str | None = None
    zalo_app_secret: str | None = None


# ========== Auto-Provision Endpoints ==========

@router.get("/auto-provision")
async def get_auto_provision_config(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get auto-provision configuration."""
    require_super_admin(current_user)
    settings = await crud_system_setting.get_by_category(db, "auto_provision")
    
    config = {
        "enabled": settings.get("auto_provision.enabled", False),
        "llm_provider_ref": settings.get("auto_provision.llm_provider_ref"),
        "tts_provider_ref": settings.get("auto_provision.tts_provider_ref"),
        "tts_voice": settings.get("auto_provision.tts_voice", "vi-VN-HoaiMyNeural"),
        "system_prompt": settings.get("auto_provision.system_prompt", 
            "Bạn là trợ lý AI thân thiện, nói tiếng Việt, ngắn gọn và hữu ích."),
    }
    return {"success": True, "config": config}


@router.post("/auto-provision")
async def update_auto_provision_config(
    config: AutoProvisionConfig,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update auto-provision configuration."""
    require_super_admin(current_user)

    # Refuse to enable auto-provision without a working LLM provider.
    # Otherwise the next device that connects gets a shadow agent with
    # LLM=None and breaks at first inference. Frontend already warns,
    # but enforce on the backend so curl/scripts can't bypass the check.
    if config.enabled and not config.llm_provider_ref:
        raise HTTPException(
            status_code=400,
            detail="Phải chọn LLM Provider trước khi bật Auto-Provision",
        )

    settings = {
        "auto_provision.enabled": config.enabled,
        "auto_provision.llm_provider_ref": config.llm_provider_ref,
        "auto_provision.tts_provider_ref": config.tts_provider_ref,
        "auto_provision.tts_voice": config.tts_voice,
        "auto_provision.system_prompt": config.system_prompt,
    }

    await crud_system_setting.bulk_set(
        db, settings, category="auto_provision", updated_by=current_user["id"]
    )

    logger.info(f"Auto-provision config updated by {current_user['id']}: enabled={config.enabled}")
    return {"success": True, "message": "Đã lưu cấu hình Auto-Provision"}


@router.get("/auto-provision/providers")
async def get_available_providers(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get all available providers for auto-provision dropdown.
    
    Returns LLM and TTS providers from:
    1. Database (current user's providers)
    2. Config.yml defaults
    """
    require_super_admin(current_user)
    
    
    # Get current user's active providers from DB
    user_id = current_user["id"]
    result = await db.execute(
        select(Provider).where(
            Provider.is_deleted == False,
            Provider.is_active == True,
            Provider.user_id == user_id,
        ).limit(500)
    )
    db_providers = result.scalars().all()
    
    llm_options = []
    tts_options = []
    
    for p in db_providers:
        item = {
            "reference": f"db:{p.id}",
            "name": p.name,
            "type": p.type,
            "source": "user",
            "owner": p.user_id,
        }
        if p.category == "LLM":
            llm_options.append(item)
        elif p.category == "TTS":
            tts_options.append(item)
    
    # Also include config.yml defaults
    try:
        # load_config imported at top-level
        config = load_config()
        
        for key, cfg in (config.get("LLM") or {}).items():
            provider_type = cfg.get("type", key) if isinstance(cfg, dict) else key
            llm_options.append({
                "reference": f"config:{key}",
                "name": key,
                "type": provider_type,
                "source": "default",
            })
        
        for key, cfg in (config.get("TTS") or {}).items():
            provider_type = cfg.get("type", key) if isinstance(cfg, dict) else key
            tts_options.append({
                "reference": f"config:{key}",
                "name": key,
                "type": provider_type,
                "source": "default",
            })
    except Exception as e:
        logger.warning(f"Failed to load config providers: {e}")
    
    return {
        "success": True,
        "LLM": llm_options,
        "TTS": tts_options,
    }


# ========== OAuth Endpoints ==========

@router.get("/oauth")
async def get_oauth_config(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get OAuth configuration."""
    require_super_admin(current_user)
    settings = await crud_system_setting.get_by_category(db, "oauth")
    
    config = {
        "google_enabled": settings.get("oauth.google.enabled", False),
        "google_client_id": settings.get("oauth.google.client_id"),
        "google_client_secret": _mask_secret(settings.get("oauth.google.client_secret")),
        "zalo_enabled": settings.get("oauth.zalo.enabled", False),
        "zalo_app_id": settings.get("oauth.zalo.app_id"),
        "zalo_app_secret": _mask_secret(settings.get("oauth.zalo.app_secret")),
    }
    return {"success": True, "config": config}


@router.post("/oauth")
async def update_oauth_config(
    config: OAuthConfig,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update OAuth configuration."""
    require_super_admin(current_user)
    
    settings = {
        "oauth.google.enabled": config.google_enabled,
        "oauth.google.client_id": config.google_client_id,
        "oauth.zalo.enabled": config.zalo_enabled,
        "oauth.zalo.app_id": config.zalo_app_id,
    }
    
    # Only update secrets if provided (not masked)
    if config.google_client_secret and not config.google_client_secret.startswith("***"):
        settings["oauth.google.client_secret"] = config.google_client_secret
    if config.zalo_app_secret and not config.zalo_app_secret.startswith("***"):
        settings["oauth.zalo.app_secret"] = config.zalo_app_secret
    
    await crud_system_setting.bulk_set(
        db, settings, category="oauth", updated_by=current_user["id"]
    )
    
    logger.info(f"OAuth config updated by {current_user['id']}")
    return {"success": True, "message": "Đã lưu cấu hình OAuth"}


@router.get("/public/oauth-providers")
async def get_public_oauth_providers(
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Get enabled OAuth providers (public — for login page).
    
    Does NOT expose secrets, only provider availability.
    """
    settings = await crud_system_setting.get_by_category(db, "oauth")
    
    providers = []
    if settings.get("oauth.google.enabled"):
        providers.append({
            "type": "google",
            "name": "Google",
            "client_id": settings.get("oauth.google.client_id"),
        })
    if settings.get("oauth.zalo.enabled"):
        providers.append({
            "type": "zalo",
            "name": "Zalo",
            "app_id": settings.get("oauth.zalo.app_id"),
        })
    
    return {"providers": providers}


@router.get("")
async def get_all_settings(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get all system settings. SuperAdmin only."""
    require_super_admin(current_user)
    settings = await crud_system_setting.get_all(db)
    return {"success": True, "settings": settings}


# ========== Helpers ==========

def _mask_secret(value: str | None) -> str | None:
    """Mask a secret string for display."""
    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]
