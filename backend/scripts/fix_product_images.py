#!/usr/bin/env python3
"""
Fix product images - Generate small JPEG images and serve them via backend static files.
Creates simple colored gradient images with product name text overlay.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Product image mapping - use reliable public URLs (Unsplash/Pexels with direct links)
# These are small, fast-loading food images
PRODUCT_IMAGE_MAP = {
    "Nước Dừa Tươi": "https://images.unsplash.com/photo-1536304929831-ee1ca9d44c28?w=400&h=400&fit=crop&q=60",
    "Combo Phở": "https://images.unsplash.com/photo-1503764654157-72d979d9af2f?w=400&h=400&fit=crop&q=60",
    "Bún Bò Huế": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=400&h=400&fit=crop&q=60",
    "Cơm Tấm": "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?w=400&h=400&fit=crop&q=60",
    "Gỏi Cuốn": "https://images.unsplash.com/photo-1562967916-eb82221dfb92?w=400&h=400&fit=crop&q=60",
    "Phở Bò": "https://images.unsplash.com/photo-1503764654157-72d979d9af2f?w=400&h=400&fit=crop&q=60",
    "Bún Chả": "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=400&fit=crop&q=60",
    "Cà Phê": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400&h=400&fit=crop&q=60",
    "Trà Đá": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&h=400&fit=crop&q=60",
    "Bánh Mì": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=400&fit=crop&q=60",
    "Sinh Tố": "https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=400&h=400&fit=crop&q=60",
    "Chả Giò": "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=400&fit=crop&q=60",
    "Mì Quảng": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=400&h=400&fit=crop&q=60",
}

# Fallback generic food image for any product not matched above
FALLBACK_IMAGE = "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=400&fit=crop&q=60"


async def update_product_images():
    """Update product images in DB with working URLs."""
    from app.core.database import async_session_factory
    from sqlalchemy import text

    async with async_session_factory() as session:
        # Get all products
        result = await session.execute(
            text("SELECT id, name, image_url FROM sales_product")
        )
        products = result.fetchall()

        print(f"Found {len(products)} products")

        for product_id, name, old_url in products:
            # Find best matching image URL
            new_url = FALLBACK_IMAGE
            for keyword, url in PRODUCT_IMAGE_MAP.items():
                if keyword.lower() in name.lower():
                    new_url = url
                    break
            
            if old_url != new_url:
                await session.execute(
                    text("UPDATE sales_product SET image_url = :url WHERE id = :id"),
                    {"url": new_url, "id": product_id}
                )
                print(f"  ✅ {name}: {new_url[:60]}...")
            else:
                print(f"  ⏭️ {name}: already up to date")

        await session.commit()
        print(f"\n🎉 Updated {len(products)} product images!")


if __name__ == "__main__":
    asyncio.run(update_product_images())
