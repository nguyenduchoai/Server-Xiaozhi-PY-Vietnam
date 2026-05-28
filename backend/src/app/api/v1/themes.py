"""
Theme API - Manage device themes and theme gallery
"""

from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.db.database import async_get_db
from app.core.logger import get_logger
from app.api.dependencies import get_current_user
from app.crud.crud_theme import crud_theme, crud_theme_installation
from app.crud.crud_device import crud_device
from app.schemas.device import DeviceRead
from app.services.mqtt_service import MQTTService

logger = get_logger(__name__)
router = APIRouter(prefix="/themes", tags=["Themes"])


# ============ Schemas ============

class ClockConfig(BaseModel):
    """Clock face configuration"""
    hour_hand: Optional[str] = Field(None, max_length=10)
    minute_hand: Optional[str] = Field(None, max_length=10)
    second_hand: Optional[str] = Field(None, max_length=10)
    center_dot: Optional[str] = Field(None, max_length=10)
    number_color: Optional[str] = Field(None, max_length=10)
    tick_color: Optional[str] = Field(None, max_length=10)
    background: Optional[str] = Field(None, max_length=10)
    background_image_url: Optional[str] = Field(None, max_length=2048)
    use_background_image: bool = False
    show_numbers: bool = True
    show_tick_marks: bool = True

    model_config = {"extra": "allow"}


class ColorConfig(BaseModel):
    """Color palette configuration"""
    primary: Optional[str] = Field(None, max_length=10)
    secondary: Optional[str] = Field(None, max_length=10)
    background: Optional[str] = Field(None, max_length=10)
    text: Optional[str] = Field(None, max_length=10)
    accent: Optional[str] = Field(None, max_length=10)

    model_config = {"extra": "allow"}


class ThemeDataConfig(BaseModel):
    """Typed theme data configuration"""
    clock: Optional[ClockConfig] = None
    colors: Optional[ColorConfig] = None
    menu: Optional[dict] = None
    idle: Optional[dict] = None

    model_config = {"extra": "allow"}


class ThemeCreate(BaseModel):
    """Create theme request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    screen_type: str = Field(default="240x240", max_length=20)
    category: str = Field(default="custom", max_length=50)
    theme_data: Optional[ThemeDataConfig] = None


class ThemeUpdate(BaseModel):
    """Update theme request"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)
    theme_data: Optional[ThemeDataConfig] = None


class ThemeResponse(BaseModel):
    """Theme response"""
    id: str
    name: str
    description: Optional[str]
    preview_url: Optional[str]
    screen_type: str
    category: str
    is_system: bool
    download_count: int
    theme_data: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


class ThemeListResponse(BaseModel):
    """Theme list response"""
    themes: List[ThemeResponse]
    total: int
    page: int
    limit: int


class WidgetConfig(BaseModel):
    """Widget configuration"""
    clock: bool = True
    weather: bool = True
    calendar: bool = False
    lunar: bool = True


class ApplyThemeRequest(BaseModel):
    """Apply theme to device"""
    theme_id: str
    widgets: Optional[WidgetConfig] = None


# ============ Theme CRUD Endpoints ============

@router.get(
    "",
    response_model=ThemeListResponse,
    summary="List all themes"
)
async def list_themes(
    screen_type: Optional[str] = Query(None, description="Filter by screen type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
):
    """List available themes with filtering"""
    skip = (page - 1) * limit
    
    themes = await crud_theme.get_multi(
        db,
        skip=skip,
        limit=limit,
        screen_type=screen_type,
        category=category,
        search=search,
    )
    
    total = await crud_theme.count(
        db,
        screen_type=screen_type,
        category=category,
    )
    
    return ThemeListResponse(
        themes=[
            ThemeResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                preview_url=t.preview_url,
                screen_type=t.screen_type or "240x240",
                category=t.category or "default",
                is_system=t.is_system or False,
                download_count=t.download_count or 0,
                theme_data=t.theme_data,
                created_at=t.created_at.isoformat() if t.created_at else "",
            )
            for t in themes
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/categories",
    summary="List theme categories"
)
async def list_categories():
    """List available theme categories"""
    return {
        "categories": [
            {"id": "default", "name": "Mặc định", "icon": "🎨"},
            {"id": "anime", "name": "Anime", "icon": "🎌"},
            {"id": "minimal", "name": "Tối giản", "icon": "⬜"},
            {"id": "cute", "name": "Dễ thương", "icon": "🥰"},
            {"id": "dark", "name": "Tối", "icon": "🌙"},
            {"id": "colorful", "name": "Nhiều màu", "icon": "🌈"},
            {"id": "seasonal", "name": "Theo mùa", "icon": "🍂"},
            {"id": "custom", "name": "Tùy chỉnh", "icon": "✏️"},
        ]
    }


@router.get(
    "/screen-types",
    summary="List screen types"
)
async def list_screen_types():
    """List supported screen types"""
    return {
        "screen_types": [
            {"id": "240x240", "name": "1.54 inch (240x240)", "description": "Lily Box Classic"},
            {"id": "284x240", "name": "OSTB (284x240)", "description": "OSTB Display"},
            {"id": "320x240", "name": "2.4 inch (320x240)", "description": "Large Display"},
            {"id": "128x64", "name": "OLED (128x64)", "description": "Small OLED"},
        ]
    }


@router.get(
    "/{theme_id}",
    response_model=ThemeResponse,
    summary="Get theme details"
)
async def get_theme(
    theme_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
):
    """Get theme by ID"""
    theme = await crud_theme.get(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    return ThemeResponse(
        id=theme.id,
        name=theme.name,
        description=theme.description,
        preview_url=theme.preview_url,
        screen_type=theme.screen_type,
        category=theme.category,
        is_system=theme.is_system,
        download_count=theme.download_count,
        created_at=theme.created_at.isoformat() if theme.created_at else "",
    )


@router.post(
    "",
    response_model=ThemeResponse,
    summary="Create custom theme"
)
async def create_theme(
    request: ThemeCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new custom theme"""
    theme = await crud_theme.create(
        db,
        name=request.name,
        description=request.description,
        screen_type=request.screen_type,
        category=request.category,
        theme_data=request.theme_data,
        created_by=current_user["id"],
        is_system=False,
    )
    
    return ThemeResponse(
        id=theme.id,
        name=theme.name,
        description=theme.description,
        preview_url=theme.preview_url,
        screen_type=theme.screen_type,
        category=theme.category,
        is_system=theme.is_system,
        download_count=theme.download_count,
        created_at=theme.created_at.isoformat() if theme.created_at else "",
    )


@router.put(
    "/{theme_id}",
    response_model=ThemeResponse,
    summary="Update theme"
)
async def update_theme(
    theme_id: str,
    request: ThemeUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update a theme (only owner or admin)"""
    theme = await crud_theme.get(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    if theme.created_by != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    theme = await crud_theme.update(db, theme_id, **updates)
    
    return ThemeResponse(
        id=theme.id,
        name=theme.name,
        description=theme.description,
        preview_url=theme.preview_url,
        screen_type=theme.screen_type,
        category=theme.category,
        is_system=theme.is_system,
        download_count=theme.download_count,
        created_at=theme.created_at.isoformat() if theme.created_at else "",
    )


@router.delete(
    "/{theme_id}",
    summary="Delete theme"
)
async def delete_theme(
    theme_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a theme (only owner or admin)"""
    theme = await crud_theme.get(db, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    if theme.is_system and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Cannot delete system themes")
    
    if theme.created_by != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await crud_theme.delete(db, theme_id)
    return {"success": True, "message": "Theme deleted"}


# ============ Device Theme Endpoints ============

@router.get(
    "/devices/{device_id}/current",
    summary="Get device's current theme"
)
async def get_device_theme(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Get currently installed theme on device"""
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    installation = await crud_theme_installation.get_active_theme(db, device_id)
    if not installation:
        return {
            "device_id": device_id,
            "theme": None,
            "widgets": {
                "clock": True,
                "weather": True,
                "calendar": False,
                "lunar": True,
            }
        }
    
    theme = await crud_theme.get(db, installation.theme_id)
    
    return {
        "device_id": device_id,
        "theme": {
            "id": theme.id if theme else None,
            "name": theme.name if theme else "Unknown",
            "preview_url": theme.preview_url if theme else None,
        } if theme else None,
        "widgets": {
            "clock": installation.widget_clock_enabled,
            "weather": installation.widget_weather_enabled,
            "calendar": installation.widget_calendar_enabled,
            "lunar": installation.widget_lunar_enabled,
        },
        "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
    }


@router.post(
    "/devices/{device_id}/apply",
    summary="Apply theme to device"
)
async def apply_theme_to_device(
    device_id: str,
    request: ApplyThemeRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Install theme on device and push via MQTT"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify theme exists
    theme = await crud_theme.get(db, request.theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # Validate theme screen compatibility with device board
    if device.board and theme.screen_type:
        from ...services.board_registry import get_board_info
        board_info = get_board_info(device.board)
        if board_info:
            # Parse theme screen type (e.g., "320x240")
            try:
                theme_parts = theme.screen_type.split("x")
                if len(theme_parts) == 2:
                    theme_w, theme_h = int(theme_parts[0]), int(theme_parts[1])
                    # Check if resolution matches (or rotated match)
                    if not (
                        (board_info.width == theme_w and board_info.height == theme_h) or
                        (board_info.width == theme_h and board_info.height == theme_w)
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Theme resolution {theme.screen_type} is not compatible with device board '{device.board}' ({board_info.resolution})"
                        )
            except ValueError:
                pass  # Skip validation if screen_type is not parseable
    
    # Create installation record
    widget_config = request.widgets.model_dump() if request.widgets else None
    installation = await crud_theme_installation.install_theme(
        db,
        device_id=device_id,
        theme_id=request.theme_id,
        widget_config=widget_config,
    )
    
    # Increment download count
    await crud_theme.increment_download(db, request.theme_id)
    
    # Push theme to device via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/theme",
                {
                    "type": "theme_install",
                    "theme_id": theme.id,
                    "theme_name": theme.name,
                    "theme_data": theme.theme_data,
                    "preview_url": theme.preview_url,
                    "widgets": widget_config or {
                        "clock": True,
                        "weather": True,
                        "calendar": False,
                        "lunar": True,
                    }
                }
            )
            logger.info(f"Theme pushed to device {device_id}: {theme.name}")
    except Exception as e:
        logger.warning(f"Failed to push theme via MQTT: {e}")
    
    return {
        "success": True,
        "message": f"Theme '{theme.name}' applied to device",
        "device_id": device_id,
        "theme_id": theme.id,
        "installation_id": installation.id,
    }


@router.put(
    "/devices/{device_id}/widgets",
    summary="Update device widget settings"
)
async def update_device_widgets(
    device_id: str,
    widgets: WidgetConfig,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update widget settings for device display"""
    # Verify device ownership
    device = await crud_device.get(db=db, id=device_id, schema_to_select=DeviceRead, return_as_model=True)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.user_id != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update installation
    await crud_theme_installation.update_widgets(
        db,
        device_id=device_id,
        widget_config=widgets.model_dump(),
    )
    
    # Push to device via MQTT
    try:
        mqtt_service = MQTTService.get_instance()
        if mqtt_service and mqtt_service.is_available():
            await mqtt_service.publish(
                f"device/{device.mac_address}/widgets",
                {
                    "type": "widget_update",
                    "widgets": widgets.model_dump()
                }
            )
            logger.info(f"Widgets updated for device {device_id}")
    except Exception as e:
        logger.warning(f"Failed to push widgets via MQTT: {e}")
    
    return {
        "success": True,
        "message": "Widget settings updated",
        "device_id": device_id,
        "widgets": widgets.model_dump(),
    }
