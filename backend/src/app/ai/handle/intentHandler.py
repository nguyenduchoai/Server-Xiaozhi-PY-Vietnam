from __future__ import annotations
from typing import TYPE_CHECKING
import json
import uuid
import asyncio
from app.ai.utils.dialogue import Message
from app.ai.providers.tts.dto.dto import ContentType
from app.ai.handle.helloHandle import checkWakeupWords
from app.ai.plugins_func.register import Action, ActionResponse
from app.ai.handle.sendAudioHandle import send_stt_message
from app.ai.utils.util import remove_punctuation_and_length
from app.ai.providers.tts.dto.dto import TTSMessageDTO, SentenceType

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler  # chỉ dùng cho hint, không chạy lúc runtime


TAG = __name__


async def handle_user_intent(conn: ConnectionHandler, text: str):
    # Tiền xử lý văn bản đầu vào, xử lý khả năng ở định dạng JSON
    try:
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                text = parsed_data["content"]  # Trích xuất content để phân tích ý định
                conn.current_speaker = parsed_data.get(
                    "speaker"
                )  # Giữ lại thông tin người nói
    except (json.JSONDecodeError, TypeError):
        pass

    # Kiểm tra xem có lệnh thoát rõ ràng hay không
    _, filtered_text = remove_punctuation_and_length(text)
    
    # QUAN TRỌNG: Kiểm tra wake word TRƯỚC KHI filter nhiễu
    # Để wake word ngắn (như "hey", "lyly") không bị bỏ qua
    if await checkWakeupWords(conn, filtered_text):
        return True

    # Kiểm tra lệnh thoát trước
    if await check_direct_exit(conn, text):
        return True
    
    # Lọc bỏ các câu quá ngắn (nhiễu môi trường) - ít hơn 2 ký tự (giảm từ 3)
    if len(filtered_text) < 2:
        conn.logger.bind(tag=TAG).debug(f"Bỏ qua text quá ngắn (nhiễu): '{text}'")
        return True  # Không xử lý, không phản hồi
    
    # Lọc bỏ các từ đơn vô nghĩa và các từ ngắn phổ biến (nhiễu môi trường)
    # CHÚ Ý: Chỉ lọc các âm thanh thực sự vô nghĩa, không lọc các từ có thể có ý nghĩa
    noise_words = {
        # Chỉ các âm thanh vô nghĩa thực sự
        "ơ", "ớ", "à", "ừ", "ử", "ể", "ỡ", "ờ", "ù", "ì", "ọ", "ụ", "ậ", "ồ", "ô", "ê",
        # Các từ đệm không có ý nghĩa
        "nhỉ", "hả", "hử", "nè"
    }
    if filtered_text.lower() in noise_words:
        conn.logger.bind(tag=TAG).debug(f"Bỏ qua từ nhiễu: '{text}'")
        return True  # Không xử lý, không phản hồi

    # 🚀 Voice Shortcuts - Quick commands without LLM
    shortcut_handled = await handle_voice_shortcuts(conn, filtered_text.lower())
    if shortcut_handled:
        return True

    if conn.intent_type == "function_call":
        # Sử dụng phương thức trò chuyện hỗ trợ function calling, không phân tích ý định nữa
        return False
    # Dùng LLM để phân tích ý định
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        return False
    # Khởi tạo sentence_id khi bắt đầu phiên
    conn.sentence_id = str(uuid.uuid4().hex)
    # Xử lý các loại ý định
    return await process_intent_result(conn, intent_result, text)


# 🚀 Voice Shortcuts - Quick commands without LLM
VOICE_SHORTCUTS = {
    # Stop commands
    "dừng": {"action": "stop", "response": "Đã dừng"},
    "dừng lại": {"action": "stop", "response": "Đã dừng"},
    "ngừng": {"action": "stop", "response": "Đã dừng"},
    "tắt": {"action": "stop", "response": "Đã tắt"},
    "im đi": {"action": "stop", "response": None},  # Silent stop
    
    # Volume commands
    "to hơn": {"action": "volume_up", "response": "Đã tăng âm lượng"},
    "lớn hơn": {"action": "volume_up", "response": "Đã tăng âm lượng"},
    "tăng âm lượng": {"action": "volume_up", "response": "Đã tăng âm lượng"},
    "nhỏ hơn": {"action": "volume_down", "response": "Đã giảm âm lượng"},
    "bé hơn": {"action": "volume_down", "response": "Đã giảm âm lượng"},
    "giảm âm lượng": {"action": "volume_down", "response": "Đã giảm âm lượng"},
    
    # Quick responses
    "cảm ơn": {"action": "response", "response": "Không có gì ạ!"},
    "cám ơn": {"action": "response", "response": "Không có gì ạ!"},
    "ok": {"action": "response", "response": "Vâng ạ"},
    "được rồi": {"action": "response", "response": "Vâng ạ"},
    
    # Status
    "bạn còn đó không": {"action": "response", "response": "Tôi đang lắng nghe đây ạ"},
    "bạn ơi": {"action": "response", "response": "Tôi nghe đây ạ"},
}


async def handle_voice_shortcuts(conn: ConnectionHandler, text: str) -> bool:
    """
    Handle quick voice commands without LLM.
    Returns True if shortcut was handled, False otherwise.
    """
    # Normalize text - strip whitespace
    text = text.strip()
    if not text:
        return False
    
    # Check for exact match first
    if text in VOICE_SHORTCUTS:
        shortcut = VOICE_SHORTCUTS[text]
        conn.logger.bind(tag=TAG).info(f"🚀 Voice Shortcut exact match: '{text}'")
        return await execute_shortcut(conn, shortcut, text)
    
    # Check for partial match (command contains the shortcut)
    for keyword, shortcut in VOICE_SHORTCUTS.items():
        if keyword in text and len(text) < len(keyword) + 15:  # Increased tolerance
            conn.logger.bind(tag=TAG).info(f"🚀 Voice Shortcut partial match: '{text}' contains '{keyword}'")
            return await execute_shortcut(conn, shortcut, text)
    
    return False


async def execute_shortcut(conn: ConnectionHandler, shortcut: dict, original_text: str) -> bool:
    """Execute a voice shortcut action."""
    action = shortcut.get("action")
    response = shortcut.get("response")
    
    conn.logger.bind(tag=TAG).info(f"🚀 Voice Shortcut: '{original_text}' -> {action}")
    
    if action == "stop":
        # Stop current TTS/audio playback
        conn.client_abort = True
        if response:
            await quick_speak(conn, response)
        return True
    
    elif action == "volume_up":
        # Send volume up command to device via MCP
        await send_device_command(conn, "volume", {"direction": "up", "amount": 10})
        if response:
            await quick_speak(conn, response)
        return True
    
    elif action == "volume_down":
        # Send volume down command to device via MCP
        await send_device_command(conn, "volume", {"direction": "down", "amount": 10})
        if response:
            await quick_speak(conn, response)
        return True
    
    elif action == "response":
        # Quick response without LLM
        if response:
            await quick_speak(conn, response)
        return True
    
    return False


async def quick_speak(conn: ConnectionHandler, text: str):
    """Quick TTS response for shortcuts."""
    from app.ai.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
    
    conn.sentence_id = str(uuid.uuid4().hex)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )


async def send_device_command(conn: ConnectionHandler, command: str, params: dict):
    """Send command to device via WebSocket."""
    try:
        import json
        message = {
            "type": "device_control",
            "command": command,
            "params": params
        }
        await conn.websocket.send(json.dumps(message))
        conn.logger.bind(tag=TAG).debug(f"Sent device command: {command}")
    except Exception as e:
        conn.logger.bind(tag=TAG).warning(f"Failed to send device command: {e}")

async def check_direct_exit(conn: ConnectionHandler, text: str):
    """Kiểm tra xem có lệnh thoát rõ ràng hay không"""
    _, normalized_text = remove_punctuation_and_length(text)
    normalized_text = normalized_text.lower()
    if not normalized_text:
        return False

    for cmd in getattr(conn, "cmd_exit", []):
        _, normalized_cmd = remove_punctuation_and_length(cmd)
        normalized_cmd = normalized_cmd.lower()
        if not normalized_cmd:
            continue
        if normalized_text == normalized_cmd:
            conn.logger.bind(tag=TAG).info(f"Phát hiện lệnh thoát rõ ràng: {text}")
            await send_stt_message(conn, text)
            conn.close_after_chat = True
            conn.client_abort = False
            conn.submit_blocking_task(conn._run_chat_turn, text)
            return True
    return False


async def analyze_intent_with_llm(conn: ConnectionHandler, text: str):
    """Dùng LLM để phân tích ý định của người dùng"""
    if not hasattr(conn, "intent") or not conn.intent:
        conn.logger.bind(tag=TAG).warning("Dịch vụ nhận dạng ý định chưa được khởi tạo")
        return None

    # Lịch sử hội thoại
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        return intent_result
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Nhận dạng ý định thất bại: {str(e)}")

    return None


async def process_intent_result(conn: ConnectionHandler, intent_result, original_text: str):
    """Xử lý kết quả nhận dạng ý định"""
    try:
        # Cố gắng phân tích kết quả thành JSON
        intent_data = json.loads(intent_result)

        # Kiểm tra xem có function_call hay không
        if "function_call" in intent_data:
            # Nhận function_call trực tiếp từ kết quả nhận dạng ý định
            conn.logger.bind(tag=TAG).debug(
                f"Phát hiện kết quả ý định dạng function_call: {intent_data['function_call']['name']}"
            )
            function_name = intent_data["function_call"]["name"]
            if function_name == "continue_chat":
                return False

            if function_name == "result_for_context":
                await send_stt_message(conn, original_text)
                conn.client_abort = False

                def process_context_result():
                    conn.dialogue.put(Message(role="user", content=original_text))

                    from app.ai.utils.current_time import get_current_time_info

                    current_time, today_date, today_weekday = (
                        get_current_time_info()
                    )

                    # Xây dựng gợi ý cơ bản kèm theo ngữ cảnh
                    context_prompt = f"""Thời gian hiện tại: {current_time}
                                        Ngày hôm nay: {today_date} ({today_weekday})
                                        Vui lòng dựa trên thông tin trên để trả lời câu hỏi của người dùng: {original_text}"""

                    response = conn.intent.replyResult(context_prompt, original_text)
                    speak_txt(conn, response)

                conn.submit_blocking_task(process_context_result)
                return True

            function_args = {}
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
                if function_args is None:
                    function_args = {}
            # Đảm bảo tham số là chuỗi JSON
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)
            conn.client_abort = False

            # Sử dụng executor để thực thi lời gọi hàm và xử lý kết quả
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))

                # Sử dụng bộ xử lý công cụ thống nhất để xử lý mọi lời gọi công cụ
                try:
                    result = asyncio.run_coroutine_threadsafe(
                        conn.func_handler.handle_llm_function_call(
                            conn, function_call_data
                        ),
                        conn.loop,
                    ).result(timeout=30)
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"Gọi công cụ thất bại: {e}")
                    result = ActionResponse(
                        action=Action.ERROR, result=str(e), response=str(e)
                    )

                if result:
                    if (
                        result.action == Action.RESPONSE
                    ):  # Phản hồi trực tiếp tới phía client
                        text = result.response
                        if text is not None:
                            speak_txt(conn, text)
                    elif (
                        result.action == Action.REQLLM
                    ):  # Sau khi gọi hàm thì yêu cầu LLM tạo câu trả lời
                        text = result.result
                        conn.dialogue.put(Message(role="tool", content=text))
                        llm_result = conn.intent.replyResult(text, original_text)
                        if llm_result is None:
                            llm_result = text
                        speak_txt(conn, llm_result)
                    elif (
                        result.action == Action.NOTFOUND
                        or result.action == Action.ERROR
                    ):
                        # Ưu tiên result, nếu không có thì dùng response
                        text = result.result or result.response
                        if text is not None:
                            speak_txt(conn, text)
                        else:
                            # Fallback message
                            speak_txt(conn, "Xin lỗi, tôi không thể thực hiện yêu cầu này.")
                    elif result.action == Action.NONE:
                        # Action.NONE = không làm gì cả, không TTS, không listen
                        # Dùng cho music streaming - nhạc đang phát background
                        pass
                    elif function_name not in ("play_music", "stream_music_url", "play_youtube"):
                        # For backward compatibility with original code
                        # Bỏ qua các music tools để không trigger TTS/listen cycle
                        # Lấy chỉ số văn bản mới nhất
                        text = result.response
                        if text is None:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)

            # Đưa việc thực thi hàm vào thread pool
            conn.submit_blocking_task(process_function_call)
            return True
        return False
    except json.JSONDecodeError as e:
        conn.logger.bind(tag=TAG).error(f"Lỗi khi xử lý kết quả ý định: {e}")
        return False


def speak_txt(conn: ConnectionHandler, text: str):
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )
    conn.dialogue.put(Message(role="assistant", content=text))
