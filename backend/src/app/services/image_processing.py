"""
Image Processing Service - Resize and optimize images for device displays
"""

import io
import hashlib
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
from app.core.logger import get_logger

logger = get_logger(__name__)

# Device screen sizes
SCREEN_SIZES = {
    "240x240": (240, 240),
    "284x240": (284, 240),
    "320x240": (320, 240),
    "128x64": (128, 64),
}

# Storage paths
THEME_ASSETS_PATH = Path("/app/data/assets/themes")
THEME_ASSETS_PATH.mkdir(parents=True, exist_ok=True)

BACKGROUND_ASSETS_PATH = Path("/app/data/assets/backgrounds")
BACKGROUND_ASSETS_PATH.mkdir(parents=True, exist_ok=True)


class ImageProcessingService:
    """Service for processing images for device displays"""
    
    @staticmethod
    def get_screen_size(screen_type: str) -> Tuple[int, int]:
        """Get screen dimensions from type"""
        return SCREEN_SIZES.get(screen_type, (240, 240))
    
    @staticmethod
    def resize_image(
        image_bytes: bytes,
        target_width: int,
        target_height: int,
        quality: int = 85,
        output_format: str = "PNG",
    ) -> bytes:
        """
        Resize image to target dimensions.
        Maintains aspect ratio and centers with black bars if needed.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Calculate resize dimensions (maintain aspect ratio)
            img_ratio = img.width / img.height
            target_ratio = target_width / target_height
            
            if img_ratio > target_ratio:
                # Image is wider - fit to width
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                # Image is taller - fit to height
                new_height = target_height
                new_width = int(target_height * img_ratio)
            
            # Resize
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create canvas with black background
            canvas = Image.new("RGB", (target_width, target_height), (0, 0, 0))
            
            # Center image on canvas
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2
            canvas.paste(img, (x_offset, y_offset))
            
            # Save to bytes
            output = io.BytesIO()
            canvas.save(output, format=output_format, quality=quality, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            raise
    
    @staticmethod
    def resize_for_screen(
        image_bytes: bytes,
        screen_type: str,
        output_format: str = "PNG",
    ) -> bytes:
        """Resize image for specific screen type"""
        width, height = ImageProcessingService.get_screen_size(screen_type)
        return ImageProcessingService.resize_image(
            image_bytes, width, height, output_format=output_format
        )
    
    @staticmethod
    def create_thumbnail(
        image_bytes: bytes,
        size: int = 100,
    ) -> bytes:
        """Create square thumbnail"""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Center crop to square
            min_dim = min(img.width, img.height)
            left = (img.width - min_dim) // 2
            top = (img.height - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))
            
            # Resize
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=75, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            raise
    
    @staticmethod
    def convert_to_device_format(
        image_bytes: bytes,
        screen_type: str = "240x240",
        as_rgb565: bool = False,
    ) -> bytes:
        """
        Convert image to device-compatible format.
        Optionally convert to RGB565 raw format for direct display.
        """
        width, height = ImageProcessingService.get_screen_size(screen_type)
        
        # First resize
        resized = ImageProcessingService.resize_image(
            image_bytes, width, height, output_format="PNG"
        )
        
        if not as_rgb565:
            return resized
        
        # Convert to RGB565 raw bytes (for ESP32 direct display)
        try:
            img = Image.open(io.BytesIO(resized))
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            rgb565_data = bytearray()
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b = img.getpixel((x, y))
                    # RGB565: 5 bits red, 6 bits green, 5 bits blue
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    # Big endian
                    rgb565_data.append((rgb565 >> 8) & 0xFF)
                    rgb565_data.append(rgb565 & 0xFF)
            
            return bytes(rgb565_data)
            
        except Exception as e:
            logger.error(f"Failed to convert to RGB565: {e}")
            raise
    
    @staticmethod
    def save_theme_asset(
        image_bytes: bytes,
        theme_id: str,
        asset_type: str,  # idle, listening, speaking, etc.
        screen_type: str = "240x240",
    ) -> str:
        """Save processed image as theme asset"""
        try:
            # Process image
            processed = ImageProcessingService.resize_for_screen(
                image_bytes, screen_type
            )
            
            # Generate filename
            checksum = hashlib.md5(processed).hexdigest()[:8]
            filename = f"{asset_type}_{checksum}.png"
            
            # Create theme folder
            theme_folder = THEME_ASSETS_PATH / theme_id
            theme_folder.mkdir(parents=True, exist_ok=True)
            
            # Save
            filepath = theme_folder / filename
            with open(filepath, "wb") as f:
                f.write(processed)
            
            logger.info(f"Saved theme asset: {filepath}")
            return f"/assets/themes/{theme_id}/{filename}"
            
        except Exception as e:
            logger.error(f"Failed to save theme asset: {e}")
            raise
    
    @staticmethod
    def save_device_background(
        image_bytes: bytes,
        device_id: str,
        background_type: str,  # idle, custom1, custom2
        screen_type: str = "240x240",
    ) -> str:
        """Save custom background for device"""
        try:
            # Process image
            processed = ImageProcessingService.resize_for_screen(
                image_bytes, screen_type
            )
            
            # Generate filename
            checksum = hashlib.md5(processed).hexdigest()[:8]
            filename = f"{background_type}_{checksum}.png"
            
            # Create device folder
            device_folder = BACKGROUND_ASSETS_PATH / device_id
            device_folder.mkdir(parents=True, exist_ok=True)
            
            # Save
            filepath = device_folder / filename
            with open(filepath, "wb") as f:
                f.write(processed)
            
            logger.info(f"Saved device background: {filepath}")
            return f"/assets/backgrounds/{device_id}/{filename}"
            
        except Exception as e:
            logger.error(f"Failed to save device background: {e}")
            raise
    
    @staticmethod
    def generate_theme_preview(
        theme_data: dict,
        screen_type: str = "240x240",
    ) -> bytes:
        """Generate preview image for theme"""
        width, height = ImageProcessingService.get_screen_size(screen_type)
        
        try:
            # Get colors from theme data
            colors = theme_data.get("colors", {})
            bg_color = colors.get("background", "#0f172a")
            text_color = colors.get("text", "#f8fafc")
            primary_color = colors.get("primary", "#6366f1")
            
            # Convert hex to RGB
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip("#")
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Create image
            img = Image.new("RGB", (width, height), hex_to_rgb(bg_color))
            draw = ImageDraw.Draw(img)
            
            # Draw some UI elements as preview
            # Title
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except Exception:
                font = ImageFont.load_default()
            
            draw.text((10, 10), theme_data.get("name", "Theme"), fill=hex_to_rgb(text_color), font=font)
            
            # Draw primary color accent
            draw.rectangle([(10, height - 40), (width - 10, height - 10)], fill=hex_to_rgb(primary_color))
            
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate theme preview: {e}")
            raise


# Singleton instance
image_processing_service = ImageProcessingService()
