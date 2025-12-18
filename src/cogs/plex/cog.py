import asyncio
import logging
from typing import Optional, cast

import discord
from discord import ApplicationContext, Bot, Embed, Interaction, Member, option
from discord.abc import Messageable
from discord.ext import commands

from config.auth import (
    PLEX_URL,
    PLEX_TOKEN,
    OVERSEERR_URL,
    OVERSEERR_API_KEY,
    GUILD_IDS,
    CACHE_REFRESH_MINUTES,
    ADMIN_ROLE_ID,
    REQUEST_CHANNEL_ID,
)
from .cache import LibraryCache
from .embeds import (
    create_media_embed,
    create_stream_embed,
    create_streams_summary_embed,
    create_recently_added_embed,
    create_request_embed,
    create_search_result_embed,
    create_request_queue_embed,
    create_server_stats_embed,
    create_error_embed,
    create_success_embed,
    PLEX_COLOR,
    OVERSEERR_COLOR,
)
from .models import CachedMedia, MediaType, OverseerrSearchResult
from .overseerr_client import OverseerrClient
from .plex_client import PlexClientWrapper
from .views import (
    MediaSelectView,
    RequestSelectView,
    ConfirmView,
    RequestActionView,
    MediaInfoView,
)


logger = logging.getLogger(__name__)


def is_admin():
    """Check if user has admin role."""

    async def predicate(ctx: ApplicationContext) -> bool:
        if ADMIN_ROLE_ID is None:
            return True  # No admin role configured, allow all
        member = cast(Member, ctx.author)
        if member.guild_permissions.administrator:
            return True
        return any(role.id == ADMIN_ROLE_ID for role in member.roles)

    return commands.check(predicate)  # type: ignore[arg-type]


class PlexCog(commands.Cog):
    """Discord cog for Plex and Overseerr integration."""

    # Command groups
    plex = discord.SlashCommandGroup(
        "plex", "Plex library commands", guild_ids=GUILD_IDS
    )
    request = discord.SlashCommandGroup(
        "request", "Media request commands", guild_ids=GUILD_IDS
    )

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(f"{__name__}.PlexCog")

        # Initialize clients
        self.plex_client = PlexClientWrapper(PLEX_URL, PLEX_TOKEN)
        self.overseerr_client = OverseerrClient(OVERSEERR_URL, OVERSEERR_API_KEY)

        # Initialize cache
        self.cache = LibraryCache(self.plex_client, CACHE_REFRESH_MINUTES)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        self.logger.info("PlexCog is ready")

        # Start background cache refresh
        await self.cache.start_background_refresh()

        # Sync commands
        await self.bot.sync_commands()

    def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        self.cache.stop_background_refresh()
        asyncio.create_task(self.overseerr_client.close())
        self.logger.info("PlexCog unloaded")

    # ==================== Plex Commands ====================

    @plex.command(name="search", description="Search the Plex library")
    @option("query", description="Search query", required=True)
    @option(
        "media_type",
        description="Filter by type",
        required=False,
        choices=["movie", "show", "artist"],
    )
    @option("library", description="Filter by library name", required=False)
    async def plex_search(
        self,
        ctx: ApplicationContext,
        query: str,
        media_type: str = "",
        library: str = "",
    ) -> None:
        """Search the Plex library with fuzzy matching."""
        await ctx.defer()

        # Ensure cache is populated
        if self.cache.is_stale:
            try:
                await self.cache.refresh()
            except Exception as e:
                await ctx.send_followup(
                    embed=create_error_embed(f"Failed to refresh cache: {e}")
                )
                return

        # Convert media type
        type_filter = None
        if media_type:
            type_map = {
                "movie": MediaType.MOVIE,
                "show": MediaType.SHOW,
                "artist": MediaType.ARTIST,
            }
            type_filter = type_map.get(media_type)

        # Search cache with fuzzy matching (limit to 20 for tighter results)
        results = self.cache.search(
            query, limit=20, media_type=type_filter, library=library
        )

        # Also search Plex directly for additional results
        if len(results) < 5:
            loop = asyncio.get_event_loop()
            direct_results = await loop.run_in_executor(
                None,
                lambda: self.plex_client.search(query, limit=10),
            )
            # Merge, avoiding duplicates
            existing_keys = {r.rating_key for r in results}
            for item in direct_results:
                if item.rating_key not in existing_keys:
                    results.append(item)
                    existing_keys.add(item.rating_key)

        if not results:
            await ctx.send_followup(
                embed=create_error_embed(f'No results found for "{query}"')
            )
            return

        # Single result - show details directly
        if len(results) == 1:
            await self._show_media_info(ctx, results[0])
            return

        # Multiple results - show list with select menu
        # Create embed showing results
        embed = Embed(
            title=f'🔍 Search results for "{query}"',
            color=PLEX_COLOR,
        )
        lines = []
        # Limit to 25 for select menu (Discord limit)
        display_results = results[:25]
        for i, media in enumerate(display_results, start=1):
            year_str = f" ({media.year})" if media.year else ""
            lines.append(f"**{i}.** {media.type_emoji} {media.title}{year_str}")
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Found {len(results)} results • Select one below for details")

        # Add select menu for viewing details
        async def on_select(interaction: Interaction, media: CachedMedia) -> None:
            await interaction.response.defer()
            await self._show_media_info(ctx, media, followup=True)

        view = MediaSelectView(
            display_results,
            callback=on_select,
            placeholder="Select media for details...",
        )
        await ctx.send_followup(embed=embed, view=view)

    async def _show_media_info(
        self,
        ctx: ApplicationContext,
        media: CachedMedia,
        followup: bool = False,
    ) -> None:
        """Display detailed media info."""
        # Try to get TMDB poster (publicly accessible) instead of Plex thumbnail
        thumb_url = None
        if media.tmdb_id:
            # Map Plex media type to TMDB media type
            tmdb_type = "movie" if media.media_type == MediaType.MOVIE else "tv"
            thumb_url = await self.overseerr_client.get_poster_url(tmdb_type, media.tmdb_id)
            self.logger.debug(f"TMDB poster URL for {media.title}: {thumb_url}")

        # Fall back to Plex thumbnail if no TMDB poster
        if not thumb_url:
            thumb_url = self.plex_client.get_thumb_url(media.thumb)
            self.logger.debug(f"Using Plex thumb URL: {thumb_url}")

        # Generate Plex web URL
        server_id = self.plex_client.server.machineIdentifier
        plex_web_url = (
            f"https://app.plex.tv/desktop#!/server/{server_id}"
            f"/details?key=%2Flibrary%2Fmetadata%2F{media.rating_key}"
        )

        embed = create_media_embed(media, thumb_url)
        view = MediaInfoView(media, plex_web_url)

        if followup:
            await ctx.send_followup(embed=embed, view=view)
        else:
            await ctx.send_followup(embed=embed, view=view)

    @plex.command(name="playing", description="Show currently active streams")
    async def plex_playing(self, ctx: ApplicationContext) -> None:
        """Show all active streams on the Plex server."""
        await ctx.defer()

        loop = asyncio.get_event_loop()
        streams = await loop.run_in_executor(
            None,
            self.plex_client.get_active_streams,
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

        # Show summary for multiple streams
        if len(streams) > 3:
            embed = create_streams_summary_embed(streams)
            await ctx.send_followup(embed=embed)
        else:
            # Show detailed view for few streams
            embeds = []
            for stream in streams:
                thumb_url = self.plex_client.get_thumb_url(stream.thumb)
                embeds.append(create_stream_embed(stream, thumb_url))
            await ctx.send_followup(embeds=embeds)

    @plex.command(name="recent", description="Show recently added media")
    @option("library", description="Filter by library name", required=False)
    @option(
        "limit",
        description="Number of items (default 10)",
        required=False,
        min_value=1,
        max_value=25,
    )
    async def plex_recent(
        self,
        ctx: ApplicationContext,
        library: str = "",
        limit: int = 10,
    ) -> None:
        """Show recently added media."""
        await ctx.defer()

        # Get from Plex directly for most up-to-date info
        loop = asyncio.get_event_loop()
        recent = await loop.run_in_executor(
            None,
            lambda: self.plex_client.get_recently_added(library, limit),
        )

        embed = create_recently_added_embed(recent, library)
        await ctx.send_followup(embed=embed)

    @plex.command(name="stats", description="Show server statistics")
    async def plex_stats(self, ctx: ApplicationContext) -> None:
        """Show Plex server and library statistics."""
        await ctx.defer()

        loop = asyncio.get_event_loop()
        server_info = await loop.run_in_executor(
            None,
            self.plex_client.get_server_info,
        )
        cache_stats = self.cache.get_stats()

        embed = create_server_stats_embed(server_info, cache_stats)
        await ctx.send_followup(embed=embed)

    # ==================== Request Commands ====================

    @request.command(name="search", description="Search for new media to request")
    @option("query", description="Search query", required=True)
    @option(
        "media_type",
        description="Type of media",
        required=False,
        choices=["movie", "tv"],
    )
    async def request_search(
        self,
        ctx: ApplicationContext,
        query: str,
        media_type: str = "",
    ) -> None:
        """Search Overseerr/TMDB for media to request."""
        await ctx.defer()

        self.logger.info(f"Request search by {ctx.author}: query='{query}', type={media_type or 'any'}")
        results = await self.overseerr_client.search(query)

        # Filter by type if specified
        if media_type:
            results = [r for r in results if r.media_type == media_type]

        if not results:
            await ctx.send_followup(
                embed=create_error_embed(f'No results found for "{query}"')
            )
            return

        # Show results with select menu
        async def on_select(
            interaction: Interaction, result: OverseerrSearchResult
        ) -> None:
            await interaction.response.defer()
            await self._handle_request_selection(ctx, result)

        view = RequestSelectView(
            results[:10],
            callback=on_select,
            placeholder="Select media to view/request...",
        )

        # Create results embed
        embed = Embed(
            title=f'🔍 Search results for "{query}"',
            color=OVERSEERR_COLOR,
        )
        lines = []
        for i, result in enumerate(results[:10], start=1):
            year_str = f" ({result.year})" if result.year else ""
            status = ""
            if result.already_available:
                status = " ✅"
            elif result.already_requested:
                status = " 📋"
            lines.append(
                f"**{i}.** {result.type_emoji} {result.title}{year_str}{status}"
            )

        embed.description = "\n".join(lines)
        embed.set_footer(text="✅ = Available | 📋 = Requested")

        await ctx.send_followup(embed=embed, view=view)

    async def _handle_request_selection(
        self,
        ctx: ApplicationContext,
        result: OverseerrSearchResult,
    ) -> None:
        """Handle when user selects a search result."""
        self.logger.info(
            f"User {ctx.author} selected: {result.title} ({result.year}) "
            f"[tmdb:{result.tmdb_id}, type:{result.media_type}]"
        )
        embed = create_search_result_embed(result)

        if result.already_available:
            # Already in Plex - offer to search library
            await ctx.send_followup(
                embed=embed,
                content="This title is already available in Plex! Use `/plex search` to find it.",
            )
        elif result.already_requested:
            # Already requested
            await ctx.send_followup(
                embed=embed,
                content="This title has already been requested.",
            )
        else:
            # Offer to request
            async def on_confirm(interaction: Interaction) -> None:
                await self._create_request(ctx, result)

            async def on_cancel(interaction: Interaction) -> None:
                await interaction.followup.send("Request cancelled.", ephemeral=True)

            view = ConfirmView(
                confirm_callback=on_confirm,
                cancel_callback=on_cancel,
                confirm_label="Request",
            )

            await ctx.send_followup(
                embed=embed,
                content="Would you like to request this title?",
                view=view,
            )

    async def _create_request(
        self,
        ctx: ApplicationContext,
        result: OverseerrSearchResult,
    ) -> None:
        """Create a request in Overseerr."""
        self.logger.info(
            f"Creating request: {result.title} ({result.year}) "
            f"[tmdb:{result.tmdb_id}, type:{result.media_type}] by {ctx.author}"
        )
        request = await self.overseerr_client.create_request(
            media_type=result.media_type,
            tmdb_id=result.tmdb_id,
        )

        if request:
            self.logger.info(
                f"Request created successfully: {result.title} "
                f"[request_id:{request.request_id}, status:{request.status.value}]"
            )
            embed = create_success_embed(
                f"**{result.title}** has been requested!\n\n"
                f"You'll be notified when it's available.",
                title="Request Submitted",
            )
            await ctx.send_followup(embed=embed)

            # Notify admin channel if configured
            if REQUEST_CHANNEL_ID:
                channel = self.bot.get_channel(REQUEST_CHANNEL_ID)
                if channel and isinstance(channel, Messageable):
                    admin_embed = create_request_embed(request)
                    admin_embed.title = f"📥 New Request: {result.title}"

                    view = RequestActionView(
                        request.request_id,
                        approve_callback=self._approve_request,
                        deny_callback=self._deny_request,
                    )

                    await channel.send(
                        content=f"Requested by {ctx.author.mention}",
                        embed=admin_embed,
                        view=view,
                    )
        else:
            self.logger.error(f"Failed to create request for {result.title} [tmdb:{result.tmdb_id}]")
            await ctx.send_followup(
                embed=create_error_embed(
                    "Failed to submit request. Please try again later."
                )
            )

    @request.command(name="status", description="View your request status")
    async def request_status(self, ctx: ApplicationContext) -> None:
        """View status of user's requests."""
        await ctx.defer()

        # Get all requests - filter client-side
        # Note: Proper user mapping would require storing Discord->Overseerr ID mapping
        requests = await self.overseerr_client.get_user_requests()

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

    @request.command(name="queue", description="View all pending requests (Admin)")
    @is_admin()
    async def request_queue(self, ctx: ApplicationContext) -> None:
        """View all pending requests (admin only)."""
        await ctx.defer()

        requests = await self.overseerr_client.get_pending_requests()

        embed = create_request_queue_embed(requests)
        await ctx.send_followup(embed=embed)

    @request.command(name="approve", description="Approve a request (Admin)")
    @option("request_id", description="Request ID to approve", required=True)
    @is_admin()
    async def request_approve(
        self,
        ctx: ApplicationContext,
        request_id: int,
    ) -> None:
        """Approve a pending request."""
        await ctx.defer()
        await self._approve_request_by_id(ctx, request_id)

    @request.command(name="deny", description="Deny a request (Admin)")
    @option("request_id", description="Request ID to deny", required=True)
    @option("reason", description="Reason for denial", required=False)
    @is_admin()
    async def request_deny(
        self,
        ctx: ApplicationContext,
        request_id: int,
        reason: str = "",
    ) -> None:
        """Deny a pending request."""
        await ctx.defer()
        await self._deny_request_by_id(ctx, request_id, reason)

    async def _approve_request(self, interaction: Interaction, request_id: int) -> None:
        """Callback for approve button."""
        self.logger.info(f"Approving request #{request_id} by {interaction.user}")
        success = await self.overseerr_client.approve_request(request_id)
        if success:
            self.logger.info(f"Request #{request_id} approved successfully")
            await interaction.followup.send(
                embed=create_success_embed(f"Request #{request_id} has been approved!")
            )
        else:
            self.logger.error(f"Failed to approve request #{request_id}")
            await interaction.followup.send(
                embed=create_error_embed(f"Failed to approve request #{request_id}")
            )

    async def _deny_request(self, interaction: Interaction, request_id: int) -> None:
        """Callback for deny button."""
        self.logger.info(f"Denying request #{request_id} by {interaction.user}")
        success = await self.overseerr_client.decline_request(request_id)
        if success:
            self.logger.info(f"Request #{request_id} denied successfully")
            await interaction.followup.send(
                embed=create_success_embed(f"Request #{request_id} has been denied.")
            )
        else:
            self.logger.error(f"Failed to deny request #{request_id}")
            await interaction.followup.send(
                embed=create_error_embed(f"Failed to deny request #{request_id}")
            )

    async def _approve_request_by_id(
        self,
        ctx: ApplicationContext,
        request_id: int,
    ) -> None:
        """Approve request by ID."""
        success = await self.overseerr_client.approve_request(request_id)
        if success:
            await ctx.send_followup(
                embed=create_success_embed(f"Request #{request_id} has been approved!")
            )
        else:
            await ctx.send_followup(
                embed=create_error_embed(
                    f"Failed to approve request #{request_id}. It may not exist or already be processed."
                )
            )

    async def _deny_request_by_id(
        self,
        ctx: ApplicationContext,
        request_id: int,
        reason: str = "",
    ) -> None:
        """Deny request by ID."""
        success = await self.overseerr_client.decline_request(request_id)
        if success:
            msg = f"Request #{request_id} has been denied."
            if reason:
                msg += f"\nReason: {reason}"
            await ctx.send_followup(embed=create_success_embed(msg))
        else:
            await ctx.send_followup(
                embed=create_error_embed(
                    f"Failed to deny request #{request_id}. It may not exist or already be processed."
                )
            )

    # ==================== Error Handlers ====================

    @plex_search.error
    @plex_playing.error
    @plex_recent.error
    @plex_stats.error
    @request_search.error
    @request_status.error
    @request_queue.error
    @request_approve.error
    @request_deny.error
    async def command_error(self, ctx: ApplicationContext, error: Exception) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CheckFailure):
            await ctx.respond(
                embed=create_error_embed(
                    "You don't have permission to use this command."
                ),
                ephemeral=True,
            )
        else:
            self.logger.error(f"Command error: {error}", exc_info=True)
            await ctx.respond(
                embed=create_error_embed(f"An error occurred: {str(error)}"),
                ephemeral=True,
            )
