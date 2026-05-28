#!/usr/bin/env python3
"""Generate product placeholder images for ALL products in Xiaozhi Sales."""
from PIL import Image, ImageDraw, ImageFont
import os, hashlib, unicodedata

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "product_images_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIZE = 240

# Color palette for different product categories
COLORS = [
    ((41, 128, 185), (174, 214, 241)),   # Blue - tech
    ((39, 174, 96), (171, 235, 198)),     # Green - nature
    ((192, 57, 43), (245, 183, 177)),     # Red - food
    ((142, 68, 173), (215, 189, 226)),    # Purple - premium
    ((243, 156, 18), (249, 231, 159)),    # Orange - warm
    ((22, 160, 133), (163, 228, 215)),    # Teal - fresh
    ((52, 73, 94), (174, 182, 191)),      # Dark - professional
    ((231, 76, 60), (250, 219, 216)),     # Coral - vibrant
]

# All products from DB
PRODUCTS = [
    "Xiaozhi ESP32-S3 Speaker",
    "Xiaozhi LCD 2.8 Module",
    "Combo Smart Home Kit",
    "Dich vu Tu van IoT Enterprise",
    "iPhone 15 Pro Max",
    "Samsung Galaxy S24 Ultra",
    "MacBook Pro 14 M3",
    "AirPods Pro 2",
    "iPad Air M2",
    "Apple Watch Ultra 2",
    "Sony WH-1000XM5",
    "DJI Mini 4 Pro",
    "Phở Bò Đặc Biệt",
    "Phở Gà Ta",
    "Combo Phở + Gỏi Cuốn + Trà Đá",
    "Bún Bò Huế",
    "Cơm Tấm Sườn Bì Chả",
    "Gỏi Cuốn (2 cuốn)",
    "Trà Đá",
    "Khoá học AI Voice Assistant",
    "Nước Dừa Tươi",
]


def slugify(text):
    """Convert product name to filename-safe slug."""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    # Remove non-ASCII
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Replace spaces/special chars
    text = text.lower().strip()
    result = []
    for c in text:
        if c.isalnum():
            result.append(c)
        elif c in ' -_':
            result.append('-')
    slug = '-'.join(filter(None, ''.join(result).split('-')))
    return slug[:50] or 'product'


def create_image(name):
    """Create a stylish product image with name."""
    # Pick color based on name hash
    idx = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(COLORS)
    primary, bg = COLORS[idx]

    img = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(img)

    # Background gradient circle
    cx, cy = SIZE // 2, SIZE // 2 - 20
    r = 80
    for i in range(r, 0, -1):
        ratio = i / r
        color = tuple(int(bg[j] + (primary[j] - bg[j]) * (1 - ratio)) for j in range(3))
        draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=color)

    # Ring
    draw.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], outline=primary, width=3)

    # Icon in center (simple shapes)
    draw.rectangle([cx - 25, cy - 18, cx + 25, cy + 18], outline=(255, 255, 255), width=2, fill=None)
    draw.line([cx - 15, cy - 8, cx + 15, cy - 8], fill=(255, 255, 255), width=2)
    draw.line([cx - 15, cy + 2, cx + 15, cy + 2], fill=(255, 255, 255), width=2)

    # Text label at bottom
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        font = ImageFont.load_default()

    # Truncate name for display
    display_name = name[:22] + "..." if len(name) > 25 else name

    # Background bar
    draw.rectangle([0, SIZE - 50, SIZE, SIZE], fill=primary)

    # Center text
    bbox = draw.textbbox((0, 0), display_name, font=font)
    tw = bbox[2] - bbox[0]
    tx = (SIZE - tw) // 2
    draw.text((tx + 1, SIZE - 40 + 1), display_name, fill=(0, 0, 0), font=font)
    draw.text((tx, SIZE - 40), display_name, fill=(255, 255, 255), font=font)

    # Second line for branding
    try:
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except:
        font_small = font
    draw.text((SIZE // 2 - 30, SIZE - 22), "XIAOZHI SALES", fill=(200, 200, 200), font=font_small)

    slug = slugify(name)
    filepath = os.path.join(OUTPUT_DIR, f"{slug}.jpg")
    img.save(filepath, "JPEG", quality=80, optimize=True)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  ✅ {slug}.jpg ({size_kb:.1f}KB) — {name}")
    return slug


if __name__ == "__main__":
    print(f"Generating {len(PRODUCTS)} product images...")
    slugs = {}
    for name in PRODUCTS:
        slug = create_image(name)
        slugs[name] = slug
    
    print(f"\n🎉 Done! {len(PRODUCTS)} images in {OUTPUT_DIR}")
    print("\n--- SQL UPDATE statements ---")
    for name, slug in slugs.items():
        url = f"https://xiaozhi-ai-iot.vn/products/{slug}.jpg"
        safe_name = name.replace("'", "''")
        print(f"UPDATE product SET image_url = '{url}' WHERE name = '{safe_name}';")
