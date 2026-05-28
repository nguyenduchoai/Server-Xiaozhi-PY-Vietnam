"""
ZingMP3 Music Search & Play Tool - Tìm và phát nhạc Việt từ Zing MP3.

Sử dụng mp3-proxy-musicVN-xiaozhi adapter để:
- Tìm kiếm bài hát theo tên/ca sĩ
- Stream audio qua proxy đã cache
- Hỗ trợ lời bài hát (lyrics)

API Endpoints:
- GET /stream_pcm?song={name}&artist={artist} - Tìm kiếm bài hát
- GET /proxy_audio?id={song_id} - Stream audio
- GET /proxy_lyric?id={song_id} - Lấy lời bài hát
- GET /health - Health check
"""

import os
import httpx

from app.ai.plugins_func.register import (
    Action,
    ActionResponse, 
    ToolType,
    register_function,
)
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()

# ZingMP3 Adapter API URLs from environment variables
ZINGMP3_API_URL = os.getenv("ZINGMP3_API_URL", "http://xiaozhi-adapter:5005")
ZINGMP3_PUBLIC_URL = os.getenv("ZINGMP3_PUBLIC_URL", "")

SEARCH_ZINGMP3_DESC = {
    "type": "function",
    "function": {
        "name": "search_zingmp3",
        "description": (
            "Tìm kiếm bài hát Việt Nam từ Zing MP3. "
            "Hỗ trợ tìm theo tên bài hát và/hoặc tên ca sĩ. "
            "Ví dụ: 'tìm bài Sóng Gió', 'bật nhạc Sơn Tùng MTP', "
            "'phát Em của ngày hôm qua', 'tìm nhạc của Hoàng Thùy Linh'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "song": {
                    "type": "string",
                    "description": "Tên bài hát cần tìm (bắt buộc)",
                },
                "artist": {
                    "type": "string",
                    "description": "Tên ca sĩ (tùy chọn, giúp tìm chính xác hơn)",
                },
            },
            "required": ["song"],
        },
    },
}


PLAY_ZINGMP3_DESC = {
    "type": "function", 
    "function": {
        "name": "play_zingmp3",
        "description": (
            "Phát bài hát từ Zing MP3 theo song_id đã tìm được. "
            "Sử dụng sau khi đã search_zingmp3 để lấy song_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "song_id": {
                    "type": "string",
                    "description": "ID của bài hát từ kết quả tìm kiếm",
                },
            },
            "required": ["song_id"],
        },
    },
}


@register_function(
    "search_zingmp3",
    SEARCH_ZINGMP3_DESC,
    ToolType.SYSTEM_CTL,
)
async def search_zingmp3(
    conn=None,
    song: str = "",
    artist: str = "",
    **kwargs,
) -> ActionResponse:
    """
    Tìm kiếm bài hát từ Zing MP3.
    
    Args:
        conn: Connection context
        song: Tên bài hát cần tìm
        artist: Tên ca sĩ (optional)
    
    Returns:
        ActionResponse với kết quả tìm kiếm và URL phát nhạc
    """
    if not song or not song.strip():
        return ActionResponse(
            action=Action.REQLLM,
            result="Vui lòng cho biết tên bài hát cần tìm.",
        )
    
    logger.bind(tag=TAG).info(f"Searching ZingMP3: song='{song}', artist='{artist}'")
    
    try:
        # Build search URL
        params = {"song": song}
        if artist:
            params["artist"] = artist
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{ZINGMP3_API_URL}/stream_pcm",
                params=params,
            )
            
            if response.status_code != 200:
                logger.bind(tag=TAG).warning(f"ZingMP3 API error: {response.status_code}")
                return ActionResponse(
                    action=Action.REQLLM,
                    result=f"Không thể tìm kiếm bài hát. Vui lòng thử lại sau.",
                )
            
            data = response.json()
            
            if not data or not data.get("songs"):
                return ActionResponse(
                    action=Action.REQLLM,
                    result=f"Không tìm thấy bài hát '{song}'" + (f" của {artist}" if artist else ""),
                )
            
            # Format results
            songs = data.get("songs", [])
            count = data.get("count", len(songs))
            
            result_lines = [f"🎵 Tìm thấy {count} bài hát:\n"]
            
            for i, s in enumerate(songs[:5], 1):  # Max 5 results
                title = s.get("title", "Unknown")
                artist_name = s.get("artist", "Unknown")
                duration = s.get("duration", 0)
                
                # Extract song_id: prefer direct 'id' field, fallback to URL parsing
                song_id = s.get("id", "")
                if not song_id:
                    audio_url = s.get("audio_url", "")
                    if "id=" in audio_url:
                        song_id = audio_url.split("id=")[-1].split("&")[0]
                    else:
                        song_id = audio_url.replace("/proxy_audio?id=", "")
                
                # Format duration
                mins = duration // 60
                secs = duration % 60
                duration_str = f"{mins}:{secs:02d}"
                
                result_lines.append(
                    f"{i}. **{title}** - {artist_name} ({duration_str})\n"
                    f"   🎧 ID: `{song_id}`"
                )
            
            result_lines.append("\n💡 Để phát nhạc, hãy nói 'phát bài số X' hoặc cho biết bài nào bạn muốn nghe.")
            
            return ActionResponse(
                action=Action.REQLLM,
                result="\n".join(result_lines),
            )
            
    except httpx.TimeoutException:
        logger.bind(tag=TAG).error("ZingMP3 API timeout")
        return ActionResponse(
            action=Action.REQLLM,
            result="Kết nối đến dịch vụ nhạc bị timeout. Vui lòng thử lại.",
        )
    except Exception as e:
        logger.bind(tag=TAG).exception(f"Error searching ZingMP3: {e}")
        return ActionResponse(
            action=Action.REQLLM,
            result="Đã xảy ra lỗi khi tìm kiếm nhạc.",
        )


@register_function(
    "play_zingmp3",
    PLAY_ZINGMP3_DESC,
    ToolType.SYSTEM_CTL,
)
async def play_zingmp3(
    conn=None,
    song_id: str = "",
    **kwargs,
) -> ActionResponse:
    """
    Phát bài hát từ Zing MP3 qua audio URL.
    
    Args:
        conn: Connection context  
        song_id: ID của bài hát từ kết quả search
    
    Returns:
        ActionResponse với URL audio để phát
    """
    if not song_id or not song_id.strip():
        return ActionResponse(
            action=Action.REQLLM,
            result="Vui lòng cung cấp ID bài hát. Hãy tìm kiếm trước bằng search_zingmp3.",
        )
    
    logger.bind(tag=TAG).info(f"Playing ZingMP3 song: {song_id}")
    
    try:
        # Build audio URL (public URL for device access)
        audio_url = f"{ZINGMP3_PUBLIC_URL}/proxy_audio?id={song_id}"
        lyric_url = f"{ZINGMP3_PUBLIC_URL}/proxy_lyric?id={song_id}"
        
        # Verify song exists by checking health/cache
        async with httpx.AsyncClient(timeout=10.0) as client:
            health = await client.get(f"{ZINGMP3_API_URL}/health")
            if health.status_code == 200:
                cache_data = health.json()
                cached_songs = cache_data.get("cached_songs", [])
                
                if song_id not in cached_songs:
                    logger.bind(tag=TAG).debug(f"Song {song_id} not in cache, will be downloaded on demand")
        
        # Return music action
        return ActionResponse(
            action=Action.MUSIC,
            result=f"🎵 Đang phát nhạc...\n\n🔗 URL: {audio_url}",
            response={
                "url": audio_url,
                "lyric_url": lyric_url,
                "song_id": song_id,
                "source": "zingmp3",
            }
        )
        
    except Exception as e:
        logger.bind(tag=TAG).exception(f"Error playing ZingMP3: {e}")
        return ActionResponse(
            action=Action.REQLLM,
            result="Đã xảy ra lỗi khi phát nhạc.",
        )
