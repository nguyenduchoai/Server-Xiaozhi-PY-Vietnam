"""
Sales Assistant Plugin Functions - Voice-First Sales

Voice commands for product search, recommendation, and display.
Integrates with SalesAssistant service and Product CRUD.

Features:
- Search products by voice query
- Display product on device LCD
- List product categories
- Get product recommendations
"""

from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from time import time

from uuid6 import uuid7

from app.ai.plugins_func.register import (
    Action,
    ActionResponse,
    ToolType,
    register_function,
)
from app.core.db.database import local_session
from app.core.logger import setup_logging
from app.services.display_image_proxy import build_proxy_image_url

TAG = __name__
logger = setup_logging()
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v", ".m3u8")


# ============================================================================
# FUNCTION DESCRIPTIONS
# ============================================================================

search_product_function_desc = {
    "type": "function",
    "function": {
        "name": "search_product",
        "description": "Tìm kiếm sản phẩm theo tên, mô tả, danh mục hoặc ngân sách. Kết quả luôn kèm ảnh/video nếu sản phẩm có media và tự đẩy top sản phẩm lên màn hình.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa tìm kiếm sản phẩm (ví dụ: 'ESP32', 'robot', 'thiết bị IoT')",
                },
                "category": {
                    "type": "string",
                    "description": "Danh mục sản phẩm (optional)",
                },
            },
            "required": ["query"],
        },
    },
}


list_products_function_desc = {
    "type": "function",
    "function": {
        "name": "list_products",
        "description": "Liệt kê sản phẩm đang bán, trả về ảnh/video của từng sản phẩm nếu có và đẩy top sản phẩm lên màn hình. Dùng khi khách hỏi 'có những sản phẩm nào', 'danh sách sản phẩm', 'bán gì'.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


show_product_function_desc = {
    "type": "function",
    "function": {
        "name": "show_product",
        "description": "Hiển thị một sản phẩm cụ thể lên màn hình thiết bị và trả về ảnh/video của sản phẩm. Dùng khi khách hỏi xem chi tiết, xem hình/video, hoặc đã chọn rõ một sản phẩm. Không gọi lặp lại cho mọi sản phẩm khi chỉ đang liệt kê danh sách.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Tên sản phẩm cần hiển thị",
                },
            },
            "required": ["product_name"],
        },
    },
}


capture_sales_lead_function_desc = {
    "type": "function",
    "function": {
        "name": "capture_sales_lead",
        "description": "Lưu hoặc cập nhật khách hàng quan tâm khi khách cung cấp tên, số điện thoại, email hoặc muốn được tư vấn/chốt đơn. Dùng sau khi đã tư vấn sản phẩm và khách đồng ý để lại thông tin.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Tên khách hàng nếu khách đã cung cấp",
                },
                "customer_phone": {
                    "type": "string",
                    "description": "Số điện thoại khách hàng nếu khách đã cung cấp",
                },
                "customer_email": {
                    "type": "string",
                    "description": "Email khách hàng nếu khách đã cung cấp",
                },
                "product_name": {
                    "type": "string",
                    "description": "Sản phẩm khách quan tâm. Nếu bỏ trống sẽ dùng sản phẩm vừa tư vấn gần nhất.",
                },
                "notes": {
                    "type": "string",
                    "description": "Ghi chú nhu cầu, địa chỉ, số lượng, thời gian gọi lại hoặc nội dung khách dặn",
                },
            },
            "required": [],
        },
    },
}


capture_customer_needs_function_desc = {
    "type": "function",
    "function": {
        "name": "capture_customer_needs",
        "description": "Ghi nhận nhu cầu khách trong phiên tư vấn trước khi tìm sản phẩm: ngân sách, mục đích, danh mục, màu/size, yêu cầu quan trọng. Dùng khi khách mô tả nhu cầu hoặc AI vừa hỏi thêm.",
        "parameters": {
            "type": "object",
            "properties": {
                "budget": {"type": "string", "description": "Ngân sách khách nói, ví dụ 'dưới 2 triệu'"},
                "purpose": {"type": "string", "description": "Mục đích sử dụng / bài toán của khách"},
                "category": {"type": "string", "description": "Danh mục khách quan tâm"},
                "variant": {"type": "string", "description": "Màu, size, dòng, phiên bản hoặc thuộc tính khách muốn"},
                "requirements": {"type": "string", "description": "Yêu cầu quan trọng khác"},
                "raw_text": {"type": "string", "description": "Câu nói gốc của khách nếu có"},
            },
            "required": [],
        },
    },
}


handle_sales_objection_function_desc = {
    "type": "function",
    "function": {
        "name": "handle_sales_objection",
        "description": "Xử lý từ chối trong bán hàng như đắt, cần suy nghĩ, so giá, hỏi bảo hành, còn hàng. Dùng sau khi khách phản đối hoặc phân vân.",
        "parameters": {
            "type": "object",
            "properties": {
                "objection_type": {
                    "type": "string",
                    "description": "Loại từ chối: price, thinking, compare, warranty, stock, shipping, other",
                },
                "product_name": {"type": "string", "description": "Sản phẩm đang tư vấn nếu có"},
                "customer_text": {"type": "string", "description": "Câu phản đối/phân vân của khách"},
            },
            "required": ["objection_type"],
        },
    },
}


start_sales_closing_function_desc = {
    "type": "function",
    "function": {
        "name": "start_sales_closing",
        "description": "Chuyển phiên tư vấn sang bước chốt lead/order khi khách đã quan tâm rõ hoặc AI chuẩn bị xin tên/số điện thoại.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Sản phẩm đang chốt nếu có"},
                "closing_text": {"type": "string", "description": "Câu chốt hoặc câu xin thông tin khách"},
            },
            "required": [],
        },
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

BUYING_INTENT_KEYWORDS = (
    "mua",
    "đặt",
    "chốt",
    "lấy",
    "ship",
    "giao",
    "thanh toán",
    "còn hàng",
    "bảo hành",
    "địa chỉ",
    "số điện thoại",
    "tư vấn",
    "giá",
)

OBJECTION_KEYWORDS = (
    "đắt",
    "mắc",
    "cao quá",
    "rẻ hơn",
    "giảm",
    "khuyến mãi",
    "bớt",
    "phân vân",
)


def _normalize_text(value: str | None) -> str:
    """Normalize Vietnamese text for accent-insensitive matching."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value.lower())
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.replace("đ", "d")


def _query_tokens(value: str | None) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", _normalize_text(value)) if len(token) >= 2]


def _parse_budget_hint(query: str | None) -> int | None:
    """Extract rough VND budget from Vietnamese buying phrases."""
    if not query:
        return None
    normalized = _normalize_text(query)
    match = re.search(
        r"(?:(duoi|tam|khoang|toi da|ngan sach|gia|re)\s*)?(\d+(?:[.,]\d+)?)\s*(trieu|tr|k|nghin|ngan)?",
        normalized,
    )
    if not match:
        return None
    cue = match.group(1) or ""
    amount_text = match.group(2)
    unit = match.group(3) or ""
    if not cue and not unit:
        return None

    amount = float(amount_text.replace(",", "."))
    if unit in {"trieu", "tr"}:
        amount *= 1_000_000
    elif unit in {"k", "nghin", "ngan"}:
        amount *= 1_000
    elif amount < 1000:
        amount *= 1_000_000
    return int(amount)


def _duration_seconds(value, default: int = 8) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        duration = default
    return max(1, min(duration, 120))


def _get_product_video_url(product) -> str:
    extra_info = getattr(product, "extra_info", None) or {}
    if isinstance(extra_info, dict):
        return str(extra_info.get("video_url") or extra_info.get("video") or "")
    return ""


def _get_product_images(product) -> list[str]:
    images = getattr(product, "images", None)
    if isinstance(images, list):
        return [str(url) for url in images if url]
    return []


def _banner_media_type(banner_obj, media_url: str) -> str:
    if isinstance(banner_obj, dict):
        media_type = str(banner_obj.get("media_type") or banner_obj.get("type") or "").lower()
        if media_type in {"image", "video"}:
            return media_type
    path = media_url.split("?", 1)[0].lower()
    return "video" if path.endswith(VIDEO_EXTENSIONS) else "image"


def _banner_media_url(banner_obj) -> str:
    if isinstance(banner_obj, dict):
        return str(banner_obj.get("video_url") or banner_obj.get("url") or banner_obj.get("fallback_url") or "")
    return str(banner_obj or "")


def _product_media(product) -> dict:
    image_url = getattr(product, "image_url", None) or ""
    gallery = _get_product_images(product)
    if not image_url and gallery:
        image_url = gallery[0]
    video_url = _get_product_video_url(product)

    return {
        "image_url": image_url,
        "image_proxy_url": build_proxy_image_url(image_url) if image_url else "",
        "images": gallery,
        "image_proxy_urls": [build_proxy_image_url(url) for url in gallery],
        "video_url": video_url,
        "primary_media_url": video_url or image_url,
        "primary_media_type": "video" if video_url else ("image" if image_url else "none"),
    }


def _product_result(product, include_description: bool = True) -> dict:
    result = {
        "id": product.id,
        "product_id": product.id,
        "name": product.name,
        "price": product.price,
        "price_formatted": _format_price(product.price),
        "original_price": getattr(product, "original_price", None),
        "category": getattr(product, "category", None),
        "sku": getattr(product, "sku", None),
        **_product_media(product),
    }
    if include_description:
        result["description"] = getattr(product, "description", None) or ""
    return result


def _sales_state(conn) -> dict:
    state = getattr(conn, "_sales_state", None)
    if not isinstance(state, dict):
        state = {
            "viewed_products": [],
            "interested_products": [],
            "last_query": None,
            "budget_hint": None,
            "objections": [],
            "last_media": None,
            "updated_at": time(),
        }
        setattr(conn, "_sales_state", state)
    return state


def _remember_product_interest(conn, product, query: str | None = None) -> dict:
    state = _sales_state(conn)
    state["last_query"] = query or state.get("last_query")
    state["updated_at"] = time()
    budget_hint = _parse_budget_hint(query)
    if budget_hint:
        state["budget_hint"] = budget_hint

    product_snapshot = _product_result(product, include_description=False)
    state["last_media"] = {
        "product_id": product.id,
        "name": product.name,
        **_product_media(product),
    }

    viewed = state.setdefault("viewed_products", [])
    if product.id not in [item.get("id") for item in viewed if isinstance(item, dict)]:
        viewed.append(product_snapshot)
        state["viewed_products"] = viewed[-10:]

    interested = state.setdefault("interested_products", [])
    if product.id not in [item.get("id") for item in interested if isinstance(item, dict)]:
        interested.append(product_snapshot)
        state["interested_products"] = interested[-5:]

    query_norm = _normalize_text(query)
    objections = state.setdefault("objections", [])
    for keyword in OBJECTION_KEYWORDS:
        if _normalize_text(keyword) in query_norm and keyword not in objections:
            objections.append(keyword)
    return state


def _lead_score(query: str | None, product, state: dict) -> int:
    score = 25
    query_norm = _normalize_text(query)
    for keyword in BUYING_INTENT_KEYWORDS:
        if _normalize_text(keyword) in query_norm:
            score += 8
    if _parse_budget_hint(query) or state.get("budget_hint"):
        score += 12
    if _get_product_video_url(product) or getattr(product, "image_url", None):
        score += 5
    if state.get("objections"):
        score += 10
    if len(state.get("viewed_products", [])) >= 2:
        score += 8
    return max(0, min(score, 100))


def _needs_complete(needs: dict) -> bool:
    return bool(needs.get("purpose") or needs.get("category")) and bool(needs.get("budget_hint") or needs.get("budget"))


def _comparison_label(index: int, product) -> str:
    if index == 0:
        return "Phù hợp nhất"
    if index == 1:
        return "Giá tốt"
    return "Nâng cấp/cao hơn"


def _rank_product(product, query: str | None, category: str | None, budget_hint: int | None) -> int:
    if not query and not category:
        return max(0, 1000 - int(getattr(product, "sort_order", 0) or 0))

    query_norm = _normalize_text(query)
    category_norm = _normalize_text(category)
    tokens = _query_tokens(query)
    name_norm = _normalize_text(getattr(product, "name", ""))
    desc_norm = _normalize_text(getattr(product, "description", ""))
    product_category_norm = _normalize_text(getattr(product, "category", ""))
    sku_norm = _normalize_text(getattr(product, "sku", ""))
    extra_norm = _normalize_text(json.dumps(getattr(product, "extra_info", None) or {}, ensure_ascii=False))

    score = 0
    if category_norm and category_norm in product_category_norm:
        score += 45
    if query_norm:
        if query_norm == name_norm:
            score += 160
        elif query_norm in name_norm:
            score += 110
        if query_norm in product_category_norm:
            score += 55
        if query_norm in sku_norm:
            score += 75
        if query_norm in desc_norm:
            score += 35
        if query_norm in extra_norm:
            score += 25
        if tokens:
            score += sum(18 for token in tokens if token in name_norm)
            score += sum(8 for token in tokens if token in product_category_norm)
            score += sum(5 for token in tokens if token in desc_norm)

    price = int(getattr(product, "price", 0) or 0)
    if budget_hint and price > 0:
        if price <= budget_hint:
            score += 35
        elif price <= budget_hint * 1.15:
            score += 12
        else:
            score -= 25
    if any(token in query_norm for token in ("re", "tiet kiem", "gia tot")) and price > 0:
        score += max(0, 30 - min(price // 100_000, 30))
    if score > 0:
        if _get_product_video_url(product):
            score += 8
        if getattr(product, "image_url", None) or _get_product_images(product):
            score += 6
        score += max(0, 30 - int(getattr(product, "sort_order", 0) or 0))
    return score


def _cancel_display_task(conn) -> None:
    task = getattr(conn, "_sales_display_task", None)
    if task and not task.done():
        task.cancel()
    setattr(conn, "_sales_display_task", None)


def _schedule_display_task(conn, coroutine) -> None:
    _cancel_display_task(conn)
    loop = getattr(conn, "loop", None)
    if loop and loop.is_running():
        task = asyncio.run_coroutine_threadsafe(coroutine, loop)
    else:
        task = asyncio.create_task(coroutine)
    setattr(conn, "_sales_display_task", task)


async def _get_user_sales_program(user_id: str):
    """Get the active sales program for a user."""
    from sqlalchemy import select

    from app.models.sales_program import SalesProgram

    async with local_session() as db:
        result = await db.execute(
            select(SalesProgram)
            .where(
                SalesProgram.user_id == user_id,
                SalesProgram.is_active.is_(True),
            )
            .order_by(SalesProgram.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def _search_products_db(
    program_ids: list,
    query: str = None,
    category: str = None,
    limit: int = 5,
):
    """Search and rank products by sales program IDs."""
    from sqlalchemy import select

    from app.models.product import Product

    if not program_ids:
        return []

    budget_hint = _parse_budget_hint(query)

    async with local_session() as db:
        stmt = select(Product).where(
            Product.sales_program_id.in_(program_ids),
            Product.is_active.is_(True),
        )

        if category:
            stmt = stmt.where(Product.category.ilike(f"%{category}%"))

        fetch_limit = max(limit * 25, 100)
        stmt = stmt.order_by(Product.sort_order, Product.name).limit(fetch_limit)

        result = await db.execute(stmt)
        products = result.scalars().all()

    ranked = [
        (_rank_product(product, query=query, category=category, budget_hint=budget_hint), product)
        for product in products
    ]
    if query or category:
        ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [product for _, product in ranked[:limit]]


async def _list_categories_db(program_ids: list) -> list[str]:
    from sqlalchemy import select

    from app.models.product import Product

    if not program_ids:
        return []
    async with local_session() as db:
        result = await db.execute(
            select(Product.category)
            .where(
                Product.sales_program_id.in_(program_ids),
                Product.is_active.is_(True),
                Product.category.isnot(None),
            )
            .distinct()
        )
    return sorted({row[0] for row in result.all() if row[0]})


def _format_price(price: int) -> str:
    """Format price to Vietnamese currency string."""
    if price <= 0:
        return "Liên hệ"
    return f"{price:,}đ".replace(",", ".")


def _format_product_voice(product) -> str:
    """Format a single product for voice output."""
    parts = [product.name]
    price_str = _format_price(product.price)
    parts.append(f"giá {price_str}")
    if product.description:
        desc = product.description[:80]
        parts.append(desc)
    return ". ".join(parts)


# ============================================================================


async def _auto_capture_lead_bg(
    conn,
    product,
    inquiry_text: str = None,
    ai_response: str = None,
):
    """Auto-capture a sales lead in the background (non-blocking).

    Only captures if the connection has an owner_user_id (agent owner).
    """
    import asyncio

    owner_user_id = getattr(conn, "owner_user_id", None)
    agent_id = getattr(conn, "agent_id", None)
    if not owner_user_id:
        return
    state = _remember_product_interest(conn, product, inquiry_text)
    score = _lead_score(inquiry_text, product, state)

    async def _capture():
        try:
            from app.api.v1.sales import auto_capture_lead

            await auto_capture_lead(
                user_id=owner_user_id,
                agent_id=agent_id,
                product_name=product.name,
                product_id=product.id,
                inquiry_text=inquiry_text,
                ai_response=ai_response,
                source="voice" if hasattr(conn, "mqtt_service") else "web",
                device_id=getattr(conn, "device_id", None),
                session_id=getattr(conn, "session_id", None),
                extra_data={
                    "lead_score": score,
                    "sales_program_id": getattr(product, "sales_program_id", None),
                    "budget_hint": state.get("budget_hint"),
                    "objections": state.get("objections", []),
                    "viewed_products": state.get("viewed_products", []),
                    "last_media": state.get("last_media"),
                },
            )
        except Exception as e:
            logger.bind(tag=TAG).debug(f"Lead capture failed (non-critical): {e}")

    loop = getattr(conn, "loop", None)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(_capture(), loop)
    else:
        try:
            asyncio.create_task(_capture())
        except RuntimeError:
            pass  # No event loop — skip silently


async def _record_display_event_bg(conn, product, message_id: str | None = None) -> None:
    owner_user_id = getattr(conn, "owner_user_id", None)
    if not owner_user_id or not product:
        return
    try:
        from app.api.v1.sales import record_sales_analytics_event, update_sales_session_state

        media = _product_media(product)
        await record_sales_analytics_event(
            user_id=owner_user_id,
            event_type="product_shown",
            agent_id=getattr(conn, "agent_id", None),
            sales_program_id=getattr(product, "sales_program_id", None),
            product_id=getattr(product, "id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            display_message_id=message_id,
            payload={"primary_media_type": media["primary_media_type"], "product_name": product.name},
        )
        await update_sales_session_state(
            user_id=owner_user_id,
            state="recommending",
            agent_id=getattr(conn, "agent_id", None),
            sales_program_id=getattr(product, "sales_program_id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            product_id=getattr(product, "id", None),
            product_name=getattr(product, "name", None),
            source="voice" if hasattr(conn, "mqtt_service") else "web",
            extra_data={"last_display_message_id": message_id, "last_media": media},
        )
    except Exception as event_err:
        logger.bind(tag=TAG).debug(f"Display analytics failed (non-critical): {event_err}")


async def _push_products_to_display(conn, products) -> bool:
    """Push products to device LCD as a short sales slideshow.

    Sends each product one-by-one using display_product action (non-persistent mode)
    so images survive LISTENING/STANDBY state transitions on the device. The
    slideshow ends after a small number of slides so idle banners can resume.
    """
    device_mac = getattr(conn, "device_id", None)
    if not device_mac or not products:
        return False

    try:
        mqtt = getattr(conn, "mqtt_service", None)
        if not mqtt or not mqtt.is_available():
            logger.bind(tag=TAG).warning("MQTT service not available for display push")
            return False

        topic = f"device/{device_mac}/server"
        topic2 = f"devices/p2p/{device_mac}"
        slide_products = products[:5]

        async def _slideshow():
            try:
                idx = 0
                total = len(slide_products)
                max_slides = min(total * 2, 10)
                sent = 0
                while not getattr(conn, "_closing", True) and sent < max_slides:
                    p = slide_products[idx]
                    price_str = _format_price(p.price)
                    title = f"{p.name} — {price_str}"
                    subtitle = (p.description or "")[:100]

                    media = _product_media(p)
                    message_id = str(uuid7())

                    display_msg = {
                        "type": "display",
                        "cmd": "show_video" if media["primary_media_type"] == "video" else "show_image",
                        "session_id": conn.session_id if conn and hasattr(conn, "session_id") else "",
                        "image": {
                            "url": media["image_proxy_url"] or media["image_url"],
                            "caption": title,
                            "position": "center",
                            "duration": 15000
                        },
                        "action": "display_product",
                        "message_id": message_id,
                        "data": {
                            "message_id": message_id,
                            "product_id": p.id,
                            "title": title,
                            "subtitle": subtitle,
                            "image_url": media["image_proxy_url"] or media["image_url"],
                            "raw_image_url": media["image_url"],
                            "gallery": media["image_proxy_urls"] or media["images"],
                            "video_url": media["video_url"],
                            "primary_media_url": media["primary_media_url"],
                            "primary_media_type": media["primary_media_type"],
                            "index": idx + 1,
                            "total": total,
                        },
                    }
                    await mqtt.publish(topic, display_msg)
                    await mqtt.publish(topic2, display_msg)
                    await _record_display_event_bg(conn, p, message_id)

                    idx = (idx + 1) % total
                    sent += 1
                    if sent < max_slides:
                        await asyncio.sleep(10)

            except asyncio.CancelledError:
                logger.bind(tag=TAG).debug("Product slideshow task cancelled")
            except Exception as slide_err:
                logger.bind(tag=TAG).warning(f"Slideshow loop failed: {slide_err}")

        _schedule_display_task(conn, _slideshow())

        return True
    except Exception as push_err:
        logger.bind(tag=TAG).warning(f"Display push failed: {push_err}")
        return False


async def _push_banners_to_display(conn) -> bool:
    """Push fallback banners to device LCD when no products are found."""
    try:
        from app.models.agent import Agent

        async with local_session() as db:
            agent = await db.get(Agent, getattr(conn, "agent_id", ""))
            if not agent or not getattr(agent, "banner_images", None):
                return False

            banners = agent.banner_images
            if not isinstance(banners, list) or len(banners) == 0:
                return False

            mqtt = getattr(conn, "mqtt_service", None)
            device_mac = getattr(conn, "device_id", None)
            if not mqtt or not mqtt.is_available() or not device_mac:
                return False

            topic = f"device/{device_mac}/server"
            topic2 = f"devices/p2p/{device_mac}"

            async def _banner_slideshow():
                try:
                    for i, banner_obj in enumerate(banners[:5]):
                        if isinstance(banner_obj, str):
                            b_url = banner_obj
                            b_media_type = _banner_media_type(banner_obj, b_url)
                            b_duration = 5
                            b_caption = "Đề xuất cho bạn"
                            b_id = f"banner-{i + 1}"
                            fallback_url = ""
                        else:
                            b_url = _banner_media_url(banner_obj)
                            b_media_type = _banner_media_type(banner_obj, b_url)
                            b_duration = _duration_seconds(banner_obj.get("duration", 10), default=10)
                            b_caption = banner_obj.get("caption", "Đề xuất cho bạn")
                            b_id = str(banner_obj.get("id") or f"banner-{i + 1}")
                            fallback_url = str(banner_obj.get("fallback_url", ""))

                        final_url = build_proxy_image_url(b_url) if b_url and b_media_type == "image" else b_url
                        fallback_image_url = build_proxy_image_url(fallback_url) if fallback_url else ""
                        message_id = str(uuid7())

                        display_msg = {
                            "type": "display",
                            "action": "display_banner",
                            "cmd": "show_video" if b_media_type == "video" else "show_image",
                            "message_id": message_id,
                            "media": {
                                "message_id": message_id,
                                "banner_id": b_id,
                                "type": b_media_type,
                                "url": final_url,
                                "fallback_url": fallback_image_url,
                                "caption": b_caption,
                                "duration": b_duration * 1000,
                            },
                            "data": {
                                "message_id": message_id,
                                "banner_id": b_id,
                                "title": "Thông Tin Tiện Ích",
                                "subtitle": b_caption,
                                "image_url": final_url if b_media_type == "image" else fallback_image_url,
                                "raw_image_url": b_url,
                                "video_url": final_url if b_media_type == "video" else "",
                                "primary_media_url": final_url,
                                "primary_media_type": b_media_type,
                                "fallback_url": fallback_image_url,
                                "index": i + 1,
                                "total": min(len(banners), 5),
                            },
                            "image": {
                                "message_id": message_id,
                                "banner_id": b_id,
                                "url": final_url if b_media_type == "image" else fallback_image_url,
                                "fallback_url": fallback_image_url,
                                "caption": b_caption,
                                "duration": b_duration * 1000,
                            },
                            "video": {
                                "message_id": message_id,
                                "banner_id": b_id,
                                "url": final_url if b_media_type == "video" else "",
                                "fallback_url": fallback_image_url,
                                "caption": b_caption,
                                "duration": b_duration * 1000,
                            },
                        }
                        await mqtt.publish(topic, display_msg)
                        await mqtt.publish(topic2, display_msg)
                        if i < min(len(banners), 5) - 1:
                            await asyncio.sleep(b_duration)
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"Banner slideshow failed: {e}")

            _schedule_display_task(conn, _banner_slideshow())

            return True
    except Exception as e:
        logger.bind(tag=TAG).warning(f"Failed to fetch fallback banners: {e}")
        return False


# ============================================================================
# SEARCH PRODUCT
# ============================================================================


@register_function("search_product", search_product_function_desc, ToolType.SYSTEM_CTL)
async def search_product(conn, query: str, category: str = None):
    """
    Search products by name, description, or category.
    Returns voice-friendly results.
    """
    logger.bind(tag=TAG).info(f"[SEARCH_PRODUCT] query={query}, category={category}")

    program_ids = getattr(conn, "sales_program_ids", None) or []

    if not program_ids:
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Chưa cấu hình chương trình bán hàng.",
        )

    try:
        products = await _search_products_db(program_ids, query=query, category=category)

        if not products:
            await _push_banners_to_display(conn)
            categories = await _list_categories_db(program_ids)
            suggestion = f" Hiện có các nhóm: {', '.join(categories[:5])}." if categories else ""
            return ActionResponse(
                action=Action.RESPONSE,
                result=json.dumps(
                    {
                        "status": "no_results",
                        "query": query,
                        "suggested_categories": categories[:5],
                    },
                    ensure_ascii=False,
                ),
                response=(
                    f"Không tìm thấy sản phẩm nào cho '{query}'.{suggestion} "
                    "Bạn muốn xem danh sách tất cả sản phẩm không?"
                ),
            )

        await _push_products_to_display(conn, products[:5])

        # Single product - detailed
        if len(products) == 1:
            p = products[0]
            media = _product_media(p)
            response = f"Tìm thấy {p.name}. Giá {_format_price(p.price)}. "
            if p.description:
                response += f"{p.description[:100]}. "
            if media["video_url"]:
                response += "Video sản phẩm đã được gửi kèm và đang hiển thị trên màn hình."
            elif media["image_url"]:
                response += "Ảnh sản phẩm đã được gửi kèm và đang hiển thị trên màn hình."

            await _auto_capture_lead_bg(conn, p, query, response)

            return ActionResponse(
                action=Action.RESPONSE,
                result=json.dumps(
                    _product_result(p),
                    ensure_ascii=False,
                ),
                response=response,
            )

        # Multiple products - summary
        response_parts = [f"Em tìm thấy {len(products)} sản phẩm phù hợp."]
        for i, p in enumerate(products[:3], 1):
            label = _comparison_label(i - 1, p)
            media_hint = (
                "có video" if _get_product_video_url(p) else ("có ảnh" if _product_media(p)["image_url"] else "")
            )
            suffix = f", {media_hint}" if media_hint else ""
            response_parts.append(f"{label}: {p.name}, giá {_format_price(p.price)}{suffix}")

        if len(products) > 3:
            response_parts.append(f"Và {len(products) - 3} sản phẩm khác.")
        response_parts.append("Em đang hiển thị các lựa chọn trên màn hình. Anh/chị muốn xem kỹ mẫu nào?")
        response = " ".join(response_parts)

        await _auto_capture_lead_bg(conn, products[0], query, response)

        return ActionResponse(
            action=Action.RESPONSE,
            result=json.dumps(
                {
                    "total": len(products),
                    "products": [_product_result(p, include_description=False) for p in products[:5]],
                    "top_media": _product_media(products[0]),
                },
                ensure_ascii=False,
            ),
            response=response,
        )

    except Exception as e:
        logger.bind(tag=TAG).exception(f"Lỗi search_product: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Có lỗi khi tìm sản phẩm. Thử lại sau nhé.",
        )


# ============================================================================
# LIST PRODUCTS
# ============================================================================


@register_function("list_products", list_products_function_desc, ToolType.SYSTEM_CTL)
async def list_products(conn):
    """List all available products."""
    logger.bind(tag=TAG).info("[LIST_PRODUCTS]")

    program_ids = getattr(conn, "sales_program_ids", None) or []

    if not program_ids:
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Chưa cấu hình chương trình bán hàng.",
        )

    try:
        products = await _search_products_db(program_ids, limit=10)

        if not products:
            await _push_banners_to_display(conn)
            return ActionResponse(
                action=Action.RESPONSE,
                result="no_products",
                response="Chưa có sản phẩm nào trong cửa hàng. Vui lòng thêm sản phẩm trong trang quản lý.",
            )

        await _push_products_to_display(conn, products[:5])

        response_parts = [f"Cửa hàng hiện có {len(products)} sản phẩm."]
        for i, p in enumerate(products[:5], 1):
            response_parts.append(f"{i}. {p.name}, {_format_price(p.price)}")

        if len(products) > 5:
            response_parts.append(f"Và {len(products) - 5} sản phẩm khác.")

        response_parts.append("Bạn muốn tìm hiểu sản phẩm nào?")

        return ActionResponse(
            action=Action.RESPONSE,
            result=json.dumps(
                {
                    "total": len(products),
                    "products": [_product_result(p, include_description=False) for p in products],
                    "top_media": _product_media(products[0]),
                },
                ensure_ascii=False,
            ),
            response=" ".join(response_parts),
        )

    except Exception as e:
        logger.bind(tag=TAG).exception(f"Lỗi list_products: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Có lỗi khi lấy danh sách sản phẩm.",
        )


# ============================================================================
# SHOW PRODUCT ON DEVICE DISPLAY
# ============================================================================


@register_function("show_product", show_product_function_desc, ToolType.SYSTEM_CTL)
async def show_product(conn, product_name: str):
    """Push product to device LCD display via MQTT."""
    logger.bind(tag=TAG).info(f"[SHOW_PRODUCT] name={product_name}")

    program_ids = getattr(conn, "sales_program_ids", None) or []
    device_mac = getattr(conn, "device_id", None)

    if not program_ids:
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Chưa cấu hình chương trình bán hàng.",
        )

    try:
        # Search for the product
        products = await _search_products_db(program_ids, query=product_name, limit=1)

        if not products:
            return ActionResponse(
                action=Action.RESPONSE,
                result="not_found",
                response=f"Không tìm thấy sản phẩm '{product_name}'.",
            )

        product = products[0]

        # Push to device display if device is connected (background, non-blocking)
        # Supports both MQTT and WebSocket transports for any firmware
        if device_mac:
            try:
                import asyncio

                _cancel_display_task(conn)
                price_str = _format_price(product.price)
                media = _product_media(product)
                message_id = str(uuid7())

                # Try image_proxy_url first, fallback to image_url
                img_url = (media["image_proxy_url"] or media["image_url"] or "")

                display_msg = {
                    "type": "display",
                    "cmd": "show_video" if media["primary_media_type"] == "video" else "show_image",
                    "session_id": conn.session_id if conn and hasattr(conn, "session_id") else "",
                    "image": {
                        "url": img_url,
                        "caption": product.name,
                        "position": "center",
                        "duration": 15000
                    },
                    "media": {
                        "message_id": message_id,
                        "type": media["primary_media_type"] if media["primary_media_type"] != "none" else "image",
                        "url": img_url,
                        "fallback_url": (media["image_proxy_url"] or ""),
                        "caption": product.name,
                        "duration": 15000,
                    },
                    "action": "display_product",
                    "message_id": message_id,
                    "data": {
                        "message_id": message_id,
                        "product_id": product.id,
                        "title": f"{product.name} — {price_str}",
                        "subtitle": (product.description or "")[:100],
                        "image_url": img_url,
                        "raw_image_url": media["image_url"],
                        "gallery": media["image_proxy_urls"] or media["images"],
                        "video_url": media["video_url"],
                        "primary_media_url": media["primary_media_url"],
                        "primary_media_type": media["primary_media_type"],
                    },
                }

                sent = False
                # Try MQTT first (for MQTT-connected devices)
                mqtt = getattr(conn, "mqtt_service", None)
                if mqtt and mqtt.is_available():
                    topic = f"device/{device_mac}/server"
                    topic2 = f"devices/p2p/{device_mac}"
                    if getattr(conn, "loop", None):
                        conn.loop.create_task(mqtt.publish(topic, display_msg))
                        conn.loop.create_task(mqtt.publish(topic2, display_msg))
                    else:
                        asyncio.create_task(mqtt.publish(topic, display_msg))
                        asyncio.create_task(mqtt.publish(topic2, display_msg))
                    sent = True

                # Fallback to WebSocket (for WebSocket-connected devices)
                if not sent:
                    ws = getattr(conn, "websocket", None)
                    if ws:
                        try:
                            import json as _json
                            await ws.send_text(_json.dumps(display_msg, ensure_ascii=False))
                            sent = True
                        except Exception as ws_err:
                            logger.bind(tag=TAG).debug(f"WebSocket product push failed: {ws_err}")

                if sent:
                    await _record_display_event_bg(conn, product, message_id)
                    logger.bind(tag=TAG).info(f"Pushed product to display: {device_mac}")
                else:
                    logger.bind(tag=TAG).warning(f"No transport available to push product to {device_mac}")
            except Exception as push_err:
                logger.bind(tag=TAG).warning(f"Display push failed: {push_err}")

        media = _product_media(product)
        response = f"Đây là {product.name}. Giá {_format_price(product.price)}. "
        if product.description:
            response += f"{product.description[:80]}. "
        if media["video_url"]:
            response += "Video sản phẩm đã được gửi kèm."
        elif media["image_url"]:
            response += "Ảnh sản phẩm đã được gửi kèm."
        if device_mac and media["primary_media_type"] != "none":
            response += " Nội dung đang hiển thị trên màn hình."

        # Auto-capture lead (outside push block)
        await _auto_capture_lead_bg(conn, product, product_name, response)

        return ActionResponse(
            action=Action.RESPONSE,
            result=json.dumps(
                {
                    **_product_result(product),
                    "displayed": bool(device_mac),
                },
                ensure_ascii=False,
            ),
            response=response,
        )

    except Exception as e:
        logger.bind(tag=TAG).exception(f"Lỗi show_product: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Có lỗi khi hiển thị sản phẩm.",
        )


@register_function("capture_customer_needs", capture_customer_needs_function_desc, ToolType.SYSTEM_CTL)
async def capture_customer_needs(
    conn,
    budget: str = None,
    purpose: str = None,
    category: str = None,
    variant: str = None,
    requirements: str = None,
    raw_text: str = None,
):
    """Track customer needs before product recommendation."""
    owner_user_id = getattr(conn, "owner_user_id", None)
    if not owner_user_id:
        return ActionResponse(action=Action.RESPONSE, result="error", response="Chưa xác định được chủ cửa hàng.")

    state = _sales_state(conn)
    needs = state.setdefault("needs", {})
    if budget:
        needs["budget"] = budget
    budget_hint = _parse_budget_hint(budget or raw_text)
    if budget_hint:
        needs["budget_hint"] = budget_hint
        state["budget_hint"] = budget_hint
    if purpose:
        needs["purpose"] = purpose
    if category:
        needs["category"] = category
    if variant:
        needs["variant"] = variant
    if requirements:
        needs["requirements"] = requirements
    if raw_text:
        needs["raw_text"] = raw_text
    state["updated_at"] = time()

    try:
        from app.api.v1.sales import record_sales_analytics_event, update_sales_session_state

        await record_sales_analytics_event(
            user_id=owner_user_id,
            event_type="needs_collected",
            agent_id=getattr(conn, "agent_id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            payload={"needs": needs, "complete": _needs_complete(needs)},
        )
        await update_sales_session_state(
            user_id=owner_user_id,
            state="needs_discovery",
            agent_id=getattr(conn, "agent_id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            needs=needs,
            source="voice" if hasattr(conn, "mqtt_service") else "web",
            extra_data={"needs_complete": _needs_complete(needs)},
        )
    except Exception as state_err:
        logger.bind(tag=TAG).debug(f"Needs state update failed (non-critical): {state_err}")

    missing = []
    if not needs.get("budget_hint") and not needs.get("budget"):
        missing.append("ngân sách")
    if not needs.get("purpose") and not needs.get("category"):
        missing.append("mục đích sử dụng")

    if missing:
        response = f"Em đã ghi nhận. Anh/chị cho em biết thêm {', '.join(missing)} để chọn đúng hơn nhé."
    else:
        response = "Em đã ghi nhận đủ nhu cầu chính, em sẽ tìm các lựa chọn phù hợp nhất."

    return ActionResponse(
        action=Action.RESPONSE,
        result=json.dumps({"status": "saved", "needs": needs, "missing": missing}, ensure_ascii=False),
        response=response,
    )


@register_function("handle_sales_objection", handle_sales_objection_function_desc, ToolType.SYSTEM_CTL)
async def handle_sales_objection(
    conn,
    objection_type: str,
    product_name: str = None,
    customer_text: str = None,
):
    """Record and respond to a sales objection."""
    owner_user_id = getattr(conn, "owner_user_id", None)
    if not owner_user_id:
        return ActionResponse(action=Action.RESPONSE, result="error", response="Chưa xác định được chủ cửa hàng.")

    objection_key = _normalize_text(objection_type or "other") or "other"
    default_scripts = {
        "price": "Dạ em hiểu. Nếu anh/chị ưu tiên chi phí, em có thể so mẫu giá tốt hơn hoặc giải thích điểm khác biệt để mình chọn đúng.",
        "thinking": "Dạ được ạ. Em tóm tắt nhanh điểm phù hợp nhất để anh/chị dễ cân nhắc nhé.",
        "compare": "Dạ em sẽ so sánh theo giá, điểm mạnh và trường hợp nên chọn từng mẫu.",
        "warranty": "Dạ mình nên kiểm tra bảo hành và chính sách đổi trả trước khi chốt. Em sẽ nhắc rõ phần này.",
        "stock": "Dạ để chắc chắn, em ghi nhận mẫu anh/chị quan tâm để cửa hàng kiểm tra tồn và liên hệ lại.",
        "shipping": "Dạ em ghi nhận nhu cầu giao hàng để cửa hàng báo phí và thời gian chính xác.",
        "other": "Dạ em hiểu băn khoăn của anh/chị. Em sẽ tư vấn theo hướng rõ lợi ích, chi phí và lựa chọn thay thế.",
    }

    custom_script = ""
    program_ids = getattr(conn, "sales_program_ids", None) or []
    if program_ids:
        try:
            from sqlalchemy import select

            from app.models.sales_program import SalesProgram

            async with local_session() as db:
                result = await db.execute(select(SalesProgram).where(SalesProgram.id == program_ids[0]))
                program = result.scalar_one_or_none()
                config = getattr(program, "display_config", None) if program else None
                scripts = config.get("objection_scripts", {}) if isinstance(config, dict) else {}
                custom_script = scripts.get(objection_key) or scripts.get(objection_type or "")
        except Exception as script_err:
            logger.bind(tag=TAG).debug(f"Objection script lookup failed: {script_err}")

    state = _sales_state(conn)
    objections = state.setdefault("objections", [])
    if objection_key not in objections:
        objections.append(objection_key)

    try:
        from app.api.v1.sales import record_sales_analytics_event, update_sales_session_state

        await record_sales_analytics_event(
            user_id=owner_user_id,
            event_type="objection_detected",
            agent_id=getattr(conn, "agent_id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            payload={"objection_type": objection_key, "product_name": product_name, "customer_text": customer_text},
        )
        await update_sales_session_state(
            user_id=owner_user_id,
            state="objection",
            agent_id=getattr(conn, "agent_id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            product_name=product_name,
            objections=objections,
            source="voice" if hasattr(conn, "mqtt_service") else "web",
            extra_data={"last_objection_text": customer_text},
        )
    except Exception as state_err:
        logger.bind(tag=TAG).debug(f"Objection state update failed (non-critical): {state_err}")

    response = custom_script or default_scripts.get(objection_key, default_scripts["other"])
    if product_name:
        response += f" Với {product_name}, em có thể so thêm một lựa chọn tiết kiệm hơn nếu anh/chị muốn."

    return ActionResponse(
        action=Action.RESPONSE,
        result=json.dumps(
            {
                "status": "handled",
                "objection_type": objection_key,
                "product_name": product_name,
                "response_script": response,
            },
            ensure_ascii=False,
        ),
        response=response,
    )


@register_function("start_sales_closing", start_sales_closing_function_desc, ToolType.SYSTEM_CTL)
async def start_sales_closing(
    conn,
    product_name: str = None,
    closing_text: str = None,
):
    """Move the current consultation into closing before contact capture."""
    owner_user_id = getattr(conn, "owner_user_id", None)
    if not owner_user_id:
        return ActionResponse(action=Action.RESPONSE, result="error", response="Chưa xác định được chủ cửa hàng.")

    try:
        from app.api.v1.sales import update_sales_session_state

        await update_sales_session_state(
            user_id=owner_user_id,
            state="closing",
            agent_id=getattr(conn, "agent_id", None),
            device_id=getattr(conn, "device_id", None),
            session_id=getattr(conn, "session_id", None),
            product_name=product_name,
            source="voice" if hasattr(conn, "mqtt_service") else "web",
            extra_data={"closing_text": closing_text},
        )
    except Exception as state_err:
        logger.bind(tag=TAG).debug(f"Closing state update failed (non-critical): {state_err}")

    response = closing_text or "Anh/chị cho em xin tên và số điện thoại để cửa hàng tư vấn/chốt đơn nhanh nhé."
    return ActionResponse(
        action=Action.RESPONSE,
        result=json.dumps({"status": "closing", "product_name": product_name}, ensure_ascii=False),
        response=response,
    )


@register_function("capture_sales_lead", capture_sales_lead_function_desc, ToolType.SYSTEM_CTL)
async def capture_sales_lead(
    conn,
    customer_name: str = None,
    customer_phone: str = None,
    customer_email: str = None,
    product_name: str = None,
    notes: str = None,
):
    """Persist contact details for the current sales conversation."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.sales_lead import SalesLead

    owner_user_id = getattr(conn, "owner_user_id", None)
    if not owner_user_id:
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Chưa xác định được chủ cửa hàng để lưu khách hàng quan tâm.",
        )

    state = _sales_state(conn)
    interested = state.get("interested_products") or []
    last_product = interested[-1] if interested and isinstance(interested[-1], dict) else {}

    resolved_product_name = (product_name or last_product.get("name") or "").strip()
    resolved_product_id = last_product.get("product_id") or last_product.get("id")
    phone = re.sub(r"[\s.\-]", "", customer_phone or "")
    email = (customer_email or "").strip()
    name = (customer_name or "").strip()
    clean_notes = (notes or "").strip()

    if not any([name, phone, email, clean_notes, resolved_product_name]):
        return ActionResponse(
            action=Action.RESPONSE,
            result="missing_info",
            response="Anh/chị cho em xin tên hoặc số điện thoại để lưu thông tin tư vấn nhé.",
        )

    agent_id = getattr(conn, "agent_id", None)
    device_id = getattr(conn, "device_id", None)
    session_id = getattr(conn, "session_id", None)
    source = "voice" if hasattr(conn, "mqtt_service") else "web"

    try:
        async with local_session() as db:
            conditions = [SalesLead.user_id == owner_user_id]
            if agent_id:
                conditions.append(SalesLead.agent_id == agent_id)
            if session_id:
                conditions.append(SalesLead.session_id == session_id)
            elif device_id:
                conditions.append(SalesLead.device_id == device_id)
            if resolved_product_id:
                conditions.append(SalesLead.product_id == resolved_product_id)
            elif resolved_product_name:
                conditions.append(SalesLead.product_name.ilike(f"%{resolved_product_name}%"))

            result = await db.execute(
                select(SalesLead).where(*conditions).order_by(SalesLead.created_at.desc()).limit(1)
            )
            lead = result.scalar_one_or_none()

            if not lead:
                lead = SalesLead(
                    user_id=owner_user_id,
                    agent_id=agent_id,
                    product_id=resolved_product_id,
                    product_name=resolved_product_name or "Chưa xác định",
                    inquiry_text=state.get("last_query"),
                    source=source,
                    device_id=device_id,
                    session_id=session_id,
                    status="new",
                )
                db.add(lead)

            if name:
                lead.customer_name = name
            if phone:
                lead.customer_phone = phone
            if email:
                lead.customer_email = email
            if clean_notes:
                lead.notes = clean_notes if not lead.notes else f"{lead.notes}\n{clean_notes}"
            if resolved_product_name and lead.product_name == "Chưa xác định":
                lead.product_name = resolved_product_name
            if resolved_product_id and not lead.product_id:
                lead.product_id = resolved_product_id

            lead.priority = max(getattr(lead, "priority", 0) or 0, 1 if phone or email else 0)
            lead.updated_at = datetime.now(timezone.utc)
            existing_extra = lead.extra_data if isinstance(lead.extra_data, dict) else {}
            lead.extra_data = {
                **existing_extra,
                "contact_captured": bool(phone or email or name),
                "budget_hint": state.get("budget_hint"),
                "objections": state.get("objections", []),
                "last_media": state.get("last_media"),
            }

            await db.commit()
            await db.refresh(lead)

        try:
            from app.api.v1.sales import record_sales_analytics_event, update_sales_session_state

            await record_sales_analytics_event(
                user_id=owner_user_id,
                event_type="lead_captured",
                agent_id=agent_id,
                product_id=lead.product_id,
                lead_id=lead.id,
                device_id=device_id,
                session_id=session_id,
                payload={
                    "customer_name": bool(lead.customer_name),
                    "customer_phone": bool(lead.customer_phone),
                    "customer_email": bool(lead.customer_email),
                    "product_name": lead.product_name,
                },
            )
            await update_sales_session_state(
                user_id=owner_user_id,
                state="captured",
                agent_id=agent_id,
                device_id=device_id,
                session_id=session_id,
                product_id=lead.product_id,
                product_name=lead.product_name,
                lead_id=lead.id,
                source=source,
                score=max(getattr(lead, "priority", 0) * 40, 80 if (phone or email) else 60),
                extra_data={"contact_captured": bool(phone or email or name), "notes": clean_notes},
            )
        except Exception as analytics_err:
            logger.bind(tag=TAG).debug(f"Sales lead analytics failed (non-critical): {analytics_err}")

        response_name = name or "khách"
        response = f"Em đã lưu thông tin {response_name}"
        if resolved_product_name:
            response += f" quan tâm {resolved_product_name}"
        response += ". Bộ phận bán hàng sẽ liên hệ lại sớm."

        return ActionResponse(
            action=Action.RESPONSE,
            result=json.dumps(
                {
                    "status": "saved",
                    "lead_id": lead.id,
                    "customer_name": lead.customer_name,
                    "customer_phone": lead.customer_phone,
                    "customer_email": lead.customer_email,
                    "product_name": lead.product_name,
                },
                ensure_ascii=False,
            ),
            response=response,
        )

    except Exception as e:
        logger.bind(tag=TAG).exception(f"Lỗi capture_sales_lead: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result="error",
            response="Có lỗi khi lưu khách hàng quan tâm.",
        )
