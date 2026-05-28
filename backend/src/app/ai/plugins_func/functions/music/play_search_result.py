"""
Tool phát bài hát từ kết quả tìm kiếm trước đó theo số thứ tự.

Khi user nói "bài số 1", "phát bài 2", tool này sẽ lấy URL từ
conn.last_search_results và gọi stream_music_url.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from app.core.logger import setup_logging

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

play_search_result_desc = {
    "type": "function",
    "function": {
        "name": "play_search_result",
        "description": (
            "Phát bài hát theo số thứ tự từ kết quả tìm kiếm trước đó. "
            "Dùng khi người dùng chọn bài sau khi đã tìm kiếm, ví dụ: "
            "'bài số 1', 'phát bài 2', 'nghe bài đầu tiên', 'bài thứ 3'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "description": "Số thứ tự bài hát (1, 2, 3...)",
                },
            },
            "required": ["index"],
        },
    },
}


@register_function("play_search_result", play_search_result_desc, ToolType.SYSTEM_CTL)
def play_search_result(conn: ConnectionHandler, index: int):
    """
    Phát bài hát theo số thứ tự từ kết quả tìm kiếm đã lưu.

    Args:
        conn: Connection handler (chứa last_search_results)
        index: Số thứ tự bài hát (1-based)

    Returns:
        ActionResponse
    """
    try:
        logger.bind(tag=TAG).debug(f"[play_search_result] index={index}")

        # Kiểm tra có kết quả tìm kiếm không
        if not hasattr(conn, 'last_search_results') or not conn.last_search_results:
            logger.bind(tag=TAG).debug("[play_search_result] No search results found")
            return ActionResponse(
                action=Action.RESPONSE,
                result="Chưa có kết quả tìm kiếm",
                response="Bạn chưa tìm kiếm bài hát nào. Hãy nói 'tìm nhạc' trước nhé!",
            )

        results = conn.last_search_results
        
        # Validate index (1-based)
        if index < 1 or index > len(results):
            logger.bind(tag=TAG).debug(f"[play_search_result] Invalid index: {index}, max={len(results)}")
            return ActionResponse(
                action=Action.RESPONSE,
                result=f"Số không hợp lệ",
                response=f"Chỉ có {len(results)} bài hát trong danh sách. Hãy chọn từ 1 đến {len(results)}.",
            )

        # Lấy bài hát được chọn
        song = results[index - 1]
        song_name = song.get("name", "")
        artist = song.get("artist_name", "")
        stream_url = song.get("stream_url", "")

        if not stream_url:
            logger.bind(tag=TAG).error(f"[play_search_result] No stream URL for song: {song_name}")
            return ActionResponse(
                action=Action.RESPONSE,
                result="Không có URL",
                response=f"Không thể phát bài '{song_name}'. Hãy thử bài khác.",
            )

        logger.bind(tag=TAG).info(f"[play_search_result] Playing: {song_name} - {artist}")

        # Import và gọi stream_music_url
        from app.ai.plugins_func.functions.music.stream_music_url import stream_music_url
        
        display_name = f"{song_name} - {artist}" if artist else song_name
        return stream_music_url(conn, url=stream_url, song_name=display_name)

    except Exception as e:
        logger.bind(tag=TAG).error(f"[play_search_result] Exception: {e}")
        return ActionResponse(
            action=Action.ERROR,
            result=str(e),
            response="Có lỗi khi phát nhạc",
        )
