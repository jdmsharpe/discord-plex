from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from discord import ApplicationContext, Embed, Interaction

from .embeds import (
    PLEX_COLOR,
    create_error_embed,
    create_media_embed,
    create_recently_added_embed,
    create_server_stats_embed,
    create_stream_embed,
    create_streams_summary_embed,
)
from .models import CachedMedia, MediaType
from .views import MediaInfoView, MediaSelectView

if TYPE_CHECKING:
    from .cog import PlexCog


async def plex_search(
    cog: PlexCog,
    ctx: ApplicationContext,
    query: str,
    media_type: str = "",
    library: str = "",
) -> None:
    """Search the Plex library with fuzzy matching."""
    await ctx.defer()

    if cog.cache.is_stale:
        try:
            await cog.cache.refresh()
        except Exception as exc:
            await ctx.send_followup(embed=create_error_embed(f"Failed to refresh cache: {exc}"))
            return

    type_filter = None
    if media_type:
        type_map = {
            "movie": MediaType.MOVIE,
            "show": MediaType.SHOW,
            "artist": MediaType.ARTIST,
        }
        type_filter = type_map.get(media_type)

    results = cog.cache.search(query, limit=20, media_type=type_filter, library=library)

    if len(results) < 5:
        loop = asyncio.get_running_loop()
        direct_results = await loop.run_in_executor(
            None,
            lambda: cog.plex_client.search(query, limit=10),
        )
        existing_keys = {result.rating_key for result in results}
        for item in direct_results:
            if item.rating_key not in existing_keys:
                results.append(item)
                existing_keys.add(item.rating_key)

    if not results:
        await ctx.send_followup(embed=create_error_embed(f'No results found for "{query}"'))
        return

    if len(results) == 1:
        await show_media_info(cog, ctx, results[0])
        return

    embed = Embed(
        title=f'🔍 Search results for "{query}"',
        color=PLEX_COLOR,
    )
    lines = []
    display_results = results[:25]
    for index, media in enumerate(display_results, start=1):
        year_str = f" ({media.year})" if media.year else ""
        lines.append(f"**{index}.** {media.type_emoji} {media.title}{year_str}")
    embed.description = "\n".join(lines)
    embed.set_footer(text=f"Found {len(results)} results • Select one below for details")

    async def on_select(interaction: Interaction, media: CachedMedia) -> None:
        await interaction.response.defer()
        await show_media_info(cog, ctx, media)

    view = MediaSelectView(
        display_results,
        callback=on_select,
        placeholder="Select media for details...",
    )
    await ctx.send_followup(embed=embed, view=view)


async def show_media_info(
    cog: PlexCog,
    ctx: ApplicationContext,
    media: CachedMedia,
) -> None:
    """Display detailed media info."""
    thumb_url = None
    if media.tmdb_id:
        tmdb_type = "movie" if media.media_type == MediaType.MOVIE else "tv"
        thumb_url = await cog.overseerr_client.get_poster_url(tmdb_type, media.tmdb_id)
        cog.logger.debug("TMDB poster URL for %s: %s", media.title, thumb_url)

    if not thumb_url:
        thumb_url = cog.plex_client.get_thumb_url(media.thumb)
        cog.logger.debug("Using Plex thumb URL: %s", thumb_url)

    server_id = cog.plex_client.server.machineIdentifier
    plex_web_url = (
        f"https://app.plex.tv/desktop#!/server/{server_id}"
        f"/details?key=%2Flibrary%2Fmetadata%2F{media.rating_key}"
    )

    embed = create_media_embed(media, thumb_url)
    view = MediaInfoView(media, plex_web_url)

    await ctx.send_followup(embed=embed, view=view)


async def plex_playing(cog: PlexCog, ctx: ApplicationContext) -> None:
    """Show all active streams on the Plex server."""
    await ctx.defer()

    loop = asyncio.get_running_loop()
    streams = await loop.run_in_executor(
        None,
        cog.plex_client.get_active_streams,
    )

    if not streams:
        await ctx.send_followup(
            embed=Embed(
                title="📺 Active Streams",
                description="No active streams.",
                color=PLEX_COLOR,
            )
        )
        return

    if len(streams) > 3:
        await ctx.send_followup(embed=create_streams_summary_embed(streams))
        return

    embeds = []
    for stream in streams:
        thumb_url = cog.plex_client.get_thumb_url(stream.thumb)
        embeds.append(create_stream_embed(stream, thumb_url))
    await ctx.send_followup(embeds=embeds)


async def plex_recent(
    cog: PlexCog,
    ctx: ApplicationContext,
    library: str = "",
    limit: int = 10,
) -> None:
    """Show recently added media."""
    await ctx.defer()

    loop = asyncio.get_running_loop()
    recent = await loop.run_in_executor(
        None,
        lambda: cog.plex_client.get_recently_added(library, limit),
    )

    embed = create_recently_added_embed(recent, library)
    await ctx.send_followup(embed=embed)


async def plex_stats(cog: PlexCog, ctx: ApplicationContext) -> None:
    """Show Plex server and library statistics."""
    await ctx.defer()

    loop = asyncio.get_running_loop()
    server_info = await loop.run_in_executor(
        None,
        cog.plex_client.get_server_info,
    )
    cache_stats = cog.cache.get_stats()

    embed = create_server_stats_embed(server_info, cache_stats)
    await ctx.send_followup(embed=embed)
