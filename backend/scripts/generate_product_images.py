#!/usr/bin/env python3
"""Generate small JPEG product images (240x240) for Sales POS demo."""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "app", "static", "products")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Product list with colors and emoji-style labels
PRODUCTS = [
    ("nuoc-dua", "Nước Dừa", (46, 139, 87), (200, 255, 200)),      # green coconut
    ("combo-pho", "Combo Phở", (180, 80, 40), (255, 240, 220)),     # warm pho
    ("bun-bo-hue", "Bún Bò Huế", (200, 60, 20), (255, 230, 210)),  # red spicy
    ("com-tam", "Cơm Tấm", (200, 160, 60), (255, 245, 220)),       # golden rice
    ("goi-cuon", "Gỏi Cuốn", (100, 170, 80), (230, 255, 230)),     # fresh green
    ("pho-bo", "Phở Bò", (160, 100, 50), (255, 235, 210)),          # broth brown
    ("bun-cha", "Bún Chả", (190, 110, 40), (255, 240, 215)),        # grilled
    ("ca-phe", "Cà Phê", (80, 50, 30), (200, 180, 150)),            # coffee dark
    ("tra-da", "Trà Đá", (50, 120, 180), (210, 235, 255)),           # cool blue
    ("banh-mi", "Bánh Mì", (210, 170, 80), (255, 245, 220)),        # bread gold
    ("sinh-to", "Sinh Tố", (180, 60, 130), (255, 220, 240)),         # berry pink
    ("cha-gio", "Chả Giò", (200, 140, 40), (255, 240, 200)),        # fried gold
    ("mi-quang", "Mì Quảng", (220, 180, 50), (255, 248, 220)),      # turmeric yellow
    ("hu-tieu", "Hủ Tiếu", (180, 150, 100), (250, 240, 225)),       # light broth
    ("che-thai", "Chè Thái", (60, 140, 120), (220, 255, 245)),       # sweet green
]

SIZE = 240


def create_product_image(filename, label, primary_color, bg_color):
    """Create a stylish product placeholder image."""
    img = Image.new("RGB", (SIZE, SIZE), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw gradient background circle
    cx, cy = SIZE // 2, SIZE // 2 - 10
    r = 90
    for i in range(r, 0, -1):
        alpha = int(255 * (i / r))
        color = tuple(min(255, c + (255 - c) * (r - i) // r) for c in primary_color)
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=color)

    # Draw decorative ring
    draw.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], outline=primary_color, width=3)

    # Product icon (simple emoji-like shapes)
    icon_color = (255, 255, 255)
    # Bowl shape
    draw.arc([cx - 40, cy - 20, cx + 40, cy + 30], 0, 180, fill=icon_color, width=3)
    draw.line([cx - 40, cy + 5, cx + 40, cy + 5], fill=icon_color, width=2)
    # Steam lines
    for offset in [-15, 0, 15]:
        draw.arc([cx + offset - 5, cy - 35, cx + offset + 5, cy - 20],
                 0, 360, fill=(255, 255, 255, 180), width=2)

    # Text label at bottom
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except:
        font = ImageFont.load_default()

    # Draw text with shadow
    text_y = SIZE - 40
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (SIZE - text_w) // 2

    # Background bar for text
    draw.rectangle([0, text_y - 8, SIZE, SIZE], fill=(*primary_color, 200))
    draw.text((text_x + 1, text_y + 1), label, fill=(0, 0, 0), font=font)
    draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)

    # Save as JPEG (small file size)
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.jpg")
    img.save(filepath, "JPEG", quality=75, optimize=True)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  ✅ {filepath} ({size_kb:.1f} KB)")
    return filepath


if __name__ == "__main__":
    print(f"Generating {len(PRODUCTS)} product images to {OUTPUT_DIR}...")
    for filename, label, primary, bg in PRODUCTS:
        create_product_image(filename, label, primary, bg)
    print(f"\n🎉 Done! {len(PRODUCTS)} images generated.")
