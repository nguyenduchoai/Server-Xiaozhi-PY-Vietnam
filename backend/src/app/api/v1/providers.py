"""Provider API router.

Exposes endpoints to:
- Get provider schemas for UI rendering
- Validate provider configs
- Test provider connections
- CRUD operations for user-defined providers
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.base import PaginatedResponse

from ...api.dependencies import get_current_user
from ...config import load_config
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...core.logger import get_logger
from ...crud.crud_provider import crud_provider
from ...core.utils.cache import CacheKey, get_cache_manager, BaseCacheManager
from ...utils.config_encryption import encrypt_config, decrypt_config
from ...schemas.provider import (
    ProviderCategory,
    ProviderSourceFilter,
    ProviderCreate,
    ProviderCreateInternal,
    ProviderRead,
    ProviderListItem,
    ProviderUpdate,
    ProviderTestRequest,
    ProviderTestResponse,
    ProviderValidateRequest,
    ProviderValidateResponse,
    ProviderReferenceValidateRequest,
    ProviderReferenceValidateResponse,
    ProviderReferenceResolvedInfo,
    ProviderTestByReferenceRequest,
    ProviderTestByReferenceResponse,
)
from ...ai.module_factory import parse_provider_reference, normalize_provider_reference
from ...ai.providers.schema_registry import (
    get_all_schemas,
    get_provider_schema,
)
from ...ai.providers.schema_validator import validate_provider_config
from ...ai.module_factory import parse_provider_reference
from ...ai.providers.provider_tester import test_provider_connection
from ...models.provider import Provider
from sqlalchemy import select, func

logger = get_logger(__name__)
LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])

MODULE_KEYS = ["LLM", "VLLM", "TTS", "Memory", "Intent", "ASR"]

PROVIDERS_CACHE_TTL = 300


def _join_openai_compatible_url(base_url: str | None, path: str) -> str:
    """Join OpenAI-compatible base URLs whether they end at host, /v1, or /openai."""
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    normalized_path = path.strip("/")
    if base.endswith(("/v1", "/v1beta", "/openai")):
        return f"{base}/{normalized_path}"
    return f"{base}/v1/{normalized_path}"


def _model_supported_methods(model: dict[str, Any]) -> list[str]:
    methods = (
        model.get("supportedGenerationMethods")
        or model.get("supported_actions")
        or model.get("supportedActions")
        or []
    )
    return [str(method) for method in methods if method]


def _append_gemini_models(
    models: list[dict[str, Any]],
    gemini_models: list[dict[str, Any]],
    capability: str = "generateContent",
) -> None:
    """Append Gemini models that support the requested API capability."""
    for model in gemini_models:
        model_name = str(model.get("name", "")).replace("models/", "")
        if "gemini" not in model_name.lower():
            continue

        supported_methods = _model_supported_methods(model)
        if supported_methods and capability not in supported_methods:
            continue

        # Older/preview list responses may omit supported methods. Keep normal
        # chat models selectable, but do not let Live-only models leak into the
        # standard LLM dropdown where they would fail at generateContent/chat.
        if not supported_methods and capability == "generateContent":
            lowered = model_name.lower()
            if "live" in lowered or "bidi" in lowered:
                continue

        models.append(
            {
                "id": model_name,
                "name": model.get("displayName", model_name),
                "description": model.get("description", ""),
                "supported_methods": supported_methods,
                "input_token_limit": model.get("inputTokenLimit"),
                "output_token_limit": model.get("outputTokenLimit"),
            }
        )


def _get_cache_manager() -> BaseCacheManager:
    from app.core.utils.cache import client as redis_client, get_cache_manager
    return get_cache_manager(redis_client)


# ========== Config Endpoints ==========


@router.get(
    "/config/modules",
    status_code=status.HTTP_200_OK,
    summary="Get available modules/providers for current user",
    description="Trả về danh sách providers của user grouped by category. Nếu include_defaults=true thì kèm cả config.yml defaults.",
)
async def get_config_modules(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    include_defaults: bool = Query(
        default=False,
        description="Include default modules from config.yml",
    ),
) -> Dict[str, List[Any]]:
    """
    Lấy danh sách providers của user grouped by category.

    Response example (include_defaults=false):
    ```json
    {
        "LLM": [
            {"id": "uuid-1", "name": "My GPT-4", "type": "openai", "source": "user"},
            {"id": "uuid-2", "name": "My Gemini", "type": "gemini", "source": "user"}
        ],
        "TTS": [
            {"id": "uuid-3", "name": "My Edge TTS", "type": "edge", "source": "user"}
        ],
        "ASR": [],
        ...
    }
    ```

    Response example (include_defaults=true):
    ```json
    {
        "LLM": [
            {"id": "uuid-1", "name": "My GPT-4", "type": "openai", "source": "user"},
            {"name": "CopilotLLM", "source": "default"},
            {"name": "GPT5miniLLM", "source": "default"}
        ],
        ...
    }
    ```
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        cache_key = CacheKey.PROVIDER_CONFIG_MODULES
        cache_manager = _get_cache_manager()
        
        cache_key_str = f"{cache_key.value}:{user_id}:{include_defaults}"
        cached_data = await cache_manager.get(cache_key_str)
        if cached_data:
            return JSONResponse(status_code=status.HTTP_200_OK, content=cached_data)
        
        from sqlalchemy import select
        from ...models.provider import Provider
        
        result: Dict[str, List[Any]] = {key: [] for key in MODULE_KEYS}

        # Query only current user's providers from database
        conditions = [
            Provider.is_deleted == False,
            Provider.is_active == True,
            Provider.user_id == user_id,
        ]
        
        query = select(Provider).where(*conditions)
        db_result = await db.execute(query)
        providers = db_result.scalars().all()

        # Group providers by category with reference field
        for provider in providers:
            category = provider.category
            if category in result:
                result[category].append(
                    {
                        "reference": f"db:{provider.id}",
                        "id": provider.id,
                        "name": provider.name,
                        "type": provider.type,
                        "source": "user",
                        "permissions": ["read", "test", "edit", "delete"],
                    }
                )

        # Include defaults from config.yml if requested
        if include_defaults:
            try:
                config = load_config()
                for module_key in MODULE_KEYS:
                    if module_key in config:
                        module_config = config[module_key]
                        if isinstance(module_config, dict):
                            for key, cfg in module_config.items():
                                # Get type from config, fallback to key name
                                provider_type = (
                                    cfg.get("type", key)
                                    if isinstance(cfg, dict)
                                    else key
                                )
                                result[module_key].append(
                                    {
                                        "reference": f"config:{key}",
                                        "name": key,
                                        "type": provider_type,
                                        "source": "default",
                                        "permissions": [
                                            "read",
                                            "test",
                                        ],  # Config providers: read-only + test
                                    }
                                )
            except Exception as config_err:
                LOGGER.warning(f"Failed to load config defaults: {config_err}")

        await cache_manager.set(cache_key_str, result, ttl=PROVIDERS_CACHE_TTL)
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)

    except Exception as exc:
        LOGGER.error(f"Error loading config modules: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to load modules: {str(exc)}"},
        )


# ========== Helper Functions ==========


def mask_secrets(
    config: dict[str, Any], category: str, provider_type: str
) -> dict[str, Any]:
    """Mask secret fields in config for API response."""
    schema = get_provider_schema(category, provider_type)
    if not schema:
        return config

    masked = config.copy()
    # for field in schema.fields:
    #     if field.type == FieldType.SECRET and field.name in masked:
    #         masked[field.name] = "***"

    return masked


async def verify_provider_ownership(
    db: AsyncSession,
    provider_id: str,
    user_id: str,
    is_superuser: bool = False,
) -> ProviderRead:
    """
    Return the requested provider if it belongs to the provided user.
    Super admin can access ANY provider.

    Raises:
        NotFoundException: If the provider does not exist for the user
    """
    if is_superuser:
        # Super admin can access any provider
        provider = await crud_provider.get(
            db=db,
            id=provider_id,
            is_deleted=False,
            schema_to_select=ProviderRead,
            return_as_model=True,
        )
    else:
        # Normal user can only access their own providers
        provider = await crud_provider.get(
            db=db,
            id=provider_id,
            user_id=user_id,
            is_deleted=False,
            schema_to_select=ProviderRead,
            return_as_model=True,
        )

    if not provider:
        raise NotFoundException(f"Provider {provider_id} not found")

    return provider


# ========== Schema Endpoints ==========


@router.get("/schemas", tags=["schemas"])
async def get_all_provider_schemas() -> dict[str, Any]:
    """
    Get all provider schemas for UI rendering.

    Returns nested structure:
    {
        "LLM": {"openai": {...}, "gemini": {...}},
        "TTS": {"edge": {...}, "google": {...}},
        ...
    }
    """
    schemas = get_all_schemas()
    return {
        category: {ptype: schema.model_dump() for ptype, schema in types.items()}
        for category, types in schemas.items()
    }


@router.get("/schemas/categories", tags=["schemas"])
async def get_schema_categories() -> dict[str, Any]:
    """
    Get all provider categories with full schema data for each type.

    Returns:
        {
            "categories": ["LLM", "TTS", "ASR"],
            "data": {
                "LLM": {"openai": {...}, "gemini": {...}},
                "TTS": {"edge": {...}, "google": {...}},
                ...
            }
        }
    """
    schemas = get_all_schemas()
    return {
        "categories": list(schemas.keys()),
        "data": {
            category: {ptype: schema.model_dump() for ptype, schema in types.items()}
            for category, types in schemas.items()
        },
    }


# ========== Dynamic Models Endpoints ==========


@router.get("/models/{provider_type}", tags=["models"])
async def get_provider_models(
    provider_type: str,
    api_key: str = Query(..., description="API key for the provider"),
    base_url: str = Query(None, description="Base URL for OpenAI-compatible APIs"),
    capability: str = Query(
        "generateContent",
        description="Gemini supportedGenerationMethods filter, e.g. generateContent or bidiGenerateContent",
    ),
) -> dict[str, Any]:
    """
    Fetch available models from provider API.
    
    Supports:
    - openai: GET https://api.openai.com/v1/models
    - gemini: GET https://generativelanguage.googleapis.com/v1beta/models
    - claude: GET https://api.anthropic.com/v1/models
    
    Returns list of models with id and name for UI dropdown.
    """
    import httpx
    
    models = []
    error = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if provider_type in ("openai", "gpt", "openai_compatible"):
                if base_url and "generativelanguage.googleapis.com" in base_url:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    _append_gemini_models(
                        models,
                        data.get("models", []),
                        capability=capability,
                    )
                else:
                    # OpenAI or compatible API
                    url = _join_openai_compatible_url(base_url, "models")
                    headers = {"Authorization": f"Bearer {api_key}"}

                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()

                    # Filter and sort models
                    for model in data.get("data", []):
                        model_id = model.get("id", "")
                        # Filter for chat/completion models
                        if any(x in model_id for x in [
                            "gpt", "gemini", "gemini_live", "claude", "deepseek",
                            "llama", "mistral", "qwen",
                        ]):
                            models.append({
                                "id": model_id,
                                "name": model_id,
                                "owned_by": model.get("owned_by", ""),
                            })

                # Sort by name
                models.sort(key=lambda x: x["id"])

            elif provider_type in ("gemini", "google"):
                # Google Gemini API
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                _append_gemini_models(
                    models,
                    data.get("models", []),
                    capability=capability,
                )
                
            elif provider_type in ("claude", "anthropic"):
                # Anthropic Claude API
                url = "https://api.anthropic.com/v1/models"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                }
                
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    models.append({
                        "id": model_id,
                        "name": model.get("display_name", model_id),
                        "created_at": model.get("created_at", ""),
                    })
                    
            else:
                error = f"Unsupported provider type: {provider_type}"
                
    except httpx.HTTPStatusError as e:
        error = f"API error: {e.response.status_code} - {e.response.text[:200]}"
    except httpx.RequestError as e:
        error = f"Request failed: {str(e)}"
    except Exception as e:
        error = f"Unexpected error: {str(e)}"

    models.sort(key=lambda item: str(item.get("id", "")))
    
    return {
        "provider_type": provider_type,
        "models": models,
        "count": len(models),
        "error": error,
    }


@router.get("/voices/{provider_type}", tags=["voices"])
async def get_provider_voices(
    provider_type: str,
    api_key: str = Query(None, description="API key (required for cloud providers)"),
    language: str = Query("vi-VN", description="Filter voices by language/locale"),
) -> dict[str, Any]:
    """
    Fetch available voices from TTS provider API, filtered for Vietnamese.
    
    Supports:
    - edge/edge_tts: Microsoft Edge TTS (free, no API key)
    - openai/openai_stream: OpenAI-compatible TTS voices
    - elevenlab: ElevenLabs TTS voices
    - deepgram: Deepgram Aura TTS voices
    - google: Google Cloud Vietnamese TTS voices
    - gwen: Gwen local TTS
    - piper_local: Piper local models
    - vieneu: VieNeu Vietnamese TTS presets
    - minimax: MiniMax TTS voices
    
    Returns list of voices with id and name for UI dropdown.
    """
    import os
    import httpx
    
    voices = []
    error = None
    
    try:
        # ── Edge TTS (Free, no API key) ──
        if provider_type in ("edge", "edge_tts"):
            try:
                import edge_tts
                all_voices = await edge_tts.list_voices()
                lang_prefix = language.split("-")[0]  # "vi" from "vi-VN"
                
                vi_voices = [v for v in all_voices 
                             if v.get("Locale", "").startswith(lang_prefix)]
                
                for v in vi_voices:
                    short_name = v.get("ShortName", "")
                    gender = v.get("Gender", "")
                    v.get("FriendlyName", short_name)
                    locale = v.get("Locale", "")
                    
                    gender_icon = "👩" if gender == "Female" else "👨"
                    # Extract readable name from ShortName like "vi-VN-HoaiMyNeural"
                    name_part = short_name.split("-")[-1].replace("Neural", "")
                    
                    voices.append({
                        "id": short_name,
                        "name": f"{gender_icon} {name_part} ({gender} - {locale})",
                        "category": "free",
                    })
                    
                voices.sort(key=lambda x: x["name"])
                
            except ImportError:
                error = "edge_tts library not installed"
            except Exception:
                # Fallback: hardcoded Vietnamese Edge voices
                voices = [
                    {"id": "vi-VN-HoaiMyNeural", "name": "👩 HoaiMy (Female - vi-VN)", "category": "free"},
                    {"id": "vi-VN-NamMinhNeural", "name": "👨 NamMinh (Male - vi-VN)", "category": "free"},
                ]
        # ── OpenAI-compatible TTS ──
        elif provider_type in ("openai", "openai_tts", "openai_stream"):
            voices = [
                {"id": "alloy", "name": "Alloy", "category": "openai"},
                {"id": "ash", "name": "Ash", "category": "openai"},
                {"id": "ballad", "name": "Ballad", "category": "openai"},
                {"id": "coral", "name": "Coral", "category": "openai"},
                {"id": "echo", "name": "Echo", "category": "openai"},
                {"id": "fable", "name": "Fable", "category": "openai"},
                {"id": "nova", "name": "Nova", "category": "openai"},
                {"id": "onyx", "name": "Onyx", "category": "openai"},
                {"id": "sage", "name": "Sage", "category": "openai"},
                {"id": "shimmer", "name": "Shimmer", "category": "openai"},
            ]

        # ── ElevenLabs TTS ──
        elif provider_type in ("elevenlab", "elevenlabs"):
            if api_key:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    response = await client.get(
                        "https://api.elevenlabs.io/v1/voices",
                        headers={"xi-api-key": api_key},
                    )
                    response.raise_for_status()
                    data = response.json()
                    voices = [
                        {
                            "id": item.get("voice_id"),
                            "name": item.get("name") or item.get("voice_id"),
                            "category": item.get("category", "elevenlabs"),
                        }
                        for item in data.get("voices", [])
                        if item.get("voice_id")
                    ]
            else:
                voices = [
                    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "category": "elevenlabs"},
                    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "category": "elevenlabs"},
                    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah", "category": "elevenlabs"},
                    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "category": "elevenlabs"},
                ]

        # ── Deepgram Aura TTS ──
        elif provider_type == "deepgram":
            voices = [
                {"id": "aura-asteria-en", "name": "Asteria", "category": "deepgram"},
                {"id": "aura-luna-en", "name": "Luna", "category": "deepgram"},
                {"id": "aura-stella-en", "name": "Stella", "category": "deepgram"},
                {"id": "aura-athena-en", "name": "Athena", "category": "deepgram"},
                {"id": "aura-hera-en", "name": "Hera", "category": "deepgram"},
                {"id": "aura-orion-en", "name": "Orion", "category": "deepgram"},
                {"id": "aura-arcas-en", "name": "Arcas", "category": "deepgram"},
                {"id": "aura-perseus-en", "name": "Perseus", "category": "deepgram"},
                {"id": "aura-angus-en", "name": "Angus", "category": "deepgram"},
                {"id": "aura-orpheus-en", "name": "Orpheus", "category": "deepgram"},
                {"id": "aura-helios-en", "name": "Helios", "category": "deepgram"},
                {"id": "aura-zeus-en", "name": "Zeus", "category": "deepgram"},
            ]

        # ── Google Cloud TTS ──
        elif provider_type in ("google", "google_tts"):
            voices = [
                {"id": "vi-VN-Standard-A", "name": "vi-VN Standard A", "category": "standard"},
                {"id": "vi-VN-Standard-B", "name": "vi-VN Standard B", "category": "standard"},
                {"id": "vi-VN-Standard-C", "name": "vi-VN Standard C", "category": "standard"},
                {"id": "vi-VN-Standard-D", "name": "vi-VN Standard D", "category": "standard"},
                {"id": "vi-VN-Wavenet-A", "name": "vi-VN Wavenet A", "category": "wavenet"},
                {"id": "vi-VN-Wavenet-B", "name": "vi-VN Wavenet B", "category": "wavenet"},
                {"id": "vi-VN-Wavenet-C", "name": "vi-VN Wavenet C", "category": "wavenet"},
                {"id": "vi-VN-Wavenet-D", "name": "vi-VN Wavenet D", "category": "wavenet"},
            ]

        # ── Gwen local TTS ──
        elif provider_type == "gwen":
            voices = [
                {"id": "gwen-vi", "name": "Gwen Vietnamese", "category": "local"},
            ]

        # ── Valtec Vietnamese TTS (all Vietnamese, local) ──
        elif provider_type in ("valtec", "valtec_tts"):
            # Static built-in voices
            voices = [
                {"id": "NF", "name": "👩 Nữ Bắc — NF", "category": "multi-speaker"},
                {"id": "SF", "name": "👩 Nữ Nam — SF", "category": "multi-speaker"},
                {"id": "NM1", "name": "👨 Nam Bắc 1 — NM1", "category": "multi-speaker"},
                {"id": "SM", "name": "👨 Nam Nam — SM", "category": "multi-speaker"},
                {"id": "NM2", "name": "👨 Nam Bắc 2 — NM2", "category": "multi-speaker"},
                {"id": "thu_ha", "name": "🎤 Thu Hà (Voice Clone)", "category": "voice-clone"},
                {"id": "minh_duc", "name": "🎤 Minh Đức (Voice Clone)", "category": "voice-clone"},
                {"id": "thanh_tam", "name": "🎤 Thanh Tâm (Voice Clone)", "category": "voice-clone"},
                {"id": "quang_huy", "name": "🎤 Quang Huy (Voice Clone)", "category": "voice-clone"},
                {"id": "ngoc_anh", "name": "🎤 Ngọc Ánh (Voice Clone)", "category": "voice-clone"},
                {"id": "hoang_nam", "name": "🎤 Hoàng Nam (Voice Clone)", "category": "voice-clone"},
            ]
            
            # Dynamically fetch custom cloned voices from Valtec-TTS service
            builtin_ids = {"NF", "SF", "NM1", "SM", "NM2", 
                          "thu_ha", "minh_duc", "thanh_tam", 
                          "quang_huy", "ngoc_anh", "hoang_nam"}
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get("http://valtec-tts:8101/reference_voices")
                    if response.status_code == 200:
                        data = response.json()
                        for voice_id in data.get("voices", []):
                            if voice_id not in builtin_ids:
                                # This is a custom cloned voice
                                display_name = voice_id.replace("_", " ").title()
                                voices.append({
                                    "id": f"custom:{voice_id}",
                                    "name": f"🎭 {display_name} (Custom Clone)",
                                    "category": "custom-clone",
                                })
            except Exception:
                pass  # Valtec-TTS not available, just use static list

        # ── Piper local TTS ──
        elif provider_type == "piper_local":
            model_dirs = [
                "/data/tts-models",
                "/app/data/tts-models",
                "/app/src/app/data/models/piper",
                "data/tts-models",
            ]
            seen = set()
            for model_dir in model_dirs:
                if not os.path.isdir(model_dir):
                    continue
                for filename in os.listdir(model_dir):
                    if not filename.endswith(".onnx"):
                        continue
                    voice_id = filename[:-5]
                    if voice_id in seen:
                        continue
                    seen.add(voice_id)
                    voices.append({
                        "id": voice_id,
                        "name": voice_id.replace("_", " "),
                        "category": "local-model",
                    })
            if not voices:
                voices = [
                    {"id": "ngochuyen", "name": "Ngọc Huyền", "category": "local"},
                    {"id": "vi_VN-vais1000", "name": "vi_VN-vais1000", "category": "local"},
                    {"id": "vi_VN-vais-medium", "name": "vi_VN-vais-medium", "category": "local"},
                ]

        # ── VieNeu Vietnamese TTS ──
        elif provider_type == "vieneu":
            voices = [
                {"id": "Doan", "name": "Đoàn", "category": "preset"},
                {"id": "ngochuyen", "name": "Ngọc Huyền", "category": "preset"},
                {"id": "auto", "name": "Auto / default voice", "category": "preset"},
            ]

        # ── MiniMax TTS ──
        elif provider_type == "minimax":
            voices = [
                {"id": "male-qn-qingse", "name": "Male QN Qingse", "category": "standard"},
                {"id": "female-tianmei", "name": "Female Tianmei", "category": "standard"},
                {"id": "male-yanjun", "name": "Male Yanjun", "category": "standard"},
                {"id": "female-zhixian", "name": "Female Zhixian", "category": "standard"},
                {"id": "male-qn-xiaobing", "name": "Male QN Xiaobing", "category": "standard"},
                {"id": "female-zhiyu", "name": "Female Zhiyu", "category": "standard"},
                {"id": "male-shawn", "name": "Male Shawn", "category": "standard"},
                {"id": "female-amira", "name": "Female Amira", "category": "standard"},
                {"id": "male-jason", "name": "Male Jason", "category": "standard"},
                {"id": "female-aria", "name": "Female Aria", "category": "standard"},
            ]

        # ── Adapters without voice lists ──
        elif provider_type in ("custom", "index_stream"):
            voices = []

        else:
            error = (
                f"Unsupported TTS provider: {provider_type}. Supported: "
                "edge, openai, openai_stream, elevenlab, deepgram, google, "
                "gwen, piper_local, vieneu, index_stream, custom, minimax"
            )
                
    except httpx.HTTPStatusError as e:
        error = f"API error: {e.response.status_code} - {e.response.text[:200]}"
    except httpx.RequestError as e:
        error = f"Request failed: {str(e)}"
    except Exception as e:
        error = f"Unexpected error: {str(e)}"
    
    return {
        "provider_type": provider_type,
        "voices": voices,
        "count": len(voices),
        "error": error,
    }


# ========== Validation Endpoints ==========


@router.post("/validate", response_model=ProviderValidateResponse, tags=["validation"])
async def validate_provider(
    request: ProviderValidateRequest,
) -> ProviderValidateResponse:
    """
    Validate provider config against schema (without saving or testing).

    Returns validation result with normalized config if valid.
    """
    is_valid, normalized, errors = validate_provider_config(
        category=request.category.value,
        provider_type=request.type,
        config=request.config,
    )

    return ProviderValidateResponse(
        valid=is_valid,
        normalized_config=normalized if is_valid else None,
        errors=errors,
    )


@router.post(
    "/validate-reference",
    response_model=ProviderReferenceValidateResponse,
    tags=["validation"],
)
async def validate_provider_reference(
    request: ProviderReferenceValidateRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> ProviderReferenceValidateResponse:
    """
    Validate provider reference format and check if provider exists.

    Reference formats:
    - "config:{name}" - Provider from config.yml
    - "db:{uuid}" - Provider from database

    Returns validation result with resolved provider info if valid.
    """
    reference = request.reference
    category = request.category.value
    errors: list[str] = []

    # Try to normalize/parse reference
    try:
        normalized = normalize_provider_reference(reference)
    except ValueError as e:
        return ProviderReferenceValidateResponse(
            valid=False,
            reference=reference,
            resolved=None,
            errors=[str(e)],
        )

    parsed = parse_provider_reference(normalized)
    if parsed is None:
        return ProviderReferenceValidateResponse(
            valid=False,
            reference=reference,
            resolved=None,
            errors=["Invalid provider reference format"],
        )

    source, value = parsed

    if source == "config":
        # Validate config provider exists
        try:
            config = load_config()
            if category not in config:
                errors.append(f"Category '{category}' not found in config")
            elif value not in config[category]:
                errors.append(
                    f"Provider '{value}' not found in config.yml for category '{category}'"
                )
            else:
                # Valid config provider
                cfg = config[category][value]
                provider_type = (
                    cfg.get("type", value) if isinstance(cfg, dict) else value
                )
                return ProviderReferenceValidateResponse(
                    valid=True,
                    reference=normalized,
                    resolved=ProviderReferenceResolvedInfo(
                        name=value,
                        type=provider_type,
                        source="default",
                    ),
                    errors=[],
                )
        except Exception as e:
            errors.append(f"Failed to load config: {str(e)}")

    elif source == "db":
        # Validate db provider exists and belongs to user
        user_id = current_user.get("sub") or current_user.get("id")
        try:
            provider = await crud_provider.get(
                db=db,
                id=value,
                user_id=user_id,
                is_deleted=False,
                schema_to_select=ProviderRead,
                return_as_model=True,
            )
            if provider is None:
                errors.append(
                    f"Provider '{value}' not found or does not belong to user"
                )
            elif provider.category != category:
                errors.append(
                    f"Provider '{value}' is category '{provider.category}', expected '{category}'"
                )
            else:
                # Valid db provider
                return ProviderReferenceValidateResponse(
                    valid=True,
                    reference=normalized,
                    resolved=ProviderReferenceResolvedInfo(
                        name=provider.name,
                        type=provider.type,
                        source="user",
                    ),
                    errors=[],
                )
        except Exception as e:
            errors.append(f"Failed to query provider: {str(e)}")

    return ProviderReferenceValidateResponse(
        valid=False,
        reference=normalized if normalized else reference,
        resolved=None,
        errors=errors,
    )


@router.post("/test", response_model=ProviderTestResponse, tags=["validation"])
async def test_provider(
    request: ProviderTestRequest,
) -> ProviderTestResponse:
    """
    Test provider config by validating schema AND making actual API call.

    1. Validates config against schema
    2. Creates temporary provider instance
    3. Makes minimal API call to verify connectivity
    4. Returns test result with latency info

    Optional `input_data` can be provided for custom test inputs:
    - ASR: `audio_base64` (base64-encoded audio)
    - TTS: `text` (custom text to synthesize)
    - LLM: `prompt` (custom prompt)
    - VLLM: `image_base64` + `question`

    If `input_data` is not provided, default test data is used.
    """
    # Step 1: Validate schema
    is_valid, normalized, errors = validate_provider_config(
        category=request.category.value,
        provider_type=request.type,
        config=request.config,
    )

    if not is_valid:
        return ProviderTestResponse(
            valid=False,
            errors=errors,
            test_result=None,
        )

    # Step 2: Test provider connection
    # Import here to avoid circular imports

    test_result = await test_provider_connection(
        category=request.category.value,
        provider_type=request.type,
        config=normalized,
        input_data=request.input_data,
    )

    return ProviderTestResponse(
        valid=True,
        normalized_config=normalized,
        errors=[],
        test_result=test_result,
    )


@router.post(
    "/test-reference",
    response_model=ProviderTestByReferenceResponse,
    tags=["validation"],
)
async def test_provider_by_reference(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    request: ProviderTestByReferenceRequest,
) -> ProviderTestByReferenceResponse:
    """
    Test provider by reference string.

    Supports:
    - "config:{name}" - test config provider from config.yml
    - "db:{uuid}" or plain UUID - test user's provider from database

    Optional `input_data` can be provided for custom test inputs:
    - ASR: `audio_base64` (base64-encoded audio)
    - TTS: `text` (custom text to synthesize)
    - LLM: `prompt` (custom prompt)
    - VLLM: `image_base64` + `question`

    If `input_data` is not provided, default test data is used.
    """


    # Parse reference
    parsed = parse_provider_reference(request.reference)
    if parsed is None:
        return ProviderTestByReferenceResponse(
            valid=False,
            reference=request.reference,
            errors=[f"Invalid provider reference format: {request.reference}"],
        )

    source, value = parsed
    provider_config: dict[str, Any] = {}
    category: str | None = None
    provider_type: str | None = None
    source_label: str | None = None

    if source == "config":
        # Load from config.yml
        try:
            config = load_config()
            found = False
            for cat in MODULE_KEYS:
                if cat in config and isinstance(config[cat], dict):
                    if value in config[cat]:
                        cfg = config[cat][value]
                        category = cat
                        provider_type = (
                            cfg.get("type", value) if isinstance(cfg, dict) else value
                        )
                        provider_config = cfg if isinstance(cfg, dict) else {}
                        provider_config["type"] = provider_type
                        source_label = "default"
                        found = True
                        break

            if not found:
                return ProviderTestByReferenceResponse(
                    valid=False,
                    reference=request.reference,
                    errors=[f"Config provider '{value}' not found"],
                )
        except Exception as e:
            return ProviderTestByReferenceResponse(
                valid=False,
                reference=request.reference,
                errors=[f"Failed to load config: {str(e)}"],
            )

    else:
        # source == "db" - fetch from database
        user_id = current_user["id"]
        try:
            provider = await crud_provider.get(
                db=db,
                id=value,
                user_id=user_id,
                is_deleted=False,
                schema_to_select=ProviderRead,
                return_as_model=True,
            )
            if not provider:
                return ProviderTestByReferenceResponse(
                    valid=False,
                    reference=request.reference,
                    errors=[f"Provider '{value}' not found or does not belong to user"],
                )

            category = provider.category
            provider_type = provider.type
            decrypted_cfg = decrypt_config(provider.config or {}, user_id)
            provider_config = {**decrypted_cfg, "type": provider.type}
            source_label = "user"
        except Exception as e:
            return ProviderTestByReferenceResponse(
                valid=False,
                reference=request.reference,
                errors=[f"Failed to fetch provider: {str(e)}"],
            )

    # Run test
    try:
        test_result = await test_provider_connection(
            category=category,
            provider_type=provider_type,
            config=provider_config,
            input_data=request.input_data,
        )

        return ProviderTestByReferenceResponse(
            valid=True,
            reference=request.reference,
            source=source_label,
            category=category,
            type=provider_type,
            errors=[],
            test_result=test_result,
        )
    except Exception as e:
        return ProviderTestByReferenceResponse(
            valid=False,
            reference=request.reference,
            source=source_label,
            category=category,
            type=provider_type,
            errors=[f"Test failed: {str(e)}"],
        )


# ========== CRUD Endpoints ==========


def _load_config_providers(category: ProviderCategory | None) -> list[dict[str, Any]]:
    """Load config providers from config.yml with optional category filter."""
    config_providers = []
    try:
        config = load_config()
        categories_to_check = [category.value] if category else MODULE_KEYS

        for cat in categories_to_check:
            if cat not in config or not isinstance(config[cat], dict):
                continue

            for name, cfg in config[cat].items():
                provider_type = cfg.get("type", name) if isinstance(cfg, dict) else name
                config_providers.append(
                    {
                        "reference": f"config:{name}",
                        "name": name,
                        "category": cat,
                        "type": provider_type,
                        "config": mask_secrets(
                            cfg if isinstance(cfg, dict) else {},
                            cat,
                            provider_type,
                        ),
                        "source": "default",
                        "permissions": ["read", "test"],
                        "is_active": True,
                    }
                )
    except Exception as e:
        LOGGER.warning(f"Failed to load config providers: {e}")

    return config_providers


def _format_user_provider(provider: Any) -> dict[str, Any]:
    """Format user provider with masked secrets and metadata."""
    p_dict = (
        provider.model_dump() if hasattr(provider, "model_dump") else dict(provider)
    )
    p_dict["config"] = mask_secrets(
        p_dict["config"], p_dict["category"], p_dict["type"]
    )
    p_dict["reference"] = f"db:{p_dict['id']}"
    p_dict["source"] = "user"
    p_dict["permissions"] = ["read", "test", "edit", "delete"]
    return p_dict


@router.get("", response_model=PaginatedResponse[ProviderListItem])
async def list_providers(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    category: Annotated[ProviderCategory | None, Query()] = None,
    source: Annotated[
        ProviderSourceFilter,
        Query(description="Filter by source: all, config, user"),
    ] = ProviderSourceFilter.USER,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, Any]:
    """
    List providers with proper pagination.
    
    Includes:
    - User's own providers
    - Config providers (if source=all or source=config)
    """
    
    user_id = current_user["id"]
    offset = (page - 1) * page_size

    # Case 1: Only config providers
    if source == ProviderSourceFilter.CONFIG:
        config_providers = _load_config_providers(category)
        total = len(config_providers)
        data = config_providers[offset : offset + page_size]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "success": True,
            "message": "Success",
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # Build query for current user's providers only
    conditions = [
        Provider.is_deleted == False,
        Provider.user_id == user_id,
    ]
    if category:
        conditions.append(Provider.category == category.value)
    
    # Count total
    count_query = select(func.count()).select_from(Provider).where(*conditions)
    count_result = await db.execute(count_query)
    user_count = count_result.scalar() or 0

    # Case 2: Only user providers
    if source == ProviderSourceFilter.USER:
        query = select(Provider).where(*conditions).offset(offset).limit(page_size)
        result = await db.execute(query)
        providers = result.scalars().all()
        
        data = []
        for p in providers:
            p_dict = {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "type": p.type,
                "config": mask_secrets(decrypt_config(p.config or {}, user_id), p.category, p.type),
                "is_active": p.is_active,
                "reference": f"db:{p.id}",
                "source": "user",
                "permissions": ["read", "test", "edit", "delete"],
            }
            data.append(p_dict)
        
        total_pages = (user_count + page_size - 1) // page_size if user_count > 0 else 0

        return {
            "success": True,
            "message": "Success",
            "data": data,
            "total": user_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # Case 3: All providers (config first, then user) with hybrid pagination
    config_providers = _load_config_providers(category)
    config_count = len(config_providers)
    total = config_count + user_count

    data: list[dict[str, Any]] = []

    if offset < config_count:
        # Page includes config providers
        config_slice = config_providers[offset : offset + page_size]
        data.extend(config_slice)

        remaining = page_size - len(config_slice)
        if remaining > 0:
            # Need user providers to fill the page
            query = select(Provider).where(*conditions).offset(0).limit(remaining)
            result = await db.execute(query)
            providers = result.scalars().all()
            for p in providers:
                data.append({
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "type": p.type,
                    "config": mask_secrets(decrypt_config(p.config or {}, user_id), p.category, p.type),
                    "is_active": p.is_active,
                    "reference": f"db:{p.id}",
                    "source": "user",
                    "permissions": ["read", "test", "edit", "delete"],
                })
    else:
        # Page is entirely in user providers
        user_offset = offset - config_count
        query = select(Provider).where(*conditions).offset(user_offset).limit(page_size)
        result = await db.execute(query)
        providers = result.scalars().all()
        for p in providers:
            data.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "type": p.type,
                "config": mask_secrets(decrypt_config(p.config or {}, user_id), p.category, p.type),
                "is_active": p.is_active,
                "reference": f"db:{p.id}",
                "source": "user",
                "permissions": ["read", "test", "edit", "delete"],
            })

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "success": True,
        "message": "Success",
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("", response_model=ProviderRead, status_code=201)
async def create_provider(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    provider: ProviderCreate,
) -> ProviderRead:
    """
    Create a new provider.

    Config is validated against schema before saving.
    """
    user_id = current_user["id"]

    # Validate config
    is_valid, normalized, errors = validate_provider_config(
        category=provider.category.value,
        provider_type=provider.type,
        config=provider.config,
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Create provider
    provider_internal = ProviderCreateInternal(
        user_id=user_id,
        name=provider.name,
        category=provider.category,
        type=provider.type,
        config=encrypt_config(normalized, user_id),
        is_active=provider.is_active,
    )

    created = await crud_provider.create(
        db=db,
        object=provider_internal,
        schema_to_select=ProviderRead,
        return_as_model=True,
    )

    # Convert ORM object to dict for response
    created_dict = {
        "id": created.id,
        "user_id": created.user_id,
        "name": created.name,
        "category": created.category,
        "type": created.type,
        "config": created.config,
        "is_active": created.is_active,
        "created_at": created.created_at,
        "updated_at": created.updated_at,
        "is_deleted": created.is_deleted,
    }

    # Mask secrets in response
    created_dict["config"] = mask_secrets(
        decrypt_config(created_dict["config"] or {}, user_id),
        created_dict["category"],
        created_dict["type"],
    )

    return created_dict


@router.get("/{reference}", response_model=None)
async def get_provider(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    reference: str,
) -> dict[str, Any]:
    """
    Get a provider by reference.

    Supports both:
    - "db:{uuid}" or plain UUID - fetch from database
    - "config:{name}" - fetch from config.yml

    Secret fields are masked in response.
    """

    parsed = parse_provider_reference(reference)
    if parsed is None:
        raise HTTPException(
            status_code=400, detail=f"Invalid provider reference format: {reference}"
        )

    source, value = parsed

    if source == "config":
        # Fetch from config.yml
        config = load_config()

        # Find provider in config by iterating categories
        for category in MODULE_KEYS:
            if category in config and isinstance(config[category], dict):
                if value in config[category]:
                    provider_config = config[category][value]
                    provider_type = (
                        provider_config.get("type", value)
                        if isinstance(provider_config, dict)
                        else value
                    )
                    return {
                        "reference": f"config:{value}",
                        "name": value,
                        "category": category,
                        "type": provider_type,
                        "config": mask_secrets(
                            (
                                provider_config
                                if isinstance(provider_config, dict)
                                else {}
                            ),
                            category,
                            provider_type,
                        ),
                        "source": "default",
                        "permissions": ["read", "test"],
                    }

        raise NotFoundException(f"Config provider '{value}' not found")

    else:
        # Fetch from database (source == "db")
        user_id = current_user["id"]
        provider = await verify_provider_ownership(db, value, user_id)

        result = (
            provider.model_dump() if hasattr(provider, "model_dump") else dict(provider)
        )
        result["config"] = mask_secrets(
            decrypt_config(result["config"] or {}, user_id), result["category"], result["type"]
        )
        result["reference"] = f"db:{result['id']}"
        result["source"] = "user"
        result["permissions"] = ["read", "test", "edit", "delete"]

        return result


@router.put("/{reference}", response_model=ProviderRead)
async def update_provider(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    reference: str,
    update_data: ProviderUpdate,
) -> dict[str, Any]:
    """
    Update a provider.

    Only database providers can be updated.
    Config providers (config:*) are read-only.

    If config is provided, it's validated against schema.
    """

    # Check if it's a config provider
    parsed = parse_provider_reference(reference)
    if parsed is None:
        raise HTTPException(
            status_code=400, detail=f"Invalid provider reference format: {reference}"
        )

    source, value = parsed
    
    # Check if user is super admin
    is_superuser = current_user.get("is_superuser", False)
    
    # Only super admin can modify config providers
    if source == "config" and not is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Config providers are read-only and cannot be updated",
        )
    
    # Config providers cannot be updated even by super admin (they're from file)
    if source == "config":
        raise HTTPException(
            status_code=400,
            detail="Config providers cannot be modified. Create a new provider instead.",
        )

    # It's a db provider, proceed with update
    provider_id = value
    user_id = current_user["id"]
    existing = await verify_provider_ownership(db, provider_id, user_id, is_superuser)

    # If config is being updated, validate it
    if update_data.config is not None:
        existing_dict = (
            existing.model_dump() if hasattr(existing, "model_dump") else dict(existing)
        )
        is_valid, normalized, errors = validate_provider_config(
            category=existing_dict["category"],
            provider_type=existing_dict["type"],
            config=update_data.config,
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})

        update_data.config = encrypt_config(normalized, user_id)

    # Build update dict excluding None values
    update_dict: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    if update_data.name is not None:
        update_dict["name"] = update_data.name
    if update_data.config is not None:
        update_dict["config"] = update_data.config
    if update_data.is_active is not None:
        update_dict["is_active"] = update_data.is_active

    # Super admin can update any provider
    if is_superuser:
        await crud_provider.update(
            db=db,
            object=update_dict,
            id=provider_id,
        )
    else:
        await crud_provider.update(
            db=db,
            object=update_dict,
            id=provider_id,
            user_id=user_id,
        )

    # Get updated provider
    updated = await verify_provider_ownership(db, provider_id, user_id, is_superuser)
    result = updated.model_dump() if hasattr(updated, "model_dump") else dict(updated)
    result["config"] = mask_secrets(
        decrypt_config(result["config"] or {}, user_id), result["category"], result["type"]
    )

    return result


@router.delete("/{reference}", status_code=204)
async def delete_provider(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    reference: str,
) -> None:
    """
    Delete a provider (soft delete).

    Only database providers can be deleted.
    Config providers (config:*) are read-only.
    """

    # Check if it's a config provider
    parsed = parse_provider_reference(reference)
    if parsed is None:
        raise HTTPException(
            status_code=400, detail=f"Invalid provider reference format: {reference}"
        )

    source, value = parsed
    
    # Check if user is super admin
    is_superuser = current_user.get("is_superuser", False)
    
    # Config providers cannot be deleted (they're from file)
    if source == "config":
        raise HTTPException(
            status_code=400,
            detail="Config providers cannot be deleted. They are defined in config.yml",
        )

    # It's a db provider, proceed with delete
    provider_id = value
    user_id = current_user["id"]
    await verify_provider_ownership(db, provider_id, user_id, is_superuser)

    # Soft delete using FastCRUD's built-in soft delete
    await crud_provider.delete(
        db=db,
        id=provider_id,
    )
