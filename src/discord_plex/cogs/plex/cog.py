import asyncio
import logging
from typing import cast

import discord
from discord import ApplicationContext, Bot, Embed, Interaction, Member, option
from discord.ext import commands

from ...config.auth import (
    ADMIN_USER_ID,
    CACHE_REFRESH_MINUTES,
    GUILD_IDS,
    OVERSEERR_API_KEY,
    OVERSEERR_URL,
    PLEX_TOKEN,
    PLEX_URL,
)
from . import library as library_commands
from . import requests as request_commands
from .cache import LibraryCache
from .embeds import (
    create_error_embed,
    create_search_result_embed,
    create_success_embed,
)
from .models import OverseerrSearchResult
from .overseerr_client import OverseerrClient
from .plex_client import PlexClientWrapper
from .views import (
    ConfirmView,
    SeasonSelectView,
)

logger = logging.getLogger(__name__)


def is_admin():
    """Check if user is the configured admin."""

    async def predicate(ctx: ApplicationContext) -> bool:
        if ADMIN_USER_ID is None:
            return True  # No admin user configured, allow all
        member = cast(Member, ctx.author)
        return member.id == ADMIN_USER_ID

    return commands.check(predicate)  # type: ignore[arg-type]


class PlexCog(commands.Cog):
    """Discord cog for Plex and Overseerr integration."""

    # Command groups
    plex = discord.SlashCommandGroup("plex", "Plex library commands", guild_ids=GUILD_IDS)
    request = discord.SlashCommandGroup("request", "Media request commands", guild_ids=GUILD_IDS)

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
        await library_commands.plex_search(self, ctx, query, media_type, library)

    @plex.command(name="playing", description="Show currently active streams")
    async def plex_playing(self, ctx: ApplicationContext) -> None:
        """Show all active streams on the Plex server."""
        await library_commands.plex_playing(self, ctx)

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
        await library_commands.plex_recent(self, ctx, library, limit)

    @plex.command(name="stats", description="Show server statistics")
    async def plex_stats(self, ctx: ApplicationContext) -> None:
        """Show Plex server and library statistics."""
        await library_commands.plex_stats(self, ctx)

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
        await request_commands.request_search(self, ctx, query, media_type)

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
        elif result.media_type == "tv":
            # TV show - let user select seasons
            await self._show_season_picker(ctx, result, embed)
        else:
            # Movie - simple confirm
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

    async def _show_season_picker(
        self,
        ctx: ApplicationContext,
        result: OverseerrSearchResult,
        embed: Embed,
    ) -> None:
        """Show season selection for TV shows."""
        # Fetch seasons info from Overseerr
        details = await self.overseerr_client.get_media_details("tv", result.tmdb_id)
        if not details or "seasons" not in details:
            # Fallback: request without seasons (will auto-request all)
            self.logger.warning(
                f"Could not fetch seasons for {result.title}, falling back to auto-request"
            )

            async def on_confirm(interaction: Interaction) -> None:
                await self._create_request(ctx, result)

            view = ConfirmView(
                confirm_callback=on_confirm,
                confirm_label="Request All Seasons",
            )
            await ctx.send_followup(
                embed=embed,
                content="Would you like to request this series?",
                view=view,
            )
            return

        seasons = details.get("seasons", [])

        async def on_seasons_selected(interaction: Interaction, selected: list[int]) -> None:
            await self._create_request(ctx, result, seasons=selected)

        async def on_cancel(interaction: Interaction) -> None:
            await interaction.followup.send("Request cancelled.", ephemeral=True)

        view = SeasonSelectView(
            seasons=seasons,
            confirm_callback=on_seasons_selected,
            cancel_callback=on_cancel,
        )

        await ctx.send_followup(
            embed=embed,
            content="Select which seasons to request:",
            view=view,
        )

    async def _create_request(
        self,
        ctx: ApplicationContext,
        result: OverseerrSearchResult,
        seasons: list[int] | None = None,
    ) -> None:
        """Create a request in Overseerr."""
        seasons_info = f", seasons={seasons}" if seasons else ""
        self.logger.info(
            f"Creating request: {result.title} ({result.year}) "
            f"[tmdb:{result.tmdb_id}, type:{result.media_type}{seasons_info}] by {ctx.author}"
        )
        request = await self.overseerr_client.create_request(
            media_type=result.media_type,
            tmdb_id=result.tmdb_id,
            seasons=seasons,
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

        else:
            self.logger.error(
                f"Failed to create request for {result.title} [tmdb:{result.tmdb_id}]"
            )
            await ctx.send_followup(
                embed=create_error_embed("Failed to submit request. Please try again later.")
            )

    @request.command(name="status", description="View your request status")
    async def request_status(self, ctx: ApplicationContext) -> None:
        """View status of user's requests."""
        await request_commands.request_status(self, ctx)

    @request.command(name="queue", description="View all pending requests (Admin)")
    @is_admin()
    async def request_queue(self, ctx: ApplicationContext) -> None:
        """View all pending requests (admin only)."""
        await request_commands.request_queue(self, ctx)

    @request.command(name="approve", description="Approve a request (Admin)")
    @option("request_id", description="Request ID to approve", required=True)
    @is_admin()
    async def request_approve(
        self,
        ctx: ApplicationContext,
        request_id: int,
    ) -> None:
        """Approve a pending request."""
        await request_commands.request_approve(self, ctx, request_id)

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
        await request_commands.request_deny(self, ctx, request_id, reason)

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

    @plex_search.error  # pyright: ignore[reportFunctionMemberAccess]
    @plex_playing.error  # pyright: ignore[reportFunctionMemberAccess]
    @plex_recent.error  # pyright: ignore[reportFunctionMemberAccess]
    @plex_stats.error  # pyright: ignore[reportFunctionMemberAccess]
    @request_search.error  # pyright: ignore[reportFunctionMemberAccess]
    @request_status.error  # pyright: ignore[reportFunctionMemberAccess]
    @request_queue.error  # pyright: ignore[reportFunctionMemberAccess]
    @request_approve.error  # pyright: ignore[reportFunctionMemberAccess]
    @request_deny.error  # pyright: ignore[reportFunctionMemberAccess]
    async def command_error(self, ctx: ApplicationContext, error: Exception) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CheckFailure):
            await ctx.respond(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True,
            )
        else:
            self.logger.error(f"Command error: {error}", exc_info=True)
            await ctx.respond(
                embed=create_error_embed(f"An error occurred: {str(error)}"),
                ephemeral=True,
            )
