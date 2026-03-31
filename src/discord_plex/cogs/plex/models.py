from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
    year: int | None
    media_type: MediaType
    library: str
    thumb: str | None = None
    summary: str | None = None
    rating: float | None = None
    duration: int | None = None  # milliseconds
    added_at: datetime | None = None
    episode_count: int | None = None  # For shows
    season_count: int | None = None  # For shows
    tmdb_id: int | None = None  # TMDB ID for poster lookup
    imdb_id: str | None = None  # IMDB ID (tt1234567 format)

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
    def duration_formatted(self) -> str | None:
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
    media_year: int | None
    media_type: MediaType
    thumb: str | None
    progress_percent: float
    progress_time: int  # milliseconds
    duration: int  # milliseconds
    state: str  # playing, paused, buffering
    quality: str | None
    transcode_decision: str | None  # direct play, transcode, copy
    player_name: str | None
    player_device: str | None

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
    device: str | None = None
    platform: str | None = None
    product: str | None = None
    state: str | None = None  # idle, playing


@dataclass
class OverseerrRequest:
    """Represents a media request from Overseerr."""

    request_id: int
    media_type: str  # movie, tv
    tmdb_id: int
    title: str
    year: int | None
    status: RequestStatus
    requested_by: str  # Overseerr username
    requested_at: datetime
    poster_path: str | None = None
    overview: str | None = None

    @property
    def poster_url(self) -> str | None:
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
    year: int | None
    poster_path: str | None
    overview: str | None
    vote_average: float | None = None
    already_available: bool = False
    already_requested: bool = False
    request_status: RequestStatus | None = None

    @property
    def poster_url(self) -> str | None:
        """Return full TMDB poster URL."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return None

    @property
    def type_emoji(self) -> str:
        """Return emoji for media type."""
        return "🎬" if self.media_type == "movie" else "📺"
