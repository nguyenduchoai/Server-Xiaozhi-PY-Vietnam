"""Hardware Types Seeder - Seed default board and screen types on startup."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import setup_logging
from ..crud.crud_board_type import crud_board_type, crud_screen_type
from ..schemas.board_type import BoardTypeCreate, ScreenTypeCreate


async def seed_default_hardware_types(db: AsyncSession) -> dict:
    """
    Seed default board and screen types if they don't exist.
    
    This runs on application startup to ensure default hardware types
    are always available.
    
    Returns:
        dict with counts of boards and screens created
    """
    logger = setup_logging().bind(tag="hardware_types_seeder")
    
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
    
    try:
        # Create boards
        for board_data in default_boards:
            existing = await crud_board_type.get(db=db, code=board_data.code)
            if not existing:
                await crud_board_type.create(db=db, object=board_data)
                boards_created += 1
                logger.debug(f"Created board type: {board_data.code}")
        
        # Create screens
        for screen_data in default_screens:
            existing = await crud_screen_type.get(db=db, code=screen_data.code)
            if not existing:
                await crud_screen_type.create(db=db, object=screen_data)
                screens_created += 1
                logger.debug(f"Created screen type: {screen_data.code}")
        
        if boards_created > 0 or screens_created > 0:
            logger.info(
                f"Hardware types seeded: {boards_created} boards, {screens_created} screens"
            )
        else:
            logger.debug("Hardware types already seeded, no new entries created")
            
    except Exception as exc:
        logger.warning(f"Failed to seed hardware types: {exc}")
    
    return {
        "boards_created": boards_created,
        "screens_created": screens_created,
    }
