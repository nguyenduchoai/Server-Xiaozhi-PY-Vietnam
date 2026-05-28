"""
Tool phát audio từ YouTube video qua FFmpeg streaming.
Sử dụng pytubefix để lấy audio stream URL.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from app.ai.handle.sendAudioHandle import send_stt_message, send_tts_message, sendAudio
from app.ai.providers.audio.ffmpeg_streamer import FFmpegURLStreamer
from app.core.logger import setup_logging

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# Frame duration cho Opus (ms) - phải khớp với FFmpeg config
FRAME_DURATION_MS = 60

play_youtube_function_desc = {
    "type": "function",
    "function": {
        "name": "play_youtube",
        "description": "Phát/mở audio từ video YouTube. Sử dụng sau khi tìm kiếm với search_youtube.",
        "parameters": {
            "type": "object",
            "properties": {
                "video_id": {
                    "type": "string",
                    "description": "Video ID của YouTube (từ kết quả search_youtube)",
                },
                "title": {
                    "type": "string",
                    "description": "Tên video để hiển thị (optional)",
                    "default": "",
                },
            },
            "required": ["video_id"],
        },
    },
}


@register_function("play_youtube", play_youtube_function_desc, ToolType.SYSTEM_CTL)
def play_youtube(conn: ConnectionHandler, video_id: str, title: str = ""):
    """
    Phát audio từ YouTube video.

    Args:
        conn: Connection handler
        video_id: YouTube video ID
        title: Tên video (optional)

    Returns:
        ActionResponse
    """
    try:
        logger.bind(tag=TAG).debug(f"[play_youtube] video_id={video_id}, title={title}")

        # Validate video_id
        if not video_id or len(video_id) < 5:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Video ID không hợp lệ",
                response="Video ID không hợp lệ",
            )

        # Check FFmpeg availability
        if not FFmpegURLStreamer.is_ffmpeg_available():
            logger.bind(tag=TAG).error("[play_youtube] FFmpeg không được cài đặt")
            return ActionResponse(
                action=Action.RESPONSE,
                result="FFmpeg không khả dụng",
                response="Hệ thống chưa sẵn sàng để phát nhạc",
            )

        # Check event loop
        if not conn.loop.is_running():
            logger.bind(tag=TAG).error("[play_youtube] Event loop không chạy")
            return ActionResponse(
                action=Action.RESPONSE,
                result="Hệ thống bận",
                response="Vui lòng thử lại sau",
            )

        logger.bind(tag=TAG).debug("[play_youtube] Creating stream task...")

        # Start streaming task
        task = conn.loop.create_task(_handle_youtube_stream(conn, video_id, title))

        def handle_done(f):
            try:
                f.result()
                logger.bind(tag=TAG).info("[play_youtube] Stream hoàn tất")
            except asyncio.CancelledError:
                logger.bind(tag=TAG).debug("[play_youtube] Stream bị hủy")
            except Exception as e:
                logger.bind(tag=TAG).error(f"[play_youtube] Stream error: {e}", exc_info=True)

        task.add_done_callback(handle_done)

        # Return NONE để không trigger TTS response - nhạc sẽ phát trực tiếp
        return ActionResponse(
            action=Action.NONE,
            result="Đang phát",
            response=None,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(f"[play_youtube] Exception: {e}", exc_info=True)
        return ActionResponse(
            action=Action.ERROR,
            result=str(e),
            response="Có lỗi khi phát YouTube",
        )


async def _handle_youtube_stream(conn: ConnectionHandler, video_id: str, title: str):
    """
    Xử lý streaming audio từ YouTube video.

    Args:
        conn: Connection handler
        video_id: YouTube video ID
        title: Tên video
    """
    logger.bind(tag=TAG).debug(f"[_handle_youtube_stream] Starting for video_id={video_id}")

    streamer = None

    try:
        # Get audio stream URL using pytubefix
        from pytubefix import YouTube

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.bind(tag=TAG).debug(f"[_handle_youtube_stream] Fetching: {video_url}")

        yt = YouTube(video_url)
        audio_stream = yt.streams.filter(only_audio=True).first()

        if not audio_stream:
            logger.bind(tag=TAG).error("[_handle_youtube_stream] No audio stream found")
            await send_stt_message(conn, "Không thể lấy audio từ video này")
            return

        stream_url = audio_stream.url
        display_name = title if title else yt.title

        logger.bind(tag=TAG).debug(
            f"[_handle_youtube_stream] Got audio URL, length={len(stream_url)}"
        )

        # Reset flow control
        conn.reset_audio_flow_control(force=True)

        # Reset music_abort flag khi bắt đầu phát nhạc mới
        conn.music_abort = False

        # Create streamer
        streamer = FFmpegURLStreamer(stream_url, frame_duration_ms=FRAME_DURATION_MS)
        conn.current_streamer = streamer

        # Chờ một lúc để AI nói xong câu thông báo "Đang phát..."
        # Điều này tránh việc âm thanh nhạc và giọng nói đè lên nhau gây giật tiếng
        await asyncio.sleep(1.0)

        # Send TTS start signal - notify client music is starting
        # Gửi tên bài hát để hiển thị trên màn hình
        display_text = f"🎵 {display_name}" if display_name else "🎵 Đang phát nhạc"
        
        # Gửi sentence_start để frontend hiển thị tên bài hát
        await send_tts_message(conn, "sentence_start", display_text)
        # Gửi start signal cho audio player
        await send_tts_message(conn, "start", display_text)
        logger.bind(tag=TAG).debug(f"[_handle_youtube_stream] Sent music-start signal with: {display_text}")

        # Stream audio frames
        frame_count = 0
        total_bytes = 0

        async for opus_frame in streamer.stream_opus_frames():
            # Check music_abort (chỉ dừng khi user yêu cầu stop_music)
            if conn.music_abort:
                logger.bind(tag=TAG).debug(f"[_handle_youtube_stream] Music aborted at frame {frame_count}")
                break
            
            # Check connection closed
            if conn._closing:
                logger.bind(tag=TAG).debug(f"[_handle_youtube_stream] Connection closing at frame {frame_count}")
                break

            await sendAudio(conn, opus_frame, frame_duration=FRAME_DURATION_MS)

            frame_count += 1
            total_bytes += len(opus_frame)

            if frame_count % 500 == 0:
                logger.bind(tag=TAG).debug(
                    f"[_handle_youtube_stream] Progress: {frame_count} frames, {total_bytes} bytes"
                )

        logger.bind(tag=TAG).info(
            f"[_handle_youtube_stream] Completed: {frame_count} frames, {total_bytes} bytes"
        )

    except asyncio.CancelledError:
        logger.bind(tag=TAG).debug("[_handle_youtube_stream] Cancelled")
        raise
    except Exception as e:
        logger.bind(tag=TAG).error(f"[_handle_youtube_stream] Exception: {e}", exc_info=True)
        await send_stt_message(conn, "Có lỗi khi phát video")
    finally:
        # Cleanup
        if streamer:
            await streamer.stop_async()
        conn.current_streamer = None

        if not conn.music_abort:
            await send_tts_message(conn, "stop", None)

        conn.clearSpeakStatus()
        logger.bind(tag=TAG).debug("[_handle_youtube_stream] Cleanup done")

