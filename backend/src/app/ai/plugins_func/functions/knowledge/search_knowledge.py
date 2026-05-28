"""
Knowledge Base Search Function - Cho phép LLM tìm kiếm trong cơ sở tri thức.

PHÂN BIỆT RÕ RÀNG:
- KNOWLEDGE BASE (RAGFlow): Documents tĩnh - PDF, DOCX, tài liệu công ty
- MEMORY (OpenMemory): Thông tin cá nhân user - sở thích, thói quen, facts

Function này dùng RAGFlow để search trong Knowledge Base.
"""

from app.ai.plugins_func.register import (
    Action,
    ActionResponse,
    ToolType,
    register_function,
)
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()

SEARCH_KNOWLEDGE_BASE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Tìm kiếm thông tin trong cơ sở tri thức (Knowledge Base) của agent. "
            "Sử dụng cho các tài liệu đã được upload như: PDF, Word, tài liệu công ty, "
            "hướng dẫn sản phẩm, FAQ, quy trình, chính sách. "
            "KHÔNG dùng cho thông tin cá nhân của user (dùng memory thay thế). "
            "Ví dụ: 'tìm thông tin về sản phẩm X', 'chính sách đổi trả', 'hướng dẫn cài đặt'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi hoặc từ khóa cần tìm kiếm trong tài liệu",
                },
                "k": {
                    "type": "integer",
                    "description": "Số lượng kết quả trả về (1-10), mặc định là 3",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}


@register_function(
    "search_knowledge_base",
    SEARCH_KNOWLEDGE_BASE_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
async def search_knowledge_base(
    conn=None,
    query: str = "",
    k: int = 3,
    **kwargs,
) -> ActionResponse:
    """
    Tìm kiếm thông tin trong cơ sở tri thức (Knowledge Base) của agent.
    
    Dùng RAGFlow cho document search (PDF, DOCX, etc.)
    Khác với Memory (OpenMemory) dùng cho thông tin cá nhân user.

    Args:
        conn: Connection context (chứa agent_id)
        query: Câu hỏi hoặc từ khóa cần tìm
        k: Số lượng kết quả trả về (1-10)

    Returns:
        ActionResponse với kết quả tìm kiếm
    """
    # Validate input
    if not query or not query.strip():
        return ActionResponse(
            action=Action.REQLLM,
            result="Vui lòng cung cấp từ khóa hoặc câu hỏi cần tìm kiếm.",
        )

    # Limit k to valid range
    k = max(1, min(k, 10))

    # Get agent_id from connection context
    agent_id = None
    if conn and hasattr(conn, "agent_id"):
        agent_id = conn.agent_id
    elif conn and hasattr(conn, "agent") and conn.agent:
        agent_id = (
            conn.agent.get("id")
            if isinstance(conn.agent, dict)
            else getattr(conn.agent, "id", None)
        )

    if not agent_id:
        logger.bind(tag=TAG).warning("No agent_id found in connection context")
        return ActionResponse(
            action=Action.REQLLM,
            result="Không thể xác định agent. Cơ sở tri thức không khả dụng.",
        )

    # Check if knowledge base is enabled in agent template
    enable_kb = True  # Default enabled
    if conn and hasattr(conn, "enable_knowledge_base"):
        enable_kb = getattr(conn, "enable_knowledge_base", True)

    if not enable_kb:
        logger.bind(tag=TAG).info(f"Knowledge base disabled for agent {agent_id}")
        return ActionResponse(
            action=Action.REQLLM,
            result="Kho tri thức đã bị tắt trong cấu hình agent.",
        )

    logger.bind(tag=TAG).info(
        f"Searching knowledge for agent {agent_id}: KB={enable_kb}, query='{query[:50]}...', k={k}"
    )

    # Get template_id from connection context
    template_id = None
    if conn and hasattr(conn, "template_id"):
        template_id = conn.template_id
    elif conn and hasattr(conn, "config") and conn.config:
        template_id = getattr(conn.config, "template_id", None)
    
    try:
        all_results = []
        image_urls = []
        video_urls = []
        
        # === Search ChromaDB (local knowledge base) ===
        chromadb_results, chromadb_images, chromadb_videos = await _search_chromadb(agent_id, template_id, query, k)
        if chromadb_results:
            all_results.append(f"📚 Từ Knowledge Base:\n{chromadb_results}")
            image_urls.extend(chromadb_images)
            video_urls.extend(chromadb_videos)

        if all_results:
            response_text = "Kết quả tìm kiếm:\n\n" + "\n\n".join(all_results)
            
            # === KIOSK MODE: Push media to device display via MQTT ===
            has_media = bool(image_urls or video_urls)
            if has_media and conn:
                await _push_media_to_device(conn, image_urls, video_urls, query)
            
            # Instruct LLM how to handle media display
            if image_urls:
                response_text += (
                    "\n\n[HIỂN THỊ: Hình ảnh sản phẩm đang được hiển thị trên màn hình thiết bị. "
                    "Hãy nhắc người dùng xem hình ảnh trên màn hình.]"
                )
            
            if video_urls:
                response_text += (
                    "\n\n[HIỂN THỊ VIDEO: Video đang được phát trên màn hình thiết bị. "
                    "Hãy nói ngắn gọn 'Mời bạn xem video trên màn hình', "
                    "sau đó ĐỢI video phát xong rồi mới tư vấn chi tiết thêm.]"
                )
            
            return ActionResponse(
                action=Action.REQLLM,
                result=response_text,
            )
        
        return ActionResponse(
            action=Action.REQLLM,
            result="Không tìm thấy thông tin liên quan trong Knowledge Base.",
        )

    except Exception as e:
        logger.bind(tag=TAG).exception(f"Error in search_knowledge_base: {e}")
        return ActionResponse(
            action=Action.REQLLM,
            result="Đã xảy ra lỗi khi tìm kiếm cơ sở tri thức.",
        )


async def _search_chromadb(
    agent_id: str, 
    template_id: str | None, 
    query: str, 
    k: int
) -> tuple[str, list[str]]:
    """
    Search in ChromaDB (knowledge base).
    
    If template_id is provided, search only KBs linked to that template.
    Otherwise, fall back to searching all agent KBs.
    
    Returns:
        tuple: (formatted results string, list of image URLs)
    """
    try:
        from app.services.chromadb_service import get_chromadb_service
        
        service = get_chromadb_service()
        if not service:
            logger.bind(tag=TAG).debug("ChromaDB service not available")
            return "", []
        
        # Get knowledge base IDs to search
        kb_ids = []
        
        if template_id:
            # NEW: Get KBs from Template-level binding
            try:
                from app.core.db.database import async_get_db_session
                from app.crud import crud_template_knowledge_base
                
                async with async_get_db_session() as db:
                    kb_ids = await crud_template_knowledge_base.get_knowledge_base_ids_for_template(
                        db=db,
                        template_id=template_id,
                    )
                    logger.bind(tag=TAG).debug(
                        f"Template {template_id} has {len(kb_ids)} linked KBs"
                    )
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Failed to get template KBs: {e}")
        
        # Collect all results from relevant KBs
        all_chunks = []
        
        if kb_ids:
            # Search specific KBs linked to template
            for kb_id in kb_ids:
                try:
                    chunks = await service.search(
                        agent_id=kb_id,  # KB ID is used as collection identifier
                        query=query,
                        top_k=k,
                    )
                    if chunks:
                        all_chunks.extend(chunks)
                except Exception as e:
                    logger.bind(tag=TAG).debug(f"KB {kb_id} search failed: {e}")
        else:
            # Fallback: search by agent_id (legacy behavior)
            logger.bind(tag=TAG).debug(f"No template KBs, falling back to agent {agent_id}")
            chunks = await service.search(
                agent_id=agent_id,
                query=query,
                top_k=k,
            )
            if chunks:
                all_chunks = chunks
        
        if not all_chunks:
            logger.bind(tag=TAG).debug(f"No ChromaDB results for query")
            return "", [], []
        
        # Sort by score and take top k
        all_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_chunks = all_chunks[:k]
        
        # Format results and collect image URLs
        formatted = []
        image_urls = []
        video_urls = []
        
        for i, chunk in enumerate(top_chunks, 1):
            content = chunk.get("content", "")[:500]
            source = chunk.get("source", "document")
            title = chunk.get("title", "")
            score = chunk.get("score", 0)
            image_url = chunk.get("image_url")
            video_url = chunk.get("video_url")
            
            # Build formatted entry
            title_info = f" - {title}" if title else ""
            formatted.append(f"{i}. [{source}{title_info}] (relevance: {score:.0%})\\n{content}")
            
            # Collect image URLs
            if image_url and image_url.strip():
                image_urls.append(image_url.strip())
            
            # Collect video URLs (YouTube, etc.)
            if video_url and video_url.strip():
                video_urls.append(video_url.strip())
        
        logger.bind(tag=TAG).info(f"ChromaDB search returned {len(formatted)} results, {len(image_urls)} images, {len(video_urls)} videos")
        return "\\n\\n".join(formatted), image_urls, video_urls
        
    except ImportError as e:
        logger.bind(tag=TAG).debug(f"ChromaDB service not available: {e}")
        return "", [], []
    except Exception as e:
        logger.bind(tag=TAG).warning(f"ChromaDB search failed: {e}")
        return "", [], []


async def _push_media_to_device(conn, image_urls: list, video_urls: list, query: str):
    """
    Push media (images/videos) to device display via MQTT.
    
    This implements the Kiosk Mode display pipeline:
    - When KB search finds media URLs, push them to the device's LCD screen
    - Device shows media full-screen with emotion face minimized to a corner
    - For videos: device plays video first, then AI continues consultation
    
    MQTT Message Format:
    Topic: device/{device_mac}/display 
    Payload: {
        "action": "display_media",
        "data": {
            "type": "image" | "video" | "carousel",
            "urls": [...],
            "title": "Context from user query",
            "duration": seconds (for images),
            "wait_for_finish": true (for videos with voice annotation),
            "emotion_position": "bottom_right_small"
        }
    }
    
    Args:
        conn: ConnectionHandler with device info and MQTT access
        image_urls: List of image URL strings
        video_urls: List of video URL strings  
        query: Original user query for context
    """
    try:
        # Get device MAC for MQTT topic
        device_mac = None
        if hasattr(conn, "device_mac_address") and conn.device_mac_address:
            device_mac = conn.device_mac_address
        elif hasattr(conn, "get_device_mac_for_mqtt"):
            device_mac = conn.get_device_mac_for_mqtt()
        
        if not device_mac:
            logger.bind(tag=TAG).debug("No device MAC available, skipping media push")
            return
        
        # Get MQTT service
        mqtt_service = None
        try:
            # Try from app state (FastAPI dependency)
            if hasattr(conn, "server") and conn.server:
                app_state = getattr(conn.server, "app_state", None)
                if app_state:
                    mqtt_service = getattr(app_state, "mqtt", None)
            
            # Fallback: import directly
            if not mqtt_service:
                from app.services.mqtt_service import MQTTService
                from app.config.settings import settings as app_settings
                if hasattr(app_settings, "mqtt") and app_settings.mqtt:
                    mqtt_service = MQTTService.from_config(app_settings.mqtt)
        except Exception as mqtt_err:
            logger.bind(tag=TAG).debug(f"MQTT service unavailable: {mqtt_err}")
            return
        
        if not mqtt_service or not mqtt_service.is_available():
            logger.bind(tag=TAG).debug("MQTT not available for media push")
            return
        
        topic = f"device/{device_mac}/display"
        
        # Push images
        if image_urls:
            if len(image_urls) == 1:
                payload = {
                    "type": "display",
                    "action": "display_media",
                    "cmd": "show_image",
                    "session_id": conn.session_id if conn and hasattr(conn, "session_id") else "",
                    "image": {
                        "url": image_urls[0],
                        "caption": query[:100],
                        "position": "center",
                        "duration": 15000
                    },
                    "data": {
                        "type": "image",
                        "url": image_urls[0],
                        "title": query[:100],
                        "duration": 15,  # Show for 15 seconds
                        "emotion_position": "bottom_right_small",
                    }
                }
            else:
                payload = {
                    "type": "display",
                    "action": "display_media",
                    "cmd": "show_image",
                    "session_id": conn.session_id if conn and hasattr(conn, "session_id") else "",
                    "image": {
                        "url": image_urls[0],
                        "caption": query[:100],
                        "position": "center",
                        "duration": 15000
                    },
                    "data": {
                        "type": "carousel",
                        "urls": image_urls[:5],  # Max 5 images
                        "title": query[:100],
                        "duration_per_item": 5,
                        "auto_scroll": True,
                        "emotion_position": "bottom_right_small",
                    }
                }
            
            await mqtt_service.publish(topic, payload, qos=1)
            logger.bind(tag=TAG).info(
                f"📺 Pushed {len(image_urls)} image(s) to device {device_mac}"
            )
        
        # Push videos (higher priority - will override images)
        if video_urls:
            payload = {
                "type": "display",
                "action": "display_media",
                "cmd": "show_video",
                "session_id": conn.session_id if conn and hasattr(conn, "session_id") else "",
                "image": {
                    "url": video_urls[0],
                    "caption": query[:100],
                    "position": "center",
                    "duration": 60000
                },
                "data": {
                    "type": "video",
                    "url": video_urls[0],  # Play first video
                    "title": query[:100],
                    "wait_for_finish": True,  # TTS should wait for video
                    "emotion_position": "bottom_right_small",
                }
            }
            
            await mqtt_service.publish(topic, payload, qos=1)
            logger.bind(tag=TAG).info(
                f"🎬 Pushed video to device {device_mac}: {video_urls[0][:80]}..."
            )
        
    except Exception as e:
        # Media push failure should NEVER break the knowledge search flow
        logger.bind(tag=TAG).warning(f"Media push to device failed (non-fatal): {e}")


# NOTE: Primary knowledge source is ChromaDB (local vector database)
# Memory (personal) is handled separately by memory_recall tool
