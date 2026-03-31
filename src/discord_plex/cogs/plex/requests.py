from __future__ import annotations

from typing import TYPE_CHECKING

from discord import ApplicationContext, Embed, Interaction

from .embeds import OVERSEERR_COLOR, create_error_embed, create_request_queue_embed
from .models import OverseerrSearchResult
from .views import RequestSelectView

if TYPE_CHECKING:
    from .cog import PlexCog


async def request_search(
    cog: PlexCog,
    ctx: ApplicationContext,
    query: str,
    media_type: str = "",
) -> None:
    """Search Overseerr/TMDB for media to request."""
    await ctx.defer()

    cog.logger.info(
        "Request search by %s: query='%s', type=%s",
        ctx.author,
        query,
        media_type or "any",
    )
    results = await cog.overseerr_client.search(query)

    if media_type:
        results = [result for result in results if result.media_type == media_type]

    if not results:
        await ctx.send_followup(embed=create_error_embed(f'No results found for "{query}"'))
        return

    async def on_select(interaction: Interaction, result: OverseerrSearchResult) -> None:
        await interaction.response.defer()
        await cog._handle_request_selection(ctx, result)

    view = RequestSelectView(
        results[:10],
        callback=on_select,
        placeholder="Select media to view/request...",
    )

    embed = Embed(
        title=f'🔍 Search results for "{query}"',
        color=OVERSEERR_COLOR,
    )
    lines = []
    for index, result in enumerate(results[:10], start=1):
        year_str = f" ({result.year})" if result.year else ""
        status = ""
        if result.already_available:
            status = " ✅"
        elif result.already_requested:
            status = " 📋"
        lines.append(f"**{index}.** {result.type_emoji} {result.title}{year_str}{status}")

    embed.description = "\n".join(lines)
    embed.set_footer(text="✅ = Available | 📋 = Requested")

    await ctx.send_followup(embed=embed, view=view)


async def request_status(cog: PlexCog, ctx: ApplicationContext) -> None:
    """View status of the user's requests."""
    await ctx.defer()

    requests = await cog.overseerr_client.get_user_requests()

    if not requests:
        await ctx.send_followup(
            embed=Embed(
                title="📋 Your Requests",
                description="No requests found.",
                color=OVERSEERR_COLOR,
            )
        )
        return

    embed = create_request_queue_embed(requests[:15])
    embed.title = "📋 Your Requests"
    await ctx.send_followup(embed=embed)


async def request_queue(cog: PlexCog, ctx: ApplicationContext) -> None:
    """View all pending requests."""
    await ctx.defer()
    requests = await cog.overseerr_client.get_pending_requests()
    embed = create_request_queue_embed(requests)
    await ctx.send_followup(embed=embed)


async def request_approve(
    cog: PlexCog,
    ctx: ApplicationContext,
    request_id: int,
) -> None:
    """Approve a pending request."""
    await ctx.defer()
    await cog._approve_request_by_id(ctx, request_id)


async def request_deny(
    cog: PlexCog,
    ctx: ApplicationContext,
    request_id: int,
    reason: str = "",
) -> None:
    """Deny a pending request."""
    await ctx.defer()
    await cog._deny_request_by_id(ctx, request_id, reason)
