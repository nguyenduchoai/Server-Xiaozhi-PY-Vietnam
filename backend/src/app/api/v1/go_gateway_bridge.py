"""
Internal API for Go Gateway Bridge v2.
Handles forwarding between Go transport layer and Python AI pipeline.

The key insight: we DON'T rewrite the AI pipeline.
Instead, we create a lightweight adapter that:
1. Receives audio/text from Go gateway
2. Uses the existing ASR/LLM/TTS providers directly
3. Streams responses back via SSE

Security: Only accessible from internal Docker network (X-Internal-Gateway header).
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json
import logging
import asyncio
import base64
import uuid
import time
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Go Gateway Bridge"])


def _verify_internal(request: Request):
    """Verify request comes from Go gateway."""
    gateway = request.headers.get("X-Internal-Gateway", "")
    if not gateway.startswith("go-gateway"):
        raise HTTPException(status_code=403, detail="Internal API only")


@router.post("/hello")
async def handle_hello(request: Request):
    """Forward device hello - returns OTA info, session config."""
    _verify_internal(request)
    body = await request.json()
    device_id = body.get("device_id", "")
    
    logger.info(f"[go-bridge] Hello from device {device_id}")
    
    # Get agent config and OTA info from existing services
    session_id = f"go-{device_id}-{int(time.time())}"
    
    response = {
        "type": "hello",
        "transport": "websocket",
        "audio_params": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
        },
        "session_id": session_id,
    }
    
    # Get OTA info (same as existing WebSocket handler)
    try:
        from app.core.config import settings
        ota_url = getattr(settings, 'OTA_URL', None) or getattr(settings, 'SERVER_URL', '')
        if ota_url:
            response["ota"] = {
                "websocket_url": ota_url,
            }
    except Exception as e:
        logger.warning(f"[go-bridge] OTA info error: {e}")
    
    return JSONResponse(content=response)


@router.post("/chat")
async def handle_chat(request: Request):
    """
    Process chat request using existing AI pipeline.
    Streams ASR→LLM→TTS results back via SSE.
    """
    _verify_internal(request)
    body = await request.json()
    device_id = body.get("device_id", "")
    session_id = body.get("session_id", "")
    text = body.get("text", "")
    opus_frames_b64 = body.get("opus_frames", [])  # Array of base64-encoded individual Opus frames
    audio_b64 = body.get("audio_pcm", "")  # Legacy: single combined blob
    agent_id = body.get("agent_id", "")
    
    # Decode Opus frames: prefer individual frames over combined blob
    opus_packets = []
    if opus_frames_b64:
        for frame_b64 in opus_frames_b64:
            try:
                opus_packets.append(base64.b64decode(frame_b64))
            except Exception:
                pass
        logger.info(f"[go-bridge] Chat: device={device_id}, text_len={len(text)}, opus_frames={len(opus_packets)}")
    elif audio_b64:
        opus_packets = [base64.b64decode(audio_b64)]  # Fallback: single blob
        logger.info(f"[go-bridge] Chat: device={device_id}, text_len={len(text)}, audio_blob_len={len(audio_b64)}")
    else:
        logger.info(f"[go-bridge] Chat: device={device_id}, text_len={len(text)}, no_audio=True")
    
    async def event_stream():
        try:
            recognized_text = text
            
            # Step 1: ASR if we have audio
            if opus_packets and not text:
                try:
                    recognized_text = await _run_asr_pipeline(device_id, opus_packets)
                    if recognized_text:
                        # Always send string data (not tuple/array)
                        yield _sse({"type": "asr_text", "data": str(recognized_text)})
                    else:
                        yield _sse({"type": "error", "data": "ASR: no speech detected"})
                        yield "data: [DONE]\n\n"
                        return
                except Exception as e:
                    logger.error(f"[go-bridge] ASR error: {e}", exc_info=True)
                    yield _sse({"type": "error", "data": f"ASR error: {str(e)}"})
                    yield "data: [DONE]\n\n"
                    return
            elif text:
                yield _sse({"type": "asr_text", "data": text})
            else:
                yield _sse({"type": "error", "data": "No audio or text provided"})
                yield "data: [DONE]\n\n"
                return
            
            # Step 2: LLM streaming
            full_response = ""
            async for chunk in _run_llm_pipeline(device_id, agent_id, recognized_text):
                full_response += chunk
                yield _sse({"type": "llm_delta", "data": chunk})
            
            # Step 3: TTS on full response
            if full_response:
                async for audio_chunk_b64 in _run_tts_pipeline(device_id, agent_id, full_response):
                    yield _sse({"type": "tts_audio", "data": audio_chunk_b64})
            
            yield "data: [DONE]\n\n"
            
        except asyncio.CancelledError:
            logger.info(f"[go-bridge] Chat cancelled for device {device_id}")
        except Exception as e:
            logger.error(f"[go-bridge] Chat error: {e}", exc_info=True)
            yield _sse({"type": "error", "data": str(e)})
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/device/event")
async def handle_device_event(request: Request):
    """Handle device online/offline events."""
    _verify_internal(request)
    body = await request.json()
    device_id = body.get("device_id", "")
    event = body.get("event", "")
    logger.info(f"[go-bridge] Device {device_id}: {event}")
    return JSONResponse(content={"status": "ok"})


@router.post("/forward")
async def handle_forward(request: Request):
    """Forward IoT/MCP messages."""
    _verify_internal(request)
    body = await request.json()
    logger.info(f"[go-bridge] Forward: {body.get('msg_type', 'unknown')}")
    return JSONResponse(content={"status": "forwarded"})


# ============ AI Pipeline Functions (using existing handlers) ============

def _sse(data: dict) -> str:
    """Format SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_handler_for_device(device_id: str):
    """Get existing MqttConnectionHandler for device."""
    try:
        from app.services.mqtt_connection_handler import get_mqtt_connection_manager
        manager = get_mqtt_connection_manager()
        if manager is None:
            logger.warning("[go-bridge] MqttConnectionManager not available")
            return None
        
        # Try device_id lookup first
        handler = manager.get_connection_by_device(device_id)
        if handler:
            logger.info(f"[go-bridge] Found handler by device_id {device_id}")
            return handler
        
        # Try MAC address lookup
        handler = manager.get_connection_by_mac(device_id)
        if handler:
            logger.info(f"[go-bridge] Found handler by mac {device_id}")
            return handler
        
        # Fallback: direct session_id lookup (in case device_id IS a session_id)
        handler = manager.get_connection(device_id)
        if handler:
            logger.info(f"[go-bridge] Found handler by session_id {device_id}")
            return handler
        
        logger.warning(f"[go-bridge] No handler found for device {device_id}, "
                       f"connections={len(manager._connections)}, "
                       f"device_sessions={list(manager._device_sessions.keys()) if hasattr(manager, '_device_sessions') else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"[go-bridge] Error getting handler: {e}", exc_info=True)
        return None


async def _run_asr_pipeline(device_id: str, opus_packets: list) -> str:
    """
    Run ASR using existing handler's ASR module.
    
    Args:
        device_id: Device MAC/ID
        opus_packets: List[bytes] — individual Opus frames already decoded from base64.
                      speech_to_text expects List[bytes] for proper Opus decoding.
    Returns:
        Recognized text string, or empty string if nothing recognized.
    """
    try:
        handler = _get_handler_for_device(device_id)
        if handler and handler.asr:
            # speech_to_text expects opus_data as List[bytes] (list of opus packets)
            result = await handler.asr.speech_to_text(opus_packets, handler.session_id or device_id, "opus")
            logger.info(f"[go-bridge] ASR result: {result}")
            # result is a tuple (text, filepath) — extract text
            if isinstance(result, tuple):
                return result[0] or ""
            return str(result) if result else ""
        
        # Fallback: create ASR from config.yml directly
        logger.info(f"[go-bridge] No handler for {device_id}, trying config.yml fallback")
        import yaml
        import os
        
        # Try multiple known config locations
        config_paths = [
            os.path.join(os.path.dirname(__file__), "../../data/.config.yml"),
            os.path.join(os.path.dirname(__file__), "../../ai/config/config.yml"),
            "/app/src/app/data/.config.yml",
            "/app/src/app/ai/config/config.yml",
        ]
        
        config = None
        for config_path in config_paths:
            config_path = os.path.normpath(config_path)
            if os.path.exists(config_path):
                logger.info(f"[go-bridge] Loading config from {config_path}")
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                break
        
        if config:
            from app.ai.module_factory import initialize_asr
            asr_provider = initialize_asr(config)
            if asr_provider:
                result = await asr_provider.speech_to_text(opus_packets, str(uuid.uuid4()), "opus")
                logger.info(f"[go-bridge] ASR result (fallback): {result}")
                if isinstance(result, tuple):
                    return result[0] or ""
                return str(result) if result else ""
            else:
                logger.warning(f"[go-bridge] initialize_asr returned None. selected_module={config.get('selected_module', {})}")
        else:
            logger.warning(f"[go-bridge] No config.yml found at any location")
        
        logger.warning(f"[go-bridge] No ASR provider available for device {device_id}")
        return ""
        
    except Exception as e:
        logger.error(f"[go-bridge] ASR pipeline error: {e}", exc_info=True)
        return ""


async def _run_llm_pipeline(device_id: str, agent_id: str, text: str):
    """
    Run LLM streaming using existing handler's LLM module.
    
    IMPORTANT: handler.llm.response(session_id, dialogue) is a SYNC generator
    that yields text tokens. It is NOT async. We run it in a thread executor
    and bridge results to async using a Queue.
    """
    try:
        handler = _get_handler_for_device(device_id)
        if handler and handler.llm:
            system_prompt = handler.prompt if hasattr(handler, 'prompt') else "Bạn là trợ lý AI. Trả lời ngắn gọn bằng tiếng Việt."
            
            dialogue = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ]
            
            # LLM.response() is a SYNC generator — run in thread
            result_queue = asyncio.Queue()
            
            def _run_sync_llm():
                try:
                    session_id = handler.session_id if hasattr(handler, 'session_id') else device_id
                    for chunk in handler.llm.response(session_id, dialogue):
                        if chunk:
                            result_queue.put_nowait(chunk)
                except Exception as e:
                    logger.error(f"[go-bridge] LLM sync error: {e}", exc_info=True)
                finally:
                    result_queue.put_nowait(None)  # Sentinel
            
            # Run sync generator in thread
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, _run_sync_llm)
            
            full_text = ""
            while True:
                chunk = await result_queue.get()
                if chunk is None:
                    break
                full_text += chunk
                yield chunk
            
            if not full_text:
                yield "Xin lỗi, tôi không thể trả lời lúc này."
            return
        
        yield f"Xin lỗi, hệ thống chưa sẵn sàng cho thiết bị {device_id}."
            
    except Exception as e:
        logger.error(f"[go-bridge] LLM pipeline error: {e}", exc_info=True)
        yield f"Lỗi hệ thống: {str(e)[:100]}"


async def _run_tts_pipeline(device_id: str, agent_id: str, text: str):
    """Run TTS and yield base64-encoded opus audio chunks."""
    try:
        handler = _get_handler_for_device(device_id)
        if handler and handler.tts:
            # Correct method name: text_to_speak(text, output_file)
            # output_file=None means return bytes directly
            audio_data = await handler.tts.text_to_speak(text, None)
            if audio_data:
                chunk_size = 4096
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i+chunk_size]
                    yield base64.b64encode(chunk).decode('ascii')
            return
        
        logger.warning(f"[go-bridge] No TTS provider for device {device_id}")
            
    except Exception as e:
        logger.error(f"[go-bridge] TTS pipeline error: {e}", exc_info=True)

