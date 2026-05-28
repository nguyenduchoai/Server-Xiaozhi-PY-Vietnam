"""Trình quản lý công cụ hợp nhất"""
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Any
from app.core.logger import setup_logging
from app.ai.plugins_func.register import Action, ActionResponse
from app.ai.utils.serializers import format_action_response
from .base import ToolType, ToolDefinition, ToolExecutor

if TYPE_CHECKING:
    from app.ai.connection import ConnectionHandler  # chỉ dùng cho hint, không chạy lúc runtime


class ToolManager:
    """Quản lý tập trung cho tất cả loại công cụ"""

    def __init__(self, conn: ConnectionHandler):
        self.conn = conn
        self.logger = setup_logging()
        self.executors: Dict[ToolType, ToolExecutor] = {}
        self._cached_tools: Optional[Dict[str, ToolDefinition]] = None
        self._cached_function_descriptions: Optional[List[Dict[str, Any]]] = None

    def register_executor(self, tool_type: ToolType, executor: ToolExecutor):
        """Đăng ký bộ thực thi công cụ"""
        self.executors[tool_type] = executor
        self._invalidate_cache()
        self.logger.debug(f"Đăng ký bộ thực thi cho loại công cụ: {tool_type.value}")

    def _invalidate_cache(self):
        """Vô hiệu hóa bộ nhớ đệm"""
        self._cached_tools = None
        self._cached_function_descriptions = None

    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        """Lấy toàn bộ định nghĩa công cụ"""
        if self._cached_tools is not None:
            return self._cached_tools

        all_tools = {}
        for tool_type, executor in self.executors.items():
            try:
                tools = executor.get_tools()
                for name, definition in tools.items():
                    if name in all_tools:
                        self.logger.warning(f"Xung đột tên công cụ: {name}")
                    all_tools[name] = definition
            except Exception as e:
                self.logger.error(f"Lỗi khi lấy công cụ loại {tool_type.value}: {e}")

        self._cached_tools = all_tools
        return all_tools

    def get_function_descriptions(self) -> List[Dict[str, Any]]:
        """Lấy mô tả hàm của tất cả công cụ (định dạng OpenAI)"""
        if self._cached_function_descriptions is not None:
            return self._cached_function_descriptions

        descriptions = []
        tools = self.get_all_tools()
        for tool_definition in tools.values():
            descriptions.append(tool_definition.description)

        self._cached_function_descriptions = descriptions
        return descriptions

    def has_tool(self, tool_name: str) -> bool:
        """Kiểm tra sự tồn tại của công cụ"""
        tools = self.get_all_tools()
        normalized_name = self._normalize_tool_name(tool_name, tools)
        return normalized_name in tools

    def get_tool_type(self, tool_name: str) -> Optional[ToolType]:
        """Lấy loại của công cụ"""
        tools = self.get_all_tools()
        normalized_name = self._normalize_tool_name(tool_name, tools)
        tool_def = tools.get(normalized_name)
        return tool_def.tool_type if tool_def else None

    def _normalize_tool_name(self, tool_name: str, tools: Dict[str, ToolDefinition]) -> str:
        """
        Normalize tool name to handle LLM variations.
        E.g., 'streammusicurl' -> 'stream_music_url'
        """
        # 1. Direct match
        if tool_name in tools:
            return tool_name
        
        # 2. Try lowercase match
        lower_name = tool_name.lower()
        for registered_name in tools.keys():
            if registered_name.lower() == lower_name:
                self.logger.debug(f"Tool name normalized: {tool_name} -> {registered_name}")
                return registered_name
        
        # 3. Try without underscores match
        # E.g., 'streammusicurl' matches 'stream_music_url'
        for registered_name in tools.keys():
            if registered_name.replace("_", "").lower() == lower_name:
                self.logger.debug(f"Tool name normalized (no underscore): {tool_name} -> {registered_name}")
                return registered_name
        
        # 4. Common alias mapping
        aliases = {
            "playsearchresult": "play_search_result",
            "searchmusic": "search_music",
            "stopmusic": "stop_music",
            "searchyoutube": "search_youtube",
            "playyoutube": "play_youtube",
            "searchzingmp3": "search_zingmp3",
            "playzingmp3": "play_zingmp3",
            "streammusicurl": "stream_music_url",
        }
        if lower_name in aliases:
            alias_target = aliases[lower_name]
            if alias_target in tools:
                self.logger.debug(f"Tool name aliased: {tool_name} -> {alias_target}")
                return alias_target
        
        # 5. No match found, return original
        return tool_name

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Thực thi lời gọi công cụ"""
        try:
            # Xác định loại công cụ
            tool_type = self.get_tool_type(tool_name)
            if not tool_type:
                return ActionResponse(
                    action=Action.NOTFOUND,
                    response=f"Công cụ {tool_name} không tồn tại",
                )

            # Lấy bộ thực thi tương ứng
            executor = self.executors.get(tool_type)
            if not executor:
                return ActionResponse(
                    action=Action.ERROR,
                    response=f"Chưa đăng ký bộ thực thi cho loại công cụ {tool_type.value}",
                )

            # Thực thi công cụ
            self.logger.debug(f"Thực thi công cụ: {tool_name}, tham số: {arguments}")
            result = await executor.execute(self.conn, tool_name, arguments)
            self.logger.debug(
                f"Kết quả thực thi công cụ: {format_action_response(result)}"
            )
            
            # Fallback: Nếu self_music_play_song fail, tự động tìm nhạc online VÀ PHÁT LUÔN
            if tool_name == "self_music_play_song" and result:
                # Kiểm tra nếu result chứa thông báo lỗi
                result_str = str(result.result or result.response or "")
                if "fail" in result_str.lower() or "error" in result_str.lower() or "không" in result_str.lower():
                    self.logger.debug(f"[Fallback] self_music_play_song failed, trying online sources...")
                    song_name = arguments.get("song_name", "")
                    query = song_name if song_name and song_name != "random" else "nhạc hot"
                    
                    # === TÌM NHACCUATUI TRƯỚC ===
                    from app.ai.plugins_func.functions.music.search_music import _search_nhaccuatui_sync
                    songs = _search_nhaccuatui_sync(query, limit=3)
                    
                    # Nếu không tìm thấy, thử lại với query đơn giản hơn
                    if not songs or not isinstance(songs, list) or len(songs) == 0:
                        simple_query = query.replace("MTP", "").replace("MT", "").strip()
                        if simple_query != query:
                            self.logger.debug(f"[Fallback] Retrying NhacCuaTui with: {simple_query}")
                            songs = _search_nhaccuatui_sync(simple_query, limit=3)
                    
                    # Nếu NhacCuaTui có kết quả, phát luôn
                    if songs and isinstance(songs, list) and len(songs) > 0:
                        first_song = songs[0]
                        stream_url = first_song.get("stream_url")
                        song_title = first_song.get("name", "")
                        
                        if stream_url:
                            self.logger.debug(f"[Fallback] NhacCuaTui found: {song_title}, auto-playing...")
                            play_result = await self.execute_tool("stream_music_url", {
                                "url": stream_url,
                                "song_name": song_title
                            })
                            return play_result
                    
                    # === NẾU NHACCUATUI KHÔNG CÓ, TÌM YOUTUBE ===
                    self.logger.debug(f"[Fallback] NhacCuaTui not found, trying YouTube...")
                    try:
                        from pytubefix import Search
                        yt_search = Search(query)
                        yt_results = list(yt_search.videos[:3])
                        
                        if yt_results:
                            first_video = yt_results[0]
                            video_id = first_video.video_id
                            video_title = first_video.title
                            
                            self.logger.debug(f"[Fallback] YouTube found: {video_title}, auto-playing...")
                            play_result = await self.execute_tool("play_youtube", {
                                "video_id": video_id,
                                "title": video_title
                            })
                            return play_result
                        else:
                            self.logger.debug("[Fallback] YouTube also not found")
                    except Exception as yt_err:
                        self.logger.debug(f"[Fallback] YouTube search error: {yt_err}")
                    
                    # === FALLBACK CUỐI: TÌM "NHẠC TRẺ" ===
                    self.logger.debug(f"[Fallback] Last resort: searching 'nhạc trẻ'...")
                    songs = _search_nhaccuatui_sync("nhạc trẻ", limit=3)
                    if songs and isinstance(songs, list) and len(songs) > 0:
                        first_song = songs[0]
                        stream_url = first_song.get("stream_url")
                        song_title = first_song.get("name", "")
                        if stream_url:
                            self.logger.debug(f"[Fallback] Playing default: {song_title}")
                            play_result = await self.execute_tool("stream_music_url", {
                                "url": stream_url,
                                "song_name": song_title
                            })
                            return play_result
            
            return result

        except Exception as e:
            self.logger.error(f"Lỗi khi thực thi công cụ {tool_name}: {e}")
            return ActionResponse(action=Action.ERROR, response=str(e))

    def get_supported_tool_names(self) -> List[str]:
        """Lấy danh sách tên công cụ được hỗ trợ"""
        tools = self.get_all_tools()
        return list(tools.keys())

    def refresh_tools(self):
        """Làm mới bộ nhớ đệm công cụ"""
        self._invalidate_cache()
        self.logger.debug("Bộ nhớ đệm công cụ đã được làm mới")

    def get_tool_statistics(self) -> Dict[str, int]:
        """Lấy thống kê số lượng công cụ"""
        stats = {}
        for tool_type, executor in self.executors.items():
            try:
                tools = executor.get_tools()
                stats[tool_type.value] = len(tools)
            except Exception as e:
                self.logger.error(
                    f"Lỗi khi lấy thống kê công cụ {tool_type.value}: {e}"
                )
                stats[tool_type.value] = 0
        return stats
