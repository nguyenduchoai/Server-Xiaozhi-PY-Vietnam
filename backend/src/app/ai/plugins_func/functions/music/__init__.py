"""Music tools: search, stream, stop, YouTube."""

from .stop_music import stop_music
from .search_youtube import search_youtube
from .play_youtube import play_youtube

__all__ = [
    "stop_music",
    "search_youtube",
    "play_youtube",
]

