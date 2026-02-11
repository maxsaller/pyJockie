from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrackInfo:
    name: str = ""
    artists: str = ""
    album: str = ""
    cover_url: str = ""
    duration_ms: int = 0


@dataclass
class AppState:
    is_playing: bool = False
    is_streaming: bool = False
    current_track: Optional[TrackInfo] = None
    position_ms: int = 0
    volume: int = 100
    shuffle: bool = False
    repeat: str = "off"

    voice_channel_id: Optional[int] = None
    guild_id: Optional[int] = None


state = AppState()
