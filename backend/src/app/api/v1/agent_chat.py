"""
Agent Chat API — Browser-based text chat for testing agents

Provides a REST endpoint to chat with any agent directly from the browser.
Loads the agent's LLM provider, system prompt, and product catalog (if sales enabled).
Maintains conversation history within a session.
"""

import re
import uuid
from typing import Annotated, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.models.agent import Agent
from app.core.logger import get_logger
from app.models.product import Product
from app.models.sales_program import SalesProgram

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["Agent Chat"])

# In-memory session storage (simple approach for testing)
# Max sessions to prevent unbounded memory growth
_MAX_SESSIONS = 200
_chat_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    images: List[str] = []  # extracted image URLs from reply


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def agent_chat(
    agent_id: str,
    data: ChatRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Chat with an agent via text. Returns LLM response.
    Uses the agent's configured LLM provider, prompt, and product catalog.
    """
    # 1. Load agent
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.is_deleted == False)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    # Check ownership (unless superadmin)
    is_super = current_user.get("is_superuser") or current_user.get("role") in ["admin", "super_admin"]
    if not is_super and str(agent.user_id) != str(current_user["id"]):
        raise HTTPException(403, "Not your agent")
    
    # 2. Build system prompt
    system_prompt = agent.prompt or "Bạn là trợ lý AI thân thiện."
    
    # Add current time context
    now = datetime.now()
    system_prompt = system_prompt.replace("{{current_time}}", now.strftime("%H:%M"))
    
    # 3. Inject product catalog if sales enabled
    if agent.enable_sales and agent.sales_program_ids:
        catalog_text = await _build_product_catalog(db, agent.sales_program_ids)
        if catalog_text:
            system_prompt += f"\n\n<product_catalog>\n{catalog_text}\nKhi khách hỏi về sản phẩm, hãy tư vấn dựa trên danh mục trên. Giới thiệu sản phẩm có giá, mô tả chi tiết, và đường link ảnh (markdown format). Nếu có khuyến mãi, nhấn mạnh giá ưu đãi.\n</product_catalog>"
    
    # 4. Inject education context if enabled
    if getattr(agent, 'enable_education', False):
        edu_text = await _build_education_context(db, agent)
        if edu_text:
            system_prompt += f"\n\n<education_context>\n{edu_text}\nBạn là gia sư AI. Khi học viên hỏi về học tập, giới thiệu các khóa học và bài học có sẵn. Hướng dẫn học viên qua từng bài, giải thích từ vựng, và khuyến khích luyện tập.\n</education_context>"
    
    # 4. Get or create session
    session_id = data.session_id or str(uuid.uuid4())
    if session_id not in _chat_sessions:
        # Evict oldest sessions if at capacity
        if len(_chat_sessions) >= _MAX_SESSIONS:
            oldest_key = next(iter(_chat_sessions))
            del _chat_sessions[oldest_key]
        _chat_sessions[session_id] = []
    
    history = _chat_sessions[session_id]
    
    # 5. Build dialogue
    dialogue = [{"role": "system", "content": system_prompt}]
    
    # Add history (max last 20 messages)
    for msg in history[-20:]:
        dialogue.append(msg)
    
    # Add current user message
    dialogue.append({"role": "user", "content": data.message})
    
    # 6. Get LLM provider
    llm_provider = await _get_llm_provider(db, agent)
    if not llm_provider:
        raise HTTPException(500, "No LLM provider configured for this agent")
    
    # 7. Generate response
    try:
        reply = ""
        for token in llm_provider.response(session_id, dialogue):
            reply += token
        
        if not reply.strip():
            reply = "Xin lỗi, tôi không thể trả lời lúc này."
        
    except Exception as e:
        logger.error(f"LLM response error: {e}")
        raise HTTPException(500, "LLM service unavailable, please try again")
    
    # 8. Save to history (In-Memory for dialogue context)
    history.append({"role": "user", "content": data.message})
    history.append({"role": "assistant", "content": reply})
    
    # Keep max 40 messages in memory
    if len(history) > 40:
        _chat_sessions[session_id] = history[-40:]
    
    # 9. Extract image URLs from reply for rich display
    images = _extract_images(reply)

    # 10. Save to Database so it appears in History tab
    try:
        from app.services.agent_service import agent_service
        # Save User Message
        await agent_service.save_chat_message(
            db=db,
            agent_id=agent_id,
            session_id=session_id,
            chat_type=1, # 1 for user
            content=data.message
        )
        # Save Assistant Message
        await agent_service.save_chat_message(
            db=db,
            agent_id=agent_id,
            session_id=session_id,
            chat_type=2, # 2 for assistant
            content=reply
        )
    except Exception as e:
        logger.error(f"Failed to save Chat Test messages to DB: {e}")
    
    return ChatResponse(
        reply=reply,
        session_id=session_id,
        images=images,
    )


@router.delete("/{agent_id}/chat/{session_id}")
async def clear_chat_session(
    agent_id: str,
    session_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Clear chat session history."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    return {"message": "Session cleared"}


async def _get_llm_provider(db: AsyncSession, agent: Agent):
    """Instantiate the agent's LLM provider."""
    try:
        from app.models.provider import Provider
        
        # Agent stores LLM as "db:UUID" format
        llm_ref = agent.LLM  # e.g., "db:019b8ebb-db46-79be-9cdd-134ee39b2c42"
        provider = None
        
        if llm_ref and llm_ref.startswith("db:"):
            provider_id = llm_ref.split(":", 1)[1]
            result = await db.execute(
                select(Provider).where(Provider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
        
        if not provider:
            # Fallback: find any LLM provider for user
            result = await db.execute(
                select(Provider).where(
                    Provider.user_id == agent.user_id,
                    Provider.category == "LLM",
                    Provider.is_active == True,
                ).limit(1)
            )
            provider = result.scalar_one_or_none()
        
        if not provider:
            return None
        
        # Build config dict from provider
        config = dict(provider.config or {})
        config["type"] = provider.type
        
        from app.ai.module_factory import initialize_llm_from_config
        return initialize_llm_from_config(config)
        
    except Exception as e:
        logger.error(f"Failed to create LLM provider: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _build_product_catalog(db: AsyncSession, sales_program_ids: list) -> str:
    """Build product catalog text for LLM context injection."""
    
    catalog_parts = []
    
    for prog_id in sales_program_ids:
        prog_result = await db.execute(
            select(SalesProgram).where(SalesProgram.id == prog_id)
        )
        program = prog_result.scalar_one_or_none()
        if not program or not program.is_active:
            continue
        
        result = await db.execute(
            select(Product).where(
                and_(
                    Product.sales_program_id == prog_id,
                    Product.is_active == True,
                )
            ).order_by(Product.sort_order, Product.name)
        )
        products = result.scalars().all()
        
        if not products:
            continue
        
        lines = [f"[DANH MỤC SẢN PHẨM - {program.business_name or program.name}]"]
        if program.business_address:
            lines.append(f"Địa chỉ: {program.business_address}")
        if program.business_phone:
            lines.append(f"Điện thoại: {program.business_phone}")
        lines.append("")
        
        for i, p in enumerate(products, 1):
            price_str = f"{p.price:,}đ".replace(",", ".")
            line = f"{i}. {p.name} — {price_str}"
            if p.original_price and p.original_price > p.price:
                orig_str = f"{p.original_price:,}đ".replace(",", ".")
                discount = round((1 - p.price / p.original_price) * 100)
                line += f" (giảm {discount}% từ {orig_str})"
            if p.description:
                line += f"\n   {p.description}"
            if p.category:
                line += f" [{p.category}]"
            if p.image_url:
                line += f"\n   Ảnh chính: {p.image_url}"
            if p.images:
                for img_idx, img_url in enumerate(p.images, 1):
                    line += f"\n   Ảnh {img_idx}: {img_url}"
            lines.append(line)
        
        catalog_parts.append("\n".join(lines))
    
    return "\n\n".join(catalog_parts)


def _extract_images(text: str) -> list[str]:
    """Extract image URLs from markdown text."""
    # Match ![alt](url) and plain image URLs
    patterns = [
        r'!\[.*?\]\((https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*)\)',
        r'!\[.*?\]\((/uploads/\S+\.(?:jpg|jpeg|png|gif|webp)\S*)\)',
    ]
    images = []
    for pattern in patterns:
        images.extend(re.findall(pattern, text, re.IGNORECASE))
    return images


async def _build_education_context(db: AsyncSession, agent: Agent) -> str:
    """Build education context for LLM prompt injection."""
    try:
        from sqlalchemy import text as sql_text

        courses: list[dict] = []

        # 1) Preferred source: courses assigned via template
        template_id = getattr(agent, "active_template_id", None) or getattr(agent, "source_template_id", None)
        if template_id:
            result = await db.execute(
                sql_text(
                    """
                    SELECT c.id, c.name, c.description, c.difficulty
                    FROM template_course tc
                    JOIN edu_course c ON tc.course_id = c.id
                    WHERE tc.template_id = :template_id AND c.is_published = true
                    ORDER BY tc.course_order
                    """
                ),
                {"template_id": template_id},
            )
            courses = [dict(row) for row in result.mappings().all()]

        # 2) Fallback source: courses assigned directly on Agent.course_ids
        if not courses and getattr(agent, "course_ids", None):
            requested_ids = [str(course_id) for course_id in (agent.course_ids or []) if course_id]
            if requested_ids:
                result = await db.execute(
                    sql_text(
                        """
                        SELECT id, name, description, difficulty
                        FROM edu_course
                        WHERE user_id = :user_id
                          AND is_published = true
                        """
                    ),
                    {"user_id": str(agent.user_id)},
                )
                available = {str(row["id"]): dict(row) for row in result.mappings().all()}
                for course_id in requested_ids:
                    course = available.get(course_id)
                    if course:
                        courses.append(course)

        if not courses:
            return ""

        parts = ["[CHƯƠNG TRÌNH HỌC TẬP]"]

        for course in courses:
            parts.append(f"\n📚 Khóa học: {course['name']}")
            if course.get("description"):
                parts.append(f"   Mô tả: {course['description']}")
            if course.get("difficulty"):
                parts.append(f"   Trình độ: {course['difficulty']}")

            # Get lessons for this course
            lesson_result = await db.execute(
                sql_text(
                    """
                    SELECT title, lesson_type, lesson_order, description
                    FROM edu_lesson
                    WHERE course_id = :course_id AND is_published = true
                    ORDER BY lesson_order
                    """
                ),
                {"course_id": course["id"]},
            )
            lessons = lesson_result.mappings().all()

            if lessons:
                parts.append(f"   Bài học ({len(lessons)} bài):")
                for lesson in lessons:
                    type_emoji = {"conversation": "💬", "story": "📖", "vocabulary": "📝"}.get(lesson["lesson_type"], "📗")
                    parts.append(f"     {type_emoji} {lesson['title']}")
                    if lesson.get("description"):
                        parts.append(f"        {lesson['description']}")

        return "\n".join(parts)

    except Exception as e:
        logger.error(f"Failed to build education context: {e}")
        return ""
