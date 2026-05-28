"""API endpoints for Board Type and Screen Type management.

Provides centralized hardware type management used by:
- Devices
- Asset Templates  
- Firmware OTA
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import async_get_db, get_current_superuser
from ...crud.crud_board_type import crud_board_type, crud_screen_type
from ...schemas.board_type import (
    BoardTypeCreate,
    BoardTypeList,
    BoardTypeRead,
    BoardTypeUpdate,
    HardwareTypesResponse,
    ScreenTypeCreate,
    ScreenTypeList,
    ScreenTypeRead,
    ScreenTypeUpdate,
)

router = APIRouter(prefix="/hardware-types", tags=["hardware-types"])


# =============================================================================
# Public endpoints - Get hardware types for dropdowns
# =============================================================================

@router.get("", response_model=HardwareTypesResponse)
async def get_hardware_types(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    active_only: bool = True,
) -> HardwareTypesResponse:
    """
    Get all board and screen types for dropdowns.
    
    Used by Devices, Asset Templates, and Firmware OTA modules.
    """
    board_filter = {"is_active": True} if active_only else {}
    screen_filter = {"is_active": True} if active_only else {}
    
    boards_result = await crud_board_type.get_multi(
        db=db,
        **board_filter,
        sort_columns=["sort_order", "name"],
        sort_orders=["asc", "asc"],
    )
    
    screens_result = await crud_screen_type.get_multi(
        db=db,
        **screen_filter,
        sort_columns=["sort_order", "name"],
        sort_orders=["asc", "asc"],
    )
    
    return HardwareTypesResponse(
        board_types=[BoardTypeList.model_validate(b) for b in boards_result.get("data", [])],
        screen_types=[ScreenTypeList.model_validate(s) for s in screens_result.get("data", [])],
    )


@router.get("/boards", response_model=list[BoardTypeList])
async def get_board_types(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    active_only: bool = True,
) -> list[BoardTypeList]:
    """Get all board types."""
    filter_params = {"is_active": True} if active_only else {}
    
    result = await crud_board_type.get_multi(
        db=db,
        **filter_params,
        sort_columns=["sort_order", "name"],
        sort_orders=["asc", "asc"],
    )
    
    return [BoardTypeList.model_validate(b) for b in result.get("data", [])]


@router.get("/screens", response_model=list[ScreenTypeList])
async def get_screen_types(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    active_only: bool = True,
) -> list[ScreenTypeList]:
    """Get all screen types."""
    filter_params = {"is_active": True} if active_only else {}
    
    result = await crud_screen_type.get_multi(
        db=db,
        **filter_params,
        sort_columns=["sort_order", "name"],
        sort_orders=["asc", "asc"],
    )
    
    return [ScreenTypeList.model_validate(s) for s in result.get("data", [])]


# =============================================================================
# Admin endpoints - Board Types CRUD
# =============================================================================

@router.get("/boards/{board_id}", response_model=BoardTypeRead)
async def get_board_type(
    board_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> BoardTypeRead:
    """Get a specific board type by ID."""
    board = await crud_board_type.get(db=db, id=board_id)
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board type not found",
        )
    return BoardTypeRead.model_validate(board)


@router.post("/boards", response_model=BoardTypeRead, status_code=status.HTTP_201_CREATED)
async def create_board_type(
    data: BoardTypeCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
) -> BoardTypeRead:
    """Create a new board type. Admin only."""
    # Check if code already exists
    existing = await crud_board_type.get(db=db, code=data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Board type with code '{data.code}' already exists",
        )
    
    board = await crud_board_type.create(db=db, object=data)
    return BoardTypeRead.model_validate(board)


@router.patch("/boards/{board_id}", response_model=BoardTypeRead)
async def update_board_type(
    board_id: int,
    data: BoardTypeUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
) -> BoardTypeRead:
    """Update a board type. Admin only."""
    board = await crud_board_type.get(db=db, id=board_id)
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board type not found",
        )
    
    # Check if new code conflicts with existing
    if data.code and data.code != board.code:
        existing = await crud_board_type.get(db=db, code=data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Board type with code '{data.code}' already exists",
            )
    
    updated = await crud_board_type.update(db=db, object=data, id=board_id)
    return BoardTypeRead.model_validate(updated)


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_type(
    board_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
    force: bool = False,
) -> None:
    """Delete a board type. Admin only.

    Hardening: refuse delete (409) if any device still references this
    board type, unless ``?force=true``. Without this guard, deleting
    a board orphans `device.board` references → device detail fetch breaks.
    """
    from sqlalchemy import select, func
    from ...models.device import Device

    board = await crud_board_type.get(db=db, id=board_id)
    if not board:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board type not found",
        )

    # Count devices referencing this board (by slug/name).
    board_ref = getattr(board, "slug", None) or getattr(board, "name", None) or str(board_id)
    cnt_q = await db.execute(
        select(func.count(Device.id)).where(
            Device.board == board_ref,
            Device.is_deleted.is_(False) if hasattr(Device, "is_deleted") else True,  # type: ignore
        )
    )
    in_use = cnt_q.scalar() or 0
    if in_use and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Board type '{board_ref}' is referenced by {in_use} device(s). "
                "Pass ?force=true to delete anyway (devices will keep stale board ref)."
            ),
        )

    await crud_board_type.delete(db=db, id=board_id)


# =============================================================================
# Admin endpoints - Screen Types CRUD
# =============================================================================

@router.get("/screens/{screen_id}", response_model=ScreenTypeRead)
async def get_screen_type(
    screen_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> ScreenTypeRead:
    """Get a specific screen type by ID."""
    screen = await crud_screen_type.get(db=db, id=screen_id)
    if not screen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screen type not found",
        )
    return ScreenTypeRead.model_validate(screen)


@router.post("/screens", response_model=ScreenTypeRead, status_code=status.HTTP_201_CREATED)
async def create_screen_type(
    data: ScreenTypeCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
) -> ScreenTypeRead:
    """Create a new screen type. Admin only."""
    # Check if code already exists
    existing = await crud_screen_type.get(db=db, code=data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Screen type with code '{data.code}' already exists",
        )
    
    screen = await crud_screen_type.create(db=db, object=data)
    return ScreenTypeRead.model_validate(screen)


@router.patch("/screens/{screen_id}", response_model=ScreenTypeRead)
async def update_screen_type(
    screen_id: int,
    data: ScreenTypeUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
) -> ScreenTypeRead:
    """Update a screen type. Admin only."""
    screen = await crud_screen_type.get(db=db, id=screen_id)
    if not screen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screen type not found",
        )
    
    # Check if new code conflicts with existing
    if data.code and data.code != screen.code:
        existing = await crud_screen_type.get(db=db, code=data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Screen type with code '{data.code}' already exists",
            )
    
    updated = await crud_screen_type.update(db=db, object=data, id=screen_id)
    return ScreenTypeRead.model_validate(updated)


@router.delete("/screens/{screen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_screen_type(
    screen_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
) -> None:
    """Delete a screen type. Admin only."""
    screen = await crud_screen_type.get(db=db, id=screen_id)
    if not screen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screen type not found",
        )
    
    await crud_screen_type.delete(db=db, id=screen_id)


# =============================================================================
# Seed default data endpoint
# =============================================================================

@router.post("/seed-defaults", status_code=status.HTTP_201_CREATED)
async def seed_default_hardware_types(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    _: Annotated[dict, Depends(get_current_superuser)],
) -> dict:
    """
    Seed default board and screen types. Admin only.
    
    This will create default entries if they don't exist.
    """
    # Default board types
    default_boards = [
        BoardTypeCreate(
            code="esp32",
            name="ESP32",
            description="ESP32 WROOM/WROVER module",
            chip_family="ESP32",
            flash_size_mb=4,
            psram_size_mb=0,
            sort_order=1,
        ),
        BoardTypeCreate(
            code="esp32s3",
            name="ESP32-S3",
            description="ESP32-S3 with AI acceleration",
            chip_family="ESP32-S3",
            flash_size_mb=8,
            psram_size_mb=8,
            sort_order=2,
        ),
        BoardTypeCreate(
            code="esp32c3",
            name="ESP32-C3",
            description="ESP32-C3 RISC-V module",
            chip_family="ESP32-C3",
            flash_size_mb=4,
            psram_size_mb=0,
            sort_order=3,
        ),
        BoardTypeCreate(
            code="esp32c6",
            name="ESP32-C6",
            description="ESP32-C6 with WiFi 6 and Thread",
            chip_family="ESP32-C6",
            flash_size_mb=4,
            psram_size_mb=0,
            sort_order=4,
        ),
    ]
    
    # Default screen types
    default_screens = [
        ScreenTypeCreate(
            code="none",
            name="Không màn hình",
            description="Device without display",
            driver="none",
            width=0,
            height=0,
            color_depth=1,
            sort_order=0,
        ),
        ScreenTypeCreate(
            code="ssd1306_128x64",
            name="OLED 128x64",
            description="SSD1306 OLED 0.96 inch",
            driver="ssd1306",
            width=128,
            height=64,
            color_depth=1,
            sort_order=1,
        ),
        ScreenTypeCreate(
            code="ssd1306_128x32",
            name="OLED 128x32",
            description="SSD1306 OLED 0.91 inch",
            driver="ssd1306",
            width=128,
            height=32,
            color_depth=1,
            sort_order=2,
        ),
        ScreenTypeCreate(
            code="st7789_240x240",
            name="LCD 240x240",
            description="ST7789 LCD 1.3 inch square",
            driver="st7789",
            width=240,
            height=240,
            color_depth=16,
            sort_order=3,
        ),
        ScreenTypeCreate(
            code="st7789_240x320",
            name="LCD 240x320",
            description="ST7789 LCD 2.0 inch",
            driver="st7789",
            width=240,
            height=320,
            color_depth=16,
            sort_order=4,
        ),
        ScreenTypeCreate(
            code="st7789_172x320",
            name="LCD 172x320",
            description="ST7789 LCD 1.47 inch",
            driver="st7789",
            width=172,
            height=320,
            color_depth=16,
            sort_order=5,
        ),
        ScreenTypeCreate(
            code="ili9341_240x320",
            name="ILI9341 240x320",
            description="ILI9341 LCD 2.4 inch",
            driver="ili9341",
            width=240,
            height=320,
            color_depth=16,
            sort_order=6,
        ),
    ]
    
    boards_created = 0
    screens_created = 0
    
    # Create boards
    for board_data in default_boards:
        existing = await crud_board_type.get(db=db, code=board_data.code)
        if not existing:
            await crud_board_type.create(db=db, object=board_data)
            boards_created += 1
    
    # Create screens
    for screen_data in default_screens:
        existing = await crud_screen_type.get(db=db, code=screen_data.code)
        if not existing:
            await crud_screen_type.create(db=db, object=screen_data)
            screens_created += 1
    
    return {
        "message": "Default hardware types seeded successfully",
        "boards_created": boards_created,
        "screens_created": screens_created,
    }
