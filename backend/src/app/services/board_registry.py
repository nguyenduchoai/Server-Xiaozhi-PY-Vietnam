"""
Board Registry - Centralized board configuration extracted from firmware.

This module provides a single source of truth for all supported boards,
including screen dimensions, chip type, and flash partition addresses.

Used by:
- OTA service: Match firmware to device board
- Theme service: Validate theme screen size matches device
- Asset service: Generate correct assets for board
- Frontend: Board selection dropdowns
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ChipFamily(str, Enum):
    """ESP32 chip families"""
    ESP32 = "esp32"
    ESP32S3 = "esp32s3"
    ESP32C3 = "esp32c3"
    ESP32C6 = "esp32c6"
    ESP32P4 = "esp32p4"


class ScreenType(str, Enum):
    """Screen types"""
    LCD = "LCD"
    OLED = "OLED"
    NONE = "NONE"


class ColorFormat(str, Enum):
    """Color formats"""
    RGB565 = "RGB565"  # 16-bit color
    MONO = "MONO"      # 1-bit monochrome


@dataclass
class BoardInfo:
    """Complete board configuration"""
    name: str
    chip: ChipFamily
    screen_type: ScreenType
    width: int
    height: int
    color_format: ColorFormat
    data_partition_address: int  # For safe theme flashing
    flash_size_mb: int = 16      # Default flash size
    description: str = ""
    
    @property
    def resolution(self) -> str:
        """Get resolution string like '320x240'"""
        return f"{self.width}x{self.height}"
    
    @property
    def is_color(self) -> bool:
        """Check if screen supports color"""
        return self.color_format == ColorFormat.RGB565
    
    @property
    def has_screen(self) -> bool:
        """Check if board has a screen"""
        return self.screen_type != ScreenType.NONE and self.width > 0


# =============================================================================
# BOARD REGISTRY
# Extracted from firmware/main/boards/*/config.h and config.json
# =============================================================================

BOARD_REGISTRY: dict[str, BoardInfo] = {}

def _register(board: BoardInfo) -> None:
    """Register a board in the registry"""
    BOARD_REGISTRY[board.name.lower()] = board


# === Vietnam Boards (Priority) ===
_register(BoardInfo(
    name="xiaozhi-ai-iot-vietnam-es3n28p-lcd-2.8",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Vietnam 2.8\" ILI9341 LCD with touch"
))

_register(BoardInfo(
    name="xiaozhi-ai-iot-vietnam-1st",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=284, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Vietnam 1st gen board"
))

_register(BoardInfo(
    name="xiaozhi-ai-iot-vietnam-dtd",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Vietnam DTD board"
))

# === ESP32-S3 320x240 (Most Common) ===
_register(BoardInfo(
    name="esp-box-3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Espressif ESP-BOX-3"
))

_register(BoardInfo(
    name="esp-box",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Espressif ESP-BOX"
))

_register(BoardInfo(
    name="esp-box-lite",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Espressif ESP-BOX-Lite"
))

_register(BoardInfo(
    name="lichuang-dev",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="LiChuang Action ESP32-S3"
))

_register(BoardInfo(
    name="m5stack-core-s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="M5Stack Core S3"
))

_register(BoardInfo(
    name="yunliao-s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Yunliao S3"
))

_register(BoardInfo(
    name="zhengchen-cam",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Zhengchen Camera Board"
))

_register(BoardInfo(
    name="zhengchen-cam-ml307",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Zhengchen Camera with 4G"
))

_register(BoardInfo(
    name="atk-dnesp32s3-box",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Alientek DNESP32S3 Box"
))

_register(BoardInfo(
    name="atk-dnesp32s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Alientek DNESP32S3"
))

# === ESP32-S3 240x240 TFT ===
_register(BoardInfo(
    name="genjutech-s3-1.54tft",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Nologo XingZhi 1.54 TFT"
))

_register(BoardInfo(
    name="esp-sparkbot",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="ESP SparkBot"
))

_register(BoardInfo(
    name="electron-bot",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Electron Bot"
))

_register(BoardInfo(
    name="otto-robot",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Otto Robot"
))

_register(BoardInfo(
    name="minsi-k08-dual",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Minsi K08 Dual"
))

_register(BoardInfo(
    name="movecall-cuican-esp32s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Movecall Cuican"
))

_register(BoardInfo(
    name="movecall-moji-esp32s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Movecall Moji"
))

_register(BoardInfo(
    name="sp-esp32-s3-1.28-box",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="SP 1.28 Box"
))

_register(BoardInfo(
    name="sp-esp32-s3-1.54-muma",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="SP 1.54 Muma"
))

_register(BoardInfo(
    name="atk-dnesp32s3-box0",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Alientek Box0"
))

_register(BoardInfo(
    name="xingzhi-cube-1.54tft-ml307",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 1.54 TFT 4G"
))

_register(BoardInfo(
    name="xingzhi-cube-1.54tft-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 1.54 TFT WiFi"
))

_register(BoardInfo(
    name="zhengchen-1.54tft-ml307",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Zhengchen 1.54 TFT 4G"
))

_register(BoardInfo(
    name="zhengchen-1.54tft-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Zhengchen 1.54 TFT WiFi"
))

# === ESP32-S3 240x320 Portrait ===
_register(BoardInfo(
    name="df-k10",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="DFRobot K10"
))

_register(BoardInfo(
    name="jiuchuan-s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Jiuchuan S3"
))

_register(BoardInfo(
    name="atk-dnesp32s3-box2-4g",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Alientek Box2 4G"
))

_register(BoardInfo(
    name="atk-dnesp32s3-box2-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Alientek Box2 WiFi"
))

# === ESP32-S3 Small Screens ===
_register(BoardInfo(
    name="aipi-lite",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="AIPI Lite"
))

_register(BoardInfo(
    name="atoms3-echo-base",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="AtomS3 Echo Base"
))

_register(BoardInfo(
    name="atoms3r-echo-base",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="AtomS3R Echo Base"
))

_register(BoardInfo(
    name="magiclick-2p4",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="MagiClick 2.4"
))

_register(BoardInfo(
    name="magiclick-2p5",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="MagiClick 2.5"
))

_register(BoardInfo(
    name="xingzhi-cube-0.85tft-ml307",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 0.85 TFT 4G"
))

_register(BoardInfo(
    name="xingzhi-cube-0.85tft-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 0.85 TFT WiFi"
))

_register(BoardInfo(
    name="du-chatx",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=160,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Du ChatX"
))

_register(BoardInfo(
    name="mixgo-nova",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=128, height=160,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="MixGo Nova"
))

# === ESP32-S3 OLED ===
_register(BoardInfo(
    name="kevin-box-2",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Kevin Box 2"
))

_register(BoardInfo(
    name="tudouzi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Tudouzi"
))

_register(BoardInfo(
    name="xingzhi-cube-0.96oled-ml307",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 0.96 OLED 4G"
))

_register(BoardInfo(
    name="xingzhi-cube-0.96oled-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 0.96 OLED WiFi"
))

_register(BoardInfo(
    name="bread-compact-ml307",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.OLED,
    width=128, height=32,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Bread Compact 4G"
))

_register(BoardInfo(
    name="bread-compact-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.OLED,
    width=128, height=32,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Bread Compact WiFi"
))

# === ESP32-S3 Large/Round Displays ===
_register(BoardInfo(
    name="echoear",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=360, height=360,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="EchoEar Round Display"
))

_register(BoardInfo(
    name="esp32-s3-touch-lcd-1.85",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=360, height=360,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 1.85 Touch LCD"
))

_register(BoardInfo(
    name="esp32-s3-touch-lcd-1.85c",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=360, height=360,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 1.85C Touch LCD"
))

_register(BoardInfo(
    name="taiji-pi-s3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=360, height=360,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Taiji Pi S3"
))

_register(BoardInfo(
    name="esp32-s3-touch-amoled-1.8",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=368, height=448,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 1.8 AMOLED"
))

_register(BoardInfo(
    name="esp32-s3-touch-lcd-1.46",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=412, height=412,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 1.46 Round"
))

_register(BoardInfo(
    name="sensecap-watcher",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=412, height=412,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="SenseCap Watcher"
))

_register(BoardInfo(
    name="waveshare-s3-touch-amoled-1.75",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=466, height=466,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 1.75 AMOLED"
))

_register(BoardInfo(
    name="waveshare-s3-touch-amoled-2.06",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=410, height=502,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 2.06 AMOLED"
))

_register(BoardInfo(
    name="esp32-s3-touch-lcd-3.5",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=480, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 3.5 LCD"
))

_register(BoardInfo(
    name="waveshare-s3-touch-lcd-3.5b",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=480, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 3.5B LCD"
))

_register(BoardInfo(
    name="esp-s3-lcd-ev-board",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=480, height=480,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="ESP-S3-LCD-EV-Board"
))

_register(BoardInfo(
    name="waveshare-s3-touch-lcd-4b",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=480, height=480,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 4B LCD"
))

_register(BoardInfo(
    name="esp-s3-lcd-ev-board-2",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=800, height=480,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="ESP-S3-LCD-EV-Board-2"
))

_register(BoardInfo(
    name="kevin-yuying-313lcd",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=376, height=960,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Kevin Yuying 3.13 LCD"
))

_register(BoardInfo(
    name="waveshare-s3-touch-lcd-3.49",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=172, height=640,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare 3.49 LCD"
))

# === ESP32-S3 Other Sizes ===
_register(BoardInfo(
    name="labplus-ledong-v2",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=172,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="LabPlus Ledong V2"
))

_register(BoardInfo(
    name="labplus-mpython-v3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=172,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="LabPlus mPython V3"
))

_register(BoardInfo(
    name="kevin-sp-v4-dev",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=280,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Kevin SP V4 Dev"
))

_register(BoardInfo(
    name="waveshare-s3-touch-lcd-1.83",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=240, height=284,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="Waveshare 1.83 LCD"
))

_register(BoardInfo(
    name="xingzhi-cube-1.83tft-wifi",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=284, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=8,
    description="XingZhi Cube 1.83 TFT WiFi"
))

# === ESP32-C3 Boards ===
_register(BoardInfo(
    name="surfer-c3-1.14tft",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.LCD,
    width=240, height=135,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="Surfer C3 1.14 TFT"
))

_register(BoardInfo(
    name="lichuang-c3-dev",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.LCD,
    width=320, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="LiChuang C3 Dev"
))

_register(BoardInfo(
    name="esp-hi",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.LCD,
    width=160, height=80,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="ESP-HI"
))

_register(BoardInfo(
    name="magiclick-c3",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="MagiClick C3"
))

_register(BoardInfo(
    name="magiclick-c3-v2",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="MagiClick C3 V2"
))

_register(BoardInfo(
    name="xmini-c3",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="XMini C3"
))

_register(BoardInfo(
    name="xmini-c3-4g",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="XMini C3 4G"
))

_register(BoardInfo(
    name="xmini-c3-v3",
    chip=ChipFamily.ESP32C3,
    screen_type=ScreenType.OLED,
    width=128, height=64,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="XMini C3 V3"
))

# === ESP32-C6 Boards ===
_register(BoardInfo(
    name="waveshare-c6-lcd-1.69",
    chip=ChipFamily.ESP32C6,
    screen_type=ScreenType.LCD,
    width=240, height=280,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="Waveshare C6 1.69 LCD"
))

# === ESP32-P4 High-End ===
_register(BoardInfo(
    name="waveshare-p4-nano",
    chip=ChipFamily.ESP32P4,
    screen_type=ScreenType.LCD,
    width=800, height=1280,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare P4 Nano"
))

_register(BoardInfo(
    name="waveshare-p4-wifi6-touch-lcd-4b",
    chip=ChipFamily.ESP32P4,
    screen_type=ScreenType.LCD,
    width=720, height=720,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare P4 WiFi6 4B"
))

_register(BoardInfo(
    name="waveshare-p4-wifi6-touch-lcd-7b",
    chip=ChipFamily.ESP32P4,
    screen_type=ScreenType.LCD,
    width=1024, height=600,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare P4 WiFi6 7B"
))

_register(BoardInfo(
    name="wireless-tag-wtp4c5mp07s",
    chip=ChipFamily.ESP32P4,
    screen_type=ScreenType.LCD,
    width=1024, height=600,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Wireless Tag WTP4"
))

# === ESP32 Classic ===
_register(BoardInfo(
    name="bread-compact-esp32",
    chip=ChipFamily.ESP32,
    screen_type=ScreenType.OLED,
    width=128, height=32,
    color_format=ColorFormat.MONO,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="Bread Compact ESP32"
))

_register(BoardInfo(
    name="bread-compact-esp32-lcd",
    chip=ChipFamily.ESP32,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="Bread Compact ESP32 LCD"
))

_register(BoardInfo(
    name="esp32-cgc",
    chip=ChipFamily.ESP32,
    screen_type=ScreenType.LCD,
    width=240, height=320,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="CGC ESP32"
))

_register(BoardInfo(
    name="esp32-cgc-144",
    chip=ChipFamily.ESP32,
    screen_type=ScreenType.LCD,
    width=128, height=128,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x600000,
    flash_size_mb=4,
    description="CGC ESP32 1.44 inch"
))

# === Additional ESP32-S3 Boards ===
_register(BoardInfo(
    name="esp32s3-korvo2-v3",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=280, height=240,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="ESP32-S3 Korvo2 V3"
))

_register(BoardInfo(
    name="waveshare-s3-audio-board",
    chip=ChipFamily.ESP32S3,
    screen_type=ScreenType.LCD,
    width=320, height=172,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare S3 Audio Board"
))

# === Additional ESP32-P4 Boards ===
_register(BoardInfo(
    name="waveshare-p4-wifi6-touch-lcd-xc",
    chip=ChipFamily.ESP32P4,
    screen_type=ScreenType.LCD,
    width=800, height=800,
    color_format=ColorFormat.RGB565,
    data_partition_address=0x800000,
    flash_size_mb=16,
    description="Waveshare P4 WiFi6 XC 800x800"
))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_board_info(board_name: str) -> Optional[BoardInfo]:
    """Get board info by name (case-insensitive)"""
    return BOARD_REGISTRY.get(board_name.lower())


def get_board_by_resolution(width: int, height: int) -> list[BoardInfo]:
    """Get all boards matching a specific resolution"""
    return [b for b in BOARD_REGISTRY.values() if b.width == width and b.height == height]


def get_boards_by_chip(chip: ChipFamily) -> list[BoardInfo]:
    """Get all boards for a specific chip family"""
    return [b for b in BOARD_REGISTRY.values() if b.chip == chip]


def is_compatible_resolution(board_name: str, theme_width: int, theme_height: int) -> bool:
    """Check if a theme resolution is compatible with a board"""
    board = get_board_info(board_name)
    if not board:
        return False
    
    # Exact match
    if board.width == theme_width and board.height == theme_height:
        return True
    
    # Rotated match (portrait <-> landscape)
    if board.width == theme_height and board.height == theme_width:
        return True
    
    return False


def get_data_partition_address(board_name: str) -> int:
    """Get safe data partition address for a board"""
    board = get_board_info(board_name)
    if board:
        return board.data_partition_address
    # Default to safe address for unknown boards
    return 0x310000


def get_all_resolutions() -> set[str]:
    """Get all unique resolutions"""
    return {b.resolution for b in BOARD_REGISTRY.values() if b.has_screen}


def board_names_list() -> list[str]:
    """Get list of all board names"""
    return list(BOARD_REGISTRY.keys())


def to_api_response() -> list[dict]:
    """Convert registry to API response format"""
    return [
        {
            "name": b.name,
            "chip": b.chip.value,
            "screen_type": b.screen_type.value,
            "width": b.width,
            "height": b.height,
            "resolution": b.resolution,
            "color_format": b.color_format.value,
            "data_partition_address": hex(b.data_partition_address),
            "flash_size_mb": b.flash_size_mb,
            "description": b.description,
        }
        for b in BOARD_REGISTRY.values()
    ]
