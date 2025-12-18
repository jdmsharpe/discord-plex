from datetime import datetime
from typing import Optional

from discord import Colour, Embed

from .models import (
    CachedMedia,
    ActiveStream,
    OverseerrRequest,
    OverseerrSearchResult,
    RequestStatus,
)


# Plex orange color
PLEX_COLOR = Colour.from_rgb(229, 160, 13)
OVERSEERR_COLOR = Colour.from_rgb(92, 107, 192)
SUCCESS_COLOR = Colour.green()
ERROR_COLOR = Colour.red()


def truncate(text: str, max_length: int = 4096) -> str:
    """Truncate text with ellipsis if exceeds max_length (Discord embed description limit is 4096)."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def create_media_embed(
    media: CachedMedia,
    thumb_url: Optional[str] = None,
) -> Embed:
    """Create a detailed embed for a media item."""
    embed = Embed(
        title=f"{media.type_emoji} {media.display_title}",
        color=PLEX_COLOR,
    )

    # Description/Summary - use full Discord limit (4096 chars)
    if media.summary:
        embed.description = truncate(media.summary)

    # Thumbnail
    if thumb_url:
        embed.set_thumbnail(url=thumb_url)

    # Type and Library
    embed.add_field(
        name="Type",
        value=media.media_type.value.title(),
        inline=True,
    )
    embed.add_field(
        name="Library",
        value=media.library,
        inline=True,
    )

    # Duration or Episode count
    if media.duration_formatted:
        embed.add_field(
            name="Duration",
            value=media.duration_formatted,
            inline=True,
        )
    elif media.episode_count:
        seasons = f"{media.season_count} seasons, " if media.season_count else ""
        embed.add_field(
            name="Episodes",
            value=f"{seasons}{media.episode_count} episodes",
            inline=True,
        )

    # Rating
    if media.rating:
        embed.add_field(
            name="Rating",
            value=f"⭐ {media.rating:.1f}",
            inline=True,
        )

    # Footer with rating key for reference
    embed.set_footer(text=f"ID: {media.rating_key}")

    return embed


def create_search_results_embed(
    results: list[CachedMedia],
    query: str,
    page: int = 1,
    per_page: int = 10,
) -> Embed:
    """Create an embed for search results list."""
    total_pages = (len(results) + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(results))
    page_results = results[start_idx:end_idx]

    embed = Embed(
        title=f'🔍 Search results for "{query}"',
        color=PLEX_COLOR,
    )

    if not page_results:
        embed.description = "No results found."
        return embed

    lines = []
    for i, media in enumerate(page_results, start=start_idx + 1):
        year_str = f" ({media.year})" if media.year else ""
        lines.append(f"**{i}.** {media.type_emoji} {media.title}{year_str}")

    embed.description = "\n".join(lines)
    embed.set_footer(
        text=f"Page {page} of {total_pages} • Use /plex info <title> for details"
    )

    return embed


def create_stream_embed(stream: ActiveStream, thumb_url: Optional[str] = None) -> Embed:
    """Create an embed for an active stream."""
    year_str = f" ({stream.media_year})" if stream.media_year else ""

    embed = Embed(
        title=f"{stream.state_emoji} Now Playing",
        description=f"**{stream.media_title}**{year_str}",
        color=PLEX_COLOR,
    )

    if thumb_url:
        embed.set_thumbnail(url=thumb_url)

    # Progress bar and time
    embed.add_field(
        name="Progress",
        value=f"{stream.progress_bar} {stream.progress_percent:.0f}%\n{stream.progress_formatted}",
        inline=False,
    )

    # Quality and transcode info
    quality_info = []
    if stream.quality:
        quality_info.append(f"Quality: {stream.quality}")
    if stream.transcode_decision:
        quality_info.append(stream.transcode_decision)
    if quality_info:
        embed.add_field(
            name="Stream Info",
            value="\n".join(quality_info),
            inline=True,
        )

    # Player info
    if stream.player_name:
        player_info = stream.player_name
        if stream.player_device:
            player_info += f" ({stream.player_device})"
        embed.add_field(
            name="Player",
            value=player_info,
            inline=True,
        )

    return embed


def create_streams_summary_embed(streams: list[ActiveStream]) -> Embed:
    """Create a summary embed for multiple streams."""
    embed = Embed(
        title="📺 Active Streams",
        color=PLEX_COLOR,
    )

    if not streams:
        embed.description = "No active streams."
        return embed

    embed.description = f"{len(streams)} active stream(s)"

    for stream in streams[:10]:  # Limit to 10 streams
        year_str = f" ({stream.media_year})" if stream.media_year else ""
        value = (
            f"{stream.progress_bar} {stream.progress_percent:.0f}%\n"
            f"{stream.transcode_decision or 'Unknown'}"
        )
        embed.add_field(
            name=f"{stream.state_emoji} {stream.media_title}{year_str}",
            value=value,
            inline=True,
        )

    return embed


def create_recently_added_embed(
    media: list[CachedMedia],
    library: Optional[str] = None,
) -> Embed:
    """Create an embed for recently added media."""
    title = "📥 Recently Added"
    if library:
        title += f" to {library}"

    embed = Embed(title=title, color=PLEX_COLOR)

    if not media:
        embed.description = "No recent additions found."
        return embed

    lines = []
    for item in media[:15]:
        year_str = f" ({item.year})" if item.year else ""
        added = ""
        if item.added_at:
            days_ago = (datetime.now() - item.added_at).days
            if days_ago == 0:
                added = " • Today"
            elif days_ago == 1:
                added = " • Yesterday"
            else:
                added = f" • {days_ago}d ago"
        lines.append(f"{item.type_emoji} **{item.title}**{year_str}{added}")

    embed.description = "\n".join(lines)
    return embed


def create_request_embed(request: OverseerrRequest) -> Embed:
    """Create an embed for a media request."""
    year_str = f" ({request.year})" if request.year else ""
    type_emoji = "🎬" if request.media_type == "movie" else "📺"

    embed = Embed(
        title=f"{type_emoji} {request.title}{year_str}",
        color=OVERSEERR_COLOR,
    )

    if request.poster_url:
        embed.set_thumbnail(url=request.poster_url)

    if request.overview:
        embed.description = truncate(request.overview)

    embed.add_field(
        name="Status",
        value=f"{request.status_emoji} {request.status.value.title()}",
        inline=True,
    )
    embed.add_field(
        name="Requested By",
        value=request.requested_by,
        inline=True,
    )
    embed.add_field(
        name="Requested",
        value=request.requested_at.strftime("%Y-%m-%d %H:%M"),
        inline=True,
    )

    embed.set_footer(text=f"Request ID: {request.request_id}")

    return embed


def create_search_result_embed(result: OverseerrSearchResult) -> Embed:
    """Create an embed for an Overseerr search result."""
    year_str = f" ({result.year})" if result.year else ""

    embed = Embed(
        title=f"{result.type_emoji} {result.title}{year_str}",
        color=OVERSEERR_COLOR,
    )

    if result.poster_url:
        embed.set_thumbnail(url=result.poster_url)

    if result.overview:
        embed.description = truncate(result.overview)

    if result.vote_average:
        embed.add_field(
            name="Rating",
            value=f"⭐ {result.vote_average:.1f}/10",
            inline=True,
        )

    # Status indicator
    if result.already_available:
        status = "✅ Available in Plex"
    elif result.already_requested:
        status_text = (
            result.request_status.value.title()
            if result.request_status
            else "Requested"
        )
        status = f"📋 {status_text}"
    else:
        status = "➕ Available to Request"

    embed.add_field(
        name="Status",
        value=status,
        inline=True,
    )

    embed.set_footer(text=f"TMDB ID: {result.tmdb_id}")

    return embed


def create_request_queue_embed(requests: list[OverseerrRequest]) -> Embed:
    """Create an embed for the request queue."""
    embed = Embed(
        title="📋 Request Queue",
        color=OVERSEERR_COLOR,
    )

    if not requests:
        embed.description = "No pending requests."
        return embed

    lines = []
    for req in requests[:15]:
        type_emoji = "🎬" if req.media_type == "movie" else "📺"
        year_str = f" ({req.year})" if req.year else ""
        lines.append(
            f"{req.status_emoji} **{req.request_id}** | {type_emoji} {req.title}{year_str}\n"
            f"   └─ By: {req.requested_by}"
        )

    embed.description = "\n".join(lines)
    embed.set_footer(text="Use /request approve <id> or /request deny <id>")

    return embed


def create_server_stats_embed(
    server_info: dict,
    cache_stats: dict,
) -> Embed:
    """Create an embed for server statistics."""
    embed = Embed(
        title="📊 Server Statistics",
        color=PLEX_COLOR,
    )

    # Server info
    if server_info:
        embed.add_field(
            name="Server",
            value=(
                f"**{server_info.get('name', 'Unknown')}**\n"
                f"Version: {server_info.get('version', 'Unknown')}\n"
                f"Platform: {server_info.get('platform', 'Unknown')}"
            ),
            inline=True,
        )

        embed.add_field(
            name="Activity",
            value=(
                f"Streams: {server_info.get('streams', 0)}\n"
                f"Transcodes: {server_info.get('transcodes', 0)}"
            ),
            inline=True,
        )

    # Library stats
    if cache_stats:
        by_type = cache_stats.get("by_type", {})
        type_lines = [f"{t.title()}: {c}" for t, c in sorted(by_type.items())]
        embed.add_field(
            name="Library",
            value="\n".join(type_lines) or "No data",
            inline=True,
        )

        by_library = cache_stats.get("by_library", {})
        library_lines = [f"{lib}: {count}" for lib, count in sorted(by_library.items())]
        embed.add_field(
            name="By Section",
            value="\n".join(library_lines[:5]) or "No data",  # Limit to 5
            inline=True,
        )

    return embed


def create_error_embed(message: str, title: str = "Error") -> Embed:
    """Create an error embed."""
    return Embed(
        title=f"❌ {title}",
        description=message,
        color=ERROR_COLOR,
    )


def create_success_embed(message: str, title: str = "Success") -> Embed:
    """Create a success embed."""
    return Embed(
        title=f"✅ {title}",
        description=message,
        color=SUCCESS_COLOR,
    )
