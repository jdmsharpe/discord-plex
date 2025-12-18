from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MediaType(Enum):
    MOVIE = "movie"
    SHOW = "show"
    EPISODE = "episode"
    SEASON = "season"
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"


class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    AVAILABLE = "available"
    PROCESSING = "processing"
    UNKNOWN = "unknown"


@dataclass
class CachedMedia:
    """Represents a cached media item from Plex."""

    rating_key: str
    title: str
    year: Optional[int]
    media_type: MediaType
    library: str
    thumb: Optional[str] = None
    summary: Optional[str] = None
    rating: Optional[float] = None
    duration: Optional[int] = None  # milliseconds
    added_at: Optional[datetime] = None
    episode_count: Optional[int] = None  # For shows
    season_count: Optional[int] = None  # For shows

    @property
    def display_title(self) -> str:
        """Return title with year if available."""
        if self.year:
            return f"{self.title} ({self.year})"
        return self.title

    @property
    def type_emoji(self) -> str:
        """Return emoji for media type."""
        emoji_map = {
            MediaType.MOVIE: "🎬",
            MediaType.SHOW: "📺",
            MediaType.EPISODE: "📺",
            MediaType.SEASON: "📺",
            MediaType.ARTIST: "🎤",
            MediaType.ALBUM: "💿",
            MediaType.TRACK: "🎵",
        }
        return emoji_map.get(self.media_type, "📁")

    @property
    def duration_formatted(self) -> Optional[str]:
        """Return formatted duration string."""
        if not self.duration:
            return None
        total_minutes = self.duration // 60000
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


@dataclass
class ActiveStream:
    """Represents an active stream on Plex."""

    session_key: str
    media_title: str
    media_year: Optional[int]
    media_type: MediaType
    thumb: Optional[str]
    progress_percent: float
    progress_time: int  # milliseconds
    duration: int  # milliseconds
    state: str  # playing, paused, buffering
    quality: Optional[str]
    transcode_decision: Optional[str]  # direct play, transcode, copy
    player_name: Optional[str]
    player_device: Optional[str]

    @property
    def progress_bar(self) -> str:
        """Return a visual progress bar."""
        filled = int(self.progress_percent / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty

    @property
    def progress_formatted(self) -> str:
        """Return formatted progress string."""
        current = self._format_time(self.progress_time)
        total = self._format_time(self.duration)
        return f"{current} / {total}"

    @staticmethod
    def _format_time(ms: int) -> str:
        """Format milliseconds to HH:MM:SS or MM:SS."""
        total_seconds = ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def state_emoji(self) -> str:
        """Return emoji for playback state."""
        state_map = {
            "playing": "▶️",
            "paused": "⏸️",
            "buffering": "⏳",
        }
        return state_map.get(self.state.lower(), "▶️")


@dataclass
class PlexClient:
    """Represents a Plex client/player."""

    machine_identifier: str
    name: str
    device: Optional[str] = None
    platform: Optional[str] = None
    product: Optional[str] = None
    state: Optional[str] = None  # idle, playing


@dataclass
class OverseerrRequest:
    """Represents a media request from Overseerr."""

    request_id: int
    media_type: str  # movie, tv
    tmdb_id: int
    title: str
    year: Optional[int]
    status: RequestStatus
    requested_by: str  # Overseerr username
    requested_at: datetime
    poster_path: Optional[str] = None
    overview: Optional[str] = None

    @property
    def poster_url(self) -> Optional[str]:
        """Return full TMDB poster URL."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return None

    @property
    def status_emoji(self) -> str:
        """Return emoji for request status."""
        status_map = {
            RequestStatus.PENDING: "⏳",
            RequestStatus.APPROVED: "✅",
            RequestStatus.DECLINED: "❌",
            RequestStatus.AVAILABLE: "🎉",
            RequestStatus.PROCESSING: "⚙️",
            RequestStatus.UNKNOWN: "❓",
        }
        return status_map.get(self.status, "❓")


@dataclass
class OverseerrSearchResult:
    """Represents a search result from Overseerr/TMDB."""

    media_type: str  # movie, tv
    tmdb_id: int
    title: str
    year: Optional[int]
    poster_path: Optional[str]
    overview: Optional[str]
    vote_average: Optional[float] = None
    already_available: bool = False
    already_requested: bool = False
    request_status: Optional[RequestStatus] = None

    @property
    def poster_url(self) -> Optional[str]:
        """Return full TMDB poster URL."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return None

    @property
    def type_emoji(self) -> str:
        """Return emoji for media type."""
        return "🎬" if self.media_type == "movie" else "📺"


@dataclass
class UserMapping:
    """Maps Discord user to Overseerr/Plex user."""

    discord_id: int
    overseerr_id: Optional[int] = None
    plex_username: Optional[str] = None
    notifications_enabled: bool = True


@dataclass
class ClientAlias:
    """Friendly name for a Plex client."""

    machine_identifier: str
    friendly_name: str
