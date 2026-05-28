"""
Board Registry API - Provides board information for frontend and validation.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from ...services.board_registry import (
    BOARD_REGISTRY,
    get_board_info,
    is_compatible_resolution,
    get_data_partition_address,
    get_all_resolutions,
    ChipFamily,
)


router = APIRouter(prefix="/boards", tags=["Boards"])


class BoardResponse(BaseModel):
    """Board info response"""
    name: str
    chip: str
    screen_type: str
    width: int
    height: int
    resolution: str
    color_format: str
    data_partition_address: str
    flash_size_mb: int
    description: str


class BoardListResponse(BaseModel):
    """List of boards"""
    boards: list[BoardResponse]
    total: int


class ResolutionListResponse(BaseModel):
    """List of unique resolutions"""
    resolutions: list[str]


class CompatibilityCheckResponse(BaseModel):
    """Compatibility check result"""
    compatible: bool
    board_name: str
    board_resolution: Optional[str] = None
    theme_resolution: str
    message: str


@router.get("", response_model=BoardListResponse)
async def list_boards(
    chip: Optional[str] = Query(None, description="Filter by chip family"),
    resolution: Optional[str] = Query(None, description="Filter by resolution (e.g. 320x240)"),
):
    """
    List all supported boards.
    
    Optionally filter by chip family or resolution.
    """
    boards = list(BOARD_REGISTRY.values())
    
    # Filter by chip
    if chip:
        try:
            chip_family = ChipFamily(chip.lower())
            boards = [b for b in boards if b.chip == chip_family]
        except ValueError:
            pass
    
    # Filter by resolution
    if resolution:
        try:
            w, h = resolution.split("x")
            width, height = int(w), int(h)
            boards = [b for b in boards if b.width == width and b.height == height]
        except (ValueError, AttributeError):
            pass
    
    return BoardListResponse(
        boards=[
            BoardResponse(
                name=b.name,
                chip=b.chip.value,
                screen_type=b.screen_type.value,
                width=b.width,
                height=b.height,
                resolution=b.resolution,
                color_format=b.color_format.value,
                data_partition_address=hex(b.data_partition_address),
                flash_size_mb=b.flash_size_mb,
                description=b.description,
            )
            for b in boards
        ],
        total=len(boards),
    )


@router.get("/resolutions", response_model=ResolutionListResponse)
async def list_resolutions():
    """Get all unique screen resolutions."""
    return ResolutionListResponse(
        resolutions=sorted(get_all_resolutions())
    )


@router.get("/{board_name}", response_model=BoardResponse)
async def get_board(board_name: str):
    """Get details for a specific board."""
    board = get_board_info(board_name)
    if not board:
        # HTTPException imported at top-level
        raise HTTPException(status_code=404, detail=f"Board '{board_name}' not found")
    
    return BoardResponse(
        name=board.name,
        chip=board.chip.value,
        screen_type=board.screen_type.value,
        width=board.width,
        height=board.height,
        resolution=board.resolution,
        color_format=board.color_format.value,
        data_partition_address=hex(board.data_partition_address),
        flash_size_mb=board.flash_size_mb,
        description=board.description,
    )


@router.get("/{board_name}/check-theme", response_model=CompatibilityCheckResponse)
async def check_theme_compatibility(
    board_name: str,
    width: int = Query(..., description="Theme width"),
    height: int = Query(..., description="Theme height"),
):
    """
    Check if a theme is compatible with a board.
    
    Returns whether the theme resolution matches the board's screen.
    """
    board = get_board_info(board_name)
    theme_resolution = f"{width}x{height}"
    
    if not board:
        return CompatibilityCheckResponse(
            compatible=False,
            board_name=board_name,
            board_resolution=None,
            theme_resolution=theme_resolution,
            message=f"Unknown board: {board_name}",
        )
    
    compatible = is_compatible_resolution(board_name, width, height)
    
    if compatible:
        message = f"Theme {theme_resolution} is compatible with {board.name}"
    else:
        message = f"Theme {theme_resolution} is NOT compatible with {board.name} ({board.resolution})"
    
    return CompatibilityCheckResponse(
        compatible=compatible,
        board_name=board_name,
        board_resolution=board.resolution,
        theme_resolution=theme_resolution,
        message=message,
    )


@router.get("/{board_name}/flash-address")
async def get_flash_address(board_name: str):
    """
    Get safe data partition address for flashing themes.
    
    This address is where theme data should be written to avoid
    overwriting the firmware.
    """
    board = get_board_info(board_name)
    address = get_data_partition_address(board_name)
    
    return {
        "board_name": board_name,
        "address": address,
        "address_hex": hex(address),
        "known_board": board is not None,
        "warning": None if board else "Unknown board, using default safe address",
    }
